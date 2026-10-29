#!/bin/sh
set -e

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

python manage.py migrate --noinput

exec python manage.py runserver 0.0.0.0:8000
