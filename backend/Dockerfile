# One image for the API, the background worker and the migrations (infra/docker-compose.production.yml):
#
#   api       the default command below
#   worker    python -m app.worker
#   migrate   alembic upgrade head
#
# Settings come from the environment (backend/.env is never copied in: see .dockerignore).
FROM python:3.12.15-slim-trixie

# Tesseract reads scanned pages when OCR_PROVIDER=tesseract (English and Hindi).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini pyproject.toml ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY app ./app

# Never root. Uploads and the search model are volumes; they take this folder's owner when created.
RUN useradd --create-home --uid 10001 eduguide \
    && mkdir -p storage/uploads storage/models \
    && chown -R eduguide storage
USER eduguide

EXPOSE 8000
# X-Forwarded-For (the browser's address, for the rate limits) is believed only from the addresses in
# FORWARDED_ALLOW_IPS: the frontend's network. Requests are logged by the app (ids, never addresses or
# query strings), so uvicorn's own access log is off.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-server-header", "--no-access-log"]
