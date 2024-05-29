#!/usr/bin/env python
# coding: utf-8

# packages need to be specified in the requirements.txt
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

# packages do not need to be specified in the requirements.txt
import re
import math
import json


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
    # Get the day of the week from the datetime object
    day_of_week = datetime_obj.strftime("%A")

    # Check if the day is in the schedule
    if day_of_week not in schedule:
        return True 

    if schedule[day_of_week] == 0:
        return False

    # Get the intervals for the day from the schedule
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
    
        # Use the search function to find if the pattern matches the string
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

        # Check if the datetime falls within this interval
        if start_time <= datetime_obj.time() <= end_time:
            return True

    # If none of the intervals match, return False
    return False



gmaps = googlemaps.Client(key='AIzaSyCHT_UZ49tsasFakgDUVha05snFVsUbq-M')

def find_quickest_destinations(start_location, destinations):
    # Calculate travel times to each destination
    travel_times = {}
    for id, destination in destinations.items():
        directions = gmaps.directions(start_location, destination, mode="driving")
        if directions:
            travel_time = directions[0]['legs'][0]['duration']['text']
            travel_times[id] = travel_time
        else:
            print(f"No route found for destination: {destination}")

    # # Find the destination with the shortest travel time
    return min(travel_times, key=travel_times.get)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Create a Dash application
server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=external_stylesheets)

# user_location = user_loc
maps = None

def initialize_database():
    global maps
    all_aeds = pd.read_excel('aed_all_inv.xlsx', engine='openpyxl')
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"]
    start_index = 15227

    # Select the last 1000 rows starting from the defined index until the end and swap latitude and longitude columns within that subset
    last_1000_rows = all_aeds.iloc[start_index:]
    last_1000_rows = last_1000_rows.copy()
    last_1000_rows[['latitude', 'longitude']] = last_1000_rows[['longitude', 'latitude']]

    # Update the last 1000 rows in the original DataFrame
    all_aeds.iloc[start_index:] = last_1000_rows
    all_aeds = all_aeds.dropna(subset=['longitude'])

    # Reset index
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

# Function to generate the map as a folium object
def generate_map(start_location, destination, destination_driving, destination_walking, display_driving, display_walking):
    m = folium.Map(location=start_location, zoom_start=18)  # Increased zoom_start for closer view
    
    # Add marker for the user's current location
    folium.Marker(
        location=start_location,
        popup="Your Location",
        icon=folium.Icon(color="green")
    ).add_to(m)
    
    # Add marker for the AED destination
    folium.Marker(
        location=destination,
        popup="AED Location",
        icon=folium.Icon(color="red")
    ).add_to(m)
    
    if display_driving:
        decoded_driving = polyline.decode(destination_driving)
        folium.PolyLine(decoded_driving, color="red", weight=2.5, opacity=1, tooltip="Driving Route").add_to(m)
        
    if display_walking:
        decoded_walking = polyline.decode(destination_walking)
        folium.PolyLine(decoded_walking, color="blue", weight=2.5, opacity=1, tooltip="Walking Route").add_to(m)

    return m

# Update map based on latest location
def update_map(user_location, quickest_destination, display_driving, display_walking):
    global maps
    directions_driving = gmaps.directions(user_location, (maps.points[quickest_destination][0].x, maps.points[quickest_destination][0].y), mode="driving")
    directions_walking = gmaps.directions(user_location, (maps.points[quickest_destination][0].x, maps.points[quickest_destination][0].y), mode="walking")
    
    destination_driving = directions_driving[0]['overview_polyline']['points']
    destination_walking = directions_walking[0]['overview_polyline']['points']
    
    destination = (maps.points[quickest_destination][0].x, maps.points[quickest_destination][0].y)
    map_object = generate_map(user_location, destination, destination_driving, destination_walking, display_driving, display_walking)
    
    return map_object._repr_html_()


# Define the layout of the app
app.layout = html.Div([
    html.H1("AED Locator", style={'text-align': 'center'}),
    dcc.Geolocation(id='user_loc'),
    
    html.Div([
        dcc.Checklist(
            id='mode-selection',
            options=[
                {'label': 'Driving', 'value': 'driving'},
                {'label': 'Walking', 'value': 'walking'}
            ],
            value=['driving', 'walking'],
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
                        "Location of AED"
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
            )
        ],
        style={'display': 'flex', 'align-items': 'center'}
    ),
    dcc.Store(id='user_state'),
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # in milliseconds
        n_intervals=0
    ),
    html.Div(id='status', style={'padding': '20px'}),
    html.Div([
        html.Div([
            html.H2("How to Operate an AED", style={'margin-bottom': '10px'}),
            html.Iframe(
                src="https://www.youtube.com/embed/2PJR0JyLPZY",
                width="100%",
                height="315",
                style={'border': 'none'}
            ),
        ], style={'flex': '1', 'padding': '10px'}),
        html.Div([
            html.H2("What to do in case of a cardiac arrest (If you do not have immediate access to an AED)", style={'margin-bottom': '10px'}),
            html.Iframe(
                src="https://www.youtube.com/embed/-NodDRTsV88",
                width="100%",
                height="315",
                style={'border': 'none'}
            ),
        ], style={'flex': '1', 'padding': '10px'})
    ], style={'display': 'flex', 'flex-direction': 'row', 'align-items': 'flex-start'})
])

# Callback to update the map and address
@app.callback(
    [Output('map', 'srcDoc'),
     Output('address', 'children'),
     Output('user_state', 'data')],
    [Input('interval-component', 'n_intervals'),
     Input('mode-selection', 'value'),
     Input('user_loc', 'position'),
     Input('user_state','data')]
)
def update_map_interval(n, selected_modes, user_loc, user_state):
    quickest_destination = None
    if(user_loc == None):
        # Try to get from IP address
        user_loc = fallback_position(request.remote_addr)
    else:
        user_loc = (user_loc['lat'], user_loc['lon'])

    if(user_state == None):
        # It means the webapp is just loaded. Check the location first
        quickest_destination = find_quickest_destinations(user_loc, maps.points_within_radius(user_loc, 10.8))
    else:
        quickest_destination = user_state['quickest_destination']

    display_driving = 'driving' in selected_modes
    display_walking = 'walking' in selected_modes
    map_html = update_map(user_loc, quickest_destination, display_driving, display_walking)
    address = maps.points[quickest_destination][0].address
    return map_html, f"AED Location: {address}", { "quickest_destination" : quickest_destination }

# Callback to update availability after 30 minutes
@app.callback(Output('status', 'children'), [Input('interval-component', 'n_intervals'), Input('user_state','data')])
def update_availability(n, user_state):
    if(user_state == None):
        return ""
    quickest_destination = user_state['quickest_destination']
    if n > 0 and n % 180 == 0:  # Every 30 minutes
        maps.update_availability(quickest_destination, 2, sit='return')
        return "AED has been returned and is now available again."
    return ""

# Run the app
initialize_database()
if __name__ == '__main__':
    app.run(jupyter_mode="external", port=8051, host="0.0.0.0")




