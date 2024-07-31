import pandas as pd
import getpass
import mysql.connector
import sqlalchemy

password = getpass.getpass("Input your password for mysql: ")
database = input("What is your database name? Please enter: ")
engine = sqlalchemy.create_engine(f"mysql+pymysql://root:{password}@localhost/{database}")

# Connect to database to read all the domains
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd=password,
    database=database
)
tablename = "doe_schools_data_2894"
query = f"""SELECT `School Name`, Domain_1, Domain_2, Domain_3, Domain_4 FROM {tablename}"""
df = pd.read_sql(query, engine)
connection.close()

df['School Name'] = df['School Name'].str.strip()
df['Domain_1'] = df['Domain_1'].str.strip()
df['Domain_2'] = df['Domain_2'].str.strip()
df['Domain_3'] = df['Domain_3'].str.strip()
df['Domain_4'] = df['Domain_4'].str.strip()

new_df = pd.DataFrame({
    'School Name': pd.Series(df['School Name'].dropna().unique()),
    'Domain': pd.Series(df['Domain_1'].dropna().unique()).str.replace(r'\.org$', '', regex=True),
    'Domain_1': pd.Series(df['Domain_1'].dropna().unique()),
    'Domain_2': pd.Series(df['Domain_2'].dropna().unique()),
    'Domain_3': pd.Series(df['Domain_3'].dropna().unique()),
    'Domain_4': pd.Series(df['Domain_4'].dropna().unique())
})

# Store all new domains into csv file
new_df.to_csv('unique_domains.csv', index=False)