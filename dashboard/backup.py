import numpy as np
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
import json

# init app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Load data
grid_data = pd.read_parquet('../data/kriging_grid_data.parquet')
well_data = pd.read_csv('../data/county_gaswells.csv')
with open('../data/new_york_counties.json') as f:
    ny_geojson = json.load(f)

initial_data = well_data.head(100)  # Load only the first 100 rows


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
        well_data['County'],
        well_data['geology']
    ], axis=-1)

    return well_data, customdata

well_data, well_customdata = process_well_data(well_data)

# Function to create field distribution pie chart
def create_field_distribution_plot(data):
    # Calculate the percentage of each County
    field_counts = data['County'].value_counts(normalize=True) * 100
    
    # Separate large and small slices
    large_counts = field_counts[field_counts >= 5]
    small_counts = field_counts[field_counts < 5]
    
    # Calculate the total percentage for the "Other" category
    other_percentage = small_counts.sum()
    
    # Combine large counts and "Other"
    if other_percentage > 0:
        field_counts = pd.concat([large_counts, pd.Series({'Other': other_percentage})])
    
    # Convert percentages back to absolute counts for plotting
    field_counts_abs = data['County'].value_counts()[large_counts.index]
    
    # Add "Other" to the absolute counts
    if 'Other' in field_counts.index:
        field_counts_abs = pd.concat([field_counts_abs, pd.Series({'Other': data['County'].value_counts()[small_counts.index].sum()})])
    
    # Create the pie chart
    fig = px.pie(field_counts_abs, values=field_counts_abs.values, names=field_counts_abs.index, title="Field Distribution")
    
    return fig

# Function to create well status vs gas production box plot
def create_well_status_vs_gas_plot(data):
    fig = px.box(data, x='status', y='gas_prod', color='status', title="Well Status vs. Gas Production")
    fig.update_layout(xaxis_title="Well Status", yaxis_title="Gas Production (MCF)")
    return fig

# Function to create parallel coordinates plot
def create_parallel_coordinates_plot(data):
    fig = px.parallel_coordinates(data, color='gas_prod', dimensions=['depth', 'elevation', 'gas_prod', 'longitude', 'latitude'],
                                  color_continuous_scale=px.colors.diverging.Tealrose,
                                  title="Parallel Coordinates Plot")
    return fig


# App layout with 3 by 2 structure
app.layout = dbc.Container([
    # First Row (Section 1) - Well Status, Field, and Geology Formation Insights
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id='selected-plot', style={'height': '300px', 'width': '100%'}),
                # Hovering dropdown card
                html.Div([
                    dbc.Card([
                        dbc.CardHeader("Select Plot", style={'fontSize': '0.7rem','padding':'0.3rem 0.3rem'}),
                        dbc.CardBody([
                            dcc.Dropdown(
                                id='plot-selector',
                                options=[
                                    {'label': 'Counties', 'value': 'field-distribution-plot'},
                                    {'label': 'Status', 'value': 'well-status-vs-gas-plot'},
                                    {'label': 'Coordinates', 'value': 'parallel-coordinates-plot'}
                                ],
                                value='field-distribution-plot',
                                style={'fontSize':'8px', 'padding':'0 0'}
                            )
                        ],style={'height':'40px','padding':'3px'})
                    ], style={"width": "6rem", 'padding':'0px'})
                ], style={
                    'position': 'absolute',
                    'bottom': '0px',
                    'left': '0px',
                    'z-index': '1000',
                    'background-color': 'rgba(255, 255, 255, 0.8)',
                    'padding': '0px',
                    'width':'100px',
                })
            ], style={'position': 'relative', 'height':'250px'})
        ], width=4),

        # Modeling Results Overview, Performance metrics, variogram + kriging stats
        dbc.Col(
            html.Div(id='section-2', style={'border': '1px solid black', 'height': '300px'}),
            width=4
        ),

        # Map Section (Top Right)
        dbc.Col(
            html.Div([
                dcc.Graph(id='choropleth-map', config={'scrollZoom': True}, style={'height': '300px'}),
                html.Div([
                    dbc.Card([
                        dbc.CardHeader("Map Layers", style={'fontSize': '0.7rem'}),
                        dbc.CardBody([
                            dcc.Checklist(
                                id='layer-toggle',
                                options=[
                                    {'label': 'Kriging', 'value': 'kriging'},
                                    {'label': 'Error Map', 'value': 'error'},
                                    {'label': 'Gas Wells', 'value': 'wells'}
                                ],
                                value=['kriging'],
                                style={'display': 'block', 'fontSize': '0.7rem'}
                            )
                        ], style={'height':'75px', 'padding':'7px'})
                    ], style={"width": "7rem"})
                ], style={
                    'position': 'absolute',
                    'bottom': '0px',
                    'left': '10px',
                    'z-index': '1000',
                    'background-color': 'rgba(255, 255, 255, 0.8)',
                    'width':'100px'
                })
            ], style={'position': 'relative', 'height': '300px'}),
            width=4
        ),
    ]),
    # Second Row
    dbc.Row([
        # Interactive Data Display with County and Status Filters (Middle Left, Section 4)
        dbc.Col([
            # DataTable with filters
            html.Div([
                dash_table.DataTable(
                    id='well-data-table',
                    columns=[{"name": i, "id": i, "deletable": False, "selectable": True} for i in well_data.columns],
                    data=initial_data.to_dict('records'),
                    page_action='none',  # Disable pagination
                    sort_action='native',  # Enable sorting by column
                    style_table={'height': '250px', 'overflowY': 'scroll'},  # Adjust height for filters
                    style_cell={'textAlign': 'left', 'fontSize': 12, 'font-family': 'Arial'},
                    style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},
                ),
                # Floating Filter Card
                dbc.Card([
                    dbc.CardHeader("Filters", style={'fontSize':'12px','padding': '0.3rem 0.5rem'}),
                    dbc.CardBody([
                        dcc.Dropdown(
                            id='county-filter',
                            options=[{'label': county, 'value': county} for county in well_data['County'].unique()],
                            placeholder="County",
                            multi=True,
                            style={'margin-bottom': '10px', 'fontSize': '9px'}
                        ),
                        dcc.Dropdown(
                            id='status-filter',
                            options=[{'label': status, 'value': status} for status in well_data['status'].unique()],
                            placeholder="Status",
                            multi=True,
                            style={'fontSize': '9px'}
                        )
                    ], style={'height':'100px','padding': '0.3rem'})
                ], style={
                    "position": "absolute",
                    "bottom": "10px",
                    "right": "10px",
                    "z-index": "1000",
                    "width": "100px",  # Small size like a legend
                }),
            ], style={'position': 'relative', 'height': '300px'}),  # Keep the DataTable contained within its section
        ], width=4),
        # well proximity
        dbc.Col(html.Div(id='section-5', style={'border': '1px solid black', 'height': '300px'}), width=4),
        # user annotation
        dbc.Col(html.Div(id='section-6', style={'border': '1px solid black', 'height': '300px'}), width=4),
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
                "County: %{customdata[7]}<br>"
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

# =============================================================================
# SECTION 4 DATA TABLE

# Callback to update the table based on selected County and Status
@app.callback(
    Output('well-data-table', 'data'),
    [Input('county-filter', 'value'),
     Input('status-filter', 'value')]
)
def update_table(selected_counties, selected_statuses):
    filtered_data = well_data

    if selected_counties:
        filtered_data = filtered_data[filtered_data['County'].isin(selected_counties)]

    if selected_statuses:
        filtered_data = filtered_data[filtered_data['status'].isin(selected_statuses)]

    # Return the filtered dataset (full or filtered)
    return filtered_data.to_dict('records')

# =============================================================================
# SECTION 1: GEO INSIGHTS

# Callback to update the displayed plot based on dropdown selection
@app.callback(
    Output('selected-plot', 'figure'),
    [Input('plot-selector', 'value'),
     Input('well-data-table', 'data')]
)
def update_selected_plot(selected_plot, data):
    df = pd.DataFrame(data)
    
    if selected_plot == 'field-distribution-plot':
        return create_field_distribution_plot(df)
    elif selected_plot == 'well-status-vs-gas-plot':
        return create_well_status_vs_gas_plot(df)
    elif selected_plot == 'parallel-coordinates-plot':
        return create_parallel_coordinates_plot(df)

# Run app
if __name__ == '__main__':
    app.run_server(debug=True)