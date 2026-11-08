#!/bin/sh
set -e

if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/media /app/staticfiles
  chown -R cafe:cafe /app/media /app/staticfiles
  exec gosu cafe /entrypoint.sh "$@"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_cafe

exec "$@"
