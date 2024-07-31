# url_database
## Objective 

This project's objective is to collect and organize information about the public schools in New York City (NYC), particularly their website URLs, borough, and district information. This information will be used to create a database of NYC public schools and their websites. 

## Background 

When teachers register for the union, they are advised not to use their work email addresses due to privacy concerns. However, some teachers still use their work emails. Additionally, the public domains used by NYC public schools tend to change frequently and are often inconsistent. 

The NYC Department of Education maintains a comprehensive list of all public schools in the city, along with their contact information and websites. This information is available on the NYC Schools website (https://schoolsearch.schools.nyc/). 

## Project Overview 

Project Source: Open Source website (https://schoolsearch.schools.nyc/)

To achieve our objective, we will follow these steps: 

1. Web Crawling: Utilize a Python web crawler to extract information about each individual school's website URL, name, domain, district information, grade levels, the borough it is located in, as well as the latitude ane longitude (to be plotted on a map) from the NYC Schools website. The output will be in the form of a JSON file. 

2. Database Creation: Create a MySQL database to store the collected information about NYC public schools. We will develop a Python script to read the JSON file generated from the web crawling process and populate the database with the relevant data. 

## Implementation 

### Web Crawling:
  - The Python web crawler will navigate through the NYC Schools website (https://schoolsearch.schools.nyc/) and extract information about each public school. 

  - Information to be extracted includes the school's website URL, borough, and district. 

  - The extracted data will be formatted as a JSON file for further processing. 

### Database Creation:

  - We will create a MySQL database schema to store the collected information. 

  - A Python script will be developed to read the JSON file generated from the web crawling process. 

  - The script will then establish a connection to the MySQL database and populate it with the extracted school data. 

  
## Usage Setup Commands

1. Clone this repo: git clone https://github.com/mhou9/url_database.git
2. cd url_database/mingrong_implementation
3. Open MySQL, connect to localhost by enter your mysql password and database name
4. In VSCode terminal, run the following code files in order: 
  - to get all the extracted school informations into a json file: python async+await.py
  - to convert JSON to CSV file then import into MySQL and include the manually hardcoded schools' coordinates: python hardcode_file.py
  - to plot all the schools into a map as a html file: python plotting.py
  - to compare the all generated domains with existing domain list in a file: python analyze_result.py
5. Run .sql file in MySQL to generate the data table

## Contributors 

Mingrong Hou

Regina Rabkina
