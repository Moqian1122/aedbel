#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
from datetime import datetime
import re
import googlemaps
import os
import geocoder
import geopy.distance
import math
import pandas as pd
from geopy.distance import geodesic
import requests
import folium
import polyline
from flask import Flask, request, jsonify, render_template_string
import threading
import time
from IPython.display import display, Javascript
import ipinfo
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import sys
import dash_leaflet as dl
import json
from threading import Thread


# In[2]:


class AEDPoint:
    def __init__(self, id, x, y, address, indication, schedule, taken):
        self.id = id
        self.x = x
        self.y = y
        self.address = address
        self.indication = indication
        self.schedule = schedule
        self.taken = taken

class MapAEDS:
    def __init__(self):
        self.points = {}

    def add_point(self, point, availability):
        self.points[point.id] = [point, availability]
        print("Succesfully Added")

    def delete_point(self, point):
        if point in self.points:
            del self.points[point.id]
            print(f"Point with ID {point.id} deleted.")
        else:
            print("Point ID not found.")

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
        points_within_circle = {}
        while radius > 0:
            points_within_circle = {}
            found_points = 0  # Track the number of points found within the current radius
            for point in self.points:
                if self.points[point][1] == True:
                    # Get the longitude and latitude from the row
                    lat, lon = self.points[point][0].x, self.points[point][0].y
                    if lon < -90 or lon > 90 or lat < -90 or lat > 90:
                        continue
                    # Calculate the distance from the point to the center of the circle
                    distance = geodesic((lat, lon), user_loc).km
                    # If the distance is less than or equal to the radius, add the point to the list
                    if distance <= radius:
                        points_within_circle[point] = (lat, lon)
                        print(points_within_circle)
                        found_points += 1
                        if found_points == 24:
                            break
            if 0 < found_points <= 23:
                break  # If no points were found within the current radius, exit the loop
            elif found_points == 0:
                radius += 5 # Increase radius
            else:
                radius -= 0.5
            print(points_within_circle)

        return points_within_circle


# In[11]:


user_loc = (50.8796, 4.7009)


# In[12]:


# Define the IPinfo token
access_token = 'c1f3a0faf18207'  # Replace with your IPinfo token

# JavaScript to get geolocation with a fallback to IPinfo
javascript_code = f"""
let initialLocationSet = false;

function getLocation() {{
    if (navigator.geolocation) {{
        // Set up a watcher to continuously get the user's location
        navigator.geolocation.watchPosition(
            showPosition,
            fallbackPosition,
            {{
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            }}
        );
    }} else {{
        alert("Geolocation is not supported by this browser.");
        fallbackPosition();
    }}
}}

function showPosition(position) {{
    var latitude = position.coords.latitude;
    var longitude = position.coords.longitude;

    // Send the coordinates to the Python server
    fetch('/update_location', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
        }},
        body: JSON.stringify({{ latitude: latitude, longitude: longitude }}),
    }});

    if (!initialLocationSet) {{
        // Send initial location to Python kernel
        var py_coords = IPython.notebook.kernel.execute("user_loc = (" + latitude + ", " + longitude + ")");
        initialLocationSet = true;
    }}
}}

function fallbackPosition(error) {{
    var ipinfo_url = "https://ipinfo.io?token={access_token}";

    fetch(ipinfo_url)
        .then(response => response.json())
        .then(data => {{
            var loc = data.loc.split(',');
            var latitude = loc[0];
            var longitude = loc[1];

            // Send the coordinates to the Python server
            fetch('/update_location', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify({{ latitude: parseFloat(latitude), longitude: parseFloat(longitude) }}),
            }});

            if (!initialLocationSet) {{
                // Send initial location to Python kernel
                var py_coords = IPython.notebook.kernel.execute("user_loc = (" + parseFloat(latitude) + ", " + parseFloat(longitude) + ")");
                initialLocationSet = true;
            }}
        }})
        .catch(error => console.error('Error fetching IP info:', error));
}}

getLocation();
"""

# Display the JavaScript
display(Javascript(javascript_code))


# In[13]:


try:
    print(f"User location: {user_loc}")
except NameError:
    print("Coordinates not set. Ensure the JavaScript code executed correctly.")


# In[14]:


#user_loc = (50.8695275, 4.6984257)


# In[15]:


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
    print(intervals)
    intervals_fix = []
    for interval in intervals:
        splits = interval.split('-')
        interval_lst = []
        interval_lst = [element.strip() for element in splits]
        intervals_fix.append(interval_lst)
    print(intervals_fix)

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


# In[16]:


all_aeds = pd.read_excel(os.path.expanduser('~/Modern Data Analytics/Front-end/aed_all_inv.xlsx'))
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


# In[17]:


# Example usage:
maps = MapAEDS()
for i in range(0, len(all_aeds)):
    dict_schedule = {}
    for weekday in weekdays:
        if isinstance(all_aeds[weekday][i] , str) or all_aeds[weekday][i] == 0:
            dict_schedule[weekday] = all_aeds[weekday][i]            
    point = AEDPoint(i, all_aeds['latitude'][i], all_aeds['longitude'][i], all_aeds['address'][i], all_aeds['location'][i], dict_schedule, False)
    maps.add_point(point, True)


# In[18]:


current_time = datetime.now()
i = 0
for point in maps.points:
    if maps.points[point][0].taken == False:
        maps.update_availability(point, 1, time = current_time)
        print(i)
    i += 1


# In[19]:


nearby_points = maps.points_within_radius(user_loc, 10.8)


# In[20]:


# Define your starting location coordinates (latitude and longitude)
start_location = user_loc

# Define your list of destination points as coordinates (latitude and longitude)
destinations = nearby_points
gmaps = googlemaps.Client(key='AIzaSyCHT_UZ49tsasFakgDUVha05snFVsUbq-M')

# Calculate travel times to each destination
travel_times = {}
for id, destination in destinations.items():
    directions = gmaps.directions(start_location, destination, mode="driving")
    if directions:
        travel_time = directions[0]['legs'][0]['duration']['text']
        travel_times[id] = travel_time
    else:
        print(f"No route found for destination: {destination}")

# Find the destination with the shortest travel time
quickest_destination = min(travel_times, key=travel_times.get)
print(f"The quickest destination is: {quickest_destination} (travel time: {travel_times[quickest_destination]})")


# In[21]:


# Google MapsDdirections API endpoint
endpoint = 'https://maps.googleapis.com/maps/api/directions/json?'

# Parameters
origin_latitude = user_loc[0]
origin_longitude = user_loc[1]
destination_latitude = maps.points[quickest_destination][0].x
destination_longitude = maps.points[quickest_destination][0].y
api_key = 'AIzaSyCHT_UZ49tsasFakgDUVha05snFVsUbq-M' # Replace with your Google Maps API key

# Building the URL for the request
nav_request_driving = 'origin={},{}&destination={},{}&mode=driving&key={}'.format(origin_latitude, origin_longitude, destination_latitude, destination_longitude, api_key)
nav_request_walking = 'origin={},{}&destination={},{}&mode=walking&key={}'.format(origin_latitude, origin_longitude, destination_latitude, destination_longitude, api_key)

# Sends the request and reads the response.
response_driving = requests.get(endpoint + nav_request_driving).json()
response_walking = requests.get(endpoint + nav_request_walking).json()

# Create map
m = folium.Map(location=[origin_latitude, origin_longitude], zoom_start=14)

# Get the polyline data from the result
points_driving = response_driving['routes'][0]['overview_polyline']['points']
points_walking = response_walking['routes'][0]['overview_polyline']['points']
decoded_driving = polyline.decode(points_driving)
decoded_walking = polyline.decode(points_walking)

# Create a PolyLine object using the points data and add it to the map
folium.PolyLine(decoded_driving, color="red", weight=2.5, opacity=1).add_to(m)
folium.PolyLine(decoded_walking, color="blue", weight=2.5, opacity=1).add_to(m)

# Display the map
m


# In[22]:


maps.update_availability(quickest_destination, 2, sit = 'take')

#After 30 minutes, or if user clicks on it:
maps.update_availability(quickest_destination, 2, sit = 'return')


# In[23]:


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Create a Dash application
server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=external_stylesheets)

user_location = user_loc

@server.route('/update_location', methods=['POST'])
def update_location():
    global user_location
    data = request.json
    user_location = (data['latitude'], data['longitude'])
    return jsonify(success=True)

# Function to generate the map as a folium object
def generate_map(start_location, destination_driving, destination_walking):
    m = folium.Map(location=start_location, zoom_start=14)
    
    # Get the polyline data from the result
    decoded_driving = polyline.decode(destination_driving)
    decoded_walking = polyline.decode(destination_walking)
    
    # Create a PolyLine object using the points data and add it to the map
    folium.PolyLine(decoded_driving, color="red", weight=2.5, opacity=1).add_to(m)
    folium.PolyLine(decoded_walking, color="blue", weight=2.5, opacity=1).add_to(m)
    
    return m

# Update map based on latest location
def update_map():
    global user_location
    
    directions_driving = gmaps.directions(user_location, (maps.points[quickest_destination][0].x, maps.points[quickest_destination][0].y), mode="driving")
    directions_walking = gmaps.directions(user_location, (maps.points[quickest_destination][0].x, maps.points[quickest_destination][0].y), mode="walking")
    
    destination_driving = directions_driving[0]['overview_polyline']['points']
    destination_walking = directions_walking[0]['overview_polyline']['points']
    
    map_object = generate_map(user_location, destination_driving, destination_walking)
    
    return map_object._repr_html_()

# Define the layout of the app
app.layout = html.Div([
    html.H1("AED Location Map"),
    html.Iframe(
        id='map',
        width='100%',
        height='600'
    ),
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # in milliseconds
        n_intervals=0
    ),
    html.Div(id='status', style={'padding': '20px'})
])

# Callback to update the map
@app.callback(
    Output('map', 'srcDoc'),
    [Input('interval-component', 'n_intervals')]
)
def update_map_interval(n):
    return update_map()

# Callback to update availability after 30 minutes
@app.callback(Output('status', 'children'), [Input('interval-component', 'n_intervals')])
def update_availability(n):
    time.sleep(30 * 60)  # Wait for 30 minutes
    maps.update_availability(quickest_destination, 2, sit='return')
    return "AED has been returned and is now available again."

# Run the app
if __name__ == '__main__':
    app.run(jupyter_mode="external", port = 8051)


# In[ ]:




