# Demeters's Orcale - Flash Drought Early Warning App

> 🥉 **3rd Place — 11th CASSINI Hackathon Barcelona: Space for Water**

An early warning application for **flash drought detection** using satellite and climate data from Copernicus services. Built in 48 hours as part of the CASSINI Hackathon focused on space-based solutions for water management.

---

##  What it does

Flash droughts are rapid-onset drought events that can devastate agriculture and water resources in a matter of weeks. This app leverages Earth Observation data to:

- Detect and monitor flash drought events in near real-time
- Visualize soil moisture and vegetation stress indicators
- Provide early warnings to support water management decisions

---

##  Data Sources

- **Copernicus Climate Data Store (CDS)** — ERA5 reanalysis and climate indicators
- **Sentinel Hub** — Satellite imagery for vegetation and land surface analysis

---

##  Project Structure

```
flash_drought_app/
├── data/
│   └── raw/             # Raw datasets
├── notebooks/           # Exploratory analysis and prototyping
├── src/
│   └── api_clients/     # Clients for Sentinel Hub and CDS APIs
└── frontend/            # App frontend
```

---

##  Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Eliiss/flash_drought_app.git
cd flash_drought_app
```

```bash
pip install sentinelhub pandas matplotlib
pip install python-dotenv
pip3 install cdsapi
pip install numpy ipyleaflet ipywidgets
pip install xarray netCDF4
```

### API credentials

Configure your CDS API access by editing the `.cdsapirc` file with your credentials from the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/).

---

##  Hackathon

This project was developed at the **11th CASSINI Hackathon — Space for Water**, held in Barcelona. The challenge called for innovative solutions using EU space data to address global water-related issues.

---

##  Tech Stack

- Python / Jupyter Notebooks
- Sentinel Hub API
- Copernicus CDS API (cdsapi)
- xarray, netCDF4
- ipyleaflet, ipywidgets
