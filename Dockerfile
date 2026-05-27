FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNSERVER_PORT=9000 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libjpeg62-turbo-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-docker.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-docker.txt

COPY . .

RUN chmod +x docker/entrypoint.sh

EXPOSE 9000

ENTRYPOINT ["docker/entrypoint.sh"]
