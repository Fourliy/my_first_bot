---
name: Conventions
description: Принципы генерации кода для MVP Telegram LLM-ассистента
alwaysApply: true
---

# Conventions

Источник истины по стеку и границам MVP: [`docs/vision.md`](docs/vision.md). Не копируй его сюда и не расходись с ним.

## Цель

Генерируй **минимальный** код, достаточный проверить идею. Не проектируй «на вырост».

## Стек

- Используй только технологии из `docs/vision.md`.
- Новую зависимость не добавляй, пока задачу нельзя решить ими.
- Не вводи БД, Redis, веб-фреймворк, webhook. Облачный хостинг — только Railway, как в vision.

```python
# ❌ BAD — лишний слой вне vision
from fastapi import FastAPI
from redis import Redis

# ✅ GOOD — aiogram + openai + logging, как в vision
from aiogram import Router
import logging
```

## Конфиг и секреты

Секреты и настройки — только из переменных окружения, не в коде и не в репозитории.

## Запуск

Локальный запуск: Make и Docker; облако — Railway по `Dockerfile`. Не усложняй деплой.

## KISS

Если можно сделать проще и остаться в рамках `docs/vision.md` — так и делай.
