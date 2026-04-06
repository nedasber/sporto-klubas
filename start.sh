#!/usr/bin/env bash
set -o errexit

python manage.py shell -c "from gym.seed_users import create_test_users; create_test_users()"
gunicorn config.wsgi:application