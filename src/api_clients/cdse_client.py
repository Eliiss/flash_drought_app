import os
import pandas as pd
import time
from dotenv import load_dotenv
from sentinelhub import SHConfig, SentinelHubStatistical, DataCollection, BBox, CRS

load_dotenv()
config = SHConfig()
config.sh_client_id = os.getenv("CDSE_CLIENT_ID")
config.sh_client_secret = os.getenv("CDSE_CLIENT_SECRET")
config.sh_base_url = 'https://sh.dataspace.copernicus.eu'

zonas = {
    'Sevilla': [-5.08, 37.53], 'Huesca':[0.32, 41.51], 'Barcelona': [2.25, 41.93],
    'Asturias': [-5.43, 43.48], 'Cantabria':[-4.05, 43.35]
}

# EVALSCRIPT OPTIMIZADO: Pedimos NDVI y NDMI a la vez
evalscript_indices = """
//VERSION=3
function setup() {
    return { 
        input: [{ bands:["B04", "B08", "B11", "SCL"], units: "DN" }], 
        output:[
            { id: "NDMI", bands: 1, sampleType: "FLOAT32" },
            { id: "NDVI", bands: 1, sampleType: "FLOAT32" }
        ] 
    };
}
function evaluatePixel(samples) {
    // Solo procesamos píxeles de Vegetación (4) y Suelo (5). Agua (6) fuera para no falsear sequía.
    if (![4, 5].includes(samples.SCL)) return { NDMI: [NaN], NDVI: [NaN] }; 
    
    let ndmi = (samples.B08 - samples.B11) / (samples.B08 + samples.B11);
    let ndvi = (samples.B08 - samples.B04) / (samples.B08 + samples.B04);
    
    return { NDMI: [ndmi], NDVI: [ndvi] };
}
"""

datos_satelite = []

for nombre, (lon, lat) in zonas.items():
    print(f"Descargando Sentinel-2 para {nombre}...")
    bbox = BBox(bbox=[lon-0.01, lat-0.01, lon+0.01, lat+0.01], crs=CRS.WGS84)
    
    try:
        request = SentinelHubStatistical(
            aggregation=SentinelHubStatistical.aggregation(
                evalscript=evalscript_indices, 
                time_interval=('2022-01-01', '2023-12-31'),
                aggregation_interval='P7D', 
                resolution=(20, 20) # Resolución óptima para B11
            ),
            input_data=[SentinelHubStatistical.input_data(DataCollection.SENTINEL2_L2A)],
            bbox=bbox, config=config
        )
        
        response = request.get_data()[0]
        
        for dato in response['data']:
            # Verificamos que existan datos válidos en AMBAS métricas
            stats_ndmi = dato['outputs']['NDMI']['bands']['B0']['stats']
            stats_ndvi = dato['outputs']['NDVI']['bands']['B0']['stats']
            
            if stats_ndmi['sampleCount'] > 0:
                datos_satelite.append({
                    'Zona': nombre,
                    'Fecha': dato['interval']['from'][:10],
                    'NDMI': stats_ndmi['mean'],
                    'NDVI': stats_ndvi['mean'],
                    'Píxeles_Válidos': stats_ndmi['sampleCount']
                })
        
        # Pausa para no saturar la API
        time.sleep(1) 
        
    except Exception as e:
        print(f"Error en zona {nombre}: {e}")
        continue

# Guardado seguro
if datos_satelite:
    df_sat = pd.DataFrame(datos_satelite)
    df_sat.to_csv('../data/raw/features_sentinel.csv', index=False)
    print(f"¡Éxito! {len(df_sat)} registros guardados en features_sentinel.csv")
else:
    print("No se recuperaron datos.")
