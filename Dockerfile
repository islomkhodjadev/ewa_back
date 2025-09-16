FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
ENV PIP_DEFAULT_TIMEOUT=1000
ENV PIP_RETRIES=10

COPY ./requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# COPY models/multilingual-e5-base /app/models/multilingual-e5-base

COPY . .

RUN mkdir -p /app/logs



EXPOSE 8000

