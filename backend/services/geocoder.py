from geopy.geocoders import Nominatim

# Initialize the geocoder (Nominatim is free and uses OpenStreetMap data)
geolocator = Nominatim(user_agent="opspilot_delivery_app")

def get_coordinates_from_text(address_text: str):
    """
    Takes an address string and returns (latitude, longitude).
    """
    try:
        # Search for the address
        location = geolocator.geocode(address_text)
        
        if location:
            return location.latitude, location.longitude
        else:
            print(f"Could not find coordinates for: {address_text}")
            return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None