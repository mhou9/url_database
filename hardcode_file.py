# hard code into MySQL
import mysql.connector
import getpass

password = getpass.getpass("Input your password for mysql: ")
database = input("What is your database name? Please enter: ")

# retrieve the coordinates
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd= password,
    database= database
)

cursor = connection.cursor()

# Update domain
# American Dream Charter School II
# Imagine Early Learning Center @ City College - MBVK
update_domain1 = """
UPDATE new_output_2891 
SET 
    `School Website` = 'https://www.adcs2.org/',
    Domain_1 = 'adcs2.org',
    Domain_2 = 'adcs2.com',
    Domain_3 = 'adcs2.edu',
    Domain_4 = 'adcs2.net'
WHERE `School Name` = 'American Dream Charter School II'
"""
update_domain2 = """
UPDATE new_output_2891 
SET 
    `School Website` = 'https://imagineelc.com/schools/city-college-child-development-center/',
    Domain_1 = 'imagineelc.org',
    Domain_2 = 'imagineelc.com',
    Domain_3 = 'imagineelc.edu',
    Domain_4 = 'imagineelc.net'
WHERE `School Name` = 'Imagine Early Learning Center @ City College - MBVK'
"""
# Execute the queries
cursor.execute(update_domain1)
cursor.execute(update_domain2)

# Update the school name, coordinates and domain
# All My Children Day Care And Nursery School (All My Children Day Care And Nursery School - KDVD)
# Imagine Early Learning Center (Imagine Early Learning Centers @ Jamaica Kids)
update_name1 = """
UPDATE new_output_2891 
SET 
    `School Name` = 'All My Children Day Care And Nursery School - MBZW'
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
UPDATE new_output_2891 
SET 
    `School Name` = 'Imagine Early Learning Centers @ Jamaica Kids'
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

# Update the coordinates and domain
updates = [
    ("Metropolitan High School", "40.8278547454867", "-73.89699654561372"),
    ("Happy Scholars, Inc", "40.61349543855342", "-74.00095981607727"),
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
    ("P.S. 277", "40.81360947234675", "-73.9135955553995")
]

# Loop through the updates and execute the queries
for school, latitude, longitude in updates:
    sql = "UPDATE new_output_2891 SET latitude = %s, longitude = %s WHERE name = %s"
    cursor.execute(sql, (latitude, longitude, school))

# Insert two schools
# All My Children Day Care And Nursery School - MBZW 40.659935747380494, -73.93083608794977
# All My Children Day Care And Nursery School - MBXN 40.71897858426893, -73.98310226160082
query1 = """
INSERT INTO schools (`School Name`, Latitude, Longitude, Grade, District, Borough, `School Website`, Domain_1, Domain_2, Domain_3, Domain_4) 
VALUES ('All My Children Day Care And Nursery School - KDVD', '40.659935747380494', '-73.93083608794977', 'PK,3K', '18', 'Brooklyn', 
    'https://allmychildrendaycare.com/', 'allmychildrendaycare.org', 'allmychildrendaycare.com', 'allmychildrendaycare.edu', 'allmychildrendaycare.net')
"""
query2 = """
INSERT INTO schools (`School Name`, Latitude, Longitude, Grade, District, Borough, `School Website`, Domain_1, Domain_2, Domain_3, Domain_4) 
VALUES ('All My Children Day Care And Nursery School - MBXN', '40.71897858426893', '-73.98310226160082', 'PK,3K,EL', '1', 'Manhattan', 
    'https://allmychildrendaycare.com/', 'allmychildrendaycare.org', 'allmychildrendaycare.com', 'allmychildrendaycare.edu', 'allmychildrendaycare.net')
"""
cursor.execute(query1)
cursor.execute(query2)


connection.commit()
cursor.close()
connection.close()