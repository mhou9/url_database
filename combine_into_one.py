import pandas as pd
import mysql.connector
import getpass

# Step 1: Read domains from the CSV file
file_path = 'C:\\Users\\mhou\\Downloads\\2024-07-17-invalid_domains.xlsx'
df_csv = pd.read_excel(file_path, sheet_name='Sheet1',header=0)
csv_domains = df_csv['Invalid Domain'].tolist()


password = getpass.getpass("Input your password for mysql: ")
database = input("What is your database name? Please enter: ")

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd=password,
    database=database
)

query = "SELECT description FROM forbidden_domain"
df_sql = pd.read_sql(query, connection)
connection.close()

sql_domains = df_sql['description'].tolist()

combined_domains = list(set(csv_domains + sql_domains))

combined_df = pd.DataFrame(combined_domains, columns=['Domain'])
output_csv_file_path = 'orgin_forbidden_domains.csv'
combined_df.to_csv(output_csv_file_path, index=False)

print("Combined domains have been written to the new CSV file.")
