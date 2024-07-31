INSERT INTO schools( url, name, personal_website, domain_name, district, grades, borough, formatted_address, latitude, longitude)
VALUES
(NULL, 'American Dream Charter School II','https://www.adcs2.org/', 'adcs2', '7', '06,07,08,09,10,11,12', 'Bronx', '510 E 141st St, Bronx, NY 10454', NULL, NULL),
(NULL, 'Imagine Early Learning Center @ City College', 'https://imagineelc.com/schools/city-college-child-development-center/', 'imagineelc', '', 'PK', 'Manhattan', '119 Convent Ave, New York, NY 10031', NULL, NULL);

UPDATE schools
SET formatted_address = '133 Kingsborough 1st Walk, Brooklyn, NY 11233'
WHERE url IN ('https://www.schools.nyc.gov/schools/KBUF', 'https://www.schools.nyc.gov/schools/KBTA');

UPDATE schools
SET formatted_address = '561 Utica Ave, Brooklyn, NY 11203'
WHERE url = 'https://www.schools.nyc.gov/schools/KDVD';

UPDATE schools
SET formatted_address = '1962 Linden Blvd, Brooklyn, NY 11207'
WHERE url = 'https://www.schools.nyc.gov/schools/K807';

-- Disable safe update mode
SET SQL_SAFE_UPDATES = 0;

-- Update latitude and longitude based on formatted_address
UPDATE schools
SET latitude = 40.70114391299868, longitude = -74.01186340459385
WHERE formatted_address = '10 South Street, Slip 7, Manhattan, NY, 10004';

UPDATE schools
SET latitude = 40.82340686718089, longitude = -73.89869727191869
WHERE formatted_address = '1010 REV. J. A. POLITE AVENUE, BRONX, NY, 10459';

UPDATE schools
SET latitude = 40.82052491636817, longitude = -73.89862701448244
WHERE formatted_address = '888 Rev J A Polite Ave, Bronx, NY, 10459';

UPDATE schools
SET latitude = 40.852933023259034, longitude = -73.9210106451699
WHERE formatted_address = '275 HARLEM RIVER PARK BRIDGE, Bronx, NY, 10453';

UPDATE schools
SET latitude = 40.850205804309994, longitude = -73.91516348935058
WHERE formatted_address = '1780 Dr. Martin Luther King Jr. Blvd, Bronx, NY, 10453';

UPDATE schools
SET latitude = 40.703136672958244, longitude = -73.80055241819312
WHERE formatted_address = '1 Jamaica Center Plaza, Queens, NY, 11432';

UPDATE schools
SET latitude = 40.81836436613102, longitude = -73.911376495595
WHERE formatted_address = '701 ST. ANNS AVENUE, Bronx, NY, 10455';

UPDATE schools
SET latitude = 40.87719270379308, longitude = -73.91254703182034
WHERE formatted_address = '99 TERRACE VIEW AVENUE, Bronx, NY, 10463';

UPDATE schools
SET latitude = 40.8363972491382, longitude = -73.90495029250535
WHERE formatted_address = '450 SAINT PAUL''S PLACE, Bronx, NY, 10456';

UPDATE schools
SET latitude = 40.817362482166653, longitude = -73.9117874760000
WHERE formatted_address = '639 St Anns Avenue, Bronx, NY, 10455';

UPDATE schools
SET latitude = 40.55214255795229, longitude = -74.19526131936398
WHERE formatted_address = '200 NEDRA LANE, Staten Island, NY, 10312';

UPDATE schools
SET latitude = 40.61131673441278, longitude = -74.08368354902152
WHERE formatted_address = '140 PALMA DRIVE, Staten Island, NY, 10304';

UPDATE schools
SET latitude = 40.82790345506797, longitude = -73.89706091832882
WHERE formatted_address = '1180 REV. J.A. POLITE AVE., Bronx, NY, 10459';

UPDATE schools
SET latitude = 40.813398351743835, longitude = -73.91389596250654
WHERE formatted_address = '519 ST ANNS AVENUE, Bronx, NY, 10455';

UPDATE schools
SET latitude = 40.85189797801912, longitude = -73.86454414716312
WHERE formatted_address = '2040 ANTIN PL, Bronx, NY, 10462';

UPDATE schools
SET latitude = 40.65352190262294, longitude = -74.00219700299436
WHERE formatted_address = '836-841 5th Avenue, Brooklyn, NY, 11232';

UPDATE schools
SET latitude = 40.63430310025094, longitude = -73.96653410484335
WHERE formatted_address = '1107-09 Newkirk Avenue, Brooklyn, NY, 11230';

UPDATE schools
SET latitude = 40.62642055783467, longitude = -73.99697000299565
WHERE formatted_address = '2157336 New Utrecht Avenue, Brooklyn, NY, 11214';

UPDATE schools
SET latitude = 40.576226102472035, longitude = -73.97153058950401
WHERE formatted_address = '271 Seabreeze Avenue, Brooklyn, NY, 11224';

UPDATE schools
SET latitude = 40.85875176924623, longitude = -73.92226989873231
WHERE formatted_address = '3703 TENTH AVENUE, Manhattan, NY, 10034';

UPDATE schools
SET latitude = 40.80591573256053, longitude = -73.93529094531698
WHERE formatted_address = '144-176 EAST 128 STREET, Manhattan, NY, 10035';

UPDATE schools
SET latitude = 40.7994259629683, longitude = -73.93389464531728
WHERE formatted_address = '2351 FIRST AVENUE, Manhattan, NY, 10035';

UPDATE schools
SET latitude = 40.853625170570766, longitude = -73.93358501832759
WHERE formatted_address = '4360-78 BROADWAY, Manhattan, NY, 10033';

UPDATE schools
SET latitude = 40.71531828396943, longitude = -73.97997045881455
WHERE formatted_address = '285 DELANCY STREET, Manhattan, NY, 10002';

UPDATE schools
SET latitude = 40.78930619325548, longitude = -73.9441845606595
WHERE formatted_address = '1991 SECOND AVENUE, Manhattan, NY, 10029';

UPDATE schools
SET latitude = 40.79036532866928, longitude = -73.94258466065948
WHERE formatted_address = '2050 Second Avenue, Manhattan, NY, 10029';

UPDATE schools
SET latitude = 40.80489986654313, longitude = -73.93559026065883
WHERE formatted_address = '2322 3rd Avenue,  Ground Floor, Manhattan, NY, 10035';

UPDATE schools
SET latitude = 40.721553615382746, longitude = -74.00562296066242
WHERE formatted_address = '21 Saint Johns Lane, Manhattan, NY, 10013';

UPDATE schools
SET latitude = 40.77022427659722, longitude = -73.95405154716663
WHERE formatted_address = '1456 First Ave, Manhattan, NY, 10021';

UPDATE schools
SET latitude = 40.58915062511852, longitude = -73.8061148913516
WHERE formatted_address = '2-45 BEACH  79 STREET, Queens, NY, 11693';

UPDATE schools
SET latitude = 40.60167859763924, longitude = -73.76401118950297
WHERE formatted_address = '8-21 BAY 25 STREET, Queens, NY, 11691';

UPDATE schools
SET latitude = 40.58673407814998, longitude = -73.82351020484542
WHERE formatted_address = '100-00 BEACH CHANNEL DRIVE, Queens, NY, 11694';

UPDATE schools
SET latitude = 40.59419878865413, longitude = -73.78668418950325
WHERE formatted_address = '3-65 BEACH 56 STREET, Queens, NY, 11692';

UPDATE schools
SET latitude = 40.73985354886928, longitude = -73.90407090299074
WHERE formatted_address = '60-10A 47 Avenue, Queens, NY, 11377';

UPDATE schools
SET latitude = 40.71349034741277, longitude = -73.81511204567315
WHERE formatted_address = '83-78 Daniel Street, Queens, NY, 11435';


-- Re-enable safe update mode
SET SQL_SAFE_UPDATES = 1;
