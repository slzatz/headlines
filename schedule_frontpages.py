#!/home/slzatz/frontpages/bin/python

import schedule
import time
from retieve_fp_urls import retrieve_urls

schedule.every().day.at("10:00").do(retrieve_urls, url='https://www.frontpages.com/newspaper-list')

while True:
    schedule.run_pending()
    time.sleep(60)

