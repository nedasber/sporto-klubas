#!/usr/bin/env bash
set -o errexit

python manage.py migrate --no-input
python manage.py shell -c "from gym.seed_plans import create_test_plans; create_test_plans()" || true
python manage.py shell -c "from gym.seed_users import create_test_users; create_test_users()" || true
python manage.py seed_achievements || true

exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2