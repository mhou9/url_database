import re  
import json
import mysql.connector
from mysql.connector import Error
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
import getpass
import folium
from geopy.geocoders import Nominatim


def get_driver():
    """
    Function to prompt the user for the browser choice and return the corresponding WebDriver instance.
    """
    while True:
        browser = input("Enter the browser you want to use (chrome or edge): ").strip().lower()
        if browser == 'chrome':
            return webdriver.Chrome()
        elif browser == 'edge':
            return webdriver.Edge()
        else:
            print("Unsupported browser. Please enter 'chrome' or 'edge'.")


def scroll_inner_div(driver, scroll_count):
    """
    Function to scroll the inner div a specified number of times.
    """
    scroller = driver.find_element(By.XPATH, "//div[@class='iScroll']")
    for _ in range(scroll_count):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroller)
        time.sleep(1)


def get_school_outer_info(driver):
    """
    Function to extract the outer information in the first page including
    the URLs of schools from anchor tags on the current page, along with their addresses.
    """
    school_divs = driver.find_elements(By.CSS_SELECTOR, 'div.item.school-item')
    school_info_list = []
    for div in school_divs:
        href = div.find_element(By.TAG_NAME, 'a').get_attribute('href')
        if href and href.startswith("https://www.schools.nyc.gov/schools/"):
            address_element = div.find_element(By.CSS_SELECTOR, 'div.column.address.pt-1')
            address_parts = address_element.find_elements(By.TAG_NAME, 'div')
            address = ', '.join(part.text for part in address_parts)
            domain = extract_domain(href)
            if domain == "sites.google":
                url = "none"
            else:
                url = href
            school_info_list.append({'url': url, 'address': address})
    return school_info_list


def extract_domain(url):
    """
    Function to extract the domain name from a given URL.
    """
    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')
    return domain_parts[-2] if len(domain_parts) > 2 else domain_parts[0]


def get_school_info(driver, school_url):
    """
    Function to retrieve school information from a given school URL, including the address.
    """
    driver.get(school_url)
    time.sleep(2)
    school_info = {'url': school_url}
    try:
        school_info['name'] = driver.find_element(By.CLASS_NAME, 'title').text
        try:
            school_website_element = driver.find_element(By.XPATH, "//li[a[contains(@class, 'more') and contains(text(), 'School Website')]]/a")
            school_info['personal_website'] = school_website_element.get_attribute('href')
            school_info['domain_name'] = extract_domain(school_info['personal_website']) if school_info['personal_website'] else None
        except:
            school_info['personal_website'] = None
            school_info['domain_name'] = None
        try:
            school_info['district'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Geographic District')]]").text.split(':')[1].strip()
        except:
            school_info['district'] = None
        try:
            school_info['grades'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Grades')]]").text.split(':')[1].strip()
        except:
            school_info['grades'] = None
        try:
            school_info['borough'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Borough')]]").text.split(':')[1].strip()
        except:
            school_info['borough'] = None
        try:
            address_element = driver.find_element(By.XPATH, "//a[@class='more'][contains(@href, 'maps.google.com')]")
            full_address = address_element.text
            clean_address = re.sub(r'\s*\(.*\)$', '', full_address)  # Clean the address
            school_info['address'] = clean_address
        except:
            school_info['address'] = None
    except Exception as e:
        print(f"Error retrieving school info for {school_url}: {str(e)}")
    return school_info


def connect_to_db():
    """
    Function to connect to the MySQL database.
    """
    try:
        password = getpass.getpass(prompt='Enter MySQL password: ')
        config = {
            'host': 'localhost',
            'user': 'root',
            'database': 'nyc_schoolsinfo'
        }
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=password,
            database=config['database']
        )
        if connection.is_connected():
            print('Connected to MySQL database')
        return connection
    except mysql.connector.Error as error:
        print("Error connecting to MySQL:", error)
        raise


def initialize_database(connection):
    """
    Function to initialize the database by creating the 'schools' table.
    """
    try:
        cursor = connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS schools")
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
            address VARCHAR(255)
        )
        """
        cursor.execute(create_query)
        print("Schools table created successfully.")
        cursor.close()
    except Error as e:
        print(f"Error initializing database: {e}")


def insert_school_info(connection, school_info):
    """
    Function to insert school information into the database.
    """
    try:
        cursor = connection.cursor()
        sql = """INSERT INTO schools 
                 (url, name, personal_website, domain_name, district, grades, borough, address)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        values = (
            school_info['url'],
            school_info['name'],
            school_info['personal_website'],
            school_info['domain_name'],
            school_info['district'],
            school_info['grades'],
            school_info['borough'],
            school_info['address']
        )
        cursor.execute(sql, values)
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"Error inserting data into MySQL table: {e}")
        return False



def plot_schools_on_map(connection):
    """
    Function to plot the schools on a map using Folium.
    """
    try:
        cursor = connection.cursor(dictionary=True)
        fetch_query = "SELECT * FROM schools"
        cursor.execute(fetch_query)
        schools_data = cursor.fetchall()
        cursor.close()

        geolocator = Nominatim(user_agent="nyc_schools_map")
        nyc_map = folium.Map(location=[40.7128, -74.0060], zoom_start=10)

        def geocode_with_retry(address, retries=5, delay=2):
            """
            Function to geocode an address with retry mechanism.

            Args:
                address (str): The address to geocode.
                retries (int): Number of retries in case of failure.
                delay (int): Delay in seconds between retries.

            Returns:
                Location: Geopy Location object or None if geocoding fails.
            """
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
            return None


        successful_geocodes = 0
        total_addresses = len(schools_data)
        
        for school in schools_data:
            if school['address']:
                location = geocode_with_retry(school['address'])
                if location:
                    folium.Marker(
                        [location.latitude, location.longitude],
                        popup=f"{school['name']}<br>{school['address']}",
                        tooltip=school['name']
                    ).add_to(nyc_map)
                    successful_geocodes += 1
                else:
                    print(f"Failed to geocode address: {school['address']}")

        nyc_map.save("nyc_schools_map.html")
        print(f"Map has been saved as nyc_schools_map.html")
        print(f"Successfully plotted {successful_geocodes} out of {total_addresses} addresses.")

    except Exception as e:
        print(f"Error plotting schools on map: {e}")



def main():
    """
    Main function to run the entire script.
    """
    connection = connect_to_db()
    if connection:
        try:
            base_url = "https://schoolsearch.schools.nyc/"
            driver = get_driver()
            driver.get(base_url)
            time.sleep(5)
            search_button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-primary[value="Search"]')
            search_button.click()
            time.sleep(3)
            scroll_inner_div(driver, 1)
            school_outer_info = get_school_outer_info(driver)
            initialize_database(connection)
            for school in school_outer_info:
                school_info = get_school_info(driver, school['url'])
                insert_school_info(connection, school_info)
            plot_schools_on_map(connection)
        finally:
            connection.close()
            driver.quit()


if __name__ == "__main__":
    main()
