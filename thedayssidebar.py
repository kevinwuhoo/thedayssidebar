import os
import urlparse
import redis
import json
from flask import Flask, jsonify, g
from bs4 import BeautifulSoup
import requests
import arrow
import sys

app = Flask(__name__)


@app.route('/')
def index():
    while True:
        palette_key = g.db.randomkey()
        if palette_key != 'sidebar':
            break

    return jsonify({
        'palette': json.loads(g.db.get(palette_key)),
        'sidebar': json.loads(g.db.get('sidebar'))
    })


@app.route('/sidebar/scrape')
def scrape_sidebar():
    r = requests.get('http://feeds.sidebar.io/SidebarFeed?format=xml')
    soup = BeautifulSoup(r.content, "xml")

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

    g.db.delete('sidebar')
    g.db.set('sidebar', json.dumps(recent_5_items))
    return jsonify({"items": recent_5_items})


@app.before_request
def before_request():
    url = urlparse.urlparse(os.environ.get('REDISCLOUD_URL'))
    r = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
    g.db = r


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'scrape':
        print requests.get('http://thedayssidebar.herokuapp.com/sidebar/scrape').json()
    else:
        app.run(debug=True)
