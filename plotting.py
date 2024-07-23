import mysql.connector
import pandas as pd
import folium
import getpass

password = getpass.getpass("Input your password for mysql: ")
database = input("What is your database name? Please enter: ")

# Retrieve the coordinates and school names
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd=password,
    database=database
)

query = "SELECT `School Name`, Latitude, Longitude FROM new_output_2894"
df = pd.read_sql(query, connection)
connection.close()

# Filter out schools that have no coordinates which would be (0,0)
df = df[(df['Latitude'] != 0) & (df['Longitude'] != 0)]

num_coordinates = len(df)
print(f"Number of coordinates to be plotted: {num_coordinates}")

# Create a map centered around the mean location
initial_location = [df['Latitude'].mean(), df['Longitude'].mean()]
map = folium.Map(location=initial_location, zoom_start=12)

# Add markers to the map with school names as labels
for idx, row in df.iterrows():
    folium.Marker(
        [row['Latitude'], row['Longitude']],
        popup=row['School Name']
    ).add_to(map)

map.save('map.html')

print("Map has been created and saved as 'map.html'")