#!/usr/bin/env bash
set -o errexit

echo "STARTING APP"
python manage.py shell -c "from gym.seed_users import create_test_users; create_test_users()"
echo "SEED DONE"
exec gunicorn config.wsgi:application