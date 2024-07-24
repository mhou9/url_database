# hard code into MySQL
import mysql.connector
import getpass

password = getpass.getpass("Input your password for mysql: ")
database = input("What is your database name? Please enter: ")

# Connect to database
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd= password,
    database= database
)

cursor = connection.cursor()
csv_file_path = 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/new_output_3001.csv'
table_name = 'DOE_schools_data_2894'

# Configure MySQL so it allow local file upload to database
set_infile = """
SET GLOBAL local_infile = 1;
"""
cursor.execute(set_infile)
connection.commit()
print("Successfully set local_infile to be TRUE.")

# Define the table schema to create a table
create_table_query = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
    `School Name` VARCHAR(255),
    Latitude DECIMAL(9, 6),
    Longitude DECIMAL(9, 6),
    Grade VARCHAR(50),
    District VARCHAR(10),
    Borough VARCHAR(50),
    `School Website` VARCHAR(255),
    Domain_1 VARCHAR(255),
    Domain_2 VARCHAR(255),
    Domain_3 VARCHAR(255),
    Domain_4 VARCHAR(255)
);
"""

# Load data from the csv file into the table
load_data_query = f"""
LOAD DATA INFILE '{csv_file_path}'
INTO TABLE {table_name}
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
"""

cursor.execute(create_table_query)
cursor.execute(load_data_query)
connection.commit()
print(f"Data imported into {table_name} successfully.")

# Add primary key
primary_key = f"""
ALTER TABLE `database`.`{table_name}`
ADD COLUMN `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST;
"""
cursor.execute(primary_key)
connection.commit()
print("Added primary key.")

# Update domain for these 2 schools
#   1. American Dream Charter School II
#   2. Imagine Early Learning Center @ City College - MBVK
update_domain1 = """
UPDATE DOE_schools_data_2894 
SET 
    `School Website` = 'https://www.adcs2.org/',
    Domain_1 = 'adcs2.org',
    Domain_2 = 'adcs2.com',
    Domain_3 = 'adcs2.edu',
    Domain_4 = 'adcs2.net'
WHERE `School Name` = 'American Dream Charter School II'
"""
update_domain2 = """
UPDATE DOE_schools_data_2894 
SET 
    `School Website` = 'https://imagineelc.com/schools/city-college-child-development-center/',
    Domain_1 = 'imagineelc.org',
    Domain_2 = 'imagineelc.com',
    Domain_3 = 'imagineelc.edu',
    Domain_4 = 'imagineelc.net'
WHERE `School Name` = 'Imagine Early Learning Center @ City College - MBVK'
"""
cursor.execute(update_domain1)
cursor.execute(update_domain2)

# Update the school name, coordinates and domain for these 2 schools
#   1. All My Children Day Care And Nursery School (All My Children Day Care And Nursery School - KDVD)
#   2. Imagine Early Learning Center (Imagine Early Learning Centers @ Jamaica Kids)
update_name1 = """
UPDATE DOE_schools_data_2894 
SET 
    `School Name` = 'All My Children Day Care And Nursery School - MBZW',
    `School Website` = 'https://allmychildrendaycare.com/',
    Domain_1 = 'allmychildrendaycare.org',
    Domain_2 = 'allmychildrendaycare.com',
    Domain_3 = 'allmychildrendaycare.edu',
    Domain_4 = 'allmychildrendaycare.net',
    Latitude = '40.790603849295216',
    Longitude = '-73.97312802020215'
WHERE `School Name` = 'All My Children Day Care And Nursery School'
"""
update_name2 = """
UPDATE DOE_schools_data_2894 
SET 
    `School Name` = 'Imagine Early Learning Centers @ Jamaica Kids',
    `School Website` = 'https://imagineelc.com/schools/jamaica-kids-early-learning-center/',
    Domain_1 = 'imagineelc.org',
    Domain_2 = 'imagineelc.com',
    Domain_3 = 'imagineelc.edu',
    Domain_4 = 'imagineelc.net',
    Latitude = '40.702697431447575',
    Longitude = '-73.80090671350494'
WHERE `School Name` = 'Imagine Early Learning Center'
"""
cursor.execute(update_name1)
cursor.execute(update_name2)

# Update the coordinates for 35 schools
updates = [
    ("Metropolitan High School, The", "40.8278547454867", "-73.89699654561372"),
    ("Happy Scholars, Inc.", "40.61349543855342", "-74.00095981607727"),
    ("P.S. 004 Maurice Wollin", "40.5525482377547", "-74.19547485118717"),
    ("P.S. 057 Hubert H. Humphrey", "40.611260529300694", "-74.08378556643316"),
    ("P.S. 055 Benjamin Franklin", "40.83635881782132", "-73.90485064490468"),
    ("Success Academy Charter School - Bronx 2", "40.836161923128095", "-73.90495027630269"),
    ("New Visions AIM Charter High School II", "40.823475491165766", "-73.89804358723288"),
    ("Arturo A. Schomburg Satellite Academy Bronx", "40.8234722164604", "-73.8987505821225"),
    ("Bronx Regional High School", "40.82346409765683", "-73.89872912445014"),
    ("Bronx Engineering and Technology Academy", "40.87710833284173", "-73.91262697747227"),
    ("Bronx School of Law and Finance", "40.87784192439847", "-73.91378652814461"),
    ("English Language Learners and International Support Preparatory Academy (ELLIS)", "40.87721291598641", "-73.91255127373923"),
    ("Marble Hill High School for International Studies", "40.87787348734404", "-73.9132797314117"),
    ("New Visions Charter High School for Advanced Math and Science", "40.877476431107944", "-73.91310203515972"),
    ("Bronx Theatre High School", "40.8779039872469", "-73.91336218908397"),
    ("New Visions Charter High School for the Humanities", "40.87711969375018", "-73.9125363032833"),
    ("I.S. 229 Roland Patterson", "40.85266869009199", "-73.92128574787593"),
    ("The New American Academy at Roberto Clemente State Park", "40.85288194181465", "-73.92104215819913"),
    ("The Longwood Academy of Discovery", "40.82054115481338", "-73.89874503212259"),
    ("Bronx High School for the Visual Arts", "40.8519304393006", "-73.86451196095722"),
    ("P.S. 277", "40.81360947234675", "-73.9135955553995"),
    ("Mott Haven Village Preparatory High School", "40.81843244053653", "-73.91176058908628"),
    ("University Heights Secondary School", "40.818400937835776", "-73.91127711606919"),
    ("Cpc-Tribeca Early Learning Center", "40.7217406342474", "-74.0055800456191"),
    ("Rockaway Park High School for Environmental Sustainability", "40.58641541203024", "-73.82339948353565"),
    ("Channel View School for Research", "40.58635306246096", "-73.82344309332062"),
    ("New Visions Charter High School for the Humanities IV", "40.58652416520215", "-73.8238615179315"),
    ("Rockaway Collegiate High School", "40.58628788034916", "-73.82367912771649"),
    ("P.S. 204 Morris Heights", "40.8502301510138", "-73.91513130328504"),
    ("Leaders of Excellence, Advocacy and Discovery", "40.82312645405477", "-73.92272148749917"),
    ("P.S. X643", "40.81735842239108", "-73.91170701001546"),
    ("Collegiate Academy for Mathematics and Personal Awareness Charter School", "40.65865283161577", "-73.88867595170069"),
    ("P.S. 958", "40.653297074920076", "-74.00208730745949"),
    ("Nayema Universal Child Center", "40.63434380970191", "-73.96646973168764"),
    ("P.S. 048 P.O. Michael J. Buczek", "40.85341823492196", "-73.9336440272124")
]

for school, latitude, longitude in updates:
    sql = "UPDATE DOE_schools_data_2894 SET Latitude = %s, Longitude = %s WHERE `School Name` = %s"
    cursor.execute(sql, (latitude, longitude, school))

# Append these 2 schools into the table, they got skipped because of same name for different branch
#   1. All My Children Day Care And Nursery School - MBZW 40.659935747380494, -73.93083608794977
#   2. All My Children Day Care And Nursery School - MBXN 40.71897858426893, -73.98310226160082
query1 = """
INSERT INTO DOE_schools_data_2894 (`School Name`, Latitude, Longitude, Grade, District, Borough, `School Website`, Domain_1, Domain_2, Domain_3, Domain_4) 
VALUES ('All My Children Day Care And Nursery School - KDVD', '40.659935747380494', '-73.93083608794977', 'PK,3K', '18', 'Brooklyn', 
    'https://allmychildrendaycare.com/', 'allmychildrendaycare.org', 'allmychildrendaycare.com', 'allmychildrendaycare.edu', 'allmychildrendaycare.net')
"""
query2 = """
INSERT INTO DOE_schools_data_2894 (`School Name`, Latitude, Longitude, Grade, District, Borough, `School Website`, Domain_1, Domain_2, Domain_3, Domain_4) 
VALUES ('All My Children Day Care And Nursery School - MBXN', '40.71897858426893', '-73.98310226160082', 'PK,3K,EL', '1', 'Manhattan', 
    'https://allmychildrendaycare.com/', 'allmychildrendaycare.org', 'allmychildrendaycare.com', 'allmychildrendaycare.edu', 'allmychildrendaycare.net')
"""
cursor.execute(query1)
cursor.execute(query2)

connection.commit()
print("Completed.")
cursor.close()
connection.close()