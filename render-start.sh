#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
gunicorn config.wsgi:application --log-file - --workers 2 --threads 4
