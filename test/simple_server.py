from flask import Flask, request
import logging
import json

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/tx', methods=['POST'])
def index():
    return "OK"


@app.route('/chunk', methods=['POST'])
def chunk():
    if request.method == "POST":
        logger.error(json.dumps(str(request.data)))
    return "OK"


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')