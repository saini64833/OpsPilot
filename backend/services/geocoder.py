from geopy.geocoders import Photon

# Photon is much more lenient with address formats and doesn't strictly block generic user agents
geolocator = Photon(user_agent="opspilot_delivery_app")

def get_coordinates_from_text(address_text: str):
    """
    Takes an address string and returns (latitude, longitude).
    """
    try:
        # Photon handles messy strings much better than Nominatim
        location = geolocator.geocode(address_text, timeout=10)
        
        if location:
            return location.latitude, location.longitude
            
        # Fallback: Strip the last segment (usually a ZIP code) if the full string fails
        parts = [p.strip() for p in address_text.split(',')]
        if len(parts) > 1:
            fallback_text = ", ".join(parts[:-1])
            location = geolocator.geocode(fallback_text, timeout=10)
            if location:
                return location.latitude, location.longitude

        print(f"Could not find coordinates for: {address_text}")
        return None, None
        
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None