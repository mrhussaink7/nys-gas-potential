import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import pickle
import plotly.express as px
from streamlit_folium import st_folium

# app title
st.title('New York State: Natural Gas Potential')

# create base map
m = folium.Map(location=[42.75, -75.50], zoom_start=7, attributionControl=False)

# add geojson layer
geojson_file = '../data/new_york_counties.json'
folium.GeoJson(geojson_file, name="County Boundaries").add_to(m)

# Add kriging model results as a choropleth (example)
# kriging results choropleth plots
# pickle load / dump model
# folium.Choropleth(geo_data=your_kriging_geojson).add_to(m)

# load gas wells data
df = pd.read_csv('../data/clean_gaswells.csv')

# add markers
for _, row in df.iterrows():
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=f"Gas Produced: {row['gas_prod']}<br>Depth: {row['depth']}<br>Elevation: {row['elevation']}<br>Field: {row['field']}<br>Geology: {row['geology']}",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(m)

# display map
st_folium(m, width=700, height=500)

print('Project by Jr Data Scientist, Kawsar Hussain')
