import pandas as pd
from datetime import datetime
import googlemaps
from geopy.distance import geodesic
import requests
import folium
import polyline
from flask import Flask, request, jsonify
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

import os
import re
import math
import json
import base64

class AEDPoint:
    def __init__(self, id, x, y, address, indication, schedule, taken):
        self.id = id
        self.x = x
        self.y = y
        self.address = address
        self.indication = indication
        self.schedule = schedule
        self.taken = taken

    def distance_from(self, loc): 
        if self.x < -90 or self.x > 90 or self.y < -90 or self.y > 90:
            return math.inf
        return geodesic((self.x, self.y), loc).km
    
class MapAEDS:
    def __init__(self):
        self.points = {}

    def add_point(self, point, availability):
        self.points[point.id] = [point, availability]

    def delete_point(self, point):
        if point in self.points:
            del self.points[point.id]

    def update_availability(self, id, method, sit = None, time = None):
        if method == 1:
            if is_in_schedule(self.points[id][0].schedule, time) == True:
                self.points[id][1] = True
            else: 
                self.points[id][1] = False
        if method == 2: 
            if sit == 'take':
                self.points[id][1] = False
                self.points[id][0].taken = True 
            elif sit == 'return':
                self.points[id][1] = True
                self.points[id][0].taken = False 
                            
    def points_within_radius(self, user_loc, radius):
        # Initialize an empty list to store the points within the circle
        distances = [(key, i.distance_from(user_loc)) for key, (i, _) in self.points.items()]
        distances.sort(key = lambda v : v[1])
        top_24 = distances[:24]
        return dict([(key, (self.points[key][0].x, self.points[key][0].y)) for key, _ in top_24])
    
def fallback_position(ip_addr):
    ipinfo_url = "https://ipinfo.io/{}/json?token=89232058aa0651".format(ip_addr)
    response = json.loads(requests.post(ipinfo_url).content)['loc'].split(',')
    return (float(response[0]), float(response[1]))

def is_in_schedule(schedule, datetime_obj):
    day_of_week = datetime_obj.strftime("%A")

    if day_of_week not in schedule:
        return True 

    if schedule[day_of_week] == 0:
        return False

    intervals = schedule[day_of_week]
    intervals = intervals.strip('[]').split(', ')

    intervals_fix = []
    for interval in intervals:
        splits = interval.split('-')
        interval_lst = []
        interval_lst = [element.strip() for element in splits]
        intervals_fix.append(interval_lst)

    for start, end in intervals_fix:
        pattern = r'^\d{2}'
    
        match_start = re.search(pattern, start)
        match_end = re.search(pattern, end)
        if bool(match_start) == True:
            if int(start[:2]) > 12:
                new_num = int(start[:2]) - 12
                start = str(new_num) + start[2:]
        if bool(match_end) == True:
            if int(end[:2]) > 12:
                new_num = int(end[:2]) - 12
                end = str(new_num) + end[2:]
    
        if start == '0 PM':
            start = '12 PM'
        if start == '0 AM':
            start = '12 AM'
        if end == '0 PM':
            end = '12 PM'
        if end == '0 AM':
            end = '12 AM'
        if start == '3PM':
            start = '3 PM'
        if end == '3PM':
            end = '3 PM'
        
        try:
            start_time = datetime.strptime(start, '%I %p').time()
        except ValueError:
            try:
                start_time = datetime.strptime(start, '%I:%M %p').time()
            except ValueError:
                if start.startswith('0'):
                    start = '12' + start[1:]
                    start_time = datetime.strptime(start, '%I:%M %p').time()
                else:
                    raise ValueError(f"Time data '{start}' does not match format '%I:%M %p'")

        try:
            end_time = datetime.strptime(end, '%I %p').time()
        except ValueError:
            try:
                end_time = datetime.strptime(end, '%I:%M %p').time()
            except ValueError:
                if end.startswith('0'):
                    end = '12' + end[1:]
                    end_time = datetime.strptime(end, '%I:%M %p').time()
                else:
                    raise ValueError(f"Time data '{end}' does not match format '%I:%M %p'")      

        if start_time <= datetime_obj.time() <= end_time:
            return True

    return False

gmaps = googlemaps.Client(key='AIzaSyCHT_UZ49tsasFakgDUVha05snFVsUbq-M')

def find_quickest_destinations(start_location, destinations):
    travel_times_driving = {}
    travel_times_walking = {}
    for id, destination in destinations.items():
        directions_driving = gmaps.directions(start_location, destination, mode="driving")
        directions_walking = gmaps.directions(start_location, destination, mode="walking")
        if directions_driving:
            travel_time_driving = directions_driving[0]['legs'][0]['duration']['value']
            travel_times_driving[id] = travel_time_driving
        if directions_walking:
            travel_time_walking = directions_walking[0]['legs'][0]['duration']['value']
            travel_times_walking[id] = travel_time_walking

    quickest_driving = min(travel_times_driving, key=travel_times_driving.get)
    quickest_walking = min(travel_times_walking, key=travel_times_walking.get)

    return quickest_driving, quickest_walking

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=external_stylesheets)

maps = None

def initialize_database():
    global maps
    all_aeds = pd.read_excel('aed_all_inv.xlsx', engine='openpyxl')
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"]
    start_index = 15227

    last_1000_rows = all_aeds.iloc[start_index:]
    last_1000_rows = last_1000_rows.copy()
    last_1000_rows[['latitude', 'longitude']] = last_1000_rows[['longitude', 'latitude']]

    all_aeds.iloc[start_index:] = last_1000_rows
    all_aeds = all_aeds.dropna(subset=['longitude'])

    all_aeds = all_aeds.reset_index(drop=True)

    for column in weekdays:
        all_aeds[column] = all_aeds[column].apply(lambda x: x.strip() if isinstance(x, str) and x[-1] != ']' else x)

    maps = MapAEDS()
    for i in range(0, len(all_aeds)):
        dict_schedule = {}
        for weekday in weekdays:
            if isinstance(all_aeds[weekday][i] , str) or all_aeds[weekday][i] == 0:
                dict_schedule[weekday] = all_aeds[weekday][i]            
        point = AEDPoint(i, all_aeds['latitude'][i], all_aeds['longitude'][i], all_aeds['address'][i], all_aeds['location'][i], dict_schedule, False)
        maps.add_point(point, True)

    
    current_time = datetime.now()
    i = 0
    for point in maps.points:
        if maps.points[point][0].taken == False:
            maps.update_availability(point, 1, time = current_time)
        i += 1

@server.route('/update_location', methods=['POST'])
def update_location():
    global user_location
    data = request.json
    user_location = (data['latitude'], data['longitude'])
    return jsonify(success=True)

def generate_map(start_location, destination_driving, destination_walking, directions_driving, directions_walking):
    m = folium.Map(location=start_location, zoom_start=18)
    
    folium.Marker(
        location=start_location,
        popup="Your Location",
        icon=folium.Icon(color="green")
    ).add_to(m)

    folium.Marker(
        location=destination_driving,
        popup="Nearest AED by Drive",
        icon=folium.Icon(color="red")
    ).add_to(m)

    folium.Marker(
        location=destination_walking,
        popup="Nearest AED by Walk",
        icon=folium.Icon(color="blue")
    ).add_to(m)
    
    if directions_driving:
        decoded_driving = polyline.decode(directions_driving)
        folium.PolyLine(decoded_driving, color="red", weight=2.5, opacity=1, tooltip="Driving Route").add_to(m)
        
    if directions_walking:
        decoded_walking = polyline.decode(directions_walking)
        folium.PolyLine(decoded_walking, color="blue", weight=2.5, opacity=1, tooltip="Walking Route").add_to(m)

    return m

def update_map(user_location, quickest_driving, quickest_walking, selected_mode):
    global maps
    driving_location = (maps.points[quickest_driving][0].x, maps.points[quickest_driving][0].y)
    walking_location = (maps.points[quickest_walking][0].x, maps.points[quickest_walking][0].y)

    directions_driving = gmaps.directions(user_location, driving_location, mode="driving")
    directions_walking = gmaps.directions(user_location, walking_location, mode="walking")

    directions_driving_polyline = directions_driving[0]['overview_polyline']['points']
    directions_walking_polyline = directions_walking[0]['overview_polyline']['points']

    if selected_mode == 'driving':
        map_object = generate_map(user_location, driving_location, walking_location, directions_driving_polyline, None)
    elif selected_mode == 'walking':
        map_object = generate_map(user_location, driving_location, walking_location, None, directions_walking_polyline)
    else:
        map_object = generate_map(user_location, driving_location, walking_location, directions_driving_polyline, directions_walking_polyline)

    return map_object._repr_html_(), directions_driving, directions_walking

ambulancecall = 'AmbulanceLogo.jpg'
ambulancecalllogo = base64.b64encode(open(ambulancecall, 'rb').read()).decode('ascii')

log_png = 'AED_Bel.png'
log_base64 = base64.b64encode(open(log_png, 'rb').read()).decode('ascii')

app.layout = html.Div([
    html.Div([
    html.Img(src='data:image/png;base64,{}'.format(log_base64), width=100, style={'display': 'inline-block'}),
    html.H1("AED Locator", style={'text-align': 'center', 'display': 'inline-block'}),
    dcc.Geolocation(id='user_loc'), ], 
    ),
    
    html.Div([
        html.Label("Choose a mode of travel (You may only choose 1):"),
        dcc.RadioItems(
            id='mode-selection',
            options=[
                {'label': 'Driving', 'value': 'driving'},
                {'label': 'Walking', 'value': 'walking'}
            ],
            value=None,
            labelStyle={'display': 'inline-block'}
        )
    ]),
    html.Iframe(
        id='map',
        width='100%',
        height='600'
    ),
    html.Div(
        children=[
            html.Div(
                id='route-legend',
                children=[
                    html.Div([
                        html.Span(style={'display': 'inline-block', 'width': '20px', 'height': '20px', 'background-color': 'red', 'margin-right': '10px'}),
                        "Driving Route"
                    ], style={'margin-bottom': '5px'}),
                    html.Div([
                        html.Span(style={'display': 'inline-block', 'width': '20px', 'height': '20px', 'background-color': 'blue', 'margin-right': '10px'}),
                        "Walking Route"
                    ])
                ],
                style={
                    'border': '1px solid grey',
                    'border-radius': '3px',
                    'padding': '5px',
                    'width': '180px',
                    'margin-top': '10px',
                    'background-color': 'white',
                    'font-family': 'Arial, sans-serif',
                    'font-size': '14px',
                    'display': 'inline-block'
                }
            ),
            html.Div(
                id='marker-legend',
                children=[
                    html.Div([
                        html.Img(src='https://maps.google.com/mapfiles/ms/icons/green-dot.png', style={'height': '20px', 'margin-right': '10px'}),
                        "You are here"
                    ], style={'margin-bottom': '5px'}),
                    html.Div([
                        html.Img(src='https://maps.google.com/mapfiles/ms/icons/red-dot.png', style={'height': '20px', 'margin-right': '10px'}),
                        "Nearest AED by Drive"
                    ]),
                    html.Div([
                        html.Img(src='https://maps.google.com/mapfiles/ms/icons/blue-dot.png', style={'height': '20px', 'margin-right': '10px'}),
                        "Nearest AED by Walk"
                    ])
                ],
                style={
                    'border': '1px solid grey',
                    'border-radius': '3px',
                    'padding': '5px',
                    'width': '180px',
                    'margin-top': '10px',
                    'background-color': 'white',
                    'font-family': 'Arial, sans-serif',
                    'font-size': '14px',
                    'display': 'inline-block',
                    'margin-left': '20px'
                }
            ),
            html.Div(
                id='address',
                style={
                    'padding': '10px',
                    'display': 'inline-block',
                    'vertical-align': 'middle',
                    'margin-left': '20px',
                    'font-family': 'Arial, sans-serif',
                    'font-size': '14px',
                    'border': '1px solid grey',
                    'border-radius': '3px',
                    'background-color': 'white'
                }
            ),
            
    html.A(
        href='tel:112',
        children=html.Img(
            src='data:image/png;base64,{}'.format(ambulancecalllogo), style={'transform': 'scale(0.3)'} 
        ),
    
)
        ],
        style={'display': 'flex', 'align-items': 'center'}
    ),
    dcc.Store(id='user_state'),
    dcc.Interval(
        id='interval-component',
        interval=10*1000,
        n_intervals=0
    ),
    html.Div(id='status', style={'padding': '20px'}),
    html.Div(id='directions-container', children=[
        html.H2("Directions to AED", style={'margin-bottom': '10px'}),
        html.Div(id='directions', style={
            'border': '1px solid grey',
            'border-radius': '3px',
            'padding': '10px',
            'background-color': 'white',
            'font-family': 'Arial, sans-serif',
            'font-size': '14px',
            'max-height': '400px',  # Increased height for better visibility
            'overflow-y': 'auto'  # Enable scrolling if content exceeds the container height
        })
    ], style={'padding': '20px', 'width': '90%', 'margin': '0 auto'}),  # Increased width for better visibility
    html.Div([
        html.Div([
            html.H2("How to Operate an AED", style={'margin-bottom': '10px', 'display': 'inline'}),
            html.Iframe(
                src="https://www.youtube.com/embed/2PJR0JyLPZY",
                width="100%",
                height="315",
                style={'border': 'none', 'display': 'inline'}
            ),
        ], style={'flex': '1', 'padding': '10px', 'display': 'inline-block'}),
        html.Div([
            html.H2("What to do in case of a cardiac arrest (If you do not have immediate access to an AED)", style={'margin-bottom': '10px', 'display': 'inline'}),
            html.Iframe(
                src="https://www.youtube.com/embed/-NodDRTsV88",
                width="100%",
                height="315",
                style={'border': 'none', 'display': 'inline'}
            ),
        ], style={'flex': '1', 'padding': '10px', 'display': 'inline-block'})
    ], style={'display': 'inline-block', 'flex-direction': 'row', 'align-items': 'flex-start'})
])

@app.callback(
    [Output('map', 'srcDoc'),
     Output('address', 'children'),
     Output('user_state', 'data'),
     Output('directions', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('mode-selection', 'value'),
     Input('user_loc', 'position'),
     Input('user_state','data')]
)
def update_map_interval(n, selected_mode, user_loc, user_state):
    quickest_driving, quickest_walking = None, None
    if user_loc is None:
        user_loc = fallback_position(request.remote_addr)
    else:
        user_loc = (user_loc['lat'], user_loc['lon'])
    previous_distance = None
    if user_state is None:
        quickest_driving, quickest_walking = find_quickest_destinations(user_loc, maps.points_within_radius(user_loc, 10.8))
        previous_distance = user_loc
    else:
        quickest_driving = user_state['quickest_driving']
        quickest_walking = user_state['quickest_walking']
        previous_distance = user_state['previous_distance']
        if geodesic(user_loc, previous_distance).km > 5:
            quickest_driving, quickest_walking = find_quickest_destinations(user_loc, maps.points_within_radius(user_loc, 10.8))
            previous_distance = user_loc

    map_html, directions_driving, directions_walking = update_map(user_loc, quickest_driving, quickest_walking, selected_mode)
    
    if selected_mode == 'driving':
        address = maps.points[quickest_driving][0].address
        directions = directions_driving[0]['legs'][0]['steps']
        travel_time = directions_driving[0]['legs'][0]['duration']['text']
    elif selected_mode == 'walking':
        address = maps.points[quickest_walking][0].address
        directions = directions_walking[0]['legs'][0]['steps']
        travel_time = directions_walking[0]['legs'][0]['duration']['text']
    else:
        address = maps.points[quickest_driving][0].address if quickest_driving == quickest_walking else f"Nearest AED by Drive: {maps.points[quickest_driving][0].address}\nNearest AED by Walk: {maps.points[quickest_walking][0].address}"
        directions = []
        travel_time = ""

    directions_text = []
    if directions:
        for step in directions:
            instructions = re.sub('<[^<]+?>', '', step['html_instructions'])  # Remove HTML tags
            directions_text.append(html.Li(instructions))

    return (
        map_html, 
        html.Div([html.Div(f"AED Location: {address}"), html.Div(f"Expected Time of Arrival: {travel_time}")]),
        {"quickest_driving": quickest_driving, "quickest_walking": quickest_walking, "previous_distance": previous_distance}, 
        html.Ul(directions_text)
    )

@app.callback(Output('status', 'children'), [Input('interval-component', 'n_intervals'), Input('user_state','data')])
def update_availability(n, user_state):
    if(user_state == None):
        return ""
    quickest_driving = user_state['quickest_driving']
    quickest_walking = user_state['quickest_walking']
    if n > 0 and n % 180 == 0:
        maps.update_availability(quickest_driving, 2, sit='return')
        maps.update_availability(quickest_walking, 2, sit='return')
        return "AED has been returned and is now available again."
    return ""

initialize_database()
if __name__ == '__main__':
    app.run(jupyter_mode="external", port=8063)