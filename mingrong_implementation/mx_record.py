# import dns.resolver
# import pandas as pd
# import time
# import sys
# import getpass
# import mysql.connector
# import sqlalchemy
# import socket
# import asyncio
# import aiohttp

# # def is_valid_mail_server(mx_record):
# #     try:
# #         # Attempt to connect to the mail server on port 25 (SMTP)
# #         mail_server = mx_record.rstrip('.')
# #         print(f"Trying to connect to {mail_server} on port 25...")
# #         with socket.create_connection((mail_server, 25), timeout=10) as conn:
# #             banner = conn.recv(1024).decode()
# #             print(f"Received banner: {banner}")
# #             if "220" in banner:
# #                 return True
# #     except Exception as e:
# #         print(f"Failed to connect to {mail_server}: {e}")
# #     return False

# async def is_valid_mail_server(mail_server):
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(f'http://{mail_server}:25') as response:
#                 if response.status == 220:
#                     return True
#     except Exception:
#         return False

# pd.__version__
# dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
# dns.resolver.default_resolver.nameservers = ['8.8.8.8']


# password = getpass.getpass("Input your password for mysql: ")
# database = input("What is your database name? Please enter: ")
# engine = sqlalchemy.create_engine(f"mysql+pymysql://root:{password}@localhost/{database}")

# # Connect to database to read all the domains
# connection = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     passwd=password,
#     database=database
# )
# tablename = "DOE_schools_data_2894"
# query = f"""SELECT `School Website`, Domain_1, Domain_2, Domain_3, Domain_4 FROM {tablename}"""
# df = pd.read_sql(query, engine)
# connection.close()

# df['Domain_1'] = df['Domain_1'].str.strip()
# df['Domain_2'] = df['Domain_2'].str.strip()
# df['Domain_3'] = df['Domain_3'].str.strip()
# df['Domain_4'] = df['Domain_4'].str.strip()

# all_domains = pd.concat([df['Domain_1'], df['Domain_2'], df['Domain_3'], df['Domain_4']])
# all_domains = all_domains.dropna().unique()

# domain_1 = pd.Series(df['Domain_1'].dropna().unique())
# domain_2 = pd.Series(df['Domain_2'].dropna().unique())
# domain_3 = pd.Series(df['Domain_3'].dropna().unique())
# domain_4 = pd.Series(df['Domain_4'].dropna().unique())
    
# mxRecords = []
# emailAddresses = []
# is_Valid = []
# all_valid_domains = []

# for domain in all_domains:
#     try:
#         answers = dns.resolver.resolve(domain, 'MX')
#     except:
#         mxRecord = "0"
#     else:
#         mxRecord = answers[0].exchange.to_text()

#         if is_valid_mail_server(mxRecord):
#             all_valid_domains.append(domain)

# for d1, d2, d3, d4 in zip(domain_1, domain_2, domain_3, domain_4):
#     domains = [d1, d2, d3, d4]
#     validity_tuple = ()
#     mx_tuple = ()
#     for domain in domains:
#         try:
#             answers = dns.resolver.resolve(domain, 'MX')
#             mxRecord = answers[0].exchange.to_text()
#             mx_tuple = mx_tuple + (mxRecord,)
#             if is_valid_mail_server(mxRecord):
#                 validity_tuple = validity_tuple + (1,)
#             else:
#                 validity_tuple = validity_tuple + (0,)
#         except Exception as e:
#             print(f"Error resolving MX record for domain {domain}: {e}")
#             mx_tuple = mx_tuple + ("error",)
#             validity_tuple = validity_tuple + (0,)
#         finally:
#             mxRecords.append(mx_tuple)
#             is_Valid.append(validity_tuple)


# df = pd.DataFrame({
#     'School Website': pd.Series(df['School Website'].dropna().unique()),
#     'Domain': pd.Series(df['Domain_1'].dropna().unique()).str.replace(r'\.org$', '', regex=True),
#     'Domain_1': domain_1,
#     'Domain_2': domain_2,
#     'Domain_3': domain_3,
#     'Domain_4': domain_4,
#     "MXRecords": mxRecords,
#     "Valid MX Records": is_Valid
# })

# print ("\n", str(len(emailAddresses)), "records processed in total") 
# print(f"\n {len(all_valid_domains)} domains have Valid mx records found.")

# all_v = pd.DataFrame(all_valid_domains, columns=['Valid Domains'])
# all_v.to_csv("Verified_domains.csv", index=False)
# df.to_csv("mx_record.csv", index=True)

import dns.resolver
import pandas as pd
import time
import sys
import getpass
import mysql.connector
import sqlalchemy
import asyncio
import aiohttp

async def is_valid_mail_server(mail_server):
    try:
        reader, writer = await asyncio.open_connection(mail_server, 25)
        banner = await reader.read(1024)
        writer.close()
        await writer.wait_closed()
        if b'220' in banner:
            return True
    except Exception as e:
        print(f"Failed to connect to {mail_server}: {e}")
    return False

async def check_mx_records(domain):
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        mx_record = answers[0].exchange.to_text()
        valid = await is_valid_mail_server(mx_record)
        return domain, mx_record, valid
    except Exception as e:
        print(f"Error resolving MX record for domain {domain}: {e}")
        return domain, "error", False

df_result = pd.DataFrame()
count = 0
all_valid_domains = []

async def main():
    global df_result
    global count 
    global all_valid_domains

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

    domain_1 = pd.Series(df['Domain_1'])
    domain_2 = pd.Series(df['Domain_2'])
    domain_3 = pd.Series(df['Domain_3'])
    domain_4 = pd.Series(df['Domain_4'])

    mxRecords = []
    is_Valid = []
   

    # Task 1: Collect all domains with valid MX records
    tasks = [check_mx_records(domain) for domain in all_domains]
    results = await asyncio.gather(*tasks)

    for domain, mx_record, valid in results:
        if mx_record != "error" and valid:
            all_valid_domains.append(domain)

    # Task 2: Check domains row-wise and collect MX records and validity as tuples
    for d1, d2, d3, d4 in zip(domain_1, domain_2, domain_3, domain_4):
        if not any([d1, d2, d3, d4]):
            mxRecords.append(("error", "error", "error", "error"))
            is_Valid.append((0, 0, 0, 0))
            continue  # Skip the current iteration if all domains are empty

        domains = [d1, d2, d3, d4]
        validity_tuple = ()
        mx_tuple = ()
        tasks = [check_mx_records(domain) for domain in domains]
        results = await asyncio.gather(*tasks)

        for domain, mx_record, valid in results:
            count += 1
            mx_tuple = mx_tuple + (mx_record,)
            validity_tuple = validity_tuple + (1 if valid else 0,)

        mxRecords.append(mx_tuple)
        is_Valid.append(validity_tuple)

    df_result = pd.DataFrame({
        'School Website': pd.Series(df['School Website']),
        'Domain': pd.Series(df['Domain_1']).str.replace(r'\.org$', '', regex=True),
        'Domain_1': domain_1,
        'Domain_2': domain_2,
        'Domain_3': domain_3,
        'Domain_4': domain_4,
        "MXRecords": mxRecords,
        "Valid MX Records": is_Valid
    })


if __name__ == "__main__":
    asyncio.run(main())
    print(f"\n{count} records processed in total")
    print(f"\n {len(all_valid_domains)} domains have valid MX records found.")

    all_v = pd.DataFrame(all_valid_domains, columns=['Valid Domains'])
    all_v.to_csv("Verified_domains.csv", index=False)
    
    df_result_cleaned = df_result.dropna(subset=['School Website'])
    df_result_cleaned.to_csv("mx_record.csv", index=True)