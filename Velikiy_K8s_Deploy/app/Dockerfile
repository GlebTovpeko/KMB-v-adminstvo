FROM python:3.11-slim

WORKDIR /app

# 🔥 Устанавливаем nginx И компиляторы для uWSGI
RUN apt-get update && apt-get install -y \
    nginx \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 🔥 Создаём недостающие директории nginx
RUN mkdir -p /var/cache/nginx /var/log/nginx /run/nginx

# Установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения и конфигов
COPY app.py .
COPY uwsgi.ini .
COPY nginx.conf /etc/nginx/nginx.conf

# 🔥 Исправленный chown (теперь директории существуют)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /run/nginx && \
    touch /run/nginx.pid && \
    chown appuser:appuser /run/nginx.pid

USER appuser

EXPOSE 80

# Запуск обоих сервисов
CMD ["sh", "-c", "uwsgi --ini uwsgi.ini & nginx -g 'daemon off;'"]