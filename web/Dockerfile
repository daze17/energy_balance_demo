FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY web/app ./app
COPY brand ./brand
COPY db/init ./db_init
RUN useradd -r -u 10001 app && chown -R app /app
USER app
EXPOSE 8000
# --proxy-headers: Caddy (HTTPS)-ийн ард зөв https холбоос үүсгэнэ
# HOST/PORT-г PaaS (Railway) өгнө; анхдагч 0.0.0.0:8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers 2 --proxy-headers --forwarded-allow-ips '*'"]
