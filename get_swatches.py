from bs4 import BeautifulSoup
import re
import json
import redis
import os
import urlparse

url = urlparse.urlparse(os.environ.get('REDISCLOUD_URL'))
r = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
r.flushdb()

hex_color_regex = re.compile(r'(#\w+)')
get_hex_color = lambda s: hex_color_regex.search(s).group(1)

soup = BeautifulSoup(open('2014-08-15.html'))

swatches = []
for swatch in soup.find_all('div', {'class': 'swatch_content'}):
    month, day, year = [date.get_text() for date in swatch.find_all('date')]

    inspiration = swatch.find('div', {'class': 'swatch_info_right'}).find('span').get_text()

    bg_right = get_hex_color(swatch['style'])
    bg_left  = get_hex_color(swatch.find('div', {'class': 'swatch_content_left'})['style'])

    colors = [get_hex_color(color['style']) for color in
              swatch.find_all('div', {'class': 'swatch'})]

    swatch = {
        'date': {'year': year, 'month': month, 'day': day},
        'inspiration': inspiration,
        'bg_right': bg_right,
        'bg_left': bg_left,
        'colors': colors
    }

    r.set("%s-%s-%s" % (year, month, day), json.dumps(swatch))
