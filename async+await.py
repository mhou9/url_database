# import asyncio
# import time
# from aiohttp import ClientSession, ClientResponseError

# async def fetch_url_data(session, url):
#     try:
#         async with session.get(url, timeout=60) as response:
#             resp = await response.read()
#     except Exception as e:
#         print(e)
#     else:
#         return resp
#     return

# async def fetch_page(session, url):
#     async with session.get(url) as response:
#         return await response.json()

# async def main():
#     async with ClientSession() as session:
#         tasks = [asyncio.ensure_future(fetch_page(session, url)) for url in urls]
#         responses = await asyncio.gather(*tasks)
#         for response in responses:
#             print(response['fact'])

# if __name__ == '__main__':
#     start_time = time.perf_counter()
#     urls = [f'https://catfact.ninja/fact' for _ in range(100)]
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(main())
#     end_time = time.perf_counter()
#     print(f'Total Time with async: {round(end_time - start_time, 5)} seconds.')

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse

async def fetch_school(session, url):
    async with session.get(url, verify_ssl=False) as response:
        html_content = await response.text()
        soup = BeautifulSoup(html_content, 'html.parser')
        school_url_elements = soup.find('a', string='School Website')

        if school_url_elements:
            url = school_url_elements.get('href')
            domain = urlparse(url).netloc.replace('www.', '').split('.')

            if "google" in domain:
                return {
                    "School Website": '',
                    "Domain_1": '',
                    "Domain_2": '',
                    "Domain_3": '',
                    "Domain_4": ''
                }
            else:
                return {
                    "School Website": url,
                    "Domain_1": f"{domain[0]}.org",
                    "Domain_2": f"{domain[0]}.com",
                    "Domain_3": f"{domain[0]}.edu",
                    "Domain_4": f"{domain[0]}.net"
                }
        else:
            return {
                "School Website": '',
                "Domain_1": '',
                "Domain_2": '',
                "Domain_3": '',
                "Domain_4": ''
            }

async def main():
    urls = [
        "http://www.schools.nyc.gov/schools/K001",
        "http://www.schools.nyc.gov/schools/K002",
        "http://www.schools.nyc.gov/schools/K003",
        # Add more URLs as needed
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_school(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

        # Process results here
        for result in results:
            print(result)

if __name__ == '__main__':
    asyncio.run(main())
