import os
from urllib.parse import urlparse
import redis
import json
from flask import Flask, jsonify, g
from bs4 import BeautifulSoup
import requests
import arrow
import sys
from selenium import webdriver
import base64
from PIL import Image

app = Flask(__name__)

if 'DYNO' in os.environ:
    is_development = False
else:
    is_development = True


@app.route('/')
def index():
    while True:
        palette_key = g.db.randomkey().decode('utf-8')
        if not 'sidebar' in palette_key:
            break

    return jsonify({
        'palette': json.loads(g.db.get(palette_key).decode('utf-8')),
        'sidebar': json.loads(g.db.get('sidebar').decode('utf-8'))
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
            'link': link
        })

    r.delete('sidebar')
    r.set('sidebar', json.dumps(recent_5_items))

    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 450
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
                driver.get(item['link'])
                driver.save_screenshot(screenshot)
                driver.quit()

                # use PIL to crop and optimize png for size
                im = Image.open(screenshot)
                im = im.crop((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
                im.save(screenshot, optimize=True)

                # encode as base64 and save to db
                encoded_img = base64.b64encode(open(screenshot, 'rb').read())
                r.set(screenshot.split('.')[0], encoded_img)
                break

            except Exception as e:
                # allow for 3 retries
                if retry < 3:
                    retry += 1
                else:
                    r.delete(screenshot)
                    print("failed on %s due to exception %s" % (item, e))
                    break

    return recent_5_items


@app.route('/sidebar/image/<img_num>')
def sidebar_img(img_num):
    return g.db.get('sidebar-img-%s' % (img_num))


@app.route('/test/images')
def test_images():
    img = "<img src='data:image/png;base64,%s'>"
    page = "<html><body>"
    for i in range(5):
        encoded_img = g.db.get('sidebar-img-%d' % (i))
        page += img % (encoded_img)
        page += "<br><hr><br>"
    page += "</body></html>"
    return page


@app.before_request
def before_request():
    g.db = connect_redis()


def connect_redis():
    url = urlparse(os.environ.get('REDISCLOUD_URL'))
    r = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
    return r


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'scrape':
        print(scrape_sidebar())
    else:
        app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
