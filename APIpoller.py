
import pandas as pd
import matplotlib.pyplot as plt
import time
import threading
import iot_api_client
from iot_api_client.rest import ApiException
import  iot_api_client.apis.tags.devices_v2_api as DevicesV2
import folium
import webbrowser
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
# from matplotlib.animation import funcanimation
from datetime import datetime
from decimal import Decimal
# Handle Exit Signals
import atexit

lock = threading.Lock()
prop_df = pd.DataFrame(columns = ['Accelerometer_Linear','Accelerometer_X','Accelerometer_Y','Accelerometer_Z','Brightness', 'Compass', 'Magnetometer_X', 'Sound_Level', 'Sound_Pitch', 'Gps'])
last_seen = "Placeholder"
inactive_count = 0
# Global Thread Control Flag
running = True

'''Callback function to handle exit signals '''
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
            else:
                inactive_count = 0
                
            last_seen = body_data['last_activity_at']


            # Extract and format the nested API response data
            prop_df.loc[datetime.now()] = {
                'Accelerometer_Linear': props[0]['last_value'],
                'Accelerometer_X': props[1]['last_value'],
                'Accelerometer_Y': props[2]['last_value'],
                'Accelerometer_Z': props[3]['last_value'],
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


''' 
MULTITHREADED DATA CALLING:
PLEASE DON'T TOUCH IF YOU DON'T KNOW WHAT YOU'RE DOING
'''
# Function to continuously update data
def continuous_data_update(api_instance, update_interval=1):
    global running
    print("Starting continuous data update")
    while running:
        fetch_and_format_api_data(api_instance)
        time.sleep(update_interval)  # Wait for the specified update interval


def main():
    global running

    # Setup the API Client
    api_instance = setup()
       
    ''' MULTITHREADING HANDLER:
    PLEASE DONT TOUCH IF YOU DONT KNOW WHAT YOU'RE DOING'''
    # Start continuous data update in a background thread
    update_thread = threading.Thread(target=continuous_data_update, args=(api_instance, 1.5))
    update_thread.start()
    
    # Register cleanup function to be called on exit
    atexit.register(cleanup)

    ''' END OF MULTITHREADING HANDLER '''



    ''' MAIN THREAD HANDLING GOES HERE '''

    # Main Thread Handling
    try:
        while running:
            time.sleep(0.2)
        ### ADD PLOTTING ETC here

    ''' END OF MAIN THREAD HANDLING '''




    ''' EXCEPTION HANDLING AND CLEANUP '''
    except KeyboardInterrupt:
        print("Keyboard Interrupt Detected. Exiting...")
        cleanup()

    # Cleanup of threads and data
    finally:
        
        print("Cleaning up...")
        cleanup()
        update_thread.join()

        # Writing data to a csv file
        try:
            prop_df.to_csv('data.csv')
            print("Data saved to data.csv")
        except Exception as e:
            print(f"An exception occurred while saving data: {e}")

        # User feedback
        print("Program Exited Cleanly")

if __name__ == "__main__":
    main()
        # Main thread can be used for other tasks, e.g., plotting
    # Note: For real-time plotting, consider using matplotlib.animation.FuncAnimation
