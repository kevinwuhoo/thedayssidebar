import os
import urlparse
import redis
import json
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    url = urlparse.urlparse(os.environ.get('REDISCLOUD_URL'))
    r = redis.StrictRedis(host=url.hostname, port=url.port, password=url.password)
    return jsonify(json.loads(r.get(r.randomkey())))

if __name__ == '__main__':
    app.run(debug=True)
