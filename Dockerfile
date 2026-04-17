FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

ENV PYTHONUNBUFFERED=1

EXPOSE 8765

# Render (and others) inject PORT at runtime; 8765 for local `docker run -p 8765:8765`
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8765}"]
