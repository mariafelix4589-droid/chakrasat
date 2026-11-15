# ChakraSat

**ES** · Herramienta de apoyo a la decisión para técnicos y extensionistas de la Amazonía ecuatoriana (Pastaza y Napo).
Detecta con datos de la NASA los meses en que el suelo pierde humedad (*ventana de estrés*) y compara tres rotaciones
de 2 años para que la chakra no quede desnuda en esos meses. **Apoya, no reemplaza, el juicio del agricultor. Validar en campo.**

**EN** · Decision-support tool for agricultural extension workers in the Ecuadorian Amazon (Pastaza and Napo).
It uses NASA data to find the months when soil moisture drops (*stress window*) and compares three 2-year crop
rotations so the field is not left bare in those months. **It supports, and does not replace, the farmer's judgement. Validate in the field.**

NASA Space Apps Challenge 2026 · Challenge "Field Shift: Adapting Farms with NASA Data" · Sangolquí (ESPE).

## Datos de la NASA / NASA data
| Variable | Dataset | Link |
|---|---|---|
| Humedad superficial del suelo / Surface soil wetness (GWETTOP), humedad raíz (GWETROOT) | NASA POWER, daily, community AG (MERRA-2) | https://power.larc.nasa.gov/ |
| Lluvia / Precipitation (PRECTOTCORR) | NASA POWER | https://power.larc.nasa.gov/docs/services/api/ |
| Vegetación / NDVI 250 m, 16 días | MODIS Terra MOD13Q1 v061 (LP DAAC), via ORNL DAAC MODIS Web Service | https://lpdaac.usgs.gov/products/mod13q1v061/ · https://modis.ornl.gov/data/modis_webservice.html |

Period: April 2015 – October 2026 (139 monthly records; 114 valid NDVI months after cloud filtering).

**Limitación / Limitation:** GWETTOP is a modelled variable (MERRA-2, ~0.5° × 0.625° cell, ~50 km); the cell elevation
(1 815 m) differs from Puyo (~950 m). Results describe the regional pattern, not the single plot. Next step: SMAP L3/L4 (9 km) via AppEEARS.

## Cómo funciona / How it works
1. **Parcela / Plot** – draw a polygon or point on the map (Folium).
2. **Suelo / Soil** – soil type, pH, organic matter and previous crops (what satellites do not see). Example profile preloaded.
3. **Ventana de estrés / Stress window** – month enters the window if soil moisture (and NDVI when available) falls below the historical 25th percentile in ≥ 40 % of years.
4. **Rotaciones / Rotations** – A current (maize → fallow → cassava), B forage peanut (perennial legume, relay-sown in July), C mucuna cover crop. Traffic-light score 0–100: base 40 + 40 × share of critical months covered + legume bonus + poor-soil bonus − bare-soil penalty for clay/sandy soils − management risk.
5. **Calendario / Calendar** – 24 months (2 agricultural years from April). Maize 110–135 days (MAG-SIPA); cassava 6–12 months, 9 used (INIAP / ESPAM).
6. **Informe / Report** – downloadable HTML for the conversation with the family.

## Ejecutar / Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Update data (optional): `python scripts/descargar_nasa_power.py --ndvi`.

## Uso de IA / AI use
Code, texts and design were developed with the help of Claude (Anthropic). The team defined the problem, the agronomic
decisions and validated the results. No AI-generated images are used.

## Licencia / License
MIT — see [LICENSE](LICENSE).
