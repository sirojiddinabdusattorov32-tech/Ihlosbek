#!/bin/bash
python manage.py migrate --noinput
daphne -b 0.0.0.0 -p $PORT main.asgi:application
