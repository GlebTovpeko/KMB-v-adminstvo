FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    nginx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY uwsgi.ini .
COPY nginx.conf /etc/nginx/nginx.conf

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /var/cache/nginx && \
    touch /run/nginx.pid && \
    chown appuser:appuser /run/nginx.pid

USER appuser

EXPOSE 80

CMD ["sh", "-c", "uwsgi --ini uwsgi.ini & nginx -g 'daemon off;'"]