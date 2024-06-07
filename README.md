# url_database
## Objective 

This project's objective is to collect and organize information about the public schools in New York City (NYC), particularly their website URLs, borough, and district information. This information will be used to create a database of NYC public schools and their websites. 

## Background 

When teachers register for the union, they are advised not to use their work email addresses due to privacy concerns. However, some teachers still use their work emails. Additionally, the public domains used by NYC public schools tend to change frequently and are often inconsistent. 

The NYC Department of Education maintains a comprehensive list of all public schools in the city, along with their contact information and websites. This information is available on the NYC Schools website (https://schoolsearch.schools.nyc/). 

## Project Overview 

To achieve our objective, we will follow these steps: 

1. Web Crawling: Utilize a Python web crawler to extract information about each individual school's website URL, borough, and district information from the NYC Schools website. The output will be in the form of a JSON file. 

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

  
## Usage 

1. Clone the repository containing the Python scripts for web crawling and database creation. 

2. Ensure that Python and MySQL are installed on your system. 

 

## Contributors 

Mingrong Hou

Regina Rabkina
 
