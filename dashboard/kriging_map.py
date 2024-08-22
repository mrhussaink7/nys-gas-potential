import numpy as np
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import json

# init app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Load data
grid_data = pd.read_parquet('../data/kriging_grid_data.parquet')
well_data = pd.read_csv('../data/clean_gaswells.csv')
with open('../data/new_york_counties.json') as f:
    ny_geojson = json.load(f)

# Process well data
def process_well_data(well_data):
    size = np.interp(well_data['gas_prod'], 
                     (well_data['gas_prod'].min(), well_data['gas_prod'].max()), 
                     (10, 30))
    
    well_data['marker_size'] = size
    well_data['marker_border_size'] = size + 2

    customdata = np.stack([
        well_data['longitude'].round(2),
        well_data['latitude'].round(2),
        well_data['gas_prod'],
        well_data['depth'],
        well_data['elevation'],
        well_data['well'],
        well_data['status'],
        well_data['field'],
        well_data['geology']
    ], axis=-1)

    return well_data, customdata

well_data, well_customdata = process_well_data(well_data)

# App layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("New York Kriging Dashboard", className="text-center"), className="mb-4 mt-4")
    ]),
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id='choropleth-map', config={'scrollZoom': True}),
                html.Div([
                    dbc.Card([
                        dbc.CardHeader("Map Layers"),
                        dbc.CardBody([
                            dcc.Checklist(
                                id='layer-toggle',
                                options=[
                                    {'label': 'Interpolation', 'value': 'kriging'},
                                    {'label': 'Error Map', 'value': 'error'},
                                    {'label': 'Well Locations', 'value': 'wells'}
                                ],
                                value=['kriging']
                            )
                        ])
                    ], style={"width": "12rem"})
                ], style={
                    'position': 'absolute',
                    'bottom': '10px',
                    'right': '120px',
                    'z-index': '1000',
                    'background-color': 'rgba(255, 255, 255, 0.8)'
                })
            ], style={'position': 'relative'})
        ], width=12)
    ]),
], fluid=True)

# Update map
@app.callback(
    Output('choropleth-map', 'figure'),
    [Input('layer-toggle', 'value')]
)
def update_map(layers):
    fig = go.Figure()

    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            zoom=6,  # Zoomed out to show the world by default
            center={"lat": 43.0, "lon": -77.0}  # World centered view
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    if 'kriging' in layers:
        kriging_layer = go.Choroplethmapbox(
            geojson=ny_geojson,
            locations=grid_data['GEOID'],  # Match this to your geojson IDs
            z=grid_data['predicted_value'],
            colorscale="plasma",
            marker_opacity=0.7,
            zmin=grid_data['predicted_value'].min(),
            zmax=grid_data['predicted_value'].max(),
            colorbar=dict(title="Gas (MCF)"),
            featureidkey="properties.GEOID",  # Ensuring this aligns with geojson
        )
        fig.add_trace(kriging_layer)

    if 'error' in layers:
        error_layer = go.Choroplethmapbox(
            geojson=ny_geojson,
            locations=grid_data['GEOID'],  # Match this to your geojson IDs
            z=grid_data['error'],
            colorscale="YlGn_r",
            marker_opacity=0.7,
            zmin=grid_data['error'].min(),
            zmax=grid_data['error'].max(),
            colorbar=dict(title="Variance"),
            featureidkey="properties.GEOID",  # Ensuring this aligns with geojson
        )
        fig.add_trace(error_layer)

    if 'wells' in layers:
        border_scatter = go.Scattermapbox(
            lat=well_data['latitude'],
            lon=well_data['longitude'],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=well_data['marker_border_size'],
                color='black',
                opacity=0.8,
                symbol='circle'
            ),
            showlegend=False,
            hoverinfo='skip'
        )
        
        well_scatter = go.Scattermapbox(
            lat=well_data['latitude'],
            lon=well_data['longitude'],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=well_data['marker_size'],
                color=well_data['gas_prod'],
                colorscale='Plasma',
                cmin=well_data['gas_prod'].min(),
                cmax=well_data['gas_prod'].max(),
                opacity=0.8,
                symbol='circle'
            ),
            customdata=well_customdata,
            hovertemplate=(
                "Longitude: %{customdata[0]}<br>"
                "Latitude: %{customdata[1]}<br>"
                "Gas Produced: %{customdata[2]}<br>"
                "Depth: %{customdata[3]}<br>"
                "Elevation: %{customdata[4]}<br>"
                "Well Type: %{customdata[5]}<br>"
                "Well Status: %{customdata[6]}<br>"
                "Field: %{customdata[7]}<br>"
                "Geology: %{customdata[8]}<extra></extra>"
            ),
            name='Well Locations',
            showlegend=False,
        )

        fig.add_traces([border_scatter, well_scatter])

    if layers:
        fig.update_layout(
            mapbox=dict(
                zoom=6,  # Zoom into New York
                center={"lat": 43.0, "lon": -77.0}  # New York centered view
            )
        )

    return fig

# Run app
if __name__ == '__main__':
    app.run_server(debug=True)