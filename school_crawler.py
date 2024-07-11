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

# MySQL Credentials
HOST = 'localhost'
USER = 'root'
DATABASE = 'schoolinfo'

# Hardcoded edge case mappings
EDGE_CASE_ADDRESSES = {
    "https://www.schools.nyc.gov/schools/KBUF": "133 Kingsborough 1st Walk, Brooklyn, NY 11233",
    "https://www.schools.nyc.gov/schools/X480": "1010 Rev. J. A. Polite Avenue, Bronx, NY 10459",
    "https://www.schools.nyc.gov/schools/X333": "888 Rev J A Polite Ave, Bronx, NY 10459",
    "https://www.schools.nyc.gov/schools/X274": "275 Harlem River Park Bridge, Bronx, NY 10453",
    "https://www.schools.nyc.gov/schools/X204": "1780 Dr. Martin Luther King Jr. Blvd, Bronx, NY 10453",
    "https://www.schools.nyc.gov/schools/QALO": "1 Jamaica Center Plaza, Queens, NY, 11432",
    "https://www.schools.nyc.gov/schools/M551": "10 South Street, Slip 7, Manhattan, NY 10004",
    "https://www.schools.nyc.gov/schools/KDVD": "561 Utica Ave, Brooklyn, NY 11203"
}

# Hardcoded school information
HARD_CODED_SCHOOLS = [
    {
        'url': None,
        'name': 'American Dream Charter School II',
        'personal_website': 'https://www.adcs2.org/',
        'domain_name': 'adcs2',
        'district': '7',
        'grades': '06,07,08,09,10,11,12',
        'borough': 'X',
        'formatted_address': '510 E 141st St, Bronx, NY 10454'
    },
    {
        'url': None,
        'name': 'Imagine Early Learning Center @ City College',
        'personal_website': 'https://imagineelc.com/schools/city-college-child-development-center/',
        'domain_name': 'imagineelc',
        'district': '',
        'grades': 'PK',
        'borough': 'M',
        'formatted_address': '119 Convent Ave, New York, NY 10031'
    }
]

def extract_domain(url):
    """
    Extract the domain name from a given URL.
    
    Args:
        url (str): The URL from which the domain name needs to be extracted.
        
    Returns:
        str: Extracted domain name in the format 'domain.extension'.
    """
    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')
    return '.'.join(domain_parts[-2:])

async def fetch_schools(api_url, session):
    """
    Fetches school data from the API.

    Args:
        api_url (str): The URL of the API to fetch data from.
        session (aiohttp.ClientSession): The aiohttp client session to use for requests.

    Returns:
        list: A list of school data dictionaries.
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

async def get_personal_website(session, url, semaphore):
    """
    Fetches the personal website of a school with rate limiting.

    Args:
        session (aiohttp.ClientSession): The aiohttp client session to use for requests.
        url (str): The URL of the school's personal website.
        semaphore (asyncio.Semaphore): Semaphore to control the rate limit.

    Returns:
        str: The URL of the personal website or None if it fails.
    """
    async with semaphore:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return str(response.url)
                else:
                    logging.error(f"Failed to fetch {url}: Status code {response.status}")
                    return None
        except Exception as e:
            logging.error(f"Error fetching personal website {url}: {e}")
            return None

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
    Processes the schools data to prepare it for insertion into the database.

    Args:
        schools_data (list): List of school data dictionaries.
        websites (list): List of websites corresponding to the schools.

    Returns:
        list: A list of tuples where each tuple represents a row to insert into the database.
    """
    schools_info = []
    hardcoded_schools_dict = {school['name']: school for school in HARD_CODED_SCHOOLS}

    for i, (school, personal_website) in enumerate(zip(schools_data, websites), 1):
        url = f"https://www.schools.nyc.gov/schools/{school['locationCode']}"

        # Check if this school has hardcoded information
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

        # Check if this school has an edge case address
        address = EDGE_CASE_ADDRESSES.get(url, f"{school['primaryAddressLine']}, {school['boroughName']}, {school['stateCode']}, {school['zip']}")
        
        # Format address with suffix
        formatted_address = add_suffix(address)

        # Extract domain
        domain_name = extract_domain(personal_website) if personal_website else None

        # Append school info
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
    Inserts data into a MySQL table in batches.

    Args:
        data (list of tuples): The list of tuples where each tuple represents a row to insert.
        password (str): MySQL password.
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

            # Truncate table to ensure it's empty
            logging.info("Truncating the table to ensure it's empty...")
            cursor.execute("TRUNCATE TABLE schools")
            connection.commit()

            # Define the insert query
            insert_query = """
                INSERT INTO schools (url, name, personal_website, domain_name, district, grades, borough, formatted_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Execute the batch insert
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
    # Configuration
    api_url = "https://ws.schools.nyc/schooldata/GetSchools?search=&borough=&grade="

    # Prompt the user for the MySQL password
    password = getpass.getpass(prompt='Enter MySQL password: ')

    async with aiohttp.ClientSession() as session:
        # Fetch the main schools data
        fetch_start = time.time()
        schools_data = await fetch_schools(api_url, session)
        fetch_end = time.time()
        logging.info(f"Retrieved data for {len(schools_data)} schools in {fetch_end - fetch_start:.2f} seconds.")

        # Create tasks for fetching personal websites
        semaphore = asyncio.Semaphore(50)
        website_tasks = []
        for school in schools_data:
            url = f"https://www.schools.nyc.gov/schools/{school['locationCode']}"
            task = asyncio.create_task(get_personal_website(session, url, semaphore))
            website_tasks.append(task)

        # Wait for all website tasks to complete
        website_start = time.time()
        logging.info("Starting to fetch personal websites...")
        websites = []
        successful_fetches = 0
        failed_fetches = 0
        for i, task in enumerate(asyncio.as_completed(website_tasks), 1):
            try:
                website = await task
                websites.append(website)
                if website:
                    successful_fetches += 1
                else:
                    failed_fetches += 1
                
                if i % 100 == 0:
                    logging.info(f"Fetched {i}/{len(website_tasks)} websites...")
            except Exception as e:
                logging.error(f"Error fetching a website: {e}")
                websites.append(None)
                failed_fetches += 1

        website_end = time.time()
        logging.info(f"Fetched personal websites in {website_end - website_start:.2f} seconds.")
        logging.info(f"Successful fetches: {successful_fetches}, Failed fetches: {failed_fetches}")

        # Process the results
        logging.info("Processing school information...")
        schools_info = process_schools(schools_data, websites)
        logging.info(f"Processed {len(schools_info)} schools.")

        # Insert the processed data into the MySQL database
        logging.info("Inserting data into MySQL...")
        batch_insert_schools(schools_info, password)
        logging.info("Data insertion completed.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    asyncio.run(main())
