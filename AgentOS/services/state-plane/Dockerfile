FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY pyproject.toml .
RUN pip install --no-cache-dir hatchling && pip install --no-cache-dir -e .

COPY . .

EXPOSE 8014

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8014"]
