#!/home/slzatz/frontpages/bin/python

import schedule
import time
from frontpages import retrieve_images

schedule.every().day.at("10:00").do(retrieve_images, url='https://www.frontpages.com/newspaper-list')

while True:
    schedule.run_pending()
    time.sleep(60)

