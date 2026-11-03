# Sajha Kaam API. SQLite on the container disk: the demo world reseeds itself on every start.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config /srv/config
COPY shared /srv/shared
COPY backend/app ./app
ENV DATABASE_URL=sqlite:////tmp/sajha_kaam.db DEMO_MODE=1
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]
