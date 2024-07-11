import logging
import time
import mysql.connector
import getpass
from selenium import webdriver
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import re

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
            logging.error(f"Geocoding attempt {attempt + 1} failed for address: {address} with error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
        except Exception as e:
            logging.error(f"Unknown error during geocoding attempt {attempt + 1} for address: {address}: {e}")
    
    logging.error(f"Geocoding failed for address: {address} after {retries} retries.")
    return None

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
            location = geocode_with_retry(school['formatted_address'])
            if location:
                update_query = "UPDATE schools SET latitude = %s, longitude = %s WHERE id = %s"
                cursor.execute(update_query, (location.latitude, location.longitude, school['id']))
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
