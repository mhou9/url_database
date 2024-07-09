import requests
import re  
import json
import mysql.connector
from mysql.connector import Error
import time
from urllib.parse import urlparse
import getpass
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from openlocationcode import openlocationcode as olc
from bs4 import BeautifulSoup
from time import sleep


# To keep track of runtime
start_time = time.time()

def get_personal_website(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            website_tag = soup.find('a', class_='')
            if website_tag and 'href' in website_tag.attrs:
                return website_tag['href']
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def extract_domain(url):
    """
    Function to extract the domain name from a given URL.
    
    Args:
        url (str): The URL from which the domain name needs to be extracted.
        
    Returns:
        str: Extracted domain name in the format 'domain.extension'.
    """
    # Parse the URL to break it into its components
    parsed_url = urlparse(url)
    
    # Split the network location (domain) by dots
    domain_parts = parsed_url.netloc.split('.')
    
    # Join the last two parts of the domain to form the domain name (excluding any subdomains)
    return '.'.join(domain_parts[-2:])


def extract_address(address):
    """
    Extracts the address from a string in the format 'Suggest an edit on [Address]'.
    
    Args:
        address (str): The input string containing the address.
    
    Returns:
        str: The extracted address.
    """
    # Regex pattern to extract the address
    pattern = r'Suggest an edit on (.+)'
    match = re.search(pattern, address)
    if match:
        return match.group(1)
    else:
        return address


def add_suffix(address):
    def get_suffix(n):
        if 10 <= n % 100 <= 20:
            return 'th'
        elif n % 10 == 1:
            return 'st'
        elif n % 10 == 2:
            return 'nd'
        elif n % 10 == 3:
            return 'rd'
        else:
            return 'th'

    patterns = [
        r'^(\d+-\d+)\s+(East|West|North|South)?\s*(\d+)\s+(\w+)(.*)$',  # "144-176 East 128 Street, Manhattan, NY 10035"
        r'^(\d+-\d+)\s+(\d+)\s+(\w+)(.*)$',  # "89-30 114 Street, Queens, NY 11418"
        r'^(\d+)\s+(.*?\d+)\s+(\w+)(.*)$'    # "80 East 181 Street, Bronx, NY, 10453"
    ]

    for pattern in patterns:
        match = re.match(pattern, address)
        if match:
            groups = match.groups()
            if len(groups) == 5:  # First pattern
                range_part, direction, number, street_name, remaining = groups
                direction = direction + " " if direction else ""
                number_to_modify = int(number)
                return f"{range_part} {direction}{number}{get_suffix(number_to_modify)} {street_name}{remaining}"
            elif len(groups) == 4:
                if '-' in groups[0]:  # Second pattern
                    first_part, number, street_name, remaining = groups
                    number_to_modify = int(number)
                    return f"{first_part} {number}{get_suffix(number_to_modify)} {street_name}{remaining}"
                else:  # Third pattern
                    first_number, second_part, street_name, remaining = groups
                    number_to_modify = int(re.search(r'\d+', second_part).group())
                    return f"{first_number} {second_part}{get_suffix(number_to_modify)} {street_name}{remaining}"

    return address  # Return original address if no pattern matches


def geocode_with_retry(address, retries=1):
    geolocator = Nominatim(user_agent="school_geocoder")
    
    for attempt in range(retries):
        try:
            location = geolocator.geocode(address)
            if location:
                return (location.latitude, location.longitude)
            else:
                if attempt == 0:
                    # Only reformat the address after the first attempt
                    address = add_suffix(address)
            sleep(1)
        except Exception as e:
            print(f"Error geocoding {address} on attempt {attempt + 1}: {e}")
            sleep(1)
    return (None, None)


api_url = "https://ws.schools.nyc/schooldata/GetSchools?search=&borough=&grade="  
response = requests.get(api_url)
schools_data = response.json()

# Parse JSON Data and Combine Address Field
schools_info = []

for school in schools_data:
    url_base = "https://www.schools.nyc.gov/schools/" # the base url for every school url
    url = url_base + school['locationCode'] 

    # retrieving the personal website
    personal_website = get_personal_website(url)

    # get the domain name of the school's website
    domain = extract_domain(personal_website)

    # concatenating the address
    address = f"{school['primaryAddressLine']}, {school['boroughName']}, {school['stateCode']}, {school['zip']}" 
    formatted_address = add_suffix(address)
    
    # retrieving the latitude and longitude of the address
    lat, lon = geocode_with_retry(address)
   

    # delay for geocoder
    sleep(1)

    schools_info.append((url, school['name'], personal_website, domain, school['district'], school['grades'], school['boroughCode'], address, lat, lon))
    print(school['name'])

print(schools_info)

print("Process finished --- %s seconds ---" % (time.time() - start_time))
