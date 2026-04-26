#!/usr/bin/env bash
# Скрипт для развёртывания Wiki-страниц в GitHub Wiki репозиторий.
#
# Предварительные требования:
#   1. Инициализируйте Wiki через GitHub UI:
#      https://github.com/SatoryKono/BioactivityDataAcquisition/wiki/_new
#      Создайте пустую Home-страницу и сохраните.
#   2. Запустите этот скрипт из корня репозитория:
#      bash docs/wiki/deploy_wiki.sh
#
set -euo pipefail

REPO_URL="https://github.com/SatoryKono/BioactivityDataAcquisition.wiki.git"
WIKI_SRC="docs/wiki"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Клонирование Wiki-репозитория..."
git clone "$REPO_URL" "$TMP_DIR"

echo "Копирование Wiki-страниц..."
for f in "$WIKI_SRC"/*.md; do
    [ "$(basename "$f")" = "README.md" ] && continue
    cp "$f" "$TMP_DIR/"
done

cd "$TMP_DIR"
git add -A
git diff --cached --quiet && { echo "Нет изменений."; exit 0; }
git commit -m "Обновление Wiki-страниц проекта BioETL"
git push origin master

echo "Wiki-страницы успешно развёрнуты!"
echo "https://github.com/SatoryKono/BioactivityDataAcquisition/wiki"

