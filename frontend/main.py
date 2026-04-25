import streamlit as st
import leafmap.foliumap as leafmap
import folium
import json
from datetime import date, timedelta
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from folium.plugins import SideBySideLayers
from streamlit_folium import st_folium
import geopandas as gpd

# URL del GeoJSON
geojson_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/spain-provinces.geojson"

@st.cache_data
def get_provinces():
    return gpd.read_file(geojson_url)

# Cargar y filtrar provincias
gdf = get_provinces()

# Lista corregida para coincidir con el GeoJSON (tildes y nombres oficiales)
lista_provincias = [
    "Pontevedra", "Lugo", "Cantabria", "Bizkaia", "Ávila", "Segovia", 
    "Guadalajara", "Zaragoza", "Teruel", "Tarragona", "Lleida", 
    "Barcelona", "Girona", "Almería", "Jaén", "Albacete", "Murcia"
]

# Filtramos el GDF original
gdf_filtrado = gdf[gdf['name'].isin(lista_provincias)]

mitad = len(gdf_filtrado) // 2
gdf_grupo_a = gdf_filtrado.iloc[:mitad]
gdf_grupo_b = gdf_filtrado.iloc[mitad:]

st.set_page_config(page_title="Demeter's Oracle", layout="wide")

# no se que es un markdown
st.markdown(
	"""
	<style>
		.block-container {
			padding-top: 1rem;
			padding-bottom: 1rem;
			padding-left: 1rem;
			padding-right: 1rem;
			max-width: 100%;
		}
	</style>
	""",
	unsafe_allow_html=True,
)

# titulo de la pagina web y caption
st.title("Demeter's Oracle")
# st.caption("Interactive drought map with Leafmap + Streamlit")

# Columnas para el mapa y la información lateral
center_col, right_col = st.columns([5.8, 2.4], gap="medium")

# Columna del mapa con el buscador
with center_col:
	# Busqueda de ubicacion
	with st.form("location_search_form", clear_on_submit=False):
		# columnas para el buscador y el boton
		search_col, search_button_col = st.columns([8, 1], gap="small")
		# input de busqueda
		with search_col:
			location_query = st.text_input(
				"Search bar",
				value=st.session_state.get("location_query", ""),
				placeholder="Barcelona, Spain",
				label_visibility="collapsed",
			)
		# boton de busqueda
		with search_button_col:
			search_clicked = st.form_submit_button("Buscar")
# Guardamos la consulta en session_state para mantenerla entre interacciones
st.session_state["location_query"] = location_query

# Datos estaticos de ejemplo con diferencia entre la actualidad (monitoreo)
# y el futuro (prediccion)
STATIC_DATA = {
	"Actual": {
		"Madrid Centro": {
			"bbox": ((40.30, -3.90), (40.55, -3.50)),
			"score": 0.28,
		},
		"Sevilla": {
			"bbox": ((37.25, -6.15), (37.55, -5.75)),
			"score": 0.62,
		},
		"Valencia": {
			"bbox": ((39.30, -0.55), (39.60, -0.20)),
			"score": 0.41,
		},
	},
	"Futuro": {
		"Madrid Centro": {
			"bbox": ((40.30, -3.90), (40.55, -3.50)),
			"score": 0.54,
		},
		"Sevilla": {
			"bbox": ((37.25, -6.15), (37.55, -5.75)),
			"score": 0.78,
		},
		"Valencia": {
			"bbox": ((39.30, -0.55), (39.60, -0.20)),
			"score": 0.66,
		},
	},
}

#
def score_to_color(score: float) -> str:
	# Gradiente simple: verde (0.0) -> rojo (1.0)
	s = max(0.0, min(1.0, score))
	r = int(255 * s)
	g = int(170 * (1 - s))
	b = int(70 * (1 - s))
	return f"#{r:02x}{g:02x}{b:02x}"


def bbox_center(sw: tuple[float, float], ne: tuple[float, float]) -> tuple[float, float]:
	return ((sw[0] + ne[0]) / 2, (sw[1] + ne[1]) / 2)


def point_in_bbox(lat: float, lon: float, bbox: tuple[tuple[float, float], tuple[float, float]]) -> bool:
	(sw_lat, sw_lon), (ne_lat, ne_lon) = bbox
	return sw_lat <= lat <= ne_lat and sw_lon <= lon <= ne_lon


def find_clicked_zone(lat: float, lon: float, area_items: dict):
	for area_name, area_data in area_items.items():
		if point_in_bbox(lat, lon, area_data["bbox"]):
			return area_name
	return None


def geocode_location(query: str):
	url = (
		"https://nominatim.openstreetmap.org/search"
		f"?q={quote_plus(query)}&format=json&limit=1"
	)
	request = Request(url, headers={"User-Agent": "flash-drought-app-streamlit"})
	try:
		with urlopen(request, timeout=8) as response:
			payload = json.loads(response.read().decode("utf-8"))
		if not payload:
			return None, None, None, "No se encontro la ubicacion."
		lat = float(payload[0]["lat"])
		lon = float(payload[0]["lon"])
		name = payload[0].get("display_name", query)
		return lat, lon, name, None
	except Exception:
		return None, None, None, "Error al buscar la ubicacion."

with st.sidebar:
	st.title(":material/filter_alt: Filtros")
	page_view = st.radio("Pagina", ["Monitoreo", "Prediccion"], horizontal=True)
	data_mode = "Actual" if page_view == "Monitoreo" else "Futuro"

	if page_view == "Prediccion":
		next_prediction_date = st.date_input(
			"Fecha de siguiente prediccion",
			value=date.today() + timedelta(days=7),
			min_value=date.today(),
		)
	else:
		next_prediction_date = None
	percentage_filter = st.slider(
		"Filtrar por porcentaje de sequia",
		min_value=0,
		max_value=100,
		value=(0, 100),
		step=1,
	)

	min_percentage, max_percentage = percentage_filter
	filtered_area_items = {
		area_name: area_data
		for area_name, area_data in STATIC_DATA[data_mode].items()
		if min_percentage <= (area_data["score"] * 100) <= max_percentage
	}

	if not filtered_area_items:
		st.warning("No hay zonas para ese rango. Se muestran todas.")
		filtered_area_items = STATIC_DATA[data_mode]

	selected_area = st.selectbox("Zona", list(filtered_area_items.keys()), index=0)
	default_bbox = filtered_area_items[selected_area]["bbox"]
	flash_drought_score = float(filtered_area_items[selected_area]["score"])

	if page_view == "Monitoreo":
		left_split = st.selectbox(
			"Split izquierda (actual)",
			["OpenStreetMap", "CartoDB.Positron", "OpenTopoMap"],
			index=0,
		)
		right_split = st.selectbox(
			"Split derecha (comparacion)",
			["Esri.WorldImagery", "CartoDB.DarkMatter", "OpenStreetMap"],
			index=0,
		)
		basemap = None
		st.caption("Modo Monitoreo: mapa dividido integrado (swipe).")
	else:
		basemap = st.selectbox(
			"Basemap",
			["OpenStreetMap", "Esri.WorldImagery", "CartoDB.Positron", "HYBRID"],
			index=0,
		)
	zoom = st.slider("Zoom", min_value=2, max_value=18, value=6)
	st.caption(
		f"Zonas visibles: {len(filtered_area_items)} de {len(STATIC_DATA[data_mode])}"
	)


sw, ne = default_bbox
error_msg = None

center_lat, center_lon = bbox_center(sw, ne)

if search_clicked:
	if location_query.strip():
		lat_search, lon_search, place_name, search_error = geocode_location(location_query.strip())
		if search_error:
			with right_col:
				st.warning(search_error)
		else:
			st.session_state["searched_location"] = {
				"lat": lat_search,
				"lon": lon_search,
				"name": place_name,
			}
	else:
		with right_col:
			st.info("Escribe una ubicacion para buscar.")

searched_location = st.session_state.get("searched_location")
if searched_location:
	center_lat = searched_location["lat"]
	center_lon = searched_location["lon"]

if "clicked_zone" not in st.session_state:
	st.session_state["clicked_zone"] = None

if page_view == "Monitoreo":
	m = folium.Map(location=(center_lat, center_lon), zoom_start=zoom, control_scale=True)
	left_layer = folium.TileLayer(left_split, name="Actual")
	right_layer = folium.TileLayer(right_split, name="Comparacion")
	left_layer.add_to(m)
	right_layer.add_to(m)
	SideBySideLayers(left_layer, right_layer).add_to(m)
    
else:
	m = leafmap.Map(
		center=(center_lat, center_lon),
		zoom=zoom,
		toolbar_control=False,
		layers_control=True,
	)
	m.add_basemap(basemap)

if error_msg:
	with right_col:
		st.subheader("Resultado")
		st.error(error_msg)
else:
	for area_name, area_data in filtered_area_items.items():
		area_sw, area_ne = area_data["bbox"]
		area_score = float(area_data["score"])
		area_color = score_to_color(area_score)
		area_fill_opacity = 0.10 + (area_score * 0.50)

		folium.Rectangle(
			bounds=[area_sw, area_ne],
			color=area_color,
			weight=3 if area_name == selected_area else 2,
			fill=True,
			fill_opacity=area_fill_opacity,
		).add_to(m)

	folium.Marker(
		location=(center_lat, center_lon),
	).add_to(m)

	if searched_location:
		folium.Marker(
			location=(searched_location["lat"], searched_location["lon"]),
			icon=folium.Icon(color="blue", icon="search", prefix="fa"),
		).add_to(m)

	with center_col:
		map_output = st_folium(
			m,
			height=400,
			width=None,
			key="main_map",
			returned_objects=["last_clicked"],
		)

	last_clicked = map_output.get("last_clicked") if map_output else None
	if last_clicked:
		clicked_lat = last_clicked.get("lat")
		clicked_lon = last_clicked.get("lng")
		if clicked_lat is not None and clicked_lon is not None:
			clicked_zone = find_clicked_zone(clicked_lat, clicked_lon, filtered_area_items)
			if clicked_zone:
				st.session_state["clicked_zone"] = clicked_zone

	active_zone = st.session_state.get("clicked_zone")
	if active_zone and active_zone in filtered_area_items:
		right_area = active_zone
	else:
		right_area = selected_area

	right_score = float(filtered_area_items[right_area]["score"])
	right_color = score_to_color(right_score)
	if data_mode == "Actual":
		reference_date = date.today()
		reference_label = "Fecha actual"
	else:
		reference_date = next_prediction_date if next_prediction_date else (date.today() + timedelta(days=7))
		reference_label = "Fecha de prediccion"

	with right_col:
		st.metric("Lugar", right_area)
		st.metric("Probabilidad de Flash Drought", f"{right_score * 100:.1f}%")
		st.progress(right_score)
		st.metric(reference_label, reference_date.strftime("%Y-%m-%d"))
		if page_view == "Monitoreo":
			st.caption("Vista dividida: izquierda=actual, derecha=comparacion")
		st.markdown("**Listado (aun no implementado)**")
		st.info("Aqui se mostrara el listado de datos climaticos en una proxima version.")