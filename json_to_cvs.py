import pandas as pd
import json

with open('new_output_3001.json', 'r') as file:
    data = json.load(file)

# Convert the dictionaries to a DataFrame
df = pd.DataFrame.from_dict(data, orient='index')

# Reset the index to make the school names a column and name as 'School Name'
df.reset_index(inplace=True)
df.rename(columns={'index': 'School Name'}, inplace=True)

# Save to a CSV file
df.to_csv('C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/new_output_3001.csv', index=False)

print("JSON data has been successfully converted to CSV and saved as 'schools.csv'")
