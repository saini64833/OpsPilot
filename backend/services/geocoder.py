import re
from geopy.geocoders import Photon, ArcGIS

# Initialize primary and fallback geocoders
photon_geolocator = Photon(user_agent="opspilot_delivery_app")
arcgis_geolocator = ArcGIS(user_agent="opspilot_delivery_app")

def clean_address_string(address_text: str) -> str:
    """Removes parentheses and normalizes whitespace which often break OSM geocoders."""
    # Remove anything inside parentheses, e.g., "(ISM)"
    cleaned = re.sub(r'\(.*?\)', '', address_text)
    # Remove extra whitespace and commas
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,')
    return cleaned

def get_coordinates_from_text(address_text: str):
    """
    Takes an address string, cleans it, and attempts geocoding via a multi-provider fallback.
    """
    try:
        cleaned_text = clean_address_string(address_text)
        
        # Attempt 1: Primary Geocoder (Photon)
        location = photon_geolocator.geocode(cleaned_text, timeout=10)
        if location:
            return location.latitude, location.longitude
            
        # Attempt 2: Fallback Geocoder (ArcGIS - excellent for institutions/fuzzy matches)
        location = arcgis_geolocator.geocode(cleaned_text, timeout=10)
        if location:
            return location.latitude, location.longitude

        # Attempt 3: Progressive segment reduction (Dynamic broadening)
        parts = [p.strip() for p in cleaned_text.split(',')]
        while len(parts) > 1:
            # Remove the most granular part of the address (usually the first or last depending on format)
            # Let's try removing the last segment (often a mismatched ZIP or strict district)
            parts.pop() 
            fallback_text = ", ".join(parts)
            
            # Use ArcGIS for the broadened search
            location = arcgis_geolocator.geocode(fallback_text, timeout=10)
            if location:
                return location.latitude, location.longitude

        print(f"Could not find coordinates dynamically for: {address_text}")
        return None, None
        
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None