import dns.resolver
import pandas as pd
import time
import sys
import getpass
import mysql.connector
import sqlalchemy
import socket

def is_valid_mail_server(mx_record):
    try:
        # Attempt to connect to the mail server on port 25 (SMTP)
        mail_server = mx_record.rstrip('.')
        print(f"Trying to connect to {mail_server} on port 25...")
        with socket.create_connection((mail_server, 25), timeout=10) as conn:
            banner = conn.recv(1024).decode()
            print(f"Received banner: {banner}")
            if "220" in banner:
                return True
    except Exception as e:
        print(f"Failed to connect to {mail_server}: {e}")
    return False

pd.__version__
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']


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
tablename = "DOE_schools_data_2894"
query = f"""SELECT `School Website`, Domain_1, Domain_2, Domain_3, Domain_4 FROM {tablename}"""
df = pd.read_sql(query, engine)
connection.close()

df['Domain_1'] = df['Domain_1'].str.strip()
df['Domain_2'] = df['Domain_2'].str.strip()
df['Domain_3'] = df['Domain_3'].str.strip()
df['Domain_4'] = df['Domain_4'].str.strip()

all_domains = pd.concat([df['Domain_1'], df['Domain_2'], df['Domain_3'], df['Domain_4']])
all_domains = all_domains.dropna().unique()

new_df = pd.DataFrame({
    'School Name': pd.Series(df['School Name'].dropna().unique()),
    'Domain': pd.Series(df['Domain_1'].dropna().unique()).str.replace(r'\.org$', '', regex=True),
    'Domain_1': pd.Series(df['Domain_1'].dropna().unique()),
    'Domain_2': pd.Series(df['Domain_2'].dropna().unique()),
    'Domain_3': pd.Series(df['Domain_3'].dropna().unique()),
    'Domain_4': pd.Series(df['Domain_4'].dropna().unique())
})
    
mxRecords = []
emailAddresses = []
with_mx_record = []
count = 0
for domain in all_domains:
    # if count >= 100: break
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        with_mx_record.append(domain)
    except:
        print ("some error")
        mxRecord = "00000000000000000000"
    else:
        mxRecord = answers[0].exchange.to_text()
        mxRecords.append(mxRecord)
    finally:
        # mxRecords.append(mxRecord)
        emailAddresses.append(domain)
        print(domain)
        time.sleep(.200)
        count += 1

#a 200 ms pause is added for good measure
#the rest of the program uses pandas to export everything neatly to CSV. It takes to lists "mxRecords" and "emailAddresses" and converts it to a dataframe.

df = pd.DataFrame({"Valid Domains":with_mx_record,
                  "MXRecords":mxRecords})

print ("\n", str(len(emailAddresses)), "records processed in total") 
print(f"\n {len(with_mx_record)} domains have mx records found.")

df.to_csv("mx_record.csv", index=True)