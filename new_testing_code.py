import asyncio
import json
import re
import time
from urllib.parse import urlparse
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
from word2number import w2n
from bs4 import BeautifulSoup
import aiohttp
import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Global variables for tracking issues
school_item_dict = {}
no_url = set()
address_issue_schools = set()
school_name_issue_urls = set()
google_url = set()
addresses = set()

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

# convert ordinal number as word to numeric with ending
def convert_word_to_numeric(word):
    word = word.strip().title()
    ordinal_mapping = {
            "First": "1st", "Second": "2nd", "Third": "3rd", "Fourth": "4th", "Fifth": "5th",
            "Sixth": "6th", "Seventh": "7th", "Eighth": "8th", "Ninth": "9th", "Tenth": "10th",
            "Eleventh": "11th", "Twelfth": "12th", "Thirteenth": "13th", "Fourteenth": "14th",
            "Fifteenth": "15th", "Sixteenth": "16th", "Seventeenth": "17th", "Eighteenth": "18th",
            "Nineteenth": "19th", "Twentieth": "20th", "Twenty-First": "21st", "Twenty-Second": "22nd",
            "Twenty-Third": "23rd", "Twenty-Fourth": "24th", "Twenty-Fifth": "25th"
        }
    if word in ordinal_mapping:
        return ordinal_mapping[word]
    else:
        return word  # Return the original word if not found in the mapping

# This function is used to handle edge cases with address for geolocator
def format_address(address):
    # Case 1 : 511 7 Ave, Brooklyn, NY 11215, 8-21 Bay 25 Street, Queens, NY 11691  -- 7 Avenue to 7th Avenue, detect Bay as direction
    # Case 2 : 10 South Street, Slip 7, Manhattan, NY 10004                         -- make sure South is detected under streetname and 'Slip 7' is removed
    # add to case 1 - 2322 3 Avenue, Ground Floor, Manhattan, NY, 10035 
    start = time.time() 

    regex1 = r'''
        (?P<HouseNumber>[\w-]+)\s+                                                              # Matches '717 ' or '90-05'
        (?P<Direction>([news]|North|East|West|South|Bay|Brighton|Kings|Beach)?)\b\s*?           # Matches 'N ' or ' ' or 'North '
        (?P<StreetName>[0-9]+)\s*                                                               # Matches ONLY numeric
        (?P<StreetDesignator>Street|Avenue|Road|Lane|Drive|Walk|Blvd.|Court|Place|Terrace)\s*   # Matches 'Street ' or 'Avenue '
        ,\s+                                                                                    # Force a comma after the street
        (?: Ground\s+Floor,|(?:\w+\s*)?\d+(?:st|nd|rd|th|)\s+(?:\w+\s*)?)?                      # Remove " Ground Floor,"
        (?P<TownName>.*),\s+                                                                    # Matches 'MANKATO, '
        (?P<State_ZIP>[A-Z]{2},\s*\d{5})                                                       # Matches 'MN ' and 'MN, '# Matches '56001'                                                                       
    '''
    regex1 = re.compile(regex1, re.VERBOSE | re.IGNORECASE) #store all the set constriant in here, verbose and ignore case
    match1 = regex1.match(address) #store a match object that record detail info of the matched string, else None

    regex2 = r'''
        (?P<HouseNumber>[\w-]+)\s+                                                              # Matches '717 ' or '90-05'
        (?P<StreetName>[A-Za-z0-9\']+)\s*                                                       # Matches anything, later check if it is only numeric
        (?:\s+(Street|Avenue|Road|Lane|Drive|Walk|Blvd.|Court|Place|Terrace|Ave|Ave.|St))?      # Matches 'Street ' or 'Avenue '
        ,\s+                                                                                    # Force a comma after the street
        (?:Ground\s+Floor,|Aprt\s+\d+|Slip\s+\d+|Unit\s+\d+|Suite\s+\d+|Room\s+\d+|Shop\s+\d+|Office\s+\d+|Lot\s+\d+|Space\s+\d+|Bay\s+\d+|Box\s+\d+|(?:\w+\s*)?\d+(?:st|nd|rd|th|)\s+(?:\w+\s*)?)?
        # Not neccssary detail
        (?P<TownName>.*),\s+                                                                    # Matches 'MANKATO, '
        (?P<State_ZIP>[A-Z]{2},\s*\d{5})                                                       # Matches 'MN ' and 'MN, '# Matches '56001'  
    '''
    regex2 = re.compile(regex2, re.VERBOSE | re.IGNORECASE) #store all the set constriant in here, verbose and ignore case
    match2 = regex2.match(address)

    # address is incorrect
    if match1:
        street = match1.group('StreetName')
        street = add_numeric_id(street)
        direction = match1.group('Direction')
        townname = match1.group('TownName')
        # 133 Kings 1 Walk, Brooklyn, NY, 11233
        if direction == "Kings":
            direction = "Kingsborough"
        if townname == "Jamaica":
            townname = "Queens"
        address = match1.expand(fr'\g<HouseNumber> {direction} {street} \g<StreetDesignator>, {townname}, \g<State_ZIP>')
        # print("After fixed: " + address)
        print("Format Address Function Runtime:", time.time()-start)
        return address

    if match2:
        street = match2.group('StreetName')
        if street.isdigit():
            street = add_numeric_id(street)

        # case where street number is written in word
        if street.title().endswith(("st", "nd", "rd", "th")):
            street = convert_word_to_numeric(street)
        else:
            try:
                number = w2n.word_to_num(street.title())
                if number:
                    number = add_numeric_id(str(number))
                    return number
            except ValueError:
                return False

        #Edge cases:
        # 285 Delancy Street, Manhattan, NY 10002
        if street == "Delancy":
            street = "Delancey"
        # 271 Seabreeze Avenue, Brooklyn, NY, 11224
        elif street == "Seabreeze":
            street = "Sea Breeze"
        # 83-78 Daniel Street, Queens, NY, 11435
        elif street == "Daniel":
            street = "Daniels"

        townname = match2.group('TownName')
        if townname == "Jamaica":
            townname = "Queens"
        street_designator = match2.group(3)

        housenumber = match2.group('HouseNumber')
        # run geocode to see if locaiton is none, if none check for house number inconsistance 
        # check if house number is xxx-xx, yes then remove -xx
        # 4360-78 Broadway, Manhattan, NY 10033             -- 4360-78 to 4360
        # 1962-84 Linden Blvd., Brooklyn, NY 11207
        # location = geocode_with_retry(geolocator, address)
        # ---------------------------let this be hard coded------------------------------#
        # if location == None:
        #     if '-' in housenumber:
        #         housenumber = housenumber.split('-')[0].strip()
        #         print("fixing round 2")
        if street_designator != None:
            address = match2.expand(fr'{housenumber} {street} {street_designator}, {townname}, \g<State_ZIP>')
        else:
            address = match2.expand(fr'{housenumber} {street}, {townname}, \g<State_ZIP>')
        # print("After fixed2: " + address)
        print("Format Address Function Runtime:", time.time()-start)
        return address

# @retry(stop_max_attempt_number=5, wait_fixed=1000)
def geocode_with_retry(geolocator, location):
    try:
        return geolocator.geocode(location, timeout=2)
    except GeocoderUnavailable as e:
        print(f"GeocoderUnavailable: {e}")
        raise

async def web_crawler_doe_async(session, doe_url, school_name):
    try: 
        async with session.get(doe_url, verify_ssl=False, timeout=5) as response:
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
    except Exception as e:
        print(f"Error fetching data for school {school_name}: {e}")
        return {
            "School Website": '',
            "Domain_1": '',
            "Domain_2": '',
            "Domain_3": '',
            "Domain_4": ''
        }

# Function to process each school asynchronously
async def process_school(session, school, geolocator):
    global json_add
    school_dict = school_item_dict.setdefault(school['name'].strip(), {})

    address = school['primaryAddressLine'].lower() + ', ' + school['boroughName'] + ', ' + school['stateCode'] + ' ' + school['zip']
    address_x = address.strip()
    loc = format_address(address_x)
    addresses.add(loc)
    location = geocode_with_retry(geolocator, loc)

    if location != None:
        school_dict["Latitude"] = location.latitude
        school_dict["Longitude"] = location.longitude
    else:
        school_dict["Latitude"] = "00000000000000000000000" #1st pair
        school_dict["Longitude"] = "0000000000000000000000000"
        address_issue_schools.add(school['name'].strip())

    school_dict["Grade"] = school['grades']
    school_dict["District"] = school['district']
    school_dict["Borough"] = school['boroughName']

    doe_url = f"http://www.schools.nyc.gov/schools/{school['locationCode']}"
    school_dict.update(await web_crawler_doe_async(session, doe_url, school['name']))

    return school_dict

# Main function to fetch and process all schools asynchronously
async def main():
    URL = "https://ws.schools.nyc/schooldata/GetSchools?search=&borough=&grade="
    r = requests.get(url = URL, verify=False)
    data = r.json() 
    geolocator = Nominatim(user_agent="my_request")
    schools = data
    print("whattttt")

    async with aiohttp.ClientSession() as session:
        tasks = [process_school(session, school, geolocator) for school in schools]
        results = await asyncio.gather(*tasks)

        # Process results here
        for result in results:
            print(json.dumps(result, indent=4))

if __name__ == '__main__':
    start_time = time.time()
    asyncio.run(main())
    json_add = json.dumps(addresses, indent=4)
    with open("addresses.json", "w") as outfile:
        outfile.write(json_add)
        print("\nSaved")
    print(f"Total execution time: {time.time() - start_time} seconds")
