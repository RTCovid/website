FROM python:3.7-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8

RUN apt-get update -qq && apt-get install -y -qq \
    gdal-bin \
    binutils \
    libproj-dev \
    libgdal-dev \
    && \
    apt-get clean all && rm -rf /var/apt/lists/* && rm -rf /var/cache/apt/*

# upgrade pip
RUN python -m pip install --no-cache-dir -U pip pip-tools

WORKDIR /app

ARG BUILD_ENV=dev
COPY reqs/ /app/reqs/
RUN python -m pip install --no-cache-dir -r reqs/$BUILD_ENV.txt

COPY . /app
