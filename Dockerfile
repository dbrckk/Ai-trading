FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8765

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN mkdir -p /app/artifacts
VOLUME ["/app/artifacts"]

EXPOSE 8765
CMD ["sh", "-c", "ai-trading dashboard --host 0.0.0.0 --port ${PORT}"]
