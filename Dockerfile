FROM python:3.7-slim

ENV PYTHONUNBUFFERED=1

# upgrade pip
RUN python -m pip install --no-cache-dir -U pip pip-tools

WORKDIR /app

ARG BUILD_ENV=dev
COPY reqs/ /app/reqs/
RUN python -m pip install --no-cache-dir -r reqs/$BUILD_ENV.txt

COPY . /app
