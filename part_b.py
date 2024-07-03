import json
import getpass

#use the json file and run the script to make sure it is running to create a table and input the data into mysql
import mysql.connector

# Load JSON data into Python dictionary
with open('output.json') as json_file:
    school_dict = json.load(json_file)

password = getpass.getpass("Input your password for mysql: ")
database = input("What is your database name? Please enter: ")

# Connect to MySQL database
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd= password,
    database= database
)

# Create cursor object
mycursor = mydb.cursor()

#create the table using python
mycursor.execute(
   "CREATE TABLE DOE_Schools_database (School_Name VARCHAR(255), Latitude VARCHAR(255), Longitude VARCHAR(255), Grade VARCHAR(255), District VARCHAR(255), Borough VARCHAR(255), School_Website VARCHAR(255), Domain_1 VARCHAR(255), Domain_2 VARCHAR(255), Domain_3 VARCHAR(255), Domain_4 VARCHAR(255))")

# Insert data into database
for school, inner in school_dict.items():
    #get all the data in the inner dictionary by their key
    Latitude = inner.get('Latitude', '')
    Longitude = inner.get('Longitude', '')
    Grade = inner.get('Grade', '')
    District = inner.get('District', '')
    Borough = inner.get('Borough', '')
    School_Website = inner.get('School Website', '')
    Domain1 = inner.get('Domain_1', '')
    Domain2 = inner.get('Domain_2', '')
    Domain3 = inner.get('Domain_3', '')
    Domain4 = inner.get('Domain_4', '')

    sql = "INSERT INTO DOE_Schools_database (School_Name, Latitude, Longitude, Grade, District, Borough, School_Website, Domain_1, Domain_2, Domain_3, Domain_4) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    val = (school, Latitude, Longitude, Grade, District, Borough, School_Website, Domain1, Domain2, Domain3, Domain4)
    mycursor.execute(sql, val)

# Commit changes to database
mydb.commit()

mycursor.execute("SELECT * FROM information_schema.tables WHERE table_name = 'DOE_Schools_database'")
result = mycursor.fetchone()
    
if result:
  print("Table created successfully!")
else:
  print("Table creation failed.")

# Close connection to database
mydb.close()