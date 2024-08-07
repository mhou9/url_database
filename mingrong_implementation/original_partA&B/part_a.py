import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse
# from geopy.geocoders import Here #EMFSMes4qAjPG6GIaFqtAt8DN_-Dh0KeqV-7zgdrmSU
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
from retrying import retry
from word2number import w2n

import re
import folium
start = time.time()

driver = webdriver.Chrome()
driver.get("https://schoolsearch.schools.nyc/")

# Locate by using the attribute set for this button,
# click the search button
# wait for the new content
search_button = driver.find_element(By.XPATH, '//input[@type="submit" and @class="btn btn-primary" and @value="Search"]')
search_button.click()
time.sleep(5)

# Locate the inner scrollable container
inner_container = driver.find_element(By.CSS_SELECTOR, '.iScroll')

# # Set the current height of the inner scroller 
# # In a loop, keep scrolling the inner scroller and update the newest height,
# #               compare between the currect and the next height to find out if scroller reach its end
# #               if yes, break the loop; else, continue until yes
# last_height = driver.execute_script("return arguments[0].scrollHeight", inner_container)
# while True:
#     driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", inner_container)
#     time.sleep(2)
#     new_height = driver.execute_script("return arguments[0].scrollHeight", inner_container)
#     if new_height == last_height:
#         break
#     last_height = new_height

# Now, we have the html content of elements inside the inner scroller
# insert all the info (school name, lat, lng, DOE url) into the dictionary of dictionaries
school_item_dict = {} #dict that stores all the info
no_url = set() # store a list of school that return None when trying to locate its school url, which means it doesn't has its own url attached
all_links = set() #get all links from the first layer
address_issue_schools = set() # get the name of all schools that have unformatted address that unable to convert to coordinates
school_name_issue_urls = set() #doe link is raise error of school name not found

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

def convert_word_to_numeric(word):
    try:
        word = word.strip().title()

        #ordinal conversion
        ordinal_mapping = {
            "First": "1st",
            "Second": "2nd",
            "Third": "3rd",
            "Fourth": "4th",
            "Fifth": "5th",
            "Sixth": "6th",
            "Seventh": "7th",
            "Eighth": "8th",
            "Ninth": "9th",
            "Tenth": "10th",
            "Eleventh": "11th",
            "Twelfth": "12th",
            "Thirteenth": "13th",
            "Fourteenth": "14th",
            "Fifteenth": "15th",
            "Sixteenth": "16th",
            "Seventeenth": "17th",
            "Eighteenth": "18th",
            "Nineteenth": "19th",
            "Twentieth": "20th",
            "Twenty-First": "21st",
            "Twenty-Second": "22nd",
            "Twenty-Third": "23rd",
            "Twenty-Fourth": "24th",
            "Twenty-Fifth": "25th",
            # Add more ordinal conversions as needed
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

def format_address(geolocator, address):
    # Case 1 : 511 7 Ave, Brooklyn, NY 11215, 8-21 Bay 25 Street, Queens, NY 11691  -- 7 Avenue to 7th Avenue, detect Bay as direction
    # Case 2 : 10 South Street, Slip 7, Manhattan, NY 10004                         -- make sure South is detected under streetname and 'Slip 7' is removed
    # add to case 1 - 2322 3 Avenue, Ground Floor, Manhattan, NY, 10035

    regex1 = r'''
        (?P<HouseNumber>[\w-]+)\s+                                                              # Matches '717 ' or '90-05'
        (?P<Direction>([news]|North|East|West|South|Bay|Brighton|Kings|Beach)?)\b\s*?           # Matches 'N ' or ' ' or 'North '
        (?P<StreetName>[0-9]+)\s*                                                               # Matches ONLY numeric
        (?P<StreetDesignator>Street|Avenue|Road|Lane|Drive|Walk|Blvd.|Court|Place|Terrace)\s*   # Matches 'Street ' or 'Avenue '
        ,\s+                                                                                    # Force a comma after the street
        (?: Ground\s+Floor,|(?:\w+\s*)?\d+(?:st|nd|rd|th|)\s+(?:\w+\s*)?)?                      # Remove " Ground Floor,"
        (?P<TownName>.*),\s+                                                                    # Matches 'MANKATO, '
        (?P<State>[A-Z]{2}),?\s+                                                                # Matches 'MN ' and 'MN, '
        (?P<ZIP>\d{5})                                                                          # Matches '56001'
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
        (?P<State>[A-Z]{2}),?\s+                                                                # Matches 'MN ' and 'MN, '
        (?P<ZIP>\d{5})                                                                          # Matches '56001'
    '''
    regex2 = re.compile(regex2, re.VERBOSE | re.IGNORECASE) #store all the set constriant in here, verbose and ignore case
    match2 = regex2.match(address)

    # address is incorrect
    if match1:
        street = match1.group('StreetName')
        street = add_numeric_id(street)
        direction = match1.group('Direction')
        # 133 Kings 1 Walk, Brooklyn, NY, 11233
        if direction == "Kings":
            direction = "Kingsborough"
        townname = match1.group('TownName')
        if townname == "Jamaica":
            townname = "Queens"
        address = match1.expand(fr'\g<HouseNumber> {direction} {street} \g<StreetDesignator>, {townname}, \g<State>, \g<ZIP>')
        print("After fixed: " + address)
        return address
    elif match2:
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
    
@retry(stop_max_attempt_number=5, wait_fixed=3000)
def geocode_with_retry(geolocator, location):
    try:
        return geolocator.geocode(location, timeout=10)
    except GeocoderUnavailable as e:
        print(f"GeocoderUnavailable: {e}")
        raise

def find_element_with_retry(driver, by, value, max_retries=5, delay=2):
    retries = 0
    while retries < max_retries:
        try:
            element = driver.find_element(by, value)
            return element
        except NoSuchElementException:
            retries += 1
            print(f"Element not found, retrying ({retries}/{max_retries})...")
            time.sleep(delay)
    raise NoSuchElementException(f"Element not found after {max_retries} retries")

# insert (school_url, grades, district, borough) into the specific dictionary of each school
# input: the url of each school for second layer crawling
#        dictionary that we store the info that we got from each school
def website_crawler(url):
    try:
        driver.get(url)
        # The school DOE link would return 404 error thus hard code its info
        # American Dream Charter School II
        # Imagine Early Learning Center @ City College - MBVK
    
        school_name = find_element_with_retry(driver, By.CSS_SELECTOR, 'div.module-header h1.title')
        # for each item, create a new dictionary with school name as the key if it doesn't exist, key, value
        school_dict = school_item_dict.setdefault(school_name.text.strip(), {})

        address = driver.find_element(By.CSS_SELECTOR, 'div.module-header a')
        
        geolocator = Nominatim(user_agent="my_request")
        address_x = address.text.split('\n')[0].strip().strip()
        
        loc = format_address(geolocator, address_x)
        location = geocode_with_retry(geolocator, loc)
        if location != None:
            print("Got location: " + location.address + "\n")
            school_dict["Latitude"] = location.latitude #1st pair
            school_dict["Longitude"] = location.longitude  #2nd pair

        # Collect the name of all school where its address was not able to convert to coordinate
        else:
            school_dict["Latitude"] = "00000000000000000000000" #1st pair
            school_dict["Longitude"] = "0000000000000000000000000" #2nd pair
            address_issue_schools.add(school_name.text.strip())
            print("NOOOOOOOOOOOOOOOOOOOOOOOOOO\n")
            print(address_x)
            print("No coordinate: " + str(address_issue_schools))
            print("\n\n\n")
            
        other_info = driver.find_element(By.CSS_SELECTOR, 'div#tab-panel-01 ul.box-list')

        # Grade store
        try:
            grade_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Grades:']]//span")
            school_dict["Grade"] = grade_span.text.split(':')[-1].strip() # 3rd pair
        except NoSuchElementException:
            school_dict["Grade"] = "None"

        # District store
        try: 
            district_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Geographic District:']]//span")
            school_dict["District"] = district_span.text.split(':')[-1].strip() # 4th pair
        except NoSuchElementException:
            school_dict["District"] = "None"

        # Borough store
        try:
            borough_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Borough:']]//span")
            school_dict["Borough"] = borough_span.text.split(':')[-1].strip() # 5th pair
        except NoSuchElementException:
            school_dict["Borough"] = "None"
        
        # extract the school url using the exact path, if no school website is found, add the school name onto the no url list
        try:   
            school_url_elements = driver.find_element(By.XPATH, "//a[contains(text(), 'School Website')]")
            print(school_url_elements)
            if school_url_elements: # store the website into the dictionary
                url = school_url_elements.get_attribute("href")
                school_dict["School Website"] = url # 6th pair
                domain = urlparse(url).netloc.replace('www.', '').split('.')
                if domain == "google": #skip
                    school_dict["Domain_1"] = "None"
                    school_dict["Domain_2"] = "None"
                    school_dict["Domain_3"] = "None"
                    school_dict["Domain_4"] = "None"
                else:
                    school_dict["Domain_1"] = domain[0] + ".org"
                    school_dict["Domain_2"] = domain[0] + ".com"
                    school_dict["Domain_3"] = domain[0] + ".edu"
                    school_dict["Domain_4"] = domain[0] + ".net"

        except NoSuchElementException:
            schools_name = driver.find_element(By.CSS_SELECTOR, 'div.module.school-detail h1.title')
            no_url.add(schools_name.text.strip())
            school_dict["School Website"] = "None"
            school_dict["Domain_1"] = "None"
            school_dict["Domain_2"] = "None"
            school_dict["Domain_3"] = "None"
            school_dict["Domain_4"] = "None"
    
    #if doe link is giving the issue of school name not found, add to list for special adjustment
    except NoSuchElementException:
        school_name_issue_urls.add(url)

    finally:
        print(school_item_dict)

# extract all school items in this page at once and store
schools_item = driver.find_elements(By.XPATH, '//div[@class="item school-item" and @data-lat and @data-lng]')
for item in schools_item:
    # grab all the a tag within each school item, which should be one per each
    a_tag = item.find_element(By.CSS_SELECTOR, 'h2.title a')
    all_links.add(a_tag.get_attribute('href'))

# call the 2nd layer of crawling to complete storing rest of the info for this school
# sending in the DOE link and the value which is the inner dictionary
sorted_links = sorted(all_links)
for link in sorted_links:
    website_crawler(link) # doe link does not need to be store into the database, the school's own url will be store

print("\nThis is list of schools without url provided in the DOE website(no private school url attached): " + str(no_url))
print("\nDOE link issue: " + str(school_name_issue_urls))
print("\nNo coordinate get for address converting: " + str(address_issue_schools))
json_str = json.dumps(school_item_dict, indent= 4)

with open("output.json", "w") as outfile:
    outfile.write(json_str)
    print("\nSaved")

driver.quit()
end = time.time()
runtime = end - start
print(f"Runtime of the program: {runtime} seconds")