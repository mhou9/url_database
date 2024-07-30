from urllib3.exceptions import InsecureRequestWarning
import time
import json
from urllib.parse import urlparse
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
# from retrying import retry
from word2number import w2n
import re
import requests
from bs4 import BeautifulSoup
import asyncio
import aiohttp
# import concurrent.futures
# from geopy.extra.rate_limiter import RateLimiter

# Disable insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Add the correct ending for all numbers
def add_numeric_id(street):
    street_Ones = int(street) % 10
    print(street_Ones)
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

# Convert ordinal number as word to numeric with ending
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
                return word  # Return the original word if not found in the mapping
        else:
            number = w2n.word_to_num(word)
            if number:
                number = add_numeric_id(str(number))
                return number
    except ValueError:
        return False

# Handle edge cases with address for geolocator
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
        (?P<State_ZIP>[A-Z]{2}\s*\d{5})                                                       # Matches 'MN ' and 'MN, '# Matches '56001'                                                                       
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
        (?P<State_ZIP>[A-Z]{2}\s*\d{5})                                                       # Matches 'MN ' and 'MN, '# Matches '56001'  
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
        print("After fixed: " + address)
        print("Format Address Function Runtime:", time.time()-start)
        return address

    if match2:
        street = match2.group('StreetName')
        if street.isdigit():
            street = add_numeric_id(street)

        # case where street number is written in word
        if convert_word_to_numeric(street) != False:
            street = convert_word_to_numeric(street)

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
        if street_designator != None:
            address = match2.expand(fr'{housenumber} {street} {street_designator}, {townname}, \g<State_ZIP>')
        else:
            address = match2.expand(fr'{housenumber} {street}, {townname}, \g<State_ZIP>')
        print("After fixed2: " + address)
        print("Format Address Function Runtime:", time.time()-start)
        return address

    print("no match")
    print("Format Address Function Runtime:", time.time()-start)
    return address

# Get the private school website and domains from the doe url by web scraping the website using BeautifulSoup
async def web_crawler_doe_async(session, doe_url, school_name):
    try: 
        start = time.time()
        async with session.get(doe_url, timeout=10000) as response:
            html_content = await response.text()
            soup = BeautifulSoup(html_content, 'html.parser')
            school_url_elements = soup.find('a', string='School Website')

            if school_url_elements:
                url = school_url_elements.get('href')
                # formats some weird urls
                if url.startswith("http:/") and not url.startswith("http://"):
                    url = url.replace("http:/", "http://")
                domain = urlparse(url).netloc.replace('www.', '').split('.')

                if "google" in domain:
                    google_url.append(school_name)
                    print("Web Crawler Doe Function Runtime:", time.time()-start)
                    return {
                        "School Website": None,
                        "Domain_1": None,
                        "Domain_2": None,
                        "Domain_3": None,
                        "Domain_4": None
                    }
                else:
                    print("Web Crawler Doe Function Runtime:", time.time()-start)
                    return {
                        "School Website": url,
                        "Domain_1": f"{domain[0]}.org",
                        "Domain_2": f"{domain[0]}.com",
                        "Domain_3": f"{domain[0]}.edu",
                        "Domain_4": f"{domain[0]}.net"
                    }
            else:
                no_url.append(school_name)
                print("Web Crawler Doe Function Runtime:", time.time()-start)
                return {
                    "School Website": None,
                    "Domain_1": None,
                    "Domain_2": None,
                    "Domain_3": None,
                    "Domain_4": None
                }
    except Exception as e:
        # goes into this exception if doe url return 404 error
        print(f"Error fetching data for school {school_name}: {e}")
        print("Web Crawler Doe Function Runtime:", time.time() - start)
        school_name_issue_urls.append(doe_url)
        # print(f"completed index {index}")
        return {
            "School Website": None,
            "Domain_1": None,
            "Domain_2": None,
            "Domain_3": None,
            "Domain_4": None
        }

# Execue the web crawler function to get the private school website and domains
async def run_domain(doe_urls):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in doe_urls:
            # for index in range(concurrent_requests):
            tasks.append(web_crawler_doe_async(session, url[0], url[1]))

        results = await asyncio.gather(*tasks)

        for result, url in zip(results, doe_urls):
            school_item_dict[url[1]].update(result)

def geocode_with_retry(geolocator, location): 
    try:
        return geolocator.geocode(location, timeout=5)
    except GeocoderUnavailable as e:
        print(f"GeocoderUnavailable: {e}")
        raise

# def geocode_to_coordinates():
#     geolocator = Nominatim(user_agent="my_request")
#     geocode_limit = RateLimiter(geo)

# Main Program
start = time.time()
URL = "https://ws.schools.nyc/schooldata/GetSchools?search=&borough=&grade="
r = requests.get(url = URL, verify=False)
data = r.json() 
geolocator = Nominatim(user_agent="my_request")

school_item_dict = {} #dict that stores all the info
no_url = [] # store a list of school that return None when trying to locate its school url, which means it doesn't has its own url attached
all_links = [] #get all links from the first layer
address_issue_schools = [] # get the name of all schools that have unformatted address that unable to convert to coordinates
school_name_issue_urls = [] #doe link is raise error of school name not found
google_url = [] # store a list of school that have site.google as their domain
doe_urls = [] # store all the doe urls and fetch them into the async function at once to run concurrently
formatted_address = [] #store all the address for fetch into multithread geocoder at once

# Total : 3001 schools in the API response object
# loop through each school and store all the info:
# {'locationCode': 'K001', 'type': 'DOE', 'boroughName': 'Brooklyn', 'boroughCode': 'K', 'name': 'P.S. 001 The Bergen', 
# 'phoneNumber': '718-567-7661', 'primaryAddressLine': '309 47 STREET', 'zip': '11220', 'grades': 'PK,0K,01,02,03,04,05,SE', 
# 'stateCode': 'NY', 'x': '-8238913.43780000', 'y': '4960699.12320000', 'profile': '', 'neighborhood': 'Sunset Park West                                                           ', 
# 'district': '15', 'distance': '', 'dataflag': 'L'}
existed_key = []
for school in data:
    if school['name'].strip() in school_item_dict:
        existed_key.append(school['name'].strip())

    school_dict = school_item_dict.setdefault(school['name'].strip(), {})
    address = school['primaryAddressLine'].title() + ', ' + school['boroughName'] + ', ' + school['stateCode'] + ' ' + school['zip']
    address_x = address.strip()

    # Fetch the address into geolocator to get the coordinates
    loc = format_address(address_x) 
    formatted_address.append(loc)
    geocode_time = time.time()
    location = geocode_with_retry(geolocator, loc) 
    print("Geocode with Retry Function Runtime:", time.time() - geocode_time)  

    if location != None:
        print("Got location: " + location.address)
        school_dict["Latitude"] = location.latitude #1st pair
        school_dict["Longitude"] = location.longitude  #2nd pair

    # Collect the name of all school where its address was not able to convert to coordinate
    else:
        school_dict["Latitude"] = "0" #1st pair
        school_dict["Longitude"] = "0" #2nd pair
        address_issue_schools.append((school['name'].strip(), address_x))

    school_dict["Grade"] = school['grades']
    school_dict["District"] = school['district']
    school_dict["Borough"] = school['boroughName']

    # extract the school url using the exact path, if no school website is found, add the school name onto the no url list
    doe_url = f"http://www.schools.nyc.gov/schools/{school['locationCode']}"
    doe_urls.append([doe_url, school['name'].strip()])
    print("\n")

concurrent_requests = 2891
asyncio.run(run_domain(doe_urls)) #concurrent_requests = concurrent_requests
print(len(data))
print(f"\nThis is list of schools without url provided in the DOE website (no private school url attached): {no_url}")
print(f"\nDOE link issue: {school_name_issue_urls}")
print(f"\nNo coordinate get for address converting: {address_issue_schools}")
print(f"\nThese are {len(google_url)} schools using google site as their url: {google_url}")
not_converted = len(address_issue_schools)
percentage = 100 - 100 * float(not_converted)/float(len(data))
no_url_number = len(no_url)
print(f"\nGeocode was not able to convert {not_converted} school addresses.\nThus, the converting percentage is {percentage}%.")
print(f"There are {no_url_number} schools with no private url provided.")

json_str = json.dumps(school_item_dict, indent= 4)
with open("testing-testing.json", "w") as outfile:
    outfile.write(json_str)
    print("\nSaved")

with open('error.log', 'w') as file:
    # Write each item in the list to a new line in the file
    for item in address_issue_schools:
        file.write(f"{item[0]} : {item[1]}\n")

print(f"Schools that need to be hardcoded for its coordinate can be found in the file {'error.log'}")

print(existed_key)
print(f"There are {len(existed_key)} duplicate schools.")
end = time.time()
runtime = end - start
print(f"Runtime of the program: {runtime} seconds")