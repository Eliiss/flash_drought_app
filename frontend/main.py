import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import joblib
import pandas as pd

import folium
import geopandas as gpd
import leafmap.foliumap as leafmap
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="Demeter's Oracle", layout="wide")

@st.cache_resource
def load_ai_model():
    # Aseguraos de que la ruta coincide con donde guardaste el .pkl
    return joblib.load('C:\\Users\\Hulia\\OneDrive\\Documents\\flash_drought_app\\src\\model\\flash_drought_rf_model.pkl')

modelo_ia = load_ai_model()

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "img" / "icon.png"
BG_PATH = BASE_DIR / "img" / "bg.png"

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
        div[data-testid="stProgress"] > div > div > div > div {
            background-color: #b22222;
        }
        div[data-testid="stProgress"] > div > div > div {
            background-color: #ffe6e6;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Demeter's Oracle")

center_col, right_col = st.columns([5.8, 2.4], gap="medium")

with center_col:
    with st.form("location_search_form", clear_on_submit=False):
        search_col, search_button_col = st.columns([7, 2], gap="medium")
        with search_col:
            location_query = st.text_input(
                "Search bar",
                value=st.session_state.get("location_query", ""),
                placeholder="Barcelona, Spain",
                label_visibility="collapsed",
            )
        with search_button_col:
            search_clicked = st.form_submit_button("Search", use_container_width=True)

st.session_state["location_query"] = location_query

STATIC_DATA = {
    "Current": {
        "Madrid Center": {
            "bbox": ((40.30, -3.90), (40.55, -3.50)),
            "score": 0.28,
        },
        "Seville": {
            "bbox": ((37.25, -6.15), (37.55, -5.75)),
            "score": 0.62,
        },
        "Valencia": {
            "bbox": ((39.30, -0.55), (39.60, -0.20)),
            "score": 0.41,
        },
    },
    "Future": {
        "Madrid Center": {
            "bbox": ((40.30, -3.90), (40.55, -3.50)),
            "score": 0.54,
        },
        "Seville": {
            "bbox": ((37.25, -6.15), (37.55, -5.75)),
            "score": 0.78,
        },
        "Valencia": {
            "bbox": ((39.30, -0.55), (39.60, -0.20)),
            "score": 0.66,
        },
    },
}

MONITORING_PROVINCES = [
    "Pontevedra",
    "Cantabria",
    "Tarragona",
    "Barcelona",
    "Albacete",
    "Murcia",
]

PREDICTION_DATA = {
    "Ourense": {
        "bbox": ((42.05, -8.30), (42.55, -7.35)),
        "score": 0.73,
    }
}

# Fake historical records for the areas defined in your app
HISTORICAL_DATA = {
    "Pontevedra": [
        {"date": "2022-06-15", "severity": "Extreme", "duration": "14 days"},
        {"date": "2019-09-12", "severity": "Moderate", "duration": "6 days"},
    ],
    "Cantabria": [
        {"date": "2021-08-20", "severity": "Moderate", "duration": "5 days"},
    ],
    "Tarragona": [
        {"date": "2023-04-10", "severity": "High", "duration": "10 days"},
    ],
    "Barcelona": [
        {"date": "2023-05-15", "severity": "High", "duration": "9 days"},
        {"date": "2020-07-22", "severity": "Moderate", "duration": "7 days"},
    ],
    "Albacete": [
        {"date": "2022-07-11", "severity": "Extreme", "duration": "20 days"},
    ],
    "Murcia": [
        {"date": "2023-08-01", "severity": "Extreme", "duration": "25 days"},
        {"date": "2021-06-15", "severity": "High", "duration": "15 days"},
    ],
    "Madrid Center": [
        {"date": "2022-08-14", "severity": "High", "duration": "11 days"},
    ],
    "Seville": [
        {"date": "2023-07-10", "severity": "Extreme", "duration": "18 days"},
    ],
    "Valencia": [
        {"date": "2022-06-25", "severity": "High", "duration": "13 days"},
    ],
    "Ourense": [
        {"date": "2023-09-05", "severity": "Moderate", "duration": "8 days"},
        {"date": "2021-08-12", "severity": "High", "duration": "12 days"},
    ]
}

def bbox_center(sw: tuple[float, float], ne: tuple[float, float]) -> tuple[float, float]:
    return ((sw[0] + ne[0]) / 2, (sw[1] + ne[1]) / 2)


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
            return None, None, None, "Location not found."
        lat = float(payload[0]["lat"])
        lon = float(payload[0]["lon"])
        name = payload[0].get("display_name", query)
        return lat, lon, name, None
    except Exception:
        return None, None, None, "Error while searching for location."


with st.sidebar:
    if ICON_PATH.exists():
        st.image(str(ICON_PATH), use_container_width=True)

    page_view = st.radio(" ", ["Monitoring", "Prediction"], horizontal=True)
    data_mode = "Current" if page_view == "Monitoring" else "Future"

    selected_monitoring_province = None
    if page_view == "Monitoring":
        selected_monitoring_province = st.selectbox(
            "Monitoring zone",
            MONITORING_PROVINCES,
            index=0,
        )

    if page_view == "Prediction":
        next_prediction_date = st.date_input(
            "Next prediction date",
            value=date.today() + timedelta(days=7),
            min_value=date.today(),
        )
        st.markdown("### 📡 Satellite Data (Nowcasting)")
        vh_vv = st.slider("Current Moisture (VH/VV dB)", -8.0, -4.0, -6.5, 0.1)
        anomalia = st.slider("Radar Anomaly", -1.0, 1.0, -0.2, 0.05)
        velocidad = st.slider("Drying Velocity", -0.5, 0.5, -0.1, 0.05)
        spei_prev = st.slider("Previous SPEI (Meteorology)", -3.0, 3.0, -1.0, 0.1)
    else:
        next_prediction_date = None

    percentage_filter = st.slider(
        "Filter by drought percentage",
        min_value=0,
        max_value=100,
        value=(0, 100),
        step=1,
    )

    min_percentage, max_percentage = percentage_filter
    area_source = STATIC_DATA[data_mode] if page_view == "Monitoring" else PREDICTION_DATA
    filtered_area_items = {
        area_name: area_data
        for area_name, area_data in area_source.items()
        if min_percentage <= (area_data["score"] * 100) <= max_percentage
    }

    if not filtered_area_items:
        st.warning("No areas for this range. Showing all.")
        filtered_area_items = area_source

    if page_view == "Monitoring":
        selected_area = next(iter(filtered_area_items))
    else:
        selected_area = st.selectbox("Zone", list(filtered_area_items.keys()), index=0)
    default_bbox = filtered_area_items[selected_area]["bbox"]

    basemap = "HYBRID"

    zoom = st.slider("Zoom", min_value=2, max_value=18, value=6)


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
            st.info("Type a location to search.")

searched_location = st.session_state.get("searched_location")
if searched_location:
    center_lat = searched_location["lat"]
    center_lon = searched_location["lon"]

geojson_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/spain-provinces.geojson"


@st.cache_data
def get_provinces():
    return gpd.read_file(geojson_url)


gdf = get_provinces()
monitoring_gdf = gdf[gdf["name"].isin(MONITORING_PROVINCES)]
prediction_gdf = gdf[gdf["name"] == "Ourense"]

if page_view == "Prediction" and not prediction_gdf.empty and not searched_location:
    ourense_centroid = prediction_gdf.geometry.unary_union.centroid
    center_lat, center_lon = ourense_centroid.y, ourense_centroid.x

m = leafmap.Map(
    center=(center_lat, center_lon),
    zoom=zoom,
    toolbar_control=False,
    layers_control=True,
)
m.add_basemap(basemap)

if page_view == "Monitoring" and not monitoring_gdf.empty:
    monitoring_geojson = json.loads(monitoring_gdf[["name", "geometry"]].to_json())
    folium.GeoJson(
        monitoring_geojson,
        name="Monitoring provinces",
        style_function=lambda _feature: {
            "color": "#b22222",
            "weight": 2,
            "fillColor": "#ff4d4d",
            "fillOpacity": 0.28,
        },
        tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Province"]),
    ).add_to(m)

if page_view == "Prediction" and not prediction_gdf.empty:
    prediction_geojson = json.loads(prediction_gdf[["name", "geometry"]].to_json())
    folium.GeoJson(
        prediction_geojson,
        name="Prediction province",
        style_function=lambda _feature: {
            "color": "#8b1a1a",
            "weight": 3,
            "fillColor": "#ff6b6b",
            "fillOpacity": 0.35,
        },
        tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Province"]),
    ).add_to(m)

if error_msg:
    with right_col:
        st.subheader("Result")
        st.error(error_msg)
else:
    if searched_location:
        folium.Marker(
            location=(searched_location["lat"], searched_location["lon"]),
            icon=folium.Icon(color="blue", icon="search", prefix="fa"),
        ).add_to(m)

    with center_col:
        st_folium(
            m,
            height=400,
            width=None,
            key="main_map",
            returned_objects=["last_clicked"],
        )

    if page_view == "Prediction":
        right_area = selected_area
        
        # --- Calculo de la probabilidad con la ia ---
        datos_entrada = pd.DataFrame([[
            vh_vv, anomalia, velocidad, spei_prev
        ]], columns=['VH_VV_Ratio_Smooth', 'Anomalia_Radar', 'Velocidad_Secado_Radar', 'SPEI_hace_1_mes'])
        
        probabilidad_ia = modelo_ia.predict_proba(datos_entrada)[0][1]
        right_score = float(probabilidad_ia)

    if page_view == "Monitoring":
        reference_date = date.today()
        reference_label = "Current date"
    else:
        reference_date = next_prediction_date if next_prediction_date else (date.today() + timedelta(days=7))
        reference_label = "Prediction date"

    with right_col:
        # Determine which area name to use for looking up history
        history_key = selected_monitoring_province if page_view == "Monitoring" else right_area
        
        if page_view == "Monitoring":
            st.metric("Location", selected_monitoring_province if selected_monitoring_province else "No province")
            st.metric("Status", "Normal / Safe")
        else:
            st.metric("Location (Prediction)", right_area)
            
            # MOSTRAR PORCENTAJE CON COLORES SEGÚN EL RIESGO
            porcentaje_final = right_score * 100
            st.markdown(f"### Flash Drought Probability: {porcentaje_final:.1f}%")
            st.progress(right_score)
            
            if porcentaje_final < 30:
                st.success("🟢 **LOW RISK**: Ecosystem moisture is stable.")
            elif porcentaje_final < 70:
                st.warning("🟡 **WARNING**: Rapid moisture loss detected.")
            else:
                st.error("🔴 **TINDERBOX ALERT**: Extreme Flash Drought. High Megafire risk!")

        
        st.metric(reference_label, reference_date.strftime("%Y-%m-%d"))

        # --- NEW HISTORICAL DATA SECTION ---
        st.subheader("Historical Events")
        
        # Get the history for the active area
        history = HISTORICAL_DATA.get(history_key, [])
        
        if history:
            for record in history:
                # Using an expander or a simple container for each event
                st.markdown(f"**Flash Drought** - {record['date']}  ({record['severity']})")
        else:
            st.info("No historical flash droughts recorded for this area.")
        # -----------------------------------
        

if BG_PATH.exists():
    st.image(str(BG_PATH), use_container_width=True)
