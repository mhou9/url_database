import pandas as pd
import getpass
import mysql.connector
import sqlalchemy

# Put all 4 types of domains into one column and insert some doe domains
def get_all_domains(df):
    df['Domain_1'] = df['Domain_1'].str.strip()
    df['Domain_2'] = df['Domain_2'].str.strip()
    df['Domain_3'] = df['Domain_3'].str.strip()
    df['Domain_4'] = df['Domain_4'].str.strip()

    all_domains = pd.concat([df['Domain_1'], df['Domain_2'], df['Domain_3'], df['Domain_4']])
    all_domains = all_domains.dropna().unique()
    domains_df = pd.DataFrame(all_domains, columns=['New_Invalid_Domains'])

    new_domains = ['schoolsnyc.gov', 'schoolsnyc.doe.org', 'schools.nyc.org', 'schools.nyc.gov.org', 'schools.nyc.gov', 
                'schools.nyc.edu', 'schools.nyc.com', 'schools.nyc', 'schools.ny.gov','schools.net.gov', 'schools.gov.nyc', 
                'schools.gov.net', 'schools.gov', 'schools.edu.nyc.gov', 'school.nyc.gov', 'schoois.nyc.gov', 
                'nycschools.gov', 'nycschools.edu', 'nyce.boe.net', 'nycdoe.org', 'nycdoe.net', 'nycdoe.gov', 'nycdoe.edu', 
                'nycdoe.com', 'nycbor.net', 'nycboe.org', 'nycboe.net', 'nycboe.gov', 'nycboe.edu', 'nycboe.com', 
                'nycbod.net', 'nyc.schools.org', 'nyc.schools.net', 'nyc.schools.gov', 'nyc.gov', 'nyc.doe.gov', 
                'nyc.boe.net', 'nyc.boe', 'nncdoe.gov', 'doe.org', 'doe.com']
    new_domains_df = pd.DataFrame(new_domains, columns=['New_Invalid_Domains'])

    updated_domains_df = pd.concat([domains_df, new_domains_df], ignore_index=True)
    return updated_domains_df

# Clean up all domains that have emails 
def clean_domain(domain):
    if '@' in domain:
        return domain.split('@')[-1]
    return domain

# 1. A list of matched domains and its count
def task1_get_matched(d1, d2):
    d1 = [domain.lower() for domain in d1]
    matching_domain_list = list(set(domain for domain in d1 if domain in d2))
    return matching_domain_list

#   2. A list of unmatched domains of the orgin csv file and its count
def task2_get_unmatched1(common, d1):
    d1 = [domain.lower() for domain in d1]
    rest_domains = list(set(d1) - set(common))
    return rest_domains

#   3. In sql and csv, a list of unmatched domains of the new generated csv file and its count
def task3_get_unmatched2(common, d2):
    rest_domains = list(set(d2) - set(common))
    return rest_domains

#   4. In sql and csv, a total number of unique domains from both orgin and generated csv files
def task4_combine_all_domains(d1, d2, d3):
    combine = d1 + d2 + d3
    return combine

# Write a sql file with all commands that generate a table with all the data in MySQL database
def perform_batch_insertion(sql_file, table, column, domain_list):
    with open(sql_file, 'w') as file:
        sql = f"DROP TABLE IF EXISTS `{table}`;\n"
        sql += f"""
        CREATE TABLE {table} (
        id INT AUTO_INCREMENT PRIMARY KEY, 
        `{column}` VARCHAR(255)
        );\n\n
        """
        sql += f"INSERT INTO `{table}` (`{column}`) VALUES\n"
        sql += ",\n".join([f"('{domain}')" for domain in domain_list])
        sql += ";\n"
        file.write(sql)

def main():
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
    query = f"""SELECT Domain_1, Domain_2, Domain_3, Domain_4 FROM {tablename}"""
    df = pd.read_sql(query, engine)
    connection.close()
    
    # Store all new domains into csv file
    all_domains = get_all_domains(df)
    output_csv_path = 'all_domains.csv'
    all_domains.to_csv(output_csv_path, index=False)
    print(f"\nAll New Domains successfully written to {output_csv_path}")

    # compare the two csv file to get the following informations:
    #   1. A list of matched unique domains and its count
    #   2. A list of unmatched domains of the orgin csv file and its count
    #   3. In sql and csv, a list of unmatched domains of the new generated csv file and its count
    #   4. In sql and csv, a total number of unique domains from both orgin and generated csv files
    orgin_domain_file = input("Please input the file path that you want to compare the new result with : ")
    df_orgin = pd.read_csv(orgin_domain_file)
    df_new = pd.read_csv('all_domains.csv')
    df_orgin['Cleaned_Domain'] = df_orgin['Domain'].apply(clean_domain)
    domains1 = df_orgin['Cleaned_Domain'].tolist() 
    domains2 = df_new['New_Invalid_Domains'].tolist()

    # Get matching domains
    common_domains = task1_get_matched(domains1, domains2)
    print(f"\nAfter comparing with the existing forbidden domains file, there are {len(common_domains)} domains appear in the new forbidden domains list: {common_domains}")
    
    # Get unmatching domains from the old list
    rest_origin_domains = task2_get_unmatched1(common_domains, domains1)
    print(f"\nThere are {len(rest_origin_domains)} domains that are not found in the new forbidden domains list: {rest_origin_domains}")
    
    # Get unmatching domain from the new list
    output_csv = 'new_found_domains.csv'
    output_sql = 'new_found_domains.sql'
    table_name = "New_Found_Domains"
    column_name = "Forbidden Domains"
    new_found = task3_get_unmatched2(common_domains, domains2)
    new_found_df = pd.DataFrame(new_found, columns=[column_name])
    new_found_df.to_csv(output_csv, index=False)
    
    perform_batch_insertion(output_sql, table_name, column_name, new_found)
    print(f"\nThere are {len(new_found)} new forbidden domains found. They are successfully written to {output_csv} as .csv file and to {output_sql} as .sql file.")

    # Get all the unique domains from both list
    output_sql = 'combined_domains.sql'
    output_csv = 'combined_domains.csv'
    table_name = "All_Forbidden_Domains"
    combined_domains = task4_combine_all_domains(common_domains, rest_origin_domains, new_found)
    combined_domains_df = pd.DataFrame(combined_domains, columns=[column_name])
    combined_domains_df.to_csv(output_csv, index=False)
    
    perform_batch_insertion(output_sql,table_name,column_name, combined_domains)
    print(f"\nIn combine of known domains and new found domains, there are {len(combined_domains)} forbidden domains. They are successfully written to {output_csv} as .csv file and to {output_sql} as .sql file.")

main()