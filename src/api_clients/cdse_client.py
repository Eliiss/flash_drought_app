import os
import pandas as pd
import numpy as np
import time
import pandas as pd
import numpy as np
import time
from dotenv import load_dotenv
from sentinelhub import SHConfig, SentinelHubStatistical, DataCollection, BBox, CRS

# --- INICIO DEL ARREGLO ---
# Buscamos la ruta absoluta de tu archivo .env que está 2 carpetas más atrás
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_env = os.path.join(ruta_actual, "../../.env")
load_dotenv(dotenv_path=ruta_env)

from sentinelhub import SHConfig, SentinelHubStatistical, DataCollection, BBox, CRS

# --- INICIO DEL ARREGLO ---
# Buscamos la ruta absoluta de tu archivo .env que está 2 carpetas más atrás
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_env = os.path.join(ruta_actual, "../../.env")
load_dotenv(dotenv_path=ruta_env)

config = SHConfig()
config.sh_client_id = os.getenv("CDSE_CLIENT_ID")
config.sh_client_secret = os.getenv("CDSE_CLIENT_SECRET")
config.sh_client_id = os.getenv("CDSE_CLIENT_ID")
config.sh_client_secret = os.getenv("CDSE_CLIENT_SECRET")
config.sh_base_url = 'https://sh.dataspace.copernicus.eu'

config.sh_token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'


# Zona
zonas = {    'Valdeorras_Incendio':[-7.16302, 42.36480] }
# ... (Tu configuración y tu .env de arriba se quedan exactamente igual) ...

# 1. ¡EL ARREGLO! Definimos que Sentinel-1 use la URL de Copernicus CDSE
S1_CDSE = DataCollection.SENTINEL1_IW.define_from("s1_cdse", service_url=config.sh_base_url)

# 2. EVALSCRIPT PARA SENTINEL-1
config.sh_token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'


# Zona
zonas = {    'Valdeorras_Incendio':[-7.16302, 42.36480] }
# ... (Tu configuración y tu .env de arriba se quedan exactamente igual) ...

# 1. ¡EL ARREGLO! Definimos que Sentinel-1 use la URL de Copernicus CDSE
S1_CDSE = DataCollection.SENTINEL1_IW.define_from("s1_cdse", service_url=config.sh_base_url)

# 2. EVALSCRIPT PARA SENTINEL-1
evalscript = """
//VERSION=3
function setup() {
    return {
        input: [{
            bands: ["VV", "VH", "dataMask"]
            bands: ["VV", "VH", "dataMask"]
        }],
        output: [
            { id: "VV", bands: 1, sampleType: "FLOAT32" },
            { id: "VH", bands: 1, sampleType: "FLOAT32" },
        output: [
            { id: "VV", bands: 1, sampleType: "FLOAT32" },
            { id: "VH", bands: 1, sampleType: "FLOAT32" },
            { id: "dataMask", bands: 1, sampleType: "UINT8" }
        ]
    };
}

function evaluatePixel(sample) {
function evaluatePixel(sample) {
    return {
        VV: [sample.VV],
        VH: [sample.VH],
        dataMask: [sample.dataMask]
        VV: [sample.VV],
        VH: [sample.VH],
        dataMask: [sample.dataMask]
    };
}
"""

datos_satelite =[]

for nombre, (lon, lat) in zonas.items():
    print(f"Descargando Radar Sentinel-1 (VV/VH) para {nombre}...")
    delta = 0.045
    bbox_coords =[lon - delta, lat - delta, lon + delta, lat + delta]
    bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
    
    try:
        request = SentinelHubStatistical(
            aggregation=SentinelHubStatistical.aggregation(
                evalscript=evalscript, 
                time_interval=('2022-01-01', '2023-12-31'),
                aggregation_interval='P7D', # Semanal
                resolution=(0.0002, 0.0002) 

            ),
            # 3. ¡USAMOS LA COLECCIÓN QUE HEMOS REDIRIGIDO!
            input_data=[SentinelHubStatistical.input_data(S1_CDSE)],
            bbox=bbox, 
            config=config
        )
        
        response = request.get_data()[0]
        
        for dato in response['data']:
            stats_vv = dato['outputs']['VV']['bands']['B0']['stats']
            stats_vh = dato['outputs']['VH']['bands']['B0']['stats']
            
            if stats_vv['sampleCount'] > 0:
                datos_satelite.append({
                    'Zona': nombre,
                    'Fecha': dato['interval']['from'][:10],
                    'VV_linear': stats_vv['mean'],
                    'VH_linear': stats_vh['mean'],
                    'Píxeles_Válidos': stats_vv['sampleCount']
                })
        
        time.sleep(1) 
        print(f" {nombre} completado.")
        
    except Exception as e:
        print(f"Error en zona {nombre}: {e}")
        continue

# 4. Procesamiento final a Decibelios
if datos_satelite:
    df_sat = pd.DataFrame(datos_satelite)
    
    df_sat['VV_dB'] = 10 * np.log10(df_sat['VV_linear'].replace(0, np.nan))
    df_sat['VH_dB'] = 10 * np.log10(df_sat['VH_linear'].replace(0, np.nan))
    df_sat['VH_VV_Ratio'] = df_sat['VH_dB'] - df_sat['VV_dB']
    
    # Creamos la carpeta si no existe
    df_sat.to_csv('C:\\Users\\Hulia\\OneDrive\\Documents\\flash_drought_app\\data\\raw\\features_sentinel1.csv', index=False)
    
    print(f"\n¡Misión cumplida! {len(df_sat)} semanas de datos de radar guardados en features_sentinel1.csv")
    print(df_sat.head())
else:
    print("No se recuperaron datos.")