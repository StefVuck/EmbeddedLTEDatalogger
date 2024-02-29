import os
import folium
import iot_api_client
from iot_api_client.rest import ApiException
import  iot_api_client.apis.tags.devices_v2_api as DevicesV2
import webbrowser

import matplotlib.pyplot as plt
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from decimal import Decimal
import json
from mpl_toolkits.basemap import Basemap
import pandas as pd


def format_api_response(parsed_data):
    """
    Extract and format the nested API response data.
    """
    # First, parse the DynamicSchema and other complex objects into a more manageable structure
    # parsed_data = parse_dynamic_schema(api_response)
    
    # Extract the 'body' part of the response which is expected to be in the first item of a tuple
    body_data = parsed_data['body'][0]  # Adjust indexing based on actual data structure
    
    # Now, you can access `body_data` as a regular dictionary
    formatted_data = {
            'ID': body_data['thing']['id'],
            'Name': body_data['thing']['device_name'],
            'Device Type': body_data['thing']['device_type'],
            'Properties Count': body_data['thing']['properties_count'],
            'Last Seen': body_data['thing']['updated_at'],
            'Timezone': body_data['thing']['timezone'],
            'Properties': [
                {
                    'Variable Name': prop['variable_name'],
                    'Property ID': prop['id'],
                    'Type': prop['type'],
                    'Last Value': prop['last_value'],
                    'Value Updated At': prop['value_updated_at'],
                }
                for prop in body_data['thing']['properties']
            ]
        
    }
    
    return formatted_data

def dynamic_schema_to_dict(dynamic_schema):
    if hasattr(dynamic_schema, '__dict__'):
        return dict(dynamic_schema.items())
    else:
        return str(dynamic_schema)  # Fallback to string representation

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # Convert Decimal to float
        elif 'DynamicSchema' in str(type(obj)):  # Check for DynamicSchema or similar
            return dynamic_schema_to_dict(obj)  # Convert DynamicSchema to dict
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


if __name__ == "__main__":
    # Setup the OAuth2 session that'll be used to request the server an access token
    oauth_client = BackendApplicationClient(client_id="objUzAHRP41Qti2luhQ9MD8LKf92p7CT")
    token_url = "https://api2.arduino.cc/iot/v1/clients/token"
    oauth = OAuth2Session(client=oauth_client)

    '''
    TODO: 
        - Functionalise the token gathering, call every 280s, to avoid timeout
        - Create setup() function, to avoid looping key generation and gathering
        - Create external verification file or OAuth??
        - Transisiton towards pandas dataframes instead of JSONs for storing data
        - Rework CustomEncoder?
        - Write to CSV
    '''

    '''
    Planned Workflow:



    '''

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

    # Get a list of devices, catching the specific exception
    try:
        resp = api_instance.devices_v2_list()
        dicter = resp.__dict__
        print("Response from server:")
        dictproper = format_api_response(resp.__dict__)
        print(resp.__dict__)

        data = json.dumps(dictproper, cls=CustomEncoder, indent=2)
        # print(data)
        with open('data.json', 'w') as f:
            write = f.write(data)

        # Assuming your data is stored in a variable named `data`
        gpsdata = dict(dictproper["Properties"][9]['Last Value'])
        # Assuming the GPS property 'Last Value' is a dictionary with 'lat' and 'lon' keys

        latitude = float(gpsdata['lat'])  # Convert Decimal to float for latitude
        longitude = float(gpsdata['lon'])  # Convert Decimal to float for longitude

        # Create a map centered around the current GPS position
        m = folium.Map(location=[latitude, longitude], zoom_start=15)

        # Add a marker for the current GPS position
        folium.Marker([latitude, longitude], popup='Current Position').add_to(m)

        # Display the map
        m.save('current_gps_position.html')

# Create a Basemap instance for a zoomed-in area
        webbrowser.get('windows-default').open('current_gps_position.html')


    except ApiException as e:
        print("An exception occurred: {}".format(e))

