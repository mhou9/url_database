import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse
# from geopy.geocoders import Here #EMFSMes4qAjPG6GIaFqtAt8DN_-Dh0KeqV-7zgdrmSU
from geopy.geocoders import Nominatim

import re

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

def format_address(address):
    # Case 1 : 511 7th Ave, Brooklyn, NY 11215         -- 7 Avenue to 7th Avenue
    # Case 2 : 10 South Street, Slip 7, Manhattan, NY 10004

    regex1 = r'''
        (?P<HouseNumber>[\w-]+)\s+                              # Matches '717 ' or '90-05'
        (?P<Direction>([news]|(?:North|East|West|South))?)\b\s*?    # Matches 'N ' or ' ' or 'North '
        (?P<StreetName>[0-9]+)\s*                               # Matches anything but only numeric
        (?P<StreetDesignator>\w*)\s*?                           # Optionally Matches 'ST '
        ,\s+                                                    # Force a comma after the street
        (?:Slip\s+\d+,\s*)?                                     # Not neccssary detail
        (?P<TownName>.*),\s+                                    # Matches 'MANKATO, '
        (?P<State>[A-Z]{2}),?\s+                                # Matches 'MN ' and 'MN, '
        (?P<ZIP>\d{5})                                          # Matches '56001'
    '''
    regex1 = re.compile(regex1, re.VERBOSE | re.IGNORECASE) #store all the set constriant in here, verbose and ignore case
    match1 = regex1.match(address) #store a match object that record detail info of the matched string, else None

    regex2 = r'''
        (?P<HouseNumber>[\w-]+)\s+                              # Matches '717 ' or '90-05'
        (?P<Direction>([news]|(?:North|East|West|South))?)\b\s*?    # Matches 'N ' or ' ' or 'North '
        (?P<StreetName>[0-9]+)\s*                               # Matches anything but only numeric
        (?P<StreetDesignator>\w*)\s*?                           # Optionally Matches 'ST '
        ,\s+                                                    # Force a comma after the street
        (?:Slip\s+\d+,\s*)?                                     # Not neccssary detail
        (?P<TownName>.*),\s+                                    # Matches 'MANKATO, '
        (?P<State>[A-Z]{2}),?\s+                                # Matches 'MN ' and 'MN, '
        (?P<ZIP>\d{5})                                          # Matches '56001'
    '''
    regex2 = re.compile(regex2, re.VERBOSE | re.IGNORECASE) #store all the set constriant in here, verbose and ignore case
    match2 = regex2.match(address)

    # address is incorrect
    if match1:
        #modify and then check
        street = match1.group('StreetName')
        street_Ones = int(street) % 10
        if street_Ones == 1:
            street = street + 'st'
        elif street_Ones == 2:
            street = street + 'nd'
        elif street_Ones == 3:
            street = street + 'rd'
        else: 
            street = street + 'th'
        
        address = match1.expand(fr'\g<HouseNumber> \g<Direction> {street} \g<StreetDesignator> \g<TownName> \g<State> \g<ZIP>')
        print("After fixed: " + address)
        return address
    else: 
        return address
    
    

# insert (school_url, grades, district, borough) into the specific dictionary of each school
# input: the url of each school for second layer crawling
#        dictionary that we store the info that we got from each school
def website_crawler(url):
    try:
        driver.get(url)
        
        school_name = driver.find_element(By.CSS_SELECTOR, 'div.module-header h1.title')
        # for each item, create a new dictionary with school name as the key if it doesn't exist, key, value
        school_dict = school_item_dict.setdefault(school_name.text.strip(), {})

        address = driver.find_element(By.CSS_SELECTOR, 'div.module-header a')
        
        geolocator = Nominatim(user_agent="my_request")
        address_x = address.text.split('\n')[0].strip().strip()
        loc = format_address("10 South Street, Slip 7, Manhattan, NY 10004")# 90-05 161st St Jamaica, NY 11432
        print("reach")
        location = geolocator.geocode(loc)
        if location != None:
            print(location.address + "\n")
            school_dict["Latitude"] = location.latitude #1st pair
            school_dict["Longitude"] = location.longitude  #2nd pair
        else:
            print("NOOOOOOOOOOOOOOOOOOOOOOOOOO\n")
            print(address_x)
    
        other_info = driver.find_element(By.CSS_SELECTOR, 'div#tab-panel-01 ul.box-list')

        # Grade store
        grade_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Grades:']]//span")
        school_dict["Grade"] = grade_span.text.split(':')[-1].strip() # 3rd pair

        # District store
        district_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Geographic District:']]//span")
        school_dict["District"] = district_span.text.split(':')[-1].strip() # 4th pair

        # Borough store
        borough_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Borough:']]//span")
        school_dict["Borough"] = borough_span.text.split(':')[-1].strip() # 5th pair

        # extract the school url using the exact path, if no school website is found, add the school name onto the no url list
        school_url_elements = driver.find_element(By.XPATH, "//a[contains(text(), 'School Website')]")
        print(school_url_elements)
        if school_url_elements: # store the website into the dictionary
            url = school_url_elements.get_attribute("href")
            school_dict["School Website"] = url # 6th pair
            domain = urlparse(url).netloc.replace('www.', '').split('.')
            if domain == "google": #skip
                school_dict["Domain_1"] = "None"
                school_dict["Domain_2"] = "None"

    except NoSuchElementException as e:
        schools_name = driver.find_element(By.CSS_SELECTOR, 'div.module.school-detail h1.title')
        no_url.add(schools_name.text)
        school_dict["School Website"] = "None"
        school_dict["Domain_1"] = "None"
        school_dict["Domain_2"] = "None"

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
for link in all_links:
    website_crawler(link) # doe link does not need to be store into the database, the school's own url will be store

print("This is list of schools without url provided in the DOE website: " + str(no_url))
json_str = json.dumps(school_item_dict, indent= 4)

# address = "8515 Ridge Boulevard, Brooklyn, NY, 11209"
# geolocator = Here(apikey='EMFSMes4qAjPG6GIaFqtAt8DN_-Dh0KeqV-7zgdrmSU', user_agent="9uzouu4JG91QHNMoChLD")
# try:
#     location = geolocator.geocode(address, exactly_one=True)
#     if location:
#         print((location.latitude, location.longitude))
#     else:
#         print("Address not found")
# except GeocoderTimedOut:
#     print("Timeout error")

with open("output.json", "w") as outfile:
    outfile.write(json_str)
    print("Saved")

driver.quit()