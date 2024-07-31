import logging
import re  
import mysql.connector
import time
from selenium import webdriver
import getpass
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from bs4 import BeautifulSoup
from openlocationcode import openlocationcode as olc
import requests
from concurrent.futures import ThreadPoolExecutor


# Record the start time for performance tracking
start_time = time.time()

# Setup logging configuration to display messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_driver():
    """
    Function to initialize and return a Chrome WebDriver instance.
    
    Returns:
        webdriver.Chrome: A new instance of Chrome WebDriver.
    """
    return webdriver.Chrome()


def connect_to_db():
    """
    Function to connect to the MySQL database using user credentials.
    
    Returns:
        mysql.connector.connection.MySQLConnection: Database connection object if successful.
    """
    try:
        # Prompt user for MySQL password securely
        password = getpass.getpass(prompt='Enter MySQL password: ')
        
        # Database configuration settings
        config = {
            'host': 'localhost',
            'user': 'root',
            'database': 'schoolinfo'
        }
        
        # Attempt to connect to the MySQL database
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=password,
            database=config['database']
        )
        
        # Log success if connection is established
        if connection.is_connected():
            logging.info('Successfully connected to the database.')
        
        return connection
    
    except mysql.connector.Error as error:
        logging.error("Error connecting to MySQL: %s", error)
        raise  # Raise the exception to indicate connection failure


def add_suffix_to_street_number(address):
    """
    Adds ordinal suffixes to street numbers in the given address.
    
    Args:
        address (str): The address where suffixes need to be added.
    
    Returns:
        str: The address with ordinal suffixes added to the street numbers.
    """
    def get_suffix(n):
        """Determine the appropriate ordinal suffix for a number."""
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
        r'^(\d+-\d+)\s+(East|West|North|South)?\s*(\d+)\s+(\w+)(.*)$',  # Matches ranges like "144-176 East 128 Street"
        r'^(\d+-\d+)\s+(\d+)\s+(\w+)(.*)$',  # Matches ranges like "89-30 114 Street"
        r'^(\d+)\s+(.*?\d+)\s+(\w+)(.*)$'    # Matches addresses like "80 East 181 Street"
    ]

    for pattern in patterns:
        match = re.match(pattern, address)
        if match:
            groups = match.groups()
            if len(groups) == 5:  # For pattern with range and direction
                range_part, direction, number, street_name, remaining = groups
                direction = direction + " " if direction else ""
                number_to_modify = int(number)
                return f"{range_part} {direction}{number}{get_suffix(number_to_modify)} {street_name}{remaining}"
            elif len(groups) == 4:
                if '-' in groups[0]:  # For pattern with range but no direction
                    first_part, number, street_name, remaining = groups
                    number_to_modify = int(number)
                    return f"{first_part} {number}{get_suffix(number_to_modify)} {street_name}{remaining}"
                else:  # For pattern without range
                    first_number, second_part, street_name, remaining = groups
                    number_to_modify = int(re.search(r'\d+', second_part).group())
                    return f"{first_number} {second_part}{get_suffix(number_to_modify)} {street_name}{remaining}"

    return address  # Return original address if no pattern matches


def fetch_page_content(address):
    """
    Fetches the HTML content of a Google Maps place URL for the given address.
    
    Args:
        address (str): The address to fetch content for.
    
    Returns:
        str: The HTML content of the Google Maps page.
    """
    googleUrl = "https://www.google.com/maps/place/"
    address = re.sub(r'\s', '+', address)  # Replace spaces with '+' for URL
    place_url = googleUrl + address + "/"
    response = requests.get(place_url, allow_redirects=True)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.text


def extract_coordinates_from_html(content):
    """
    Extracts latitude and longitude coordinates from the HTML content.
    
    Args:
        content (str): The HTML content of a Google Maps page.
    
    Returns:
        tuple: A tuple of (latitude, longitude) if found, otherwise (None, None).
    """
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


def geocode(addresses, retries=2, delay=3):
    """
    Geocodes a list of addresses using Nominatim.

    Args:
        addresses (list): List of addresses to geocode.
        retries (int): Number of retries in case of failure.
        delay (int): Delay between retries in seconds.

    Returns:
        dict: Dictionary with addresses as keys and (latitude, longitude) tuples as values.
    """
    geolocator = Nominatim(user_agent="nyc_schools_map")
    geocoded_data = {}

    for address in addresses:
        # Attempt geocoding with retries
        for attempt in range(retries):
            try:
                location = geolocator.geocode(address, timeout=10)
                if location:
                    geocoded_data[address] = (location.latitude, location.longitude)
                    break
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                logging.warning(f"Geocoding attempt {attempt + 1} failed for address: {address} with error: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            except Exception as e:
                logging.error(f"Unknown error during geocoding attempt {attempt + 1} for address: {address}: {e}")
                break

        # Log failure if address could not be geocoded
        if address not in geocoded_data:
            logging.error(f"Geocoding failed for address: {address} after {retries} retries.")
            geocoded_data[address] = (None, None)

    return geocoded_data


def update_geocoded_coordinates(connection):
    """
    Updates the geocoded coordinates (latitude and longitude) for addresses in the database.
    
    Args:
        connection (Connection): The database connection object.
    """
    try:
        cursor = connection.cursor(dictionary=True)
        fetch_query = "SELECT id, formatted_address FROM schools WHERE latitude IS NULL OR longitude IS NULL"
        cursor.execute(fetch_query)
        schools_data = cursor.fetchall()
        logging.info(f"Fetched {len(schools_data)} records to geocode.")
        
        # Divide addresses into batches to process
        batch_size = 10  
        address_batches = [schools_data[i:i + batch_size] for i in range(0, len(schools_data), batch_size)]
        
        failed_addresses = []
        
        def process_batch(batch):
            nonlocal failed_addresses
            addresses = [school['formatted_address'] for school in batch]
            geocoded_data = {}
            
            # Geocode addresses
            batch_results = geocode(addresses)
            for address in addresses:
                geocoded_data[address] = batch_results.get(address, (None, None))
            
            # Update the database with the geocoded data
            for school in batch:
                address = school['formatted_address']
                latitude, longitude = geocoded_data[address]
                if latitude is not None and longitude is not None:
                    update_query = "UPDATE schools SET latitude = %s, longitude = %s WHERE id = %s"
                    cursor.execute(update_query, (latitude, longitude, school['id']))
                    connection.commit()
                else:
                    failed_addresses.append(address)
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(process_batch, address_batches)
        end_time = time.time()

        logging.info(f"Geocoding process completed in {end_time - start_time:.2f} seconds.")
        
        # Log addresses that could not be geocoded
        if failed_addresses:
            log_failed_addresses(failed_addresses)
        
        cursor.close()
        logging.info("Geocoded coordinates updated in the database.")
    except Exception as e:
        logging.error(f"Error updating geocoded coordinates: {e}")


def log_failed_addresses(failed_addresses, file_path='failed_addresses.txt'):
    """
    Logs addresses that failed geocoding to a text file.
    
    Args:
        failed_addresses (list): List of addresses that failed to be geocoded.
        file_path (str): Path to the text file where failed addresses will be saved.
    """
    try:
        # Open the file in write mode to clear its contents
        with open(file_path, 'w') as file:
            pass
        
        # Now append the failed addresses
        with open(file_path, 'a') as file:
            for address in failed_addresses:
                file.write(f"{address}\n")
        logging.info(f"Failed addresses logged to {file_path}.")
    except Exception as e:
        logging.error(f"Error writing to file {file_path}: {e}")


def plot_schools_on_map(connection):
    """
    Plots the schools with geocoded coordinates on a map using Folium.
    
    Args:
        connection (Connection): The database connection object.
    """
    try:
        cursor = connection.cursor(dictionary=True)
        fetch_query = "SELECT name, formatted_address, latitude, longitude FROM schools WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
        cursor.execute(fetch_query)
        schools_data = cursor.fetchall()
        print(len(schools_data))
        cursor.close()

        # Initialize the map centered around NYC
        nyc_map = folium.Map(location=[40.7128, -74.0060], zoom_start=10)

        # Add markers for each school
        for school in schools_data:
            folium.Marker(
                [school['latitude'], school['longitude']],
                popup=f"{school['name']}<br>{school['formatted_address']}",
                tooltip=school['name']
            ).add_to(nyc_map)

        # Save the map to an HTML file
        nyc_map.save("nyc_schools_map.html")
        logging.info(f"Map has been saved as nyc_schools_map.html")

    except Exception as e:
        logging.error(f"Error plotting schools on map: {e}")


def main():
    """
    Main function to orchestrate the execution of connecting to the database, updating geocoded coordinates, 
    and plotting schools on a map.
    """
    try:
        # Establish database connection
        connection = connect_to_db()
        
        # Update geocoded coordinates for addresses in the database
        update_geocoded_coordinates(connection)
        
        # Plot the schools on a map
        plot_schools_on_map(connection)
    
    finally:
        # Close the database connection
        if connection.is_connected():
            connection.close()
            logging.info("Database connection closed.")
        
        logging.info("Script execution finished.")

if __name__ == "__main__":
    # Run the main function
    main()

# Calculate and log the total runtime of the script
end_time = time.time()
logging.info(f"Total runtime: {end_time - start_time} seconds")
