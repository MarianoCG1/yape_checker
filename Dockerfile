FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PORT=8000

# Forma shell (no exec-array) a propósito: así se expande $PORT, que Render
# inyecta dinámicamente. Localmente sigue usando 8000 por el ENV de arriba.
CMD uvicorn FastApi:app --host 0.0.0.0 --port ${PORT:-8000}
