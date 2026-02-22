import os
import redis
import psycopg2
import json
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from datetime import datetime, date # Импортируем для проверки типов

app = Flask(__name__)

# Переменные окружения
PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_NAME = os.getenv("PG_NAME", "crud_db")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

def get_pg_connection():
    return psycopg2.connect(host=PG_HOST, port=PG_PORT, database=PG_NAME, user=PG_USER, password=PG_PASSWORD)

def get_redis_connection():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Вспомогательная функция для сериализации дат (FIX)
def serialize_data(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

@app.route("/users", methods=["GET"])
def get_users():
    r = get_redis_connection()
    cache_key = "all_users"
    
    # Проверка кэша
    cached = r.get(cache_key)
    if cached:
        return jsonify(json.loads(cached)), 200
    
    # Запрос к БД
    conn = get_pg_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, name, email, created_at FROM users ORDER BY id")
    data = cur.fetchall()
    cur.close()
    conn.close()
    
    # Сериализуем данные, преобразуя даты в строки
    json_data = json.dumps(data, default=serialize_data)
    
    # Сохранение в кэш
    r.setex(cache_key, 60, json_data)
    return jsonify(data), 200

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    r = get_redis_connection()
    cache_key = f"user:{user_id}"
    
    cached = r.get(cache_key)
    if cached:
        return jsonify(json.loads(cached)), 200
    
    conn = get_pg_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, name, email, created_at FROM users WHERE id = %s", (user_id,))
    data = cur.fetchone()
    cur.close()
    conn.close()
    
    if not data:
        return jsonify({"error": "Not found"}), 404
        
    # Сериализуем данные
    json_data = json.dumps(data, default=serialize_data)
    r.setex(cache_key, 60, json_data)
    return jsonify(data), 200

@app.route("/users", methods=["POST"])
def create_user():
    data = request.json
    if not data or 'name' not in data or 'email' not in data:
        return jsonify({"error": "Name and email required"}), 400
    
    conn = get_pg_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id", (data['name'], data['email']))
        new_id = cur.fetchone()['id']
        conn.commit()
        
        # Инвалидация кэша
        r = get_redis_connection()
        r.delete("all_users")
        
        return jsonify({"id": new_id, "message": "Created"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    
    conn = get_pg_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404
    
    sets = []
    vals = []
    if 'name' in data:
        sets.append("name=%s")
        vals.append(data['name'])
    if 'email' in data:
        sets.append("email=%s")
        vals.append(data['email'])
    
    if sets:
        vals.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=%s", vals)
        conn.commit()
    
    cur.close()
    conn.close()
    
    # Инвалидация
    r = get_redis_connection()
    r.delete(f"user:{user_id}")
    r.delete("all_users")
    
    return jsonify({"message": "Updated"}), 200

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_pg_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if not deleted:
        return jsonify({"error": "Not found"}), 404
        
    r = get_redis_connection()
    r.delete(f"user:{user_id}")
    r.delete("all_users")
    
    return jsonify({"message": "Deleted"}), 200

@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_pg_connection()
        conn.close()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
