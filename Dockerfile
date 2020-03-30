FROM python:3.7-slim

ENV PYTHONUNBUFFERED=1

# upgrade pip
RUN python -m pip install -U pip

WORKDIR /app

COPY requirements.txt /app/

RUN python -m pip install -r requirements.txt

COPY . /app
