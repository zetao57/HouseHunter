from contextlib import contextmanager
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse
import json
import os
import sqlite3

APP_DIR = Path(__file__).resolve().parent / "dist"
DB_PATH = Path(os.environ.get("DATABASE_PATH", "/data/househunter.sqlite3"))
PORT = int(os.environ.get("PORT", "80"))
FIELDS = [
    "id",
    "title",
    "rent",
    "payment",
    "layout",
    "area",
    "status",
    "address",
    "longitude",
    "latitude",
    "contactName",
    "contactPhone",
    "description",
    "images",
    "createdAt",
    "updatedAt",
]


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            rent REAL,
            payment TEXT,
            layout TEXT,
            area REAL,
            status TEXT,
            address TEXT,
            longitude REAL,
            latitude REAL,
            contactName TEXT,
            contactPhone TEXT,
            description TEXT,
            images TEXT NOT NULL DEFAULT '[]',
            createdAt TEXT NOT NULL,
            updatedAt TEXT NOT NULL
        )
        """
    )
    con.commit()
    return con


@contextmanager
def database():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def normalize(payload, existing=None):
    data = dict(existing or {})
    for key in FIELDS:
        if key in payload:
            data[key] = payload[key]
    data["images"] = json.dumps(data.get("images") or [], ensure_ascii=False)
    return data


def row_to_record(row):
    item = dict(row)
    try:
        item["images"] = json.loads(item.get("images") or "[]")
    except json.JSONDecodeError:
        item["images"] = []
    for key in ("rent", "area", "longitude", "latitude"):
        if item.get(key) is None:
            item[key] = ""
    return item


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def send_json(self, status, body=None):
        raw = b"" if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def api_id(self):
        path = urlparse(self.path).path
        if path == "/api/records":
            return None
        prefix = "/api/records/"
        if path.startswith(prefix):
            return unquote(path[len(prefix):])
        return False

    def do_GET(self):
        record_id = self.api_id()
        if record_id is not False:
            with database() as con:
                if record_id is None:
                    rows = con.execute("SELECT * FROM records ORDER BY updatedAt DESC").fetchall()
                    self.send_json(200, [row_to_record(row) for row in rows])
                else:
                    row = con.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
                    self.send_json(200, row_to_record(row)) if row else self.send_json(404, {"error": "Not found"})
            return
        super().do_GET()

    def do_POST(self):
        if self.api_id() is not None:
            self.send_json(404, {"error": "Not found"})
            return
        payload = self.read_json()
        if not payload.get("id") or not payload.get("title"):
            self.send_json(400, {"error": "id and title are required"})
            return
        data = normalize(payload)
        cols = ", ".join(FIELDS)
        marks = ", ".join("?" for _ in FIELDS)
        with database() as con:
            con.execute(f"INSERT INTO records ({cols}) VALUES ({marks})", [data.get(k) for k in FIELDS])
            row = con.execute("SELECT * FROM records WHERE id = ?", (data["id"],)).fetchone()
        self.send_json(201, row_to_record(row))

    def do_PUT(self):
        record_id = self.api_id()
        if not record_id:
            self.send_json(404, {"error": "Not found"})
            return
        payload = self.read_json()
        with database() as con:
            row = con.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
            if not row:
                self.send_json(404, {"error": "Not found"})
                return
            data = normalize(payload, row_to_record(row))
            data["id"] = record_id
            assignments = ", ".join(f"{key} = ?" for key in FIELDS if key != "id")
            con.execute(f"UPDATE records SET {assignments} WHERE id = ?", [data.get(k) for k in FIELDS if k != "id"] + [record_id])
            row = con.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
        self.send_json(200, row_to_record(row))

    def do_DELETE(self):
        record_id = self.api_id()
        if not record_id:
            self.send_json(404, {"error": "Not found"})
            return
        with database() as con:
            cur = con.execute("DELETE FROM records WHERE id = ?", (record_id,))
        self.send_json(204 if cur.rowcount else 404, None if cur.rowcount else {"error": "Not found"})

    def end_headers(self):
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "public, max-age=3600")
        super().end_headers()

    def send_head(self):
        if self.path.startswith("/api/"):
            self.send_json(404, {"error": "Not found"})
            return None
        path = self.translate_path(self.path)
        if not Path(path).exists() and not Path(path).suffix:
            self.path = "/index.html"
        return super().send_head()


if __name__ == "__main__":
    connect().close()
    print(f"Serving HouseHunter on :{PORT}, SQLite database: {DB_PATH}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
