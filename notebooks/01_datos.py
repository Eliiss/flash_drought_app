import xarray as xr
import pandas as pd

# 1. Definir nuestras zonas
zonas = {
#    'Sevilla': {'lon': -5.08, 'lat': 37.53}
#    'Galicia_01': {'lat': -6, 'lon': 43.87},
    'Oviedo': {'lon': -6.01, 'lat': 43.46},
    'Villadepan': {'lon': -6.02, 'lat': 42.89},
    'Astorga': {'lon': -5.91, 'lat': 42.32},
    'Benavente': {'lon': -5.99, 'lat': 41.96},
#    'Galicia_06': {'lat': -6.69, 'lon': 43.80},
    'Castrillón': {'lon': -6.69, 'lat': 43.43},
    'Toreno': {'lon': -6.68, 'lat': 42.80},
    'Ponferrada': {'lon': -6.71, 'lat': 42.29},
    'Braganza': {'lon': -6.75, 'lat': 41.75},
    'Cervo': {'lon': -7.31, 'lat': 43.86},
    'Mondoñedo': {'lon': -7.35, 'lat': 43.41},
    'Lugo': {'lon': -7.33, 'lat': 42.89},
    'Maceda': {'lon': -7.27, 'lat': 42.30},
    'Verín': {'lon': -7.33, 'lat': 41.71},
    'Ortigueira': {'lon': -8.24, 'lat': 43.91},
    'A Coruña': {'lon': -8, 'lat': 43.27},
    'Lalín': {'lon': -8.11, 'lat': 42.81},
    'Ourense': {'lon': -8.18, 'lat': 42.39},
    'Braga': {'lon': -8.12, 'lat': 41.80},
    'Carballo': {'lon': -8.67, 'lat': 43.47},
    'Santiago de Compostela': {'lon': -8.61, 'lat': 42.82},
    'Vigo': {'lon': -8.88, 'lat': 42.48},
    'Viana do Castelo': {'lon': -8.81, 'lat': 41.86},
#    'Muxía': {'lon': -9.69, 'lat': 43.45},
    'Finisterre': {'lon': -9.44, 'lat': 42.86},
}

# 2. Cargar el archivo global del CSIC
ds = xr.open_dataset('./data/raw/spei01.nc')

datos_spei =[]

# 3. Extraer los datos de las coordenadas exactas
for nombre, coords in zonas.items():
    # Seleccionamos el punto más cercano a nuestras coordenadas
    ts = ds.sel(lon=coords['lon'], lat=coords['lat'], method='nearest')
    
    # Lo convertimos a DataFrame
    df_temp = ts.to_dataframe().reset_index()
    df_temp = df_temp[['time', 'spei']] # Nos quedamos solo con fecha y valor
    df_temp['Zona'] = nombre
    
#    df_temp = df_temp[(df_temp['time'] >= '1901-01-16') & (df_temp['time'] <= '2024-12-16')]
    df_temp = df_temp[(df_temp['time'] >= '2015-01-16') & (df_temp['time'] <= '2019-12-16')]
    datos_spei.append(df_temp)

df_final_spei = pd.concat(datos_spei)
df_final_spei.rename(columns={'time': 'Fecha', 'spei': 'SPEI'}, inplace=True)
df_final_spei.to_csv('./data/raw/target_spei.csv', index=False)
print("¡Archivo target_spei.csv creado con éxito!")