import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from selenium.common.exceptions import NoSuchElementException

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

# Set the current height of the inner scroller 
# In a loop, keep scrolling the inner scroller and update the newest height,
#               compare between the currect and the next height to find out if scroller reach its end
#               if yes, break the loop; else, continue until yes
last_height = driver.execute_script("return arguments[0].scrollHeight", inner_container)
while True:
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", inner_container)
    time.sleep(2)
    new_height = driver.execute_script("return arguments[0].scrollHeight", inner_container)
    if new_height == last_height:
        break
    last_height = new_height

# Now, we have the html content of elements inside the inner scroller
# insert all the info (school name, lat, lng, DOE url) into the dictionary of dictionaries
school_item_dict = {} #dict that stores all the info
no_url = set() # store a list of school that return None when trying to locate its school url, which means it doesn't has its own url attached


# insert (school_url, grades, district, borough) into the specific dictionary of each school
# input: the url of each school for second layer crawling
#        dictionary that we store the info that we got from each school
def website_crawler(url, dict):
    try:
        driver_2nd_layer = webdriver.Chrome()
        driver_2nd_layer.get(url)
    
        other_info = driver_2nd_layer.find_element(By.CSS_SELECTOR, 'div#tab-panel-01 ul.box-list')
        # Grade store
        grade_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Grades:']]//span")
        dict["Grade"] = grade_span.text.split(':')[-1].strip() # 3rd pair

        # District store
        district_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Geographic District:']]//span")
        dict["District"] = district_span.text.split(':')[-1].strip() # 4th pair

        # Borough store
        borough_span = other_info.find_element(By.XPATH, ".//li[.//strong[text()='Borough:']]//span")
        dict["Borough"] = borough_span.text.split(':')[-1].strip() # 5th pair

        # extract the school url using the exact path, if no school website is found, add the school name onto the no url list
        school_url_elements = driver_2nd_layer.find_element(By.XPATH, "//a[contains(text(), 'School Website')]")
        print(school_url_elements)
        if school_url_elements: # store the website into the dictionary
            dict["School Website"] = school_url_elements.get_attribute("href") # 6th pair

    except NoSuchElementException as e:
        schools_name = driver_2nd_layer.find_element(By.CSS_SELECTOR, 'div.module.school-detail h1.title')
        no_url.add(schools_name.text)
        print(schools_name.text)
        dict["School Website"] = "None"

    finally:
        print(school_item_dict)
        driver_2nd_layer.quit()

# extract all school items in this page at once and store
schools_item = driver.find_elements(By.XPATH, '//div[@class="item school-item" and @data-lat and @data-lng]')
for item in schools_item:
    # grab all the a tag within each school item, which should be one per each
    a_tag = item.find_element(By.CSS_SELECTOR, 'h2.title a')

    # for each item, create a new dictionary with school name as the key if it doesn't exist, key, value
    school_dict = school_item_dict.setdefault(item.get_attribute('data-name'), {})
    
    school_dict["Latitude"] = item.get_attribute('data-lat') #1st pair
    school_dict["Longitude"] = item.get_attribute('data-lng') #2nd pair

    # call the 2nd layer of crawling to complete storing rest of the info for this school
    # sending in the DOE link and the value which is the inner dictionary
    website_crawler(a_tag.get_attribute('href'), school_dict) # doe link does not need to be store into the database, the school's own url will be store


# # In a loop, input every link into the crawler function for a second layer of crawling to extract info
# for link in all_links:
#     website_crawler(link, school_item_dict)

print(no_url)
json_str = json.dumps(school_item_dict, indent= 4)

with open("output.json", "w") as outfile:
    outfile.write(json_str)
    print("Saved")

driver.quit()