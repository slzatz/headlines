#!/home/slzatz/frontpages/.venv/bin/python

import requests
from bs4 import BeautifulSoup
import shutil
import os
import json
from newspaper_list import newspapers

#url = 'https://www.frontpages.com/newspaper-list'  

def retrieve_images(url):
    response = requests.get(url)
   
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error accessing the page: {response.status_code}")
        return []

    # Parse the content with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all image tags
    images = soup.find_all('img')

    # Filter for .webp images of front pages -- all those images have data-src
    all_images = [img['data-src'] for img in images if img.get('data-src')]
    #print(all_images[:5])
    
    d = {x[x.rfind("/")+1:x.rfind("-")]: x for x in all_images}
    dd = {k: v for k,v in d.items() if k in newspapers}
    select_images = list(dd.values())

    for index, value in enumerate(select_images):
        #select_images[index] = '/g'+value.removeprefix('/t') + '.jpg'
        select_images[index] = '/g'+value.removeprefix('/t')
    
    for key, value in dd.items():
        dd[key] = '/g'+value.removeprefix('/t')

    with open('frontpageurls.py', 'w') as file:
        text = "urls = " + repr(select_images)
        file.write(text)
# Serialization with json

    with open('frontpageurls.json', 'w') as file:
        json.dump(dd, file)

    #file_path = '/home/slzatz/frontpages/frontpageurls.py'

    ## Check if the file exists to avoid FileNotFoundError
    #if os.path.exists(file_path):
    #    os.remove(file_path)
    #    print(f"File {file_path} has been removed.")
    #else:
    #    print(f"File {file_path} does not exist.")

    #try:
    #    shutil.move('frontpageurls.py', '/home/slzatz/inkplate_server/')
    #    return f"fontpageurls.py has been successfully moved to inkplate_server"
    #except FileNotFoundError:
    #    return "File not found in the source directory."
    #except Exception as e:
    #    return f"An error occurred: {e}"

if __name__ == '__main__':
    retrieve_images('https://www.frontpages.com/newspaper-list')
