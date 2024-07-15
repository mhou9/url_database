import json
import mysql.connector
from mysql.connector import Error
import time
from urllib.parse import urlparse
import getpass
import logging
import aiohttp
import asyncio
import traceback
import re
from bs4 import BeautifulSoup
import requests

# MySQL Credentials
HOST = 'localhost'
USER = 'root'
DATABASE = 'schoolinfo'

# Hardcoded edge case mappings for specific school URLs to their addresses
EDGE_CASE_ADDRESSES = {
    "https://www.schools.nyc.gov/schools/KBUF": "133 Kingsborough 1st Walk, Brooklyn, NY 11233",
    "https://www.schools.nyc.gov/schools/KDVD": "561 Utica Ave, Brooklyn, NY 11203"
}

# Hardcoded school information used as a fallback for known schools
HARD_CODED_SCHOOLS = [
    {
        'url': None,
        'name': 'American Dream Charter School II',
        'personal_website': 'https://www.adcs2.org/',
        'domain_name': 'adcs2',
        'district': '7',
        'grades': '06,07,08,09,10,11,12',
        'borough': 'Bronx',
        'formatted_address': '510 E 141st St, Bronx, NY 10454'
    },
    {
        'url': None,
        'name': 'Imagine Early Learning Center @ City College',
        'personal_website': 'https://imagineelc.com/schools/city-college-child-development-center/',
        'domain_name': 'imagineelc',
        'district': '',
        'grades': 'PK',
        'borough': 'Manhattan',
        'formatted_address': '119 Convent Ave, New York, NY 10031'
    }
]


def extract_domain(url):
    """
    Extracts the domain name from a given URL.
    
    Args:
        url (str): The URL from which the domain name is to be extracted.
        
    Returns:
        str: The domain name in the format 'domain.extension'.
    """
    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')
    return '.'.join(domain_parts[-2:])


async def fetch_schools(api_url, session):
    """
    Fetches school data from the API asynchronously.

    Args:
        api_url (str): The API URL to fetch data from.
        session (aiohttp.ClientSession): The aiohttp session to use for HTTP requests.

    Returns:
        list: A list of dictionaries containing school data.
    """
    try:
        async with session.get(api_url) as response:
            if response.status != 200:
                logging.error(f"Error: Received status code {response.status}")
                return []

            text = await response.text()
            schools_data = json.loads(text)
            return schools_data
    except Exception as e:
        logging.error(f"Error fetching or parsing school data: {e}")
        return []


async def get_school_website(session, school_info_url):
    """
    Asynchronously fetches the HTML content of a school's info page and extracts the school's personal website URL.
    If the URL is from Google Sites, returns None.

    Args:
        session (aiohttp.ClientSession): The aiohttp session to use.
        school_info_url (str): The URL of the school's info page.

    Returns:
        str: The URL of the school's personal website or None if not found or if it is a Google site.
    """
    try:
        async with session.get(school_info_url) as response:
            response.raise_for_status()  # Ensure the request was successful
            html_content = await response.text()

            # Parse the HTML content with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all <li> elements
            list_items = soup.find_all('li')

            # Extract URLs based on <svg> class
            for item in list_items:
                svg = item.find('svg')
                if svg and 'icon-globe' in svg.get('class', []):
                    a_tag = item.find('a')
                    if a_tag and a_tag.get('href'):
                        url = a_tag.get('href')
                        if "sites.google.com" in url:
                            return None
                        return url
        
        return None  # Return None if no personal website URL was found

    except aiohttp.ClientError as e:
        logging.error(f"Error fetching the URL: {e}")
        return None
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None


async def fetch_school_website_with_semaphore(session, semaphore, url):
    """
    Fetches a school's personal website URL with semaphore to control concurrency.

    Args:
        session (aiohttp.ClientSession): The aiohttp session to use.
        semaphore (asyncio.Semaphore): Semaphore to limit the number of concurrent requests.
        url (str): The URL of the school's info page.

    Returns:
        str: The URL of the school's personal website or None if not found.
    """
    async with semaphore:
        return await get_school_website(session, url)


def add_suffix(address):
    """
    Adds ordinal suffix to street numbers in the given address.

    Args:
        address (str): The address where suffixes need to be added.

    Returns:
        str: The address with ordinal suffixes added to the street numbers.
    """
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
        r'^(\d+-\d+)\s+(East|West|North|South)?\s*(\d+)\s+(\w+)(.*)$',
        r'^(\d+-\d+)\s+(\d+)\s+(\w+)(.*)$',
        r'^(\d+)\s+(.*?\d+)\s+(\w+)(.*)$'
    ]

    for pattern in patterns:
        match = re.match(pattern, address)
        if match:
            groups = match.groups()
            if len(groups) == 5:
                range_part, direction, number, street_name, remaining = groups
                direction = direction + " " if direction else ""
                number_to_modify = int(number)
                return f"{range_part} {direction}{number}{get_suffix(number_to_modify)} {street_name}{remaining}"
            elif len(groups) == 4:
                if '-' in groups[0]:
                    first_part, number, street_name, remaining = groups
                    number_to_modify = int(number)
                    return f"{first_part} {number}{get_suffix(number_to_modify)} {street_name}{remaining}"
                else:
                    first_number, second_part, street_name, remaining = groups
                    number_to_modify = int(re.search(r'\d+', second_part).group())
                    return f"{first_number} {second_part}{get_suffix(number_to_modify)} {street_name}{remaining}"

    return address


def process_schools(schools_data, websites):
    """
    Processes the list of schools and their corresponding website URLs to prepare data for database insertion.

    Args:
        schools_data (list): List of dictionaries containing school data from the API.
        websites (list): List of website URLs for the schools.

    Returns:
        list: A list of tuples where each tuple represents a row to be inserted into the database.
    """
    schools_info = []
    hardcoded_schools_dict = {school['name']: school for school in HARD_CODED_SCHOOLS}

    for i, (school, personal_website) in enumerate(zip(schools_data, websites), 1):
        url = f"https://www.schools.nyc.gov/schools/{school['locationCode']}"

        # Check if the school has hardcoded information
        if school['name'] in hardcoded_schools_dict:
            hardcoded_school = hardcoded_schools_dict[school['name']]
            formatted_address = hardcoded_school['formatted_address']
            domain_name = extract_domain(personal_website) if personal_website else hardcoded_school['domain_name']
            schools_info.append((
                hardcoded_school['url'],
                hardcoded_school['name'],
                hardcoded_school['personal_website'],
                domain_name,
                hardcoded_school['district'],
                hardcoded_school['grades'],
                hardcoded_school['borough'],
                formatted_address
            ))
            continue

        # Check if the school has an edge case address
        address = EDGE_CASE_ADDRESSES.get(url, f"{school['primaryAddressLine']}, {school['boroughName']}, {school['stateCode']}, {school['zip']}")
        
        # Format the address with an ordinal suffix
        formatted_address = add_suffix(address)

        # Extract domain name from personal website if available
        domain_name = extract_domain(personal_website) if personal_website else None

        # Append the processed school information
        schools_info.append((
            url,
            school['name'],
            personal_website,
            domain_name,
            school.get('district', ''),
            school.get('grades', ''),
            school.get('boroughName', ''),
            formatted_address
        ))

        if i % 500 == 0:
            logging.info(f"Processed {i} schools...")

    return schools_info


def batch_insert_schools(data, password):
    """
    Inserts school data into a MySQL database in batches.

    Args:
        data (list of tuples): List of tuples where each tuple represents a row to be inserted.
        password (str): MySQL password for database authentication.
    """
    try:
        connection = mysql.connector.connect(
            host=HOST,
            user=USER,
            password=password,
            database=DATABASE
        )
        if connection.is_connected():
            cursor = connection.cursor()

            # Truncate the table to ensure it is empty before insertion
            logging.info("Truncating the table to ensure it's empty...")
            cursor.execute("TRUNCATE TABLE schools")
            connection.commit()

            # Define the SQL insert query
            insert_query = """
                INSERT INTO schools (url, name, personal_website, domain_name, district, grades, borough, formatted_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Execute the batch insert in chunks
            batch_size = 100
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                cursor.executemany(insert_query, batch)
                connection.commit()

            logging.info(f"Successfully inserted {len(data)} rows into the database.")

    except Error as e:
        logging.error(f"Error while inserting data into MySQL: {e}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


async def main():
    """
    Main function to orchestrate fetching, processing, and inserting school data.
    """
    # Configuration for API URL
    api_url = "https://ws.schools.nyc/schooldata/GetSchools?search=&borough=&grade="

    # Prompt user for MySQL password
    password = getpass.getpass(prompt='Enter MySQL password: ')

    async with aiohttp.ClientSession() as session:
        # Fetch school data from the API
        fetch_start = time.time()
        schools_data = await fetch_schools(api_url, session)
        fetch_end = time.time()
        logging.info(f"Retrieved data for {len(schools_data)} schools in {fetch_end - fetch_start:.2f} seconds.")

        # Create tasks to fetch personal websites concurrently with a semaphore to control the rate
        semaphore = asyncio.Semaphore(50)
        website_tasks = []
        for index, school in enumerate(schools_data):
            if index % 100 == 0 and index > 0:
                logging.info(f"Processing school {index} out of {len(schools_data)}")
            url = f"https://www.schools.nyc.gov/schools/{school['locationCode']}"
            task = asyncio.create_task(fetch_school_website_with_semaphore(session, semaphore, url))
            website_tasks.append(task)

        # Wait for all website fetch tasks to complete
        website_start = time.time()
        logging.info("Starting to fetch personal websites...")
        websites = await asyncio.gather(*website_tasks)

        website_end = time.time()
        logging.info(f"Fetched personal websites in {website_end - website_start:.2f} seconds.")
        successful_fetches = sum(1 for website in websites if website is not None)
        failed_fetches = len(websites) - successful_fetches
        logging.info(f"Successful fetches: {successful_fetches}, Failed fetches: {failed_fetches}")

        # Process the fetched school data
        logging.info("Processing school information...")
        schools_info = process_schools(schools_data, websites)
        logging.info(f"Processed {len(schools_info)} schools.")

        # Insert the processed data into the MySQL database
        logging.info("Inserting data into MySQL...")
        batch_insert_schools(schools_info, password)
        logging.info("Data insertion completed.")


# Configure logging to output information
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    asyncio.run(main())
