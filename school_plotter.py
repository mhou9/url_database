import logging
import re  
import json
import mysql.connector
from mysql.connector import Error
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import getpass
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from bs4 import BeautifulSoup
from openlocationcode import openlocationcode as olc
import time
import requests

# To keep track of runtime
start_time = time.time()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_driver():
    """
    Function to return a Chrome WebDriver instance.
    """
    return webdriver.Chrome()

def connect_to_db():
    """
    Function to connect to the MySQL database.
    
    Returns:
        mysql.connector.connection.MySQLConnection: Database connection object if successful.
    """
    try:
        # Prompt user for MySQL password securely
        password = getpass.getpass(prompt='Enter MySQL password: ')
        
        # Database configuration
        config = {
            'host': 'localhost',
            'user': 'root',
            'database': 'schoolinfo'
        }
        
        # Connect to MySQL database
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=password,
            database=config['database']
        )
        
        # Check if connection is successful
        if connection.is_connected():
            logging.info('Successfully connected to the database.')
        
        return connection
    
    except mysql.connector.Error as error:
        logging.error("Error connecting to MySQL: %s", error)
        raise  # Raise the exception to indicate connection failure

def add_suffix_to_street_number(address):
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

# Function to fetch the page content
def fetch_page_content(address):
    googleUrl = "https://www.google.com/maps/place/"
    address = re.sub(r'\s', '+', address)
    place_url = googleUrl + address + "/"
    response = requests.get(place_url, allow_redirects=True)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.text

# Function to extract coordinates from the HTML content
def extract_coordinates_from_html(content):
    soup = BeautifulSoup(content, 'html.parser')
    
    # Find the meta tag containing the coordinates
    meta_tag = soup.find('meta', attrs={'content': re.compile(r'geo0.ggpht.com')})
    
    if meta_tag:
        # Extract the coordinates from the meta tag content
        content_value = meta_tag['content']
        match = re.search(r'll=([\d.-]+),([\d.-]+)', content_value)
        if match:
            latitude = match.group(1)
            longitude = match.group(2)
            return float(latitude), float(longitude)

    return None, None

# Function to geocode an address with a retry mechanism
def geocode_with_retry(address, retries=2, delay=2):
    """
    Function to geocode an address with a retry mechanism.
    
    Args:
        address (str): The address to geocode.
        retries (int): Number of retries in case of failure.
        delay (int): Delay between retries in seconds.
    
    Returns:
        tuple: The geocoded latitude and longitude or (None, None) if geocoding fails.
    """
    geolocator = Nominatim(user_agent="nyc_schools_map")
    for attempt in range(retries):
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                return location.latitude, location.longitude
             
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Geocoding attempt {attempt + 1} failed for address: {address} with error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)

        except Exception as e:
            print(f"Unknown error during geocoding attempt {attempt + 1} for address: {address}: {e}")
    
    print(f"Geocoding failed for address: {address} after {retries} retries.")
    
    # Fallback to HTML extraction if geocoding fails
    print(f"Attempting to extract coordinates from Google Maps for address: {address}")
    try:
        html_content = fetch_page_content(address)
        latitude, longitude = extract_coordinates_from_html(html_content)
        if latitude and longitude:
            print(f"Extracted coordinates from HTML: Latitude = {latitude}, Longitude = {longitude}")
            return latitude, longitude
        else:
            print(f"Failed to extract coordinates from HTML for address: {address}")
    except Exception as e:
        print(f"Error fetching page content or extracting coordinates for address: {address}: {e}")
    
    return None, None

def update_geocoded_coordinates(connection):
    """
    Function to update the geocoded coordinates in the database.
    
    Args:
        connection (Connection): The database connection.
    """
    try:
        cursor = connection.cursor(dictionary=True)
        fetch_query = "SELECT id, formatted_address FROM schools WHERE latitude IS NULL OR longitude IS NULL"
        cursor.execute(fetch_query)
        schools_data = cursor.fetchall()

        for school in schools_data:
            latitude, longitude = geocode_with_retry(school['formatted_address'])
            if latitude is not None and longitude is not None:
                update_query = "UPDATE schools SET latitude = %s, longitude = %s WHERE id = %s"
                cursor.execute(update_query, (latitude, longitude, school['id']))
                connection.commit()
        
        cursor.close()
        logging.info("Geocoded coordinates updated in the database.")
    except Exception as e:
        logging.error(f"Error updating geocoded coordinates: {e}")

def plot_schools_on_map(connection):
    """
    Function to plot the schools on a map using Folium.
    
    Parameters:
        connection (Connection): The database connection.
    """
    try:
        cursor = connection.cursor(dictionary=True)
        fetch_query = "SELECT name, formatted_address, latitude, longitude FROM schools WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        cursor.execute(fetch_query)
        schools_data = cursor.fetchall()
        cursor.close()

        nyc_map = folium.Map(location=[40.7128, -74.0060], zoom_start=10)

        for school in schools_data:
            folium.Marker(
                [school['latitude'], school['longitude']],
                popup=f"{school['name']}<br>{school['formatted_address']}",
                tooltip=school['name']
            ).add_to(nyc_map)

        nyc_map.save("nyc_schools_map.html")
        logging.info(f"Map has been saved as nyc_schools_map.html")

    except Exception as e:
        logging.error(f"Error plotting schools on map: {e}")

def main():
    try:
        connection = connect_to_db()
        driver = get_driver()
        update_geocoded_coordinates(connection)
        plot_schools_on_map(connection)
    finally:
        if connection.is_connected():
            connection.close()
            logging.info("Database connection closed.")
        driver.quit()
        logging.info("Selenium WebDriver closed.")

if __name__ == "__main__":
    main()

# Calculate and print runtime
end_time = time.time()
logging.info(f"Total runtime: {end_time - start_time} seconds")
