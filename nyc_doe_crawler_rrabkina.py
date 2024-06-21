import json
import mysql.connector
from mysql.connector import Error
import time
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
import getpass
import folium

def get_driver():
    """
    Function to prompt the user for the browser choice and return the corresponding WebDriver instance.

    Returns:
        WebDriver: Instance of the selected WebDriver (Chrome or Edge).
    """
    while True:
        # Prompt user for browser choice and convert input to lowercase
        browser = input("Enter the browser you want to use (chrome or edge): ").strip().lower()
        
        # Check if the user input matches supported browsers
        if browser == 'chrome':
            # Return a WebDriver instance for Chrome
            return webdriver.Chrome()
        elif browser == 'edge':
            # Return a WebDriver instance for Edge
            return webdriver.Edge()
        else:
            # Inform user of unsupported browser choice and prompt again
            print("Unsupported browser. Please enter 'chrome' or 'edge'.")


def scroll_inner_div(driver, scroll_count):
    """
    Function to scroll the inner div a specified number of times.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        scroll_count (int): Number of times to scroll the div.
    """
    # Find the inner scrollable div element using XPath
    scroller = driver.find_element(By.XPATH, "//div[@class='iScroll']")
    
    # Loop to scroll the div 'scroll_count' times
    for _ in range(scroll_count):
        # Execute JavaScript to scroll the div to the bottom
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroller)
        
        # Wait for a second to allow content to load/animations to complete
        time.sleep(1)


def get_school_outer_info(driver):
    """
    Function to extract school information including URLs and addresses.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.

    Returns:
        list: A list of dictionaries, each containing 'url' and 'address' of schools.
    """
    school_divs = driver.find_elements(By.CSS_SELECTOR, 'div.item.school-item')
    school_info_list = []

    for div in school_divs:
        href = div.find_element(By.TAG_NAME, 'a').get_attribute('href')
        if href and href.startswith("https://www.schools.nyc.gov/schools/"):
            # Extract address
            address_div = div.find_element(By.CSS_SELECTOR, 'div.column.address')
            address_elements = address_div.find_elements(By.TAG_NAME, 'div')

            # Assuming the first div contains the street and city, and the second contains postal code
            street_city = address_elements[0].text.strip()
            postal_code = address_elements[1].text.strip() if len(address_elements) > 1 else ""

            full_address = f"{street_city}, {postal_code}"

            school_info = {
                'url': href,
                'address': full_address
            }
            school_info_list.append(school_info)

    return school_info_list


def extract_domain(url):
    """
    Function to extract the domain name from a given URL.

    Args:
        url (str): The URL from which the domain name is to be extracted.

    Returns:
        str: The extracted domain name.
    """
    # Parse the URL to extract its components
    parsed_url = urlparse(url)
    
    # Check if the URL belongs to sites.google.com
    if parsed_url.netloc.startswith('sites.google.com'):
        # For URLs like 'https://sites.google.com/schools.nyc.gov/example/home'
        path_parts = parsed_url.path.strip('/').split('/')
        return path_parts[-2] if len(path_parts) >= 2 else None
    else:
        # For typical domain names like 'www.example.com'
        domain_parts = parsed_url.netloc.split('.')
        if len(domain_parts) > 2:
            return domain_parts[-2]  # Get the second-to-last part
        else:
            return domain_parts[0]  # Fallback to the first part if no extension found


def get_school_info(driver, school_url):
    """
    Function to retrieve school information from a given school URL, including the address.

    Args:
        driver (WebDriver): The Selenium WebDriver instance.
        school_url (str): The URL of the school's webpage.

    Returns:
        dict: A dictionary containing school information such as name, website, domain name, district, grades, borough, and address.
    """
    # Load the school's webpage
    driver.get(school_url)
    time.sleep(2)  # Wait for page to load
    
    school_info = {'url': school_url}  # Initialize dictionary to store school information
    
    try:
        # Extract school name
        school_info['name'] = driver.find_element(By.CLASS_NAME, 'title').text
        
        # Extract school website and domain name
        try:
            school_website_element = driver.find_element(By.XPATH, "//li[a[contains(@class, 'more') and contains(text(), 'School Website')]]/a")
            school_info['personal_website'] = school_website_element.get_attribute('href')
            if school_info['personal_website']:
                school_info['domain_name'] = extract_domain(school_info['personal_website'])
            else:
                school_info['domain_name'] = None
        except:
            school_info['personal_website'] = None
            school_info['domain_name'] = None
        
        # Extract district information
        try:
            school_info['district'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Geographic District')]]").text.split(':')[1].strip()
        except:
            school_info['district'] = None
        
        # Extract grades offered by the school
        try:
            school_info['grades'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Grades')]]").text.split(':')[1].strip()
        except:
            school_info['grades'] = None
        
        # Extract borough location of the school
        try:
            school_info['borough'] = driver.find_element(By.XPATH, "//span[strong[contains(text(), 'Borough')]]").text.split(':')[1].strip()
        except:
            school_info['borough'] = None
        
        # Extract address of the school using a link to Google Maps
        try:
            address_element = driver.find_element(By.XPATH, "//a[@class='more'][contains(@href, 'maps.google.com')]")
            school_info['address'] = address_element.text
        except:
            school_info['address'] = None
        
    except Exception as e:
        print(f"Error retrieving school info for {school_url}: {str(e)}")
    
    return school_info


def connect_to_db():
    """
    Function to connect to the MySQL database.

    Returns:
        MySQLConnection: The MySQL database connection.
    """
    try:
        # Prompt user for MySQL password securely
        password = getpass.getpass(prompt='Enter MySQL password: ')
        
        # MySQL database connection configuration
        config = {
            'host': 'localhost',
            'user': 'root',
            'database': 'nyc_schoolsinfo'
        }
        
        # Attempt to connect to MySQL using provided credentials
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
        # Handle error if connection fails
        print("Error connecting to MySQL:", error)
        raise  # Re-raise the exception for higher-level handling


def initialize_database(connection):
    """
    Function to initialize the database by creating the 'schools' table.

    Args:
        connection (MySQLConnection): The MySQL database connection.
    """
    try:
        cursor = connection.cursor()

        # Drop the 'schools' table if it exists to start fresh
        cursor.execute("DROP TABLE IF EXISTS schools")

        # Define the SQL query to create the 'schools' table with necessary columns
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

        # Execute the create table query
        cursor.execute(create_query)
        print("Schools table created successfully.")

        # Close the cursor to free up resources
        cursor.close()

    except Error as e:
        # Handle any errors that occur during table creation
        print(f"Error initializing database: {e}")


def insert_school_info(connection, school_info):
    """
    Function to insert school information into the database.

    Args:
        connection (MySQLConnection): The MySQL database connection.
        school_info (dict): A dictionary containing school information to be inserted.

    Returns:
        bool: True if insertion is successful, False otherwise.
    """
    try:
        cursor = connection.cursor()
        
        # SQL query to insert school information into the 'schools' table
        sql = """INSERT INTO schools 
                 (url, name, personal_website, domain_name, district, grades, borough, address)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        
        # Prepare the values to be inserted into the SQL query
        values = (
            school_info['url'],               # URL of the school
            school_info['name'],              # Name of the school
            school_info['personal_website'],  # Personal website of the school (if available)
            school_info['domain_name'],       # Domain name extracted from personal website (if available)
            school_info['district'],          # Geographic district of the school
            school_info['grades'],            # Grades offered by the school
            school_info['borough'],           # Borough where the school is located
            school_info['address']            # Full address of the school
        )
        
        # Execute the SQL query with the prepared values
        cursor.execute(sql, values)
        
        # Commit the transaction to persist changes in the database
        connection.commit()
        
        # Close the cursor to release resources
        cursor.close()
        
        return True  # Return True indicating successful insertion
    
    except Error as e:
        # Print error message if insertion fails and return False
        print(f"Error inserting data into MySQL table: {e}")
        return False


def main():
    # Connect to the MySQL database
    connection = connect_to_db()
    
    if connection:
        try:
            # Base URL of the NYC school search website
            base_url = "https://schoolsearch.schools.nyc/"
            
            # Initialize the web driver
            driver = get_driver()
            
            # Open the base URL in the browser
            driver.get(base_url)
            time.sleep(5)  # Wait for the page to load
            
            # Find and click the search button to display the list of schools
            search_button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-primary[value="Search"]')
            search_button.click()
            time.sleep(3)  # Wait for the search results to load
            
            # Scroll to load more schools
            scroll_inner_div(driver, 1)
            
            # Extract the outer information of schools (URLs and addresses)
            school_outer_info = get_school_outer_info(driver)
            
            # Initialize the database (create tables, etc.)
            initialize_database(connection)
            
            # Loop through the list of schools and get detailed information for each school
            for school in school_outer_info:
                school_info = get_school_info(driver, school['url'])
                
                # Insert the detailed school information into the database
                insert_school_info(connection, school_info)
        
        finally:
            # Close the database connection and the web driver
            connection.close()
            driver.quit()

if __name__ == "__main__":
    main()
