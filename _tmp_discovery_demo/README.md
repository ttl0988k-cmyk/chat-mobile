# demo-server

A tiny product-list web server.

## Setup & Run

```bash
python server.py
```

The server starts on **port 9191** (hardcoded in `server.py`).

> **Note:** `config.yaml` declares port 8080, but the actual server uses **9191**. Always refer to `server.py` as the source of truth.

## API Endpoints

- **GET** `http://127.0.0.1:9191/api/items` — Returns the full product list as JSON.

## Available Products

The server maintains a list of products in the `ITEMS` array (`server.py` lines 7–9). Each product follows this structure:

```json
{
  "id": <int>,
  "name": <str>
}
```

### Current Products

| ID | Name   | Description         |
|----|--------|---------------------|
| 1  | apple  | Fresh red apple     |
| 2  | banana | Yellow banana       |
| 3  | cherry | Sweet cherry        |

### Example Response

```json
[
  {"id": 1, "name": "apple"},
  {"id": 2, "name": "banana"},
  {"id": 3, "name": "cherry"}
]
```

## Cherry Product

**Cherry** (`{"id": 3, "name": "cherry"}`) was added as the third product. It follows the same data structure as existing items (integer `id`, string `name`).

To verify cherry is available, call the `/api/items` endpoint and check for an object with `"name": "cherry"` in the response array.
