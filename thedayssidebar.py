import os
from urllib.parse import urlparse
import redis
import json
from flask import Flask, jsonify, g
from bs4 import BeautifulSoup
import requests
import arrow
import sys
import random
import string
from selenium import webdriver
from PIL import Image
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)

if 'DYNO' in os.environ:
    is_development = False
else:
    is_development = True


@app.route('/')
def index():
    while True:
        palette_key = g.db.randomkey()
        if not ('sidebar' == palette_key or
                'cloudinary_last_tag' == palette_key):
            break

    return jsonify({
        'palette': json.loads(g.db.get(palette_key)),
        'sidebar': json.loads(g.db.get('sidebar'))
    })


def scrape_sidebar():
    r = connect_redis()

    req = requests.get('http://feeds.sidebar.io/SidebarFeed?format=xml')
    soup = BeautifulSoup(req.content, "xml")

    # go through xml feed and get title, link, and parse date with arrow
    items = []
    for item in soup.find_all('item'):
        title = item.find('title').get_text()

        # this link has an extra sidebar redirect
        # defer following redirect so that only 5 reqs have to be made
        link = item.find('link').get_text()

        date = item.find('pubDate').get_text().split()[1:5]
        date = " ".join(date)
        date = arrow.get(date, 'DD MMM YYYY HH:mm:ss')
        items.append({'title': title, 'link': link, 'date': date})

    # ensure sorted by chonological, remove date, follow redirect
    items = sorted(items, key=lambda x: x['date'], reverse=True)
    recent_5_items = []
    for item in items[:5]:
        link = requests.get(item['link'], verify=False).url
        recent_5_items.append({
            'title': item['title'],
            'url': link
        })

    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 450
    CLOUDINARY_TAG = ''.join(random.choice(string.ascii_uppercase) for i in range(4))
    for i, item in enumerate(recent_5_items):

        screenshot = 'sidebar-img-%d.png' % (i)
        retry = 0
        while True:
            try:
                # screenshot the site with phantomjs
                if is_development:
                    driver = webdriver.PhantomJS()
                else:
                    phantomjs_path = 'vendor/phantomjs/bin/phantomjs'
                    driver = webdriver.PhantomJS(phantomjs_path)

                driver.set_page_load_timeout(30)
                driver.set_window_size(1440, 450)
                driver.get(item['url'])
                driver.save_screenshot(screenshot)
                driver.quit()

                # use PIL to crop and optimize png for size
                im = Image.open(screenshot)
                im = im.crop((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
                im.save(screenshot, optimize=True)

                # upload image to cloudinary and add to list
                image_upload = cloudinary.uploader.upload(screenshot, tags=CLOUDINARY_TAG)
                recent_5_items[i]['image_url'] = image_upload['secure_url']
                break

            except Exception as e:
                # allow for 3 retries
                if retry < 3:
                    retry += 1
                else:
                    r.delete(screenshot)
                    print("failed on %s due to exception %s" % (item, e))
                    break

    if r.get('cloudinary_last_tag'):
        cloudinary.api.delete_resources_by_tag(r.get('cloudinary_last_tag'))

    r.set('sidebar', json.dumps(recent_5_items))
    r.set('cloudinary_last_tag', CLOUDINARY_TAG)

    return recent_5_items


@app.route('/test/images')
def test_images():
    img = "<img src='%s'>"
    page = "<html><body>"
    for post in json.loads(g.db.get('sidebar')):
        print(post)
        page += img % (post['image_url'])
        page += "<br><hr><br>"
    page += "</body></html>"
    return page


@app.before_request
def before_request():
    g.db = connect_redis()


def connect_redis():
    url = urlparse(os.environ.get('REDISCLOUD_URL'))
    r = redis.StrictRedis(
            host=url.hostname,
            port=url.port,
            password=url.password,
            charset='utf-8',
            decode_responses=True
        )
    return r


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'scrape':
        print(scrape_sidebar())
    else:
        app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
