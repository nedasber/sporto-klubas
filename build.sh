#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Pradiniai duomenys (tik kai DB tuščia - jei jau yra, nieko nekeis)
python manage.py shell -c "from gym.seed_plans import create_test_plans; create_test_plans()" || true
python manage.py shell -c "from gym.seed_users import create_test_users; create_test_users()" || true
python manage.py seed_achievements || true