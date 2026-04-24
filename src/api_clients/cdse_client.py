import os
from dotenv import load_dotenv
import pandas as pd
from sentinelhub import (
    SHConfig,
    SentinelHubStatistical,
    DataCollection,
    BBox,
    CRS,
    geometry
)


# Esto busca tu archivo .env y carga las variables en memoria
load_dotenv() 

# Ahora ya puedes llamarlas así:
mi_id = os.getenv("CDSE_CLIENT_ID")
mi_secreto = os.getenv("CDSE_CLIENT_SECRET")

# Y se las pasas a la configuración de Copernicus:
config = SHConfig()
config.sh_client_id = mi_id
config.sh_client_secret = mi_secreto
config.sh_base_url = 'https://sh.dataspace.copernicus.eu'


# 2. DEFINIR LA PARCELA Y EL TIEMPO
# Coordenadas de ejemplo (Bounding Box) de un campo agrícola en España
# Formato: [min_lon, min_lat, max_lon, max_lat]
bbox_campo = BBox(bbox=[-3.85, 39.85, -3.84, 39.86], crs=CRS.WGS84)
intervalo_tiempo = ('2023-04-01', '2023-05-30') # Época de sequía

# 3. EL EVALSCRIPT (El "cerebro" que procesa en la nube)
# Calcula el NDMI: (B08 - B11) / (B08 + B11) 
# y filtra los píxeles que son nubes para que no ensucien los datos.
evalscript = """
//VERSION=3
function setup() {
    return {
        input: [{
            bands:["B08", "B11", "SCL"],
            units: "DN"
        }],
        output:[
            { id: "NDMI", bands: 1, sampleType: "FLOAT32" },
            { id: "dataMask", bands: 1, sampleType: "UINT8" }
        ]
    };
}

function evaluatePixel(samples) {
    let ndmi = (samples.B08 - samples.B11) / (samples.B08 + samples.B11);
    
    // Filtrar nubes usando la capa SCL (Scene Classification Layer)
    // 4=Vegetación, 5=Suelo desnudo, 6=Agua. Ignoramos nubes (8,9,10)
    let validPixel = [4, 5, 6].includes(samples.SCL) ? 1 : 0;
    
    return {
        NDMI: [ndmi],
        dataMask: [validPixel]
    };
}
"""

# 4. CREAR LA PETICIÓN ESTADÍSTICA
request = SentinelHubStatistical(
    aggregation=SentinelHubStatistical.aggregation(
        evalscript=evalscript,
        time_interval=intervalo_tiempo,
        aggregation_interval='P1D', # Agrupar por 1 Día
        resolution=(10, 10)         # Resolución Sentinel-2 (10x10 metros)
    ),
    input_data=[
        SentinelHubStatistical.input_data(
            DataCollection.SENTINEL2_L2A # Producto ya corregido atmosféricamente
        )
    ],
    bbox=bbox_campo,
    config=config
)

# 5. EJECUTAR Y LIMPIAR DATOS
print("Descargando estadísticas de NDMI...")
response = request.get_data()[0]

# Convertir el feo JSON a un precioso DataFrame de Pandas
datos = []
for dato_diario in response['data']:
    fecha = dato_diario['interval']['from']
    # Solo guardar si hay datos válidos ese día (que no estuviera todo nublado)
    if dato_diario['outputs']['NDMI']['bands']['B0']['stats']['sampleCount'] > 0:
        media_ndmi = dato_diario['outputs']['NDMI']['bands']['B0']['stats']['mean']
        datos.append({'Fecha': fecha, 'NDMI_Mean': media_ndmi})

df_ndmi = pd.DataFrame(datos)
df_ndmi['Fecha'] = pd.to_datetime(df_ndmi['Fecha'])

print("¡Datos listos!")
print(df_ndmi.head())