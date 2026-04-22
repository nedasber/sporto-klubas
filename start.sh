#!/usr/bin/env bash
set -o errexit

exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2