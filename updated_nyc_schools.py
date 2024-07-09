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

# To keep track of runtime
start_time = time.time()


def get_driver():
    """
    Function to return a Chrome WebDriver instance.
    """
    return webdriver.Chrome()


def scroll_inner_div(driver, scroll_count):
    """
    Function to scroll the inner div a specified number of times.

    Args:
        driver (WebDriver): The WebDriver instance used to interact with the web page.
        scroll_count (int): Number of times to scroll the inner div.

    Returns:
        None
    """
    # Locate the inner div element that needs to be scrolled
    scroller = driver.find_element(By.XPATH, "//div[@class='iScroll']")

    # Perform scrolling 'scroll_count' times
    for _ in range(scroll_count):
        # Execute JavaScript to scroll the div to the bottom
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroller)
        
        # Pause execution for 1 second to allow content to load
        time.sleep(1)


def get_school_outer_info(driver):
    """
    Function to extract the outer information in the first page including
    the URLs of schools from anchor tags on the current page, along with their addresses.
    
    Args:
        driver (WebDriver): The WebDriver instance used to interact with the web page.
        
    Returns:
        list: List of dictionaries containing school URLs and addresses.
              Each dictionary has keys 'url' and 'address'.
    """
    # Locate all school item divs on the page
    try:
        school_divs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.item.school-item'))
        )
    except TimeoutException:
        print("Timeout: School divs not found.")
        return []

    # Initialize an empty list to store school information
    school_info_list = []

    # Iterate through each school item div
    for div in school_divs:
        try:
            # Extract the URL of the school from the anchor tag within the div
            href = div.find_element(By.TAG_NAME, 'a').get_attribute('href')

            # Check if the extracted URL starts with the specified base URL
            if href and href.startswith("https://www.schools.nyc.gov/schools/"):
                # Extract the address of the school from the address element within the div
                try:
                    address_element = div.find_element(By.CSS_SELECTOR, 'div.column.address.pt-1')
                    address_parts = address_element.find_elements(By.TAG_NAME, 'div')
                    address = ', '.join(part.text for part in address_parts)
                except NoSuchElementException:
                    address = "Address not found"

                # Hardcode the address for the specific school URL
                if href == "https://www.schools.nyc.gov/schools/KBTA":
                    address = "133 Kingsborough 1st Walk, Brooklyn, NY 11233"

                # Extract the domain name from the URL to determine if it's a Google site
                domain = extract_domain(href)

                # Set the URL to 'none' if it belongs to a Google site, otherwise use the extracted URL
                if domain == "sites.google":
                    url = "none"
                else:
                    url = href
                
                # Append the URL and address to the list as a dictionary
                school_info_list.append({'url': url, 'address': address})
        except NoSuchElementException as e:
            print(f"Element not found: {e}")

    # Return the list of school information dictionaries
    return school_info_list


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


def get_school_info(driver, school_url):
    """
    Function to retrieve school information from a given school URL, including the address and Google Maps URL.
    
    Args:
        driver (selenium.webdriver.Chrome): The Selenium WebDriver instance used to navigate and scrape the web page.
        school_url (str): The URL of the school's web page from which information will be extracted.
    
    Returns:
        dict: A dictionary containing the school's information, including name, personal website, domain name, 
              district, grades, borough, address, and Google Maps URL.
    """
    # Navigate to the provided school URL
    driver.get(school_url)
    # Wait for 2 seconds to allow the page to load
    time.sleep(2)
    
    # Initialize a dictionary to store school information
    school_info = {'url': school_url}
    
    try:
        # Retrieve the school name from the page
        school_info['name'] = driver.find_element(By.CLASS_NAME, 'title').text
        
        try:
            # Locate the element for the school's personal website
            school_website_element = driver.find_element(By.XPATH, "//li[a[contains(@class, 'more') and contains(text(), 'School Website')]]/a")
            # Extract the URL of the school's personal website
            school_info['personal_website'] = school_website_element.get_attribute('href')
            # Extract the domain name from the personal website URL
            school_info['domain_name'] = extract_domain(school_info['personal_website']) if school_info['personal_website'] else None
        except NoSuchElementException:
            # Set personal website and domain name to None if not found
            school_info['personal_website'] = None
            school_info['domain_name'] = None
        
        try:
            # Retrieve the geographic district information
            school_info['district'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Geographic District')]]").text.split(':')[1].strip()
        except NoSuchElementException:
            # Set district to None if not found
            school_info['district'] = None
        
        try:
            # Retrieve the grades information
            school_info['grades'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Grades')]]").text.split(':')[1].strip()
        except NoSuchElementException:
            # Set grades to None if not found
            school_info['grades'] = None
        
        try:
            # Retrieve the borough information
            school_info['borough'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Borough')]]").text.split(':')[1].strip()
        except NoSuchElementException:
            # Set borough to None if not found
            school_info['borough'] = None
        
        try:
            # Locate the address element which contains a link to Google Maps
            address_element = driver.find_element(By.XPATH, "//a[@class='more'][contains(@href, 'maps.google.com')]")
            # Extract the full address text
            full_address = address_element.text
            # Clean the address by removing any text in parentheses
            clean_address = re.sub(r'\s*\(.*\)$', '', full_address)
            # Format the address
            formatted_address = add_suffix_to_street_number(clean_address)
            # Store the formatted address
            school_info['address'] = formatted_address
            # Extract the Google Maps URL from the address element
            school_info['google_maps_url'] = address_element.get_attribute('href')
        except NoSuchElementException:
            # Set address and Google Maps URL to None if not found
            school_info['address'] = None
            school_info['google_maps_url'] = None
    except Exception as e:
        # Print an error message if there is an issue retrieving the school information
        print(f"Error retrieving school info for {school_url}: {str(e)}")
    
    # Return the dictionary containing the school information
    return school_info


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
            print('Connected to MySQL database')
        
        return connection
    
    except mysql.connector.Error as error:
        # Handle connection errors
        print("Error connecting to MySQL:", error)
        raise  # Raise the exception to indicate connection failure


def initialize_database(connection):
    """
    Function to initialize the database by creating the 'schools' table.

    Args:
        connection (mysql.connector.connection.MySQLConnection): The connection object to the MySQL database.
    """
    try:
        # Create a cursor object to interact with the database
        cursor = connection.cursor()
        
        # Drop the 'schools' table if it exists to start fresh
        cursor.execute("DROP TABLE IF EXISTS schools")
        
        # Define the SQL query to create the 'schools' table
        create_query = """
        CREATE TABLE IF NOT EXISTS schools (
            id INT AUTO_INCREMENT PRIMARY KEY,
            url VARCHAR(255),
            name VARCHAR(255),
            personal_website VARCHAR(255),
            domain_name VARCHAR(255),
            district VARCHAR(50),
            grades VARCHAR(50),
            borough VARCHAR(50),
            address VARCHAR(255),
            google_maps_url VARCHAR(255)
        )
        """
        
        # Execute the create table query
        cursor.execute(create_query)
        
        # Confirm successful creation of the table
        print("Schools table created successfully.")
        
        # Close the cursor to free up resources
        cursor.close()
    
    except Error as e:
        # Handle any errors that occur during table creation
        print(f"Error initializing database: {e}")


def insert_school_info(connection, school_info):
    """
    Insert or update school information into the database.
    
    Args:
        connection (mysql.connector.connection.MySQLConnection): The connection object to the MySQL database.
        school_info (dict): A dictionary containing school information to be inserted or updated.
    """
    try:
        # Create a new cursor to interact with the database
        cursor = connection.cursor()
        
        # SQL query to insert a new record or update an existing record in the schools table
        insert_query = """
        INSERT INTO schools (name, personal_website, domain_name, district, grades, borough, address, google_maps_url, url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        personal_website=VALUES(personal_website), domain_name=VALUES(domain_name), district=VALUES(district),
        grades=VALUES(grades), borough=VALUES(borough), address=VALUES(address), google_maps_url=VALUES(google_maps_url), url=VALUES(url)
        """
        
        # Execute the SQL query with the provided school information
        cursor.execute(insert_query, (
            school_info['name'], school_info.get('personal_website'), school_info.get('domain_name'),
            school_info.get('district'), school_info.get('grades'), school_info.get('borough'),
            school_info.get('address'), school_info.get('google_maps_url'), school_info['url']
        ))
        
        # Commit the transaction to save the changes to the database
        connection.commit()
        
        # Close the cursor
        cursor.close()
    except mysql.connector.Error as e:
        # Print an error message if there is an issue inserting the school information
        print(f"Error inserting school info: {e}")


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
        print(f"Primary selector failed: {str(e1)}")

    try:
        # Check for plus codes and convert to latitude and longitude if found
        plus_code_element = driver.find_element(By.CSS_SELECTOR, "div[data-section-id='178'] .DkEaL")
        if plus_code_element:
            plus_code = plus_code_element.text
            print(f"Found plus code: {plus_code}")
            try:
                location = olc.decode(plus_code)
                return (location.latitudeCenter, location.longitudeCenter)
            except Exception as e:
                print(f"Error decoding plus code: {str(e)}")
    except NoSuchElementException as e2:
        print(f"No plus code found: {str(e2)}")
    
    try:
        # Try an alternative selector for the address
        corrected_address = driver.find_element(By.XPATH, "//h2[@class='bwoZTb fontBodyMedium']").text
        return corrected_address
    except NoSuchElementException as e2:
        print(f"Alternative selector failed: {str(e2)}")

    try:
        # Fallback to another possible pattern
        corrected_address = driver.find_element(By.XPATH, "//div[@aria-label='Address']//span[@class='DkEaL']").text
        return corrected_address
    except NoSuchElementException as e3:
        print(f"Fallback selector failed: {str(e3)}")

    return None


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
            print(f"Geocoding attempt {attempt + 1} failed for address: {address} with error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
        except Exception as e:
            print(f"Unknown error during geocoding attempt {attempt + 1} for address: {address}: {e}")
    
    print(f"Geocoding failed for address: {address} after {retries} retries.")
    
    # Try to reformat the address if it includes 'Suggest an edit on'
    reformatted_address = extract_address(address)
    if reformatted_address != address:
        print(f"Trying to reformat and geocode the address: {reformatted_address}")
        reformatted_address_with_suffix = add_suffix_to_street_number(reformatted_address)
        return geocode_with_retry(reformatted_address_with_suffix, retries, delay)
    
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
            if school['address']:
                # Hardcode the address for the specific school URL if available
                if school['url'] in url_to_address_mapping:
                    school['address'] = url_to_address_mapping[school['url']]

                # Try to geocode the address with retries
                location = geocode_with_retry(school['address'])
                # If geocoding fails and a Google Maps URL is available, try to extract and geocode the corrected address
                if not location and 'google_maps_url' in school and school['google_maps_url']:
                    corrected_address = extract_corrected_address(driver, school['google_maps_url'])
                    if corrected_address:
                        location = geocode_with_retry(corrected_address)
                if location:
                    # Add a marker for the successfully geocoded address
                    folium.Marker(
                        [location.latitude, location.longitude],
                        popup=f"{school['name']}<br>{school['address']}",
                        tooltip=school['name']
                    ).add_to(nyc_map)
                    successful_geocodes += 1
                else:
                    print(f"Failed to geocode address: {school['address']}")
                    failed_addresses.append(school['address'])

        nyc_map.save("nyc_schools_map.html")
        print(f"Map has been saved as nyc_schools_map.html")
        print(f"Successfully plotted {successful_geocodes} out of {total_addresses} addresses.")
        if failed_addresses:
            print("Addresses that were not able to be plotted:")
            for failed_address in failed_addresses:
                print(f"- {failed_address}")

    except Exception as e:
        print(f"Error plotting schools on map: {e}")



def main():
    """
    Main function to run the entire script.
    """
    print(add_suffix_to_street_number("144-176 East 128 Street, Manhattan, NY 10035"))
    # Establish a connection to the MySQL database
    connection = connect_to_db()
    
    # Proceed if connection to the database is successful
    if connection:
        try:
            # Base URL for school search
            base_url = "https://schoolsearch.schools.nyc/"
            
            # Initialize WebDriver instance based on user input
            driver = get_driver()
            
            # Navigate to the base URL
            driver.get(base_url)
            
            # Wait for the page to load (5 seconds)
            time.sleep(5)
            
            # Locate and click the search button on the webpage
            search_button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-primary[value="Search"]')
            search_button.click()
            
            # Wait for search results to load (3 seconds)
            time.sleep(3)
            
            # Scroll the inner div of the webpage three times
            scroll_inner_div(driver, 610)
            
            # Extract school information from the first page of search results
            school_outer_info = get_school_outer_info(driver)
            
            # Initialize the database by creating the 'schools' table if not exists
            initialize_database(connection)
            
    
            # Iterate over each school info extracted from the outer page
            for school in school_outer_info:
                # Retrieve detailed school information from the school URL
                school_info = get_school_info(driver, school['url'])
                
                # Insert school information into the MySQL database
                insert_school_info(connection, school_info)
            
            # Plot the schools on a map using Folium and save it as HTML
            plot_schools_on_map(connection, driver)
        
        finally:
            # Close the database connection
            connection.close()
            
            # Quit the WebDriver instance
            driver.quit()
       
    print("Process finished --- %s seconds ---" % (time.time() - start_time))



if __name__ == "__main__":
    main()

