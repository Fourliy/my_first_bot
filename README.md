# my_first_bot — агент-консультант

Telegram-бот-консультант компании. Отвечает через агентный цикл с инструментами (tool calling), помнит контекст чата и при желании пишет трассы в LangSmith. Работает круглосуточно в облаке Railway.

Сейчас работают агентный цикл, поиск по PDF компании и фиксация лида. Проверка фактов в интернете — в следующей итерации.

## Возможности

- **Агентный цикл.** Запрос и список инструментов уходят в модель; если она просит вызвать инструмент — он выполняется, результат возвращается в модель, пока не придёт текстовый ответ. Не больше 5 шагов за ход.
- **Контекст диалога.** Последние 20 реплик чата хранятся в памяти и пропадают при перезапуске.
- **Устойчивость к ошибкам.** Таймаут и недоступность модели не роняют бота; длинный ввод усекается до 2000 символов; нетекстовые сообщения получают подсказку.
- **Ответы по документам.** На вопрос о курсе, услуге или портфолио агент вызывает `rag_search` и отвечает по фрагментам PDF из `./data`. Если в документах этого нет, бот так и говорит.
- **Заявка на консультацию.** Когда пользователь назвал имя и контакт, агент вызывает `capture_lead` и записывает лида в `./data/leads.db`. Без имени или контакта заявка не создаётся.
- **Трассировка LangSmith.** Включается `LANGSMITH_ENABLED=true`; запросы к модели видны в проекте LangSmith.

## Технологический стек

| Слой | Технология |
|---|---|
| Язык | Python 3.12 |
| Зависимости | [uv](https://docs.astral.sh/uv/) (`pyproject.toml`, `uv.lock`) |
| Telegram | aiogram 3, long polling |
| LLM | пакет `openai`, [OpenRouter](https://openrouter.ai) (`openai/gpt-4o-mini`); локально можно [Ollama](https://ollama.com) |
| Мониторинг | langsmith (опционально) |
| Лиды | sqlite3, `./data/leads.db` |
| Документы | PDF в `./data`, индекс chromadb в `./data/chroma` |
| Конфигурация | переменные окружения, `python-dotenv` для локального `.env` |
| Запуск | Make, Docker |
| Хостинг | [Railway](https://railway.com) |

Архитектура и решения: [`docs/vision.md`](docs/vision.md), план разработки: [`docs/tasklist.md`](docs/tasklist.md).

## Установка и запуск

### 1. Подготовка

1. Создайте бота у [@BotFather](https://t.me/BotFather) и получите токен.
2. Получите ключ на [OpenRouter](https://openrouter.ai/keys). Вместо него можно взять локальный [Ollama](https://ollama.com) (см. .env.example).
3. Установите [uv](https://docs.astral.sh/uv/) и Make; для запуска в контейнере — Docker Desktop.
4. Склонируйте репозиторий:

   ```
   git clone https://github.com/Fourliy/my_first_bot.git
   cd my_first_bot
   ```

### 2. Настройка

Скопируйте `.env.example` в `.env` и заполните значения:

| Переменная | Обязательна | Описание |
|---|---|---|
| `TELEGRAM_TOKEN` | да | токен бота от BotFather |
| `OPENAI_API_KEY` | да | ключ OpenRouter; подойдёт и `OPENROUTER_API_KEY`; для локального Ollama — `ollama` |
| `OPENAI_BASE_URL` | нет | адрес API, по умолчанию `https://openrouter.ai/api/v1` |
| `MODEL_TEXT` | нет | модель диалога, по умолчанию `openai/gpt-4o-mini` |
| `EMBEDDING_MODEL` | нет | модель эмбеддингов, по умолчанию `openai/text-embedding-3-small` |
| `LOG_LEVEL` | нет | уровень логов, по умолчанию `INFO` |
| `LANGSMITH_ENABLED` | нет | трассировка LangSmith, по умолчанию `false` |
| `LANGSMITH_API_KEY` | если трассировка включена | ключ LangSmith |
| `LANGSMITH_PROJECT` | нет | проект в LangSmith |

Файл `.env` не попадает в git и в Docker-образ. Не публикуйте токен и ключи.

### 3. Локальный запуск

```
# в виртуальном окружении
make install
make run

# или в Docker
make docker-build
make docker-run
```

Остановка: `Ctrl+C`. Другие цели Make: `venv`, `clean`.

Одновременно должен работать только один экземпляр бота: два процесса с одним токеном конфликтуют (ошибка `Conflict: terminated by other getUpdates request`). Если бот запущен в Railway, локально его не запускайте.

### 4. Деплой в Railway

1. В [Railway](https://railway.com): New Project → Deploy from GitHub repo → этот репозиторий.
2. Railway соберёт образ по `Dockerfile`; настройки сборки и перезапуска при падении лежат в `railway.json`.
3. В сервисе откройте Variables → Raw Editor, вставьте переменные из таблицы выше, нажмите Update Variables, затем Deploy. Локальный `.env` в Railway не попадает.
4. Оставьте один экземпляр сервиса. Публичный домен не нужен: бот сам опрашивает Telegram.
5. Каждый push в `main` запускает новый деплой. Если автодеплой недоступен («Could not load branches»), выдайте приложению Railway доступ к репозиторию на [github.com/settings/installations](https://github.com/settings/installations).

После старта в логах (Deployments → View Logs) появляется строка `event=start`.

## Настройка поведения

- Роль и краткие сведения о компании — `SYSTEM_PROMPT` в `src/my_first_bot/config.py`.
- Агентный цикл и лимит шагов (`MAX_STEPS`) — `src/my_first_bot/agent.py`.
- Инструменты — `src/my_first_bot/tools.py` (`TOOLS` — схемы, `TOOL_HANDLERS` — реализации).
- Запись лида — `src/my_first_bot/leads.py`, база `./data/leads.db`.
- Поиск по PDF — `bot/tools/rag.py`, функция `rag_search(query, n_results)`. Индексация — `scripts/index_pdf.py` (также запускается при старте бота). Файлы `*.pdf` лежат в `./data`, образец — `data/company.pdf`.
- Лимиты истории и ввода (`MAX_HISTORY`, `MAX_INPUT_CHARS`) — `src/my_first_bot/telegram_bot.py`; лимит ответа (`MAX_TOKENS`) — `src/my_first_bot/llm_client.py`.

## Ограничения

- Проверки фактов в интернете пока нет.
- Индекс chromadb строится при старте и хранится в `./data/chroma`. Уже проиндексированный PDF повторно не обрабатывается.
- История диалога хранится в памяти и пропадает при перезапуске; записанные лиды остаются в `./data/leads.db`.
- Нет автотестов и CI.
