"""Demo server for items API."""
import os
from flask import Flask, jsonify

app = Flask(__name__)

# Items list with cherry as new product
ITEMS = [
    {"id": 1, "name": "apple", "description": "Fresh red apple"},
    {"id": 2, "name": "banana", "description": "Sweet yellow banana"},
    {"id": 3, "name": "cherry", "description": "Sweet red cherry"}
]


@app.route('/api/items', methods=['GET'])
def get_items():
    """Return all items as JSON array."""
    return jsonify(ITEMS)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
