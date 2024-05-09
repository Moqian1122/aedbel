#!/usr/bin/env python
# coding: utf-8

# In[4]:


import dash
from dash import jupyter_dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import dash_leaflet as dl

# Example coordinates for Brussels, Belgium
example_lat, example_lon = 50.8503, 4.3517

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(fluid=True, children=[
    dbc.Row([
        dbc.Col(html.H1("AED Locator", className="text-center"), width=12)
    ]),
    dbc.Row([
        dbc.Col([
            dl.Map(center=(example_lat, example_lon), zoom=12, children=[
                dl.TileLayer(),
                dl.Marker(position=(example_lat, example_lon), children=[
                    dl.Tooltip("Your Location (Example)"),
                    dl.Popup("This is an example location in Brussels, Belgium.")
                ])
            ], style={'width': '100%', 'height': '50vh', 'margin': "auto", "display": "block"})
        ], width=12)
    ]),
    dbc.Row([
        dbc.Col(dbc.Button("Get Directions to Nearest AED", color="primary", className="mt-3", id="get-directions-btn"), width=12)
    ]),
    dbc.Row([
        dbc.Col(html.Div(id="directions-output"), width=12)
    ])
])

# Placeholder callback for button
@callback(
    Output("directions-output", "children"),
    Input("get-directions-btn", "n_clicks")
)
def show_directions(n_clicks):
    if n_clicks:
        return html.P("Directions to the nearest AED will be displayed here.")
    return ""

if __name__ == '__main__':
    app.run(jupyter_mode="external", port = 8051)


# In[ ]:




