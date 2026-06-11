# TaskMaster

Система управления задачами: FastAPI + PostgreSQL (сервер), PySide6 + SQLite (клиент).

## Запуск бэкенда

```bash
docker compose up -d          # PostgreSQL
cd backend
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --app-dir .
```

API: http://127.0.0.1:8000/docs

## Запуск клиента

```bash
cd client
pip install -r requirements.txt
python -m app.main
```

## Структура

- `backend/app/` — FastAPI, модели, CRUD, API
- `client/app/` — PySide6 десктоп-клиент
- `progress.txt` — краткий статус разработки
