import logging
import mysql.connector
from mysql.connector import Error
import getpass
import folium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import openlocationcode as olc


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
            'database': 'nyc_schoolsinfo'
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
            logging.info('Connected to MySQL database')
        
        return connection
    
    except Error as error:
        # Handle connection errors
        logging.error(f"Error connecting to MySQL: {error}")
        raise  # Raise the exception to indicate connection failure


def extract_address(s):
    """
    Extracts the address from a string in the format 'Suggest an edit on [Address]'.
    
    Args:
        s (str): The input string containing the address.
    
    Returns:
        str: The extracted address.
    """
    # Regex pattern to extract the address
    pattern = r'Suggest an edit on (.+)'
    match = re.search(pattern, s)
    if match:
        return match.group(1)
    else:
        return s


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


def geocode_with_retry(address, retries=5, delay=2):
    """
    Function to geocode an address with a retry mechanism.
    
    Args:
        address (str): The address to geocode.
        retries (int): Number of retries in case of failure.
        delay (int): Delay between retries in seconds.
    
    Returns:
        Location: The geocoded location object or None if geocoding fails.
    """
    geolocator = Nominatim(user_agent="nyc_schools_map")
    for attempt in range(retries):
        try:
            location = geolocator.geocode(address, timeout=10)
            if location:
                return location
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logging.warning(f"Geocoding attempt {attempt + 1} failed for address: {address} with error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
        except Exception as e:
            logging.error(f"Unknown error during geocoding attempt {attempt + 1} for address: {address}: {e}")
    
    logging.error(f"Geocoding failed for address: {address} after {retries} retries.")
    
    # Try to reformat the address if it includes 'Suggest an edit on'
    reformatted_address = extract_address(address)
    if reformatted_address != address:
        logging.info(f"Trying to reformat and geocode the address: {reformatted_address}")
        reformatted_address_with_suffix = add_suffix(reformatted_address)
        return geocode_with_retry(reformatted_address_with_suffix, retries, delay)
    
    return None


def extract_corrected_address(driver, google_maps_url):
    """
    Function to extract the corrected address from a Google Maps page.
    
    Args:
        driver (WebDriver): The WebDriver instance used to interact with the web page.
        google_maps_url (str): The URL of the Google Maps page for the school.
        
    Returns:
        str or tuple: The corrected address if found, otherwise a tuple of (latitude, longitude) if a plus code is found, or None.
    """
    driver.get(google_maps_url)
    time.sleep(3)  # Wait for the page to load

    try:
        # First try the primary selector for the address
        corrected_address = driver.find_element(By.XPATH, "//h1[@class='DUwDvf lfPIob']").text
        return corrected_address
    except NoSuchElementException as e1:
        logging.warning(f"Primary selector failed: {str(e1)}")

    try:
        # Check for plus codes and convert to latitude and longitude if found
        plus_code_element = driver.find_element(By.CSS_SELECTOR, "div[data-section-id='178'] .DkEaL")
        if plus_code_element:
            plus_code = plus_code_element.text
            logging.info(f"Found plus code: {plus_code}")
            try:
                location = olc.decode(plus_code)
                return (location.latitudeCenter, location.longitudeCenter)
            except Exception as e:
                logging.error(f"Error decoding plus code: {str(e)}")
    except NoSuchElementException as e2:
        logging.warning(f"No plus code found: {str(e2)}")
    
    try:
        # Try an alternative selector for the address
        corrected_address = driver.find_element(By.XPATH, "//h2[@class='bwoZTb fontBodyMedium']").text
        return corrected_address
    except NoSuchElementException as e2:
        logging.warning(f"Alternative selector failed: {str(e2)}")

    try:
        # Fallback to another possible pattern
        corrected_address = driver.find_element(By.XPATH, "//div[@aria-label='Address']//span[@class='DkEaL']").text
        return corrected_address
    except NoSuchElementException as e3:
        logging.warning(f"Fallback selector failed: {str(e3)}")

    return None


def plot_schools_on_map(connection, driver):
    """
    Function to plot the schools on a map using Folium.
    
    Parameters:
        connection (Connection): The database connection.
        driver (WebDriver): The Selenium WebDriver instance.
    """
    try:
        cursor = connection.cursor(dictionary=True)
        fetch_query = "SELECT * FROM schools"
        cursor.execute(fetch_query)
        schools_data = cursor.fetchall()
        cursor.close()

        logging.info(f"Total records fetched: {len(schools_data)}")

        nyc_map = folium.Map(location=[40.7128, -74.0060], zoom_start=10)

        successful_geocodes = 0
        total_addresses = len(schools_data)
        failed_addresses = []

        url_to_address_mapping = {
            "https://www.schools.nyc.gov/schools/KBTA": "133 Kingsborough 1st Walk, Brooklyn, NY 11233",
            "https://www.schools.nyc.gov/schools/X480": "1010 Rev. J. A. Polite Avenue, Bronx, NY 10459",
            "https://www.schools.nyc.gov/schools/X333": "888 Rev J A Polite Ave, Bronx, NY 10459",
            "https://www.schools.nyc.gov/schools/X274": "275 Harlem River Park Bridge, Bronx, NY 10453",
            "https://www.schools.nyc.gov/schools/X204": "1780 Dr. Martin Luther King Jr. Blvd, Bronx, NY 10453",
            "https://www.schools.nyc.gov/schools/QALO": "1 Jamaica Center Plaza, Queens, NY, 11432",
            "https://www.schools.nyc.gov/schools/M551": "10 South Street, Slip 7, Manhattan, NY 10004",
        }

        for school in schools_data:
            logging.info(f"Processing school: {school['name']}")

            if 'url' in school and school['url'] in url_to_address_mapping:
                school['address'] = url_to_address_mapping[school['url']]
                logging.info(f"Using hardcoded address for {school['name']}: {school['address']}")

            if 'address' in school and school['address']:
                location = geocode_with_retry(school['address'])
                if not location and 'google_maps_url' in school and school['google_maps_url']:
                    logging.info(f"Trying to extract corrected address for {school['name']} from Google Maps URL: {school['google_maps_url']}")
                    corrected_address = extract_corrected_address(driver, school['google_maps_url'])
                    if corrected_address:
                        location = geocode_with_retry(corrected_address)
                
                if location:
                    logging.info(f"Successfully geocoded address for {school['name']}: {location.latitude}, {location.longitude}")
                    folium.Marker(
                        [location.latitude, location.longitude],
                        popup=f"{school['name']}<br>{school['address']}",
                        tooltip=school['name']
                    ).add_to(nyc_map)
                    successful_geocodes += 1
                else:
                    logging.warning(f"Failed to geocode address: {school['address']}")
                    failed_addresses.append(school['address'])
            else:
                logging.warning(f"No address found for {school['name']}")

        nyc_map.save("nyc_schools_map.html")
        logging.info(f"Map has been saved as nyc_schools_map.html")
        logging.info(f"Successfully plotted {successful_geocodes} out of {total_addresses} addresses.")
        if failed_addresses:
            logging.warning("Addresses that were not able to be plotted:")
            for failed_address in failed_addresses:
                logging.warning(f"- {failed_address}")

    except Exception as e:
        logging.error(f"Error plotting schools on map: {e}")


def main():
    # To keep track of runtime
    start_time = time.time()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        # Get the database connection
        connection = connect_to_db()
        if not connection:
            raise Exception("Database connection failed.")

        # Set up Selenium WebDriver
        driver = get_driver()

        # Plot schools on the map
        plot_schools_on_map(connection, driver)
    
    except Exception as e:
        logging.error(f"Error in main function: {e}")
    
    finally:
        # Clean up
        if connection and connection.is_connected():
            connection.close()
            logging.info("Database connection closed.")
        driver.quit()
        logging.info("Selenium WebDriver closed.")

    # Calculate and log the runtime
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"Total runtime: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
