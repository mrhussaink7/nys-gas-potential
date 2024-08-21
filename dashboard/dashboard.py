import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.express as px
import json

# init app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# load grid data
grid_data = pd.read_parquet('../data/kriging_grid_data.parquet')

# load geojson from your data
with open('../data/new_york_counties.json') as f:
    ny_geojson = json.load(f)

# app layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("New York Kriging Dashboard", className="text-center"), className="mb-4 mt-4")
    ]),
    dbc.Row([
        dbc.Col([
            # kriging interpolation
            dcc.Checklist(
                id='layer-toggle',
                options=[
                    {'label': 'Kriging Interpolation', 'value': 'kriging'},
                    {'label': 'Error Map', 'value': 'error'}
                ],
                value=['kriging']
            ),
            # choropleth map
            dcc.Graph(id='choropleth-map'),
        ], width=12)
    ]),
], fluid=True)

# update map
@app.callback(
    Output('choropleth-map', 'figure'),
    [Input('layer-toggle', 'value')]
)
def update_map(layers):
    fig = None

    if 'kriging' in layers:
        fig = px.choropleth_mapbox(
            grid_data,
            geojson=ny_geojson,
            locations='GEOID',
            featureidkey="properties.GEOID",
            color='predicted_value',
            color_continuous_scale="plasma",
            mapbox_style="carto-positron",
            zoom=6,
            center={"lat": 43.0, "lon": -75.0},
            opacity=0.7,
            labels={'predicted_value':'Kriging Interpolation'}
        )

    if 'error' in layers:
        if fig is None:
            fig = px.choropleth_mapbox(
                grid_data,
                geojson=ny_geojson,
                locations='GEOID',
                featureidkey="properties.GEOID",
                color='error',
                color_continuous_scale="YlGn_r",
                mapbox_style="carto-positron",
                zoom=6,
                center={"lat": 43.0, "lon": -75.0},
                opacity=0.7,
                labels={'error':'Error Map'}
            )
        else:
            error_fig = px.choropleth_mapbox(
                grid_data,
                geojson=ny_geojson,
                locations='GEOID',
                featureidkey="properties.GEOID",
                color='error',
                color_continuous_scale="YlGn_r",
                mapbox_style="carto-positron",
                zoom=6,
                center={"lat": 43.0, "lon": -75.0},
                opacity=0.7,
                labels={'error':'Error Map'}
            )
            for trace in error_fig.data:
                fig.add_trace(trace)

    if fig:
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    
    return fig

# run app
if __name__ == '__main__':
    app.run_server(debug=True)
