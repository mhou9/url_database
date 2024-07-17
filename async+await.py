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
import traceback

# Disable insecure request warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# add the correct ending for all numbers
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

# convert ordinal number as word to numeric with ending
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
        print("After fixed2: " + address)
        print("Format Address Function Runtime:", time.time()-start)
        return address

    print("no match")
    print("Format Address Function Runtime:", time.time()-start)
    return address

def geocode_with_retry(geolocator, location): 
    try:
        return geolocator.geocode(location, timeout=5)
    except GeocoderUnavailable as e:
        print(f"GeocoderUnavailable: {e}")
        raise

async def web_crawler_doe_async(session, doe_url, school_name):
    try: 
        start = time.time()
        async with session.get(doe_url, timeout=10000) as response:
            html_content = await response.text()
            soup = BeautifulSoup(html_content, 'html.parser')
            school_url_elements = soup.find('a', string='School Website')

            if school_url_elements:
                url = school_url_elements.get('href')
                domain = urlparse(url).netloc.replace('www.', '').split('.')

                if "google" in domain:
                    google_url.append(school_name)
                    print("Web Crawler Doe Function Runtime:", time.time()-start)
                    return {
                        "School Website": '',
                        "Domain_1": '',
                        "Domain_2": '',
                        "Domain_3": '',
                        "Domain_4": ''
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
                    "School Website": '',
                    "Domain_1": '',
                    "Domain_2": '',
                    "Domain_3": '',
                    "Domain_4": ''
                }
    except Exception as e:
        # goes into this exception if doe url return 404 error
        print(f"Error fetching data for school {school_name}: {e}")
        print(f"Exception type: {type(e)}")
        print(f"Exception args: {e.args}")
        print("Web Crawler Doe Function Runtime:", time.time() - start)
        print(traceback.format_exc())
        traceback.print_stack()
        school_name_issue_urls.append(doe_url)
        return {
            "School Website": '',
            "Domain_1": '',
            "Domain_2": '',
            "Domain_3": '',
            "Domain_4": ''
        }
    
async def run_domain(doe_urls):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in doe_urls:
            tasks.append(web_crawler_doe_async(session, url[0], url[1]))

        results = await asyncio.gather(*tasks)

        # Process results here (printing for demonstration)
        for result, url in zip(results, doe_urls):
            print(result)
            school_item_dict[url[1]].update(result)


# Main Program
start = time.time()
URL = "https://ws.schools.nyc/schooldata/GetSchools?search=&borough=&grade="
geolocator = Nominatim(user_agent="my_request")
r = requests.get(url = URL, verify=False)
data = r.json() 

school_item_dict = {} #dict that stores all the info
no_url = [] # store a list of school that return None when trying to locate its school url, which means it doesn't has its own url attached
all_links = [] #get all links from the first layer
address_issue_schools = [] # get the name of all schools that have unformatted address that unable to convert to coordinates
school_name_issue_urls = [] #doe link is raise error of school name not found
google_url = [] # 
doe_urls = []

# Total : 2900 schools
# loop through each school and store all the info:
# {'locationCode': 'K001', 'type': 'DOE', 'boroughName': 'Brooklyn', 'boroughCode': 'K', 'name': 'P.S. 001 The Bergen', 
# 'phoneNumber': '718-567-7661', 'primaryAddressLine': '309 47 STREET', 'zip': '11220', 'grades': 'PK,0K,01,02,03,04,05,SE', 
# 'stateCode': 'NY', 'x': '-8238913.43780000', 'y': '4960699.12320000', 'profile': '', 'neighborhood': 'Sunset Park West                                                           ', 
# 'district': '15', 'distance': '', 'dataflag': 'L'}
# 'profile' contains the school's private url link, need to turn lower case
count = 0 
existed_key = []
for school in data: 
    # if count >= 1000: break 
    if school['name'].strip() in school_item_dict:
        existed_key.append(school['name'].strip())
    school_dict = school_item_dict.setdefault(school['name'].strip(), {})
    address = school['primaryAddressLine'].lower() + ', ' + school['boroughName'] + ', ' + school['stateCode'] + ' ' + school['zip']
    address_x = address.strip()
    print("Address:", address_x) 

    # coordinates
    loc = format_address(address_x) 
    print("Reformated Address:", loc) 

    geocode_time = time.time()
    location = geocode_with_retry(geolocator, loc) 
    print("Geocode with Retry Function Runtime:", time.time() - geocode_time)  
    # print("Location: ", location) 

    if location != None:
        print("Got location: " + location.address)
        school_dict["Latitude"] = location.latitude #1st pair
        school_dict["Longitude"] = location.longitude  #2nd pair

    # Collect the name of all school where its address was not able to convert to coordinate
    else:
        school_dict["Latitude"] = "00000000000000000000000" #1st pair
        school_dict["Longitude"] = "0000000000000000000000000" #2nd pair
        address_issue_schools.append(school['name'].strip())

    school_dict["Grade"] = school['grades']
    school_dict["District"] = school['district']
    school_dict["Borough"] = school['boroughName']

    # extract the school url using the exact path, if no school website is found, add the school name onto the no url list
    doe_url = f"http://www.schools.nyc.gov/schools/{school['locationCode']}"
    doe_urls.append([doe_url, school['name'].strip()])
    # school_dict["School Website"] = school['profile'].lower()
    # the_url = school['profile'].lower()
    # print("URL:", the_url) 

    # # if url is not found in the API database
    # if the_url == ''or the_url == "-" or the_url == "n/a": 
    #     print("Got no url thus get from doe link")
    #     # get the private website from the doe website
    #     # web_crawler_doe("http://www.schools.nyc.gov/schools/" + school['locationCode'], school['name'])
    #     doe_url = f"http://www.schools.nyc.gov/schools/{school['locationCode']}"
    #     doe_urls.append([doe_url, school['name'].strip()])

    # else:
    #     if the_url.startswith('https://') == False:
    #         the_url = 'http://' + the_url

    #     the_url = urlparse(the_url)
    #     domain = the_url.netloc.replace('www.', '').split('.')
    #     print(domain)
    #     if "google" in domain: #skip
    #         google_url.append(school['name'].strip())
    #         school_dict["Domain_1"] = ''
    #         school_dict["Domain_2"] = ''
    #         school_dict["Domain_3"] = ''
    #         school_dict["Domain_4"] = ''
    #     else:
    #         school_dict["Domain_1"] = domain[0] + ".org"
    #         school_dict["Domain_2"] = domain[0] + ".com"
    #         school_dict["Domain_3"] = domain[0] + ".edu"
    #         school_dict["Domain_4"] = domain[0] + ".net"

    count+=1
    print("\n")

asyncio.run(run_domain(doe_urls))
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
with open("new_output_file.json", "w") as outfile:
    outfile.write(json_str)
    print("\nSaved")

print(count)
print(existed_key)
print(f"There are {len(existed_key)} duplicate schools.")
end = time.time()
runtime = end - start
print(f"Runtime of the program: {runtime} seconds")