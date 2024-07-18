domain = [
    "WSCNYC.ORG",
    "AMNH.ORG",
    "AMSBRONX.ORG",
    "AOITHS.ORG",
    "BCS448.ORG",
    "BRONXSOFTWARE.ORG",
    "CIX.CSI.CUNY.EDU",
    "ESCHS.ORG",
    "EWSIS.ORG",
    "JOHNDEWEYHIGHSCHOOL.ORG",
    "KIPPNY.ORG",
    "MANHATTANBRIDGESHS.ORG",
    "MYCHAH.ORG",
    "PS1CONNECTS.ORG",
    "PS170X.ORG",
    "PS321.INFO",
    "PS372.NET",
    "P94M.ORG",
    "SCHOOLS.NYC.GOV",
    "ACADEMYOFTHECITY.ORG",
    "AMNH.ORG",
    "AMSBRONX.ORG",
    "AOITHS.ORG",
    "AOITHS.ORG",
    "ARCHIMEDESACADEMY.ORG",
    "BAYCHESTERWAVES.ORG",
    "BAYSIDEHIGHSCHOOL.ORG",
    "BCS448.ORG",
    "BEACONSCHOOL.ORG",
    "BNS146.ORG",
    "BRONXARENA.ORG",
    "BRONXDALEHS.ORG",
    "BRONXSOFTWARE.ORG",
    "BROOKLYNBEES.ORG",
    "CIX.CSI.CUNY.EDU",
    "COLUMBIASECONDARY.ORG",
    "CSSJBRONX.ORG",
    "DIGITALTECHHS.ORG",
    "EPICSCHOOLSNYC.ORG",
    "ESCHS.ORG",
    "ESSEXSTREETACADEMY.ORG",
    "EWSIS.ORG",
    "FANNIELOU.ORG",
    "FDA2.NET",
    "FLHFHS.ORG",
    "FUTURELEADERSINSTITUTE.ORG",
    "HSARTSTECH.ORG",
    "HSMSE.ORG",
    "IHPCH.ORG",
    "JOHNDEWEYHIGHSCHOOL.ORG",
    "KIPPNY.ORG",
    "KIPPNYC.ORG",
    "K051.ORG",
    "K497.ORG",
    "LANGUAGEANDINNOVATION.ORG",
    "LEADERS6-12.ORG",
    "MANHATTANBRIDGESHS.ORG",
    "MCNDHS.COM",
    "MILLENNIUMBROOKLYNHS.ORG",
    "MOTTHALL2.ORG",
    "MYBIHS.ORG",
    "MYCHAH.ORG",
    "NEWHEIGHTSMS.ORG",
    "NYC.GOV",
    "NYCLABSCHOOL.ORG",
    "OWMS.ORG",
    "PPASSHARE.ORG",
    "PSICOLOGOS.COM",
    "PSMS108.ORG",
    "PSMS161.ORG",
    "PSMS29.COM",
    "PS1CONNECTS.ORG",
    "PS10.ORG",
    "PS107.ORG",
    "PS116.ORG",
    "PS130BROOKLYN.COM",
    "PS151K.ORG",
    "PS261BROOKLYN.ORG",
    "PS277X.COM",
    "PS29BK.ORG",
    "PS295.ORG",
    "PS330Q.ORG",
    "PS361.ORG",
    "PS372.NET",
    "PS372.ORG",
    "PS39.ORG",
    "PS39.ORG",
    "PS57.US",
    "PS58ONLINE.ORG",
    "PS6NYC.COM",
    "PS61X.ORG",
    "PS72M.ORG",
    "PS72M.ORG",
    "PS89.ORG",
    "P94M.ORG",
    "SCHOLARSNYC.COM",
    "SCHOOLS.NYC",
    "SCHOOLS.NYC.GOV",
    "SCHOOLS.NYC.ORG",
    "SLJHS.ORG",
    "TSMSONLINE.ORG",
    "TYWLSBROOKLYN.ORG",
    "UAMUSICANDART.ORG",
    "UPPUBLICSCHOOLS.ORG",
    "VALIDUSPREP.ORG",
    "WHEELSNYC.ORG",
    "WILLIAMSBURGPREP.ORG",
    "CIX.CSI.CUNY.EDU",
    "MCNDHS.COM",
    "MCNDHS.COM",
    "CRISTOREYBROOKLYN.ORG",
    "CHARTER.NEWVISIONS.ORG",
    "CIX.CSI.CUNY.EDU",
    "ESCHS.ORG",
    "MS131.ORG",
    "MYBIHS.ORG",
    "MYBIHS.ORG",
    "MYBIHS.ORG",
    "PS32.ORG",
    "PS503ONLINE.ORG",
    "ACADEMYOFTHECITY.ORG",
    "ACADEMYOFTHECITY.ORG",
    "AMSBRONX.ORG",
    "AOITHS.ORG",
    "SCHOOLS.NY.GOV",
    "SCHOOLSNYC.GOV",
    "VALIDUSPREP.ORG",
    "AMSBRONX.ORG",
    "AMSBRONX.ORG",
    "BCS448.ORG",
    "BCS448.ORG",
    "BRONXSOFTWARE.ORG",
    "CSSJBRONX.ORG",
    "EPICSCHOOLSNYC.ORG",
    "ESCHS.ORG",
    "EWSIS.ORG",
    "FLHFHS.ORG",
    "HSFI.US",
    "HSFI.US",
    "HSMSE.ORG",
    "HSTAT.ORG",
    "MILLENNIUMBROOKLYNHS.ORG",
    "MS233.ORG",
    "MYBIHS.ORG",
    "PAIHSMONROE.ORG",
    "PETRIDESSCHOOL.COM",
    "SLJHS.ORG",
    "EWSIS.ORG",
    "HSFI.US",
    "ICHSBRONX.ORG",
    "MYBIHS.ORG"
]

import json

# Function to read JSON data from a file
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

# Function to check if a specific word exists in the JSON data
def check_word_in_json(data, word):
    if isinstance(data, dict):
        for key, value in data.items():
            if check_word_in_json(key, word) or check_word_in_json(value, word):
                return True
    elif isinstance(data, list):
        for item in data:
            if check_word_in_json(item, word):
                return True
    elif isinstance(data, str):
        if word in data:
            return True
    return False

# Read the JSON data from the file
file_path = 'new_output_file.json'
json_data = read_json_file(file_path)

existed = []
# Check if a specific word exists in the JSON data
for word in domain:
    exists = check_word_in_json(json_data, word.lower())
    if exists:
        existed.append(word)

print(existed)
