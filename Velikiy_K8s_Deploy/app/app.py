import os
import time
import json
import psycopg2
import redis
from datetime import datetime, date
from flask import Flask, request, jsonify, abort
from psycopg2.extras import RealDictCursor
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP requests',
    ['method', 'endpoint', 'http_status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP request latency in seconds',
    ['endpoint']
)

DB_ERRORS = Counter('db_errors_total', 'Total DB errors')


start_time = None

PG_HOST = os.getenv('PG_HOST', 'postgres')
PG_PORT = int(os.getenv('PG_PORT', 5432))
PG_NAME = os.getenv('PG_NAME', 'crud_db')
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD', 'postgres')

REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))


def get_db():
    try:
        return psycopg2.connect(
            host=PG_HOST, port=PG_PORT, database=PG_NAME,
            user=PG_USER, password=PG_PASSWORD,
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        DB_ERRORS.inc()
        raise

def get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def serialize_data(obj):
    """Сериализация datetime для JSON"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@app.before_request
def before_request():
    global start_time
    start_time = time.time()

@app.after_request
def track_after_request(response):
    global start_time
    if start_time:
        endpoint = request.path
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            request.method, 
            endpoint, 
            str(response.status_code)
        ).inc()
        REQUEST_LATENCY.labels(endpoint).observe(duration)
    return response

@app.errorhandler(Exception)
def handle_error(error):
    global start_time
    if start_time:
        endpoint = request.path
        duration = time.time() - start_time
        status = "500"
        if hasattr(error, 'code'):
            status = str(error.code)
        REQUEST_COUNT.labels(request.method, endpoint, status).inc()
        REQUEST_LATENCY.labels(endpoint).observe(duration)
    if hasattr(error, 'code'):
        return jsonify({"error": str(error)}), error.code
    return jsonify({"error": "Internal Server Error"}), 500


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return jsonify({"status": "healthy", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500



@app.route("/users", methods=["GET"])
def list_users():
    limit = request.args.get('limit', 10, type=int)
    

    r = get_redis()
    cache_key = "all_users"
    cached = r.get(cache_key)
    if cached:
        return jsonify(json.loads(cached)), 200
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, surname, age, town FROM users ORDER BY id LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    data = [dict(row) for row in rows]
    r.setex(cache_key, 60, json.dumps(data, default=serialize_data))
    return jsonify(data)

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    r = get_redis()
    cache_key = f"user:{user_id}"
    cached = r.get(cache_key)
    if cached:
        return jsonify(json.loads(cached)), 200
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, surname, age, town FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row:
        abort(404)
    
    data = dict(row)
    r.setex(cache_key, 60, json.dumps(data, default=serialize_data))
    return jsonify(data)

@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    if not data or 'name' not in data:
        abort(400)
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, surname, age, town) VALUES (%s, %s, %s, %s) RETURNING id",
        (data['name'], data.get('surname', ''), data.get('age', 0), data.get('town', ''))
    )
    new_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()
    

    r = get_redis()
    r.delete("all_users")
    
    return jsonify({"id": new_id, **data}), 201

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json()
    if not data or 'name' not in data:
        abort(400)
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET name=%s, surname=%s, age=%s, town=%s WHERE id=%s RETURNING id",
        (data['name'], data.get('surname', ''), data.get('age', 0), data.get('town', ''), user_id)
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if not row:
        abort(404)
    

    r = get_redis()
    r.delete(f"user:{user_id}")
    r.delete("all_users")
    
    return jsonify({"id": user_id, **data})

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    if deleted == 0:
        abort(404)
    

    r = get_redis()
    r.delete(f"user:{user_id}")
    r.delete("all_users")
    
    return "", 204

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)