import pandas as pd
import json

# Read the JSON file
with open('new_output_3001.json', 'r') as file:
    data = json.load(file)

# Convert the dictionaries to a DataFrame
df = pd.DataFrame.from_dict(data, orient='index')

# Reset the index to make the school names a column
df.reset_index(inplace=True)

# Rename the index column to 'School Name'
df.rename(columns={'index': 'School Name'}, inplace=True)

# Save the DataFrame to a CSV file
df.to_csv('new_output_3001.csv', index=False)

print("JSON data has been successfully converted to CSV and saved as 'schools.csv'")
