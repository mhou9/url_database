import json
import requests
import re
import time
from word2number import w2n

addresses = set()

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

def format_address(address):
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
        townname = match1.group('TownName')
        # 133 Kings 1 Walk, Brooklyn, NY, 11233
        if direction == "Kings":
            direction = "Kingsborough"
        if townname == "Jamaica":
            townname = "Queens"
        address = match1.expand(fr'\g<HouseNumber> {direction} {street} \g<StreetDesignator>, {townname}, \g<State>, \g<ZIP>')
        print("After fixed: " + address)
        return address
    elif match2:
        street = match2.group('StreetName').strip()
        if street.isdigit():
            street = add_numeric_id(street)
        
        # case where street number is written in word
        if convert_word_to_numeric(street) != False:
            street = convert_word_to_numeric(street)
        else:
            print("no match")
            return address

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
            address = match2.expand(fr'{housenumber} {street} {street_designator}, {townname}, \g<State>, \g<ZIP>')
        else:
            address = match2.expand(fr'{housenumber} {street}, {townname}, \g<State>, \g<ZIP>')
        print("After fixed2: " + address)
        return address
    else: 
        print("no match")
        return address

def main():
    # Example addresses, replace with your actual data source
    URL = "https://ws.schools.nyc/schooldata/GetSchools?search=&borough=&grade="
    r = requests.get(url = URL, verify=False)
    data = r.json()

    for school in data:
        address = school['primaryAddressLine'].lower() + ', ' + school['boroughName'] + ', ' + school['stateCode'] + ' ' + school['zip']
        print(address)
        address_x = address.strip()
        loc = format_address(address_x)
        print(loc)
        addresses.add(loc)

    addresses_list = list(addresses)
    print(len(addresses_list))
    print(len(data))
    # Write formatted addresses to a JSON file
    with open("addresses.json", "w") as outfile:
        json.dump(addresses_list, outfile, indent=4)
        print("\nSaved")

if __name__ == '__main__':
    main()
