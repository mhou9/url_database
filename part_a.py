import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse
from geopy.geocoders import Here #EMFSMes4qAjPG6GIaFqtAt8DN_-Dh0KeqV-7zgdrmSU
from geopy.exc import GeocoderTimedOut

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

# insert (school_url, grades, district, borough) into the specific dictionary of each school
# input: the url of each school for second layer crawling
#        dictionary that we store the info that we got from each school
def website_crawler(url):
    try:
        driver.get(url)
        
        school_name = driver.find_element(By.CSS_SELECTOR, 'div.module-header h1.title')
        # for each item, create a new dictionary with school name as the key if it doesn't exist, key, value
        school_dict = school_item_dict.setdefault(school_name.text.strip(), {})
    
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
            if domain == "google":
                domain = url.split('/')
                if len(domain) >= 4 and domain[2] == "sites.google.com":
                    school_dict["Domain_1"] = domain[4] + ".org"
                    school_dict["Domain_2"] = domain[4] + ".com"
                elif len(domain) >= 3 and domain[2] == "sites.google.com":
                    school_dict["Domain_1"] = domain[3] + ".org"
                    school_dict["Domain_2"] = domain[3]+ ".com"
            else:
                school_dict["Domain_1"] = domain[0] + ".org"
                school_dict["Domain_2"] = domain[0] + ".com"

    except NoSuchElementException as e:
        schools_name = driver.find_element(By.CSS_SELECTOR, 'div.module.school-detail h1.title')
        no_url.add(schools_name.text)
        print(schools_name.text)
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
    
    # school_dict["Latitude"] = item.get_attribute('data-lat') #1st pair
    # school_dict["Longitude"] = item.get_attribute('data-lng') #2nd pair


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