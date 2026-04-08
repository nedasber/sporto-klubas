#!/usr/bin/env bash
set -o errexit

python manage.py shell -c "from gym.seed_users import create_test_users; create_test_users()"
python manage.py shell -c "from gym.seed_plans import create_test_plans; create_test_plans()"
exec gunicorn config.wsgi:application