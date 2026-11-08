#!/bin/sh
# Запуск на Raspberry Pi в каталоге проекта.
set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Создайте .env из .env.example перед запуском."
  exit 1
fi

docker compose up -d --build
docker compose ps
echo "Откройте http://192.168.1.104/"
