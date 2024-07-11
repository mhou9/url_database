import asyncio
import json
import re
import time
from urllib.parse import urlparse
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
from retrying import retry
from word2number import w2n
from bs4 import BeautifulSoup
import aiohttp
import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Global variables for tracking issues
no_url = set()
address_issue_schools = set()
school_name_issue_urls = set()
google_url = set()

# Function to add ordinal suffix to numbers
def add_numeric_id(street):
    street_Ones = int(street) % 10
    if street_Ones == 0 or (int(street) % 100) in [11, 12, 13]:
        street = street + 'th'
    elif street_Ones == 1:
        street = street + 'st'
    elif street_Ones == 2:
        street = street + 'nd'
    elif street_Ones == 3:
        street = street + 'rd'
    else:
        street = street + 'th'
    return street

# Function to convert ordinal words to numeric with suffix
def convert_word_to_numeric(word):
    try:
        word = word.strip().title()
        ordinal_mapping = {
            "First": "1st", "Second": "2nd", "Third": "3rd", "Fourth": "4th", "Fifth": "5th",
            "Sixth": "6th", "Seventh": "7th", "Eighth": "8th", "Ninth": "9th", "Tenth": "10th",
            "Eleventh": "11th", "Twelfth": "12th", "Thirteenth": "13th", "Fourteenth": "14th",
            "Fifteenth": "15th", "Sixteenth": "16th", "Seventeenth": "17th", "Eighteenth": "18th",
            "Nineteenth": "19th", "Twentieth": "20th", "Twenty-First": "21st", "Twenty-Second": "22nd",
            "Twenty-Third": "23rd", "Twenty-Fourth": "24th", "Twenty-Fifth": "25th"
        }
        if word.endswith(("st", "nd", "rd", "th")):
            if word in ordinal_mapping:
                return ordinal_mapping[word]
            else:
                return word
        else:
            number = w2n.word_to_num(word)
            if number:
                number = add_numeric_id(str(number))
                return number
    except ValueError:
        return False

# Function to format address
def format_address(geolocator, address):
    regex1 = r'''
        (?P<HouseNumber>[\w-]+)\s+
        (?P<Direction>([news]|North|East|West|South|Bay|Brighton|Kings|Beach)?)\b\s*?
        (?P<StreetName>[0-9]+)\s*
        (?P<StreetDesignator>Street|Avenue|Road|Lane|Drive|Walk|Blvd.|Court|Place|Terrace)\s*
        ,\s+
        (?: Ground\s+Floor,|(?:\w+\s*)?\d+(?:st|nd|rd|th|)\s+(?:\w+\s*)?)?
        (?P<TownName>.*),\s+
        (?P<State>[A-Z]{2}),?\s+
        (?P<ZIP>\d{5})
    '''
    regex1 = re.compile(regex1, re.VERBOSE | re.IGNORECASE)
    match1 = regex1.match(address)

    regex2 = r'''
        (?P<HouseNumber>[\w-]+)\s+
        (?P<StreetName>[A-Za-z0-9\']+)\s*
        (?:\s+(Street|Avenue|Road|Lane|Drive|Walk|Blvd.|Court|Place|Terrace|Ave|Ave.|St))?
        ,\s+
        (?:Ground\s+Floor,|Aprt\s+\d+|Slip\s+\d+|Unit\s+\d+|Suite\s+\d+|Room\s+\d+|Shop\s+\d+|Office\s+\d+|Lot\s+\d+|Space\s+\d+|Bay\s+\d+|Box\s+\d+|(?:\w+\s*)?\d+(?:st|nd|rd|th|)\s+(?:\w+\s*)?)?
        (?P<TownName>.*),\s+
        (?P<State>[A-Z]{2}),?\s+
        (?P<ZIP>\d{5})
    '''
    regex2 = re.compile(regex2, re.VERBOSE | re.IGNORECASE)
    match2 = regex2.match(address)

    if match1:
        street = match1.group('StreetName')
        street = add_numeric_id(street)
        direction = match1.group('Direction')
        townname = match1.group('TownName')

        if direction == "Kings":
            direction = "Kingsborough"
        if townname == "Jamaica":
            townname = "Queens"

        address = match1.expand(fr'\g<HouseNumber> {direction} {street} \g<StreetDesignator>, {townname}, \g<State>, \g<ZIP>')
        print("After fixed: " + address)
        return address

    elif match2:
        street = match2.group('StreetName')
        if street.isdigit():
            street = add_numeric_id(street)

        if convert_word_to_numeric(street) != False:
            street = convert_word_to_numeric(street)

        if street == "Delancy":
            street = "Delancey"
        elif street == "Seabreeze":
            street = "Sea Breeze"
        elif street == "Daniel":
            street = "Daniels"

        townname = match2.group('TownName')
        if townname == "Jamaica":
            townname = "Queens"
        street_designator = match2.group(3)

        housenumber = match2.group('HouseNumber')
        location = geocode_with_retry(geolocator, address)

        if location == None:
            if '-' in housenumber:
                housenumber = housenumber.split('-')[0].strip()
                print("fixing round 2")

        if street_designator != None:
            address = match2.expand(fr'{housenumber} {street} {street_designator}, {townname}, \g<State>, \g<ZIP>')
        else:
            address = match2.expand(fr'{housenumber} {street}, {townname}, \g<State>, \g<ZIP>')
        print("After fixed2: " + address)
        return address

    else:
        print("no match")
        return address

# Retry decorator for geocoding function
@retry(stop_max_attempt_number=5, wait_fixed=1000)
def geocode_with_retry(geolocator, location):
    try:
        return geolocator.geocode(location, timeout=2)
    except GeocoderUnavailable as e:
        print(f"GeocoderUnavailable: {e}")
        raise

# Function to perform async HTTP request to DOE website
async def web_crawler_doe_async(session, doe_url, school_name):
    async with session.get(doe_url, verify_ssl=False) as response:
        html_content = await response.text()
        soup = BeautifulSoup(html_content, 'html.parser')
        school_url_elements = soup.find('a', string='School Website')

        if school_url_elements:
            url = school_url_elements.get('href')
            domain = urlparse(url).netloc.replace('www.', '').split('.')

            if "google" in domain:
                google_url.add(school_name)
                return {
                    "School Website": '',
                    "Domain_1": '',
                    "Domain_2": '',
                    "Domain_3": '',
                    "Domain_4": ''
                }
            else:
                return {
                    "School Website": url,
                    "Domain_1": f"{domain[0]}.org",
                    "Domain_2": f"{domain[0]}.com",
                    "Domain_3": f"{domain[0]}.edu",
                    "Domain_4": f"{domain[0]}.net"
                }
        else:
            no_url.add(school_name)
            return {
                "School Website": '',
                "Domain_1": '',
                "Domain_2": '',
                "Domain_3": '',
                "Domain_4": ''
            }

# Function to process each school asynchronously
async def process_school(session, school, geolocator):
    school_dict = {}

    address = school['primaryAddressLine'].lower() + ', ' + school['boroughName'] + ', ' + school['stateCode'] + ' ' + school['zip']
    loc = format_address(geolocator, address)
    location = geocode_with_retry(geolocator, loc)

    if location != None:
        school_dict["Latitude"] = location.latitude
        school_dict["Longitude"] = location.longitude
    else:
        school_dict["Latitude"] = "unknown"
        school_dict["Longitude"] = "unknown"

    school_dict["schoolName"] = school['schoolName']

    doe_url = f"https://data.cityofnewyork.us/resource/{school['Location']}.json"
    school_dict.update(await web_crawler_doe_async(session, doe_url, school['schoolName']))

    return school_dict

# Main function to fetch and process all schools asynchronously
async def main():
    geolocator = Nominatim(user_agent="geoapiExercises")
    schools = [
        {"primaryAddressLine": "388", "boroughName": "Manhattan", "stateCode": "MN", "zip": "56001", "schoolName": "Mankato West High School", "Location": "swapi_film"},
        {"primaryAddressLine": "1", "boroughName": "Brooklyn", "stateCode": "NY", "zip": "11211", "schoolName": "Brooklyn Technical High School", "Location": "starwars"}
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [process_school(session, school, geolocator) for school in schools]
        results = await asyncio.gather(*tasks)

        # Process results here
        for result in results:
            print(json.dumps(result, indent=4))

if __name__ == '__main__':
    start_time = time.time()
    asyncio.run(main())
    print(f"Total execution time: {time.time() - start_time} seconds")
