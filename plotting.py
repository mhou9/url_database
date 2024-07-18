import mysql.connector
import pandas as pd
import folium
import getpass


password = getpass.getpass("Input your password for mysql: ")
database = input("What is your database name? Please enter: ")

# Step 1: Connect to the MySQL database and retrieve the coordinates
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd= password,
    database= database
)

query = "SELECT Latitude, Longitude FROM new_output_2891"
df = pd.read_sql(query, connection)
connection.close()

# # Step 2: Use Folium to plot the coordinates onto a map
# initial_location = [df['Latitude'].mean(), df['Longitude'].mean()]
# map = folium.Map(location=initial_location, zoom_start=12)
# count = 0
# for idx, row in df.iterrows():
#     folium.Marker([row['Latitude'], row['Longitude']]).add_to(map)
#     count += 1

# map.save('map.html')

# print("Map has been created and saved as 'map.html'")
# print(count)

# Filter out invalid coordinates (e.g., 0,0)
df = df[(df['Latitude'] != 0) & (df['Longitude'] != 0)]

# Count the number of valid coordinates
num_coordinates = len(df)
print(f"Number of valid coordinates to be plotted: {num_coordinates}")
count = 0
# Create a map centered around the mean location of valid coordinates
if num_coordinates > 0:
    initial_location = [df['Latitude'].mean(), df['Longitude'].mean()]
    map = folium.Map(location=initial_location, zoom_start=12)

    # Add markers to the map
    for idx, row in df.iterrows():
        folium.Marker([row['Latitude'], row['Longitude']]).add_to(map)
        count += 1

    # Save the map to an HTML file
    map.save('map.html')

    print("Map has been created and saved as 'map.html'")
    print(count)
else:
    print("No valid coordinates to plot.")
