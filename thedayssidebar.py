import os
import urlparse
import redis
import json
from flask import Flask, jsonify, g
from bs4 import BeautifulSoup
import requests
import collections
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

    # sometimes there aren't 5 items, group by date first
    items_by_date = collections.defaultdict(list)
    for item in soup.find_all('item'):
        title = item.find('title').get_text()

        link = item.find('link').get_text()
        link = requests.get(link).url

        date = item.find('pubDate').get_text().split()[1:4]
        date = " ".join(date)
        date = arrow.get(date, 'DD MMM YYYY')
        date = "%s-%s-%s" % (date.year, date.month, date.day)

        items_by_date[date].append({
            'title': title,
            'link': link,
        })

    sorted_dates = sorted(items_by_date.keys(), reverse=True)

    # find the first one with 5 links
    for i in range(len(items_by_date)):
        items = items_by_date[sorted_dates[i]]
        if len(items) == 5:
            g.db.delete('sidebar')
            g.db.set('sidebar', json.dumps(items))
            return jsonify({sorted_dates[i]: items})


@app.before_request
def before_request():
    url = urlparse.urlparse(os.environ.get('REDISCLOUD_URL'))
    r = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
    g.db = r


if __name__ == '__main__':
    if sys.argv[1] == 'scrape':
        print requests.get('http://thedayscolor.herokuapp.com/sidebar/scrape').json()
    else:
        app.run(debug=True)
