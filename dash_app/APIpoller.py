# General Imports:
import pandas as pd
import time
import threading
from datetime import datetime
from decimal import Decimal

# Handle Exit Signals
import atexit

# API Client Imports:
import iot_api_client
from iot_api_client.rest import ApiException
import  iot_api_client.apis.tags.devices_v2_api as DevicesV2
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# Dash-Based Imports:
import plotly.express as px
from dash import Dash, html, dcc
from dash.dependencies import Input, Output

# Map Generation Imports:
import folium
import sys
import os

# Determine if the app is "frozen" and running as an executable
if getattr(sys, 'frozen', False):
    # If the app is running as a frozen executable, the base path is set to sys._MEIPASS
    application_root = sys._MEIPASS
else:
    # If running in a development environment, use the current directory as the base path
    application_root = os.path.dirname(os.path.abspath(__file__))

# Specify the assets folder path relative to the determined base path
assets_folder = os.path.join(application_root, 'assets/')
print(f"Assets folder: {assets_folder}")
# Initialize the Dash app with the dynamically determined assets folder
app = Dash(__name__)

# Initialize our Dataframe
prop_df = pd.DataFrame(columns = ['Timestamp','Accelerometer_Linear','Accelerometer_X','Accelerometer_Y','Accelerometer_Z','Brightness', 'Compass', 'Magnetometer_X', 'Sound_Level', 'Sound_Pitch', 'Gps'])

# Multithreading Handling
lock = threading.Lock()
running = True # Global flag to control the main loop
shutdown_event = threading.Event()

# Inactivity Handling
last_seen = "Placeholder"
inactive_count = 0


"""Dashboard Layout"""
app.layout = html.Div([
 
    # Container for the title and logo
    html.Div([
        html.Img(src='/assets/UGR.png', style={'width': '200px', 'height': 'auto'}),
        html.H1("Telemetry Dashboard", className='dashboard-header'),
    ], className='title-container'),
      

    # Container for the first two items (iframe and graph)
    html.Div(className='dashboard-container', children=[
        # Card effect container for the iframe
        html.Div(className='card-effect', children=[
            html.Iframe(id='live-update-map')
        ]),

        dcc.Graph(id='Accel_Lin', className='graph-container'),
    ]),

    # Container for the next three graphs
    html.Div(className='graph-container', children=[
        dcc.Graph(id='Accel_X', className='graph-item'),
        dcc.Graph(id='Accel_Y', className='graph-item'),
        dcc.Graph(id='Accel_Z', className='graph-item'),
    ]),

    # Interval component to trigger updates, set to 1.3 seconds
    dcc.Interval(id='interval-component', interval=1300, n_intervals=0),
])



"""Callback function to handle exit signals"""
def cleanup():
    global running
    running = False
    # Please don't add pre-exit code here, cleanup gets executed by all threads.
        # Pre-Exit code should be added in the "finally" section of the main thread.
    


# TODO: Abstract this out into a separate file ?
# function to fetch and format api data into a pandas dataframe
def fetch_and_format_api_data(api_instance):
    global prop_df, meta_df, last_seen, inactive_count, running

    # Bug Handling to do with Multithreading
    if not running:
        return

    def handle_special_data(value):
        if isinstance(value, Decimal):
            return float(value)
        elif hasattr(value, '__dict__'):  # checks if the value is an object that can be converted to a dict
            value = dict(value)  # convert dynamicschema or similar objects to dict
            return ', '.join([f"{k}: {float(v)}" for k, v in value.items()])
        else:
            return value

    # Multithreading lock
    with lock:
        print("Fetching data...")
        try:
            resp = api_instance.devices_v2_list()
            devices = resp.__dict__ 
            body_data = devices['body'][0]  
            props = devices['body'][0]['thing']['properties']
            
            # Check if the device has been inactive for over 10 seconds (8 consecutive checks of 1.5ish second each)
            if body_data['last_activity_at'] == last_seen:
                if inactive_count < 8: 
                    inactive_count += 1 
                else:
                    print("\n\nDevice inactive for over 10 seconds, exiting...")
                    cleanup()
                    return
            else:
                inactive_count = 0
                
            last_seen = body_data['last_activity_at']

            timestamp = datetime.now()
            # Extract and format the nested API response data
            prop_df.loc[timestamp] = {
                'Timestamp' : timestamp,
                'Accelerometer_Linear': handle_special_data(props[0]['last_value']),
                'Accelerometer_X': handle_special_data(props[1]['last_value']),
                'Accelerometer_Y': handle_special_data(props[2]['last_value']),
                'Accelerometer_Z': handle_special_data(props[3]['last_value']),
                'Brightness': props[4]['last_value'],
                'Compass': handle_special_data(props[5]['last_value']),
                'Magnetometer_X': props[6]['last_value'],
                'Sound_Level': props[7]['last_value'],
                'Sound_Pitch': handle_special_data(props[8]['last_value']),
                'Gps': handle_special_data(props[9]['last_value'])
            }

            # Bug Fix: Don't Touch
            if running:
                print(prop_df)

        except ApiException as e:
            print(f"an exception occurred: {e}")



"""Parse the GPS string format into latitude and longitude."""
def parse_gps(gps_str):
    try:
        lat, lon = gps_str.split(', ')
        lat_val = float(lat.split(': ')[1])
        lon_val = float(lon.split(': ')[1])
        print(lat_val, lon_val)
        return lat_val, lon_val
    except ValueError:
        # Handle the case where parsing fails
        return None, None


"""Folium GPS Map Creation"""
def create_folium_map(df):
    # Assuming the first row has valid GPS data to center the map
    with lock:    
        first_lat, first_lon = parse_gps(df['Gps'].iloc[0])
    m = folium.Map(location=[first_lat, first_lon], zoom_start=15)
    with lock: 
        gps_strs = df['Gps']

    for gps_str in gps_strs:
        lat, lon = parse_gps(gps_str)
        if lat and lon:
            folium.Marker([lat, lon]).add_to(m)
    
    # Save the map to an HTML file
    m.save('map.html')
    return 'map.html'


"""
This function will update the graph info for the Dash Ouputs: 
"Accel_Lin", "Accel_X", "Accel_Y", "Accel_Z"

On update of input: 
"interval-component"

Which is set to 1.3 seconds in the layout
"""
@app.callback(
    [Output('Accel_Lin', 'figure'),
    Output('Accel_X', 'figure'),
    Output('Accel_Y', 'figure'),
    Output('Accel_Z', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_graph(n):
    global prop_df, lock

    # Optimisation: 
    # As we must keep the data in prop_df locked while accessing, we can copy the data to a new dataframe
    # This will allow the API thread to continue running/appending while this data gets processed into plots

    with lock:
        dff = prop_df.copy()

    # Generate the figures with transparent backgrounds
    figures = []
    for axis in ['Accelerometer_Linear', 'Accelerometer_X', 'Accelerometer_Y', 'Accelerometer_Z']:
        fig = px.line(dff, x='Timestamp', y=axis)
        fig.update_layout({
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'font': {
                'color': '#ccc'
            }
        })
        fig.update_traces(line=dict(color='#DAA520'),  # Darker shade of yellow for the line
                          marker=dict(color='#FFFF00', size=10))  # Lighter yellow for points with specified size
        figures.append(fig)    


    return figures

"""
This function will update the graph info for the Dash Ouputs: 
"live-update-map"

On update of input: 
"interval-component"

Which is set to 1.3 seconds in the layout
"""
@app.callback(
    [Output('live-update-map', 'srcDoc')],
    [Input('interval-component', 'n_intervals')]
    )
def update_map(n):
    global prop_df, lock

    with lock:
        dff = prop_df.copy()


    map_html = create_folium_map(dff)
    try:
        # Attempt to read the HTML content of the map
        with open(map_html, 'r') as file:
            map_html_content = file.read()
        return [map_html_content]  # Return the content in a list to match the expected output structure
    except Exception as e:
        print(f"Error reading map HTML file: {e}")
        return ["Map is not available"]  # Return an error message if unable to read the file



def setup():
    # Setup the OAuth2 session that'll be used to request the server an access token
    oauth_client = BackendApplicationClient(client_id="objUzAHRP41Qti2luhQ9MD8LKf92p7CT")
    token_url = "https://api2.arduino.cc/iot/v1/clients/token"
    oauth = OAuth2Session(client=oauth_client)

    # This will fire an actual HTTP call to the server to exchange client_id and
    # client_secret with a fresh access token
    token = oauth.fetch_token(
        token_url=token_url,
        client_id="objUzAHRP41Qti2luhQ9MD8LKf92p7CT",
        client_secret="DTAkkcoZkqr18mqbybl3vVYShz0K20lrZKu5o2CPvOsaH1aCNxvmwlI3See0htU0",
        include_client_id=True,
        audience="https://api2.arduino.cc/iot",
    )

    # If we get here we got the token, print its expiration time
    print("Got a token, expires in {} seconds".format(token.get("expires_in")))

    # Now we setup the iot-api Python client, first of all create a
    # configuration object. The access token goes in the config object.
    client_config = iot_api_client.Configuration(host = "https://api2.arduino.cc/iot")
    # client_config.debug = True
    client_config.access_token = token.get("access_token")

    # Create the iot-api Python client with the given configuration
    api_client = iot_api_client.ApiClient(client_config)

    # Each API model has its own wrapper, here we want to interact with
    # devices, so we create a DevicesV2Api object
    api_instance = DevicesV2.DevicesV2Api(api_client)
    print("API instance created", api_instance)
    return api_instance


""" MULTITHREADED DATA CALLING: PLEASE DON'T TOUCH IF YOU DON'T KNOW WHAT YOU'RE DOING"""
# Function to continuously update data
def continuous_data_update(api_instance, update_interval=1):
    global running
    print("Starting continuous data update")
    while running:
        try:
            fetch_and_format_api_data(api_instance)
            time.sleep(update_interval)  # Wait for the specified update interval
        except:
            print("Error in continuous_data_update")
            break
    print("Exiting continuous data update")
    shutdown_event.set()  # Signal the shutdown event


def main():
    global running, prop_df

    # Setup the API Client
    api_instance = setup()
       
    """MULTITHREADING HANDLER: PLEASE DONT TOUCH IF YOU DONT KNOW WHAT YOU'RE DOING"""
        # Define a route within your Dash app to handle shutdown
    @app.server.route('/shutdown', methods=['POST'])
    def shutdown():
        shutdown_server()
        return 'Server shutting down...'
    # Start continuous data update in a background thread
    update_thread = threading.Thread(target=continuous_data_update, args=(api_instance, 1.5))
    update_thread.start()

    """ END OF MULTITHREADING HANDLER """
    
    # Register cleanup function to be called on exit
    atexit.register(cleanup)

    # Optimisation: Keep Dash up until shutdown event is set, don't let end of data transmission kill it
    try:
        # Run the Dash app
        while not shutdown_event.is_set():
            app.run_server() 


    except KeyboardInterrupt:
        print("Keyboard Interrupt Detected. Exiting...")

    # Cleanup of threads and data
    finally:
        cleanup() 
        print("Cleaning up...")
        update_thread.join()
        print("Exiting main thread")
        try:
            with lock:
                # Writing data to a csv file
                try:
                    prop_df.to_csv('data.csv', index=False)
                    print("Data saved to data.csv")
                except Exception as e:
                    print(f"An exception occurred while saving data: {e}")
        except Exception as e:
            print(f"An exception occurred while cleaning up: {e}")
        finally:
            # User feedback
            print("Program Exited Cleanly")

if __name__ == "__main__":
    main()
