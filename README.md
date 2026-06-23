# Асинхронный сервис процессинга платежей

Сервис принимает платежи через HTTP API, сохраняет их в PostgreSQL, публикует событие через outbox pattern в RabbitMQ и асинхронно обрабатывает платеж consumer. Результат обработки отправляется на `webhook_url`.

## Стек

- FastAPI + Pydantic v2
- SQLModel + SQLAlchemy async + asyncpg
- PostgreSQL
- RabbitMQ + FastStream
- Alembic
- Docker Compose

## Структура

- `main.py` - FastAPI app, FastStream consumer app и composition root.
- `config.py` - настройки из переменных окружения.
- `common/database/schemas/` - SQLModel-схемы таблиц `payments` и `outbox`.
- `common/database/session.py` - `async_session_maker()`.
- `common/enums/` - enum для статусов, валют, очередей, subjects и consumer names.
- `common/services/broker_client.py` - RabbitMQ client и инициализация exchange/queue/DLQ.
- `routes/` - HTTP routes; `routes/handler/` - FastStream subscribers.
- `services/` - бизнес-логика платежей, outbox publisher, webhook и gateway emulator.

## Архитектура

- `POST /api/private/v1/payments/create` создает платеж со статусом `pending` и запись в `outbox` в одной транзакции.
- Outbox publisher в API читает `outbox`, публикует событие `payment.created` в `payments.exchange` и помечает событие как `published`.
- Consumer читает очередь `payments.new`, эмулирует платежный шлюз 2-5 секунд, выставляет `succeeded` или `failed`, затем отправляет webhook.
- При ошибке обработки или webhook сообщение отправляется в `payments.retry` с TTL и экспоненциальной задержкой. После TTL RabbitMQ возвращает его в `payments.new`.
- После 3 попыток сообщение делаем reject в `payments.dlx` и попадает в `payments.dlq`.
- Идемпотентность обеспечивается уникальным заголовком `Idempotency-Key`.

## Запуск

```bash
docker compose up --build
```

Доступы:

- API: `http://localhost:8000`
- Healthcheck: `http://localhost:8000/api/public/v1/health`
- PostgreSQL с хоста: `localhost:5435`
- RabbitMQ Management UI: `http://localhost:15672` (`guest` / `guest`)

Внутри Docker-сети сервисы подключаются к PostgreSQL через `postgres:5432`. Host-порт `5435` нужен только для подключения с машины разработчика.

## Примеры

Создать платеж:

```bash
curl -i -X POST http://localhost:8000/api/private/v1/payments/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key" \
  -H "Idempotency-Key: order-1001" \
  -d '{
    "amount": "1299.50",
    "currency": "RUB",
    "description": "Order #1001",
    "metadata": {"order_id": "1001"},
    "webhook_url": "https://example.com/payments/webhook"
  }'
```

Ответ:

```json
{
  "payment_id": "7e4f3197-1a44-4a4f-9a9a-79f7d8d624e4",
  "status": "pending",
  "created_at": "2026-06-23T00:00:00Z"
}
```

Получить платеж:

```bash
curl -i http://localhost:8000/api/private/v1/payments/<payment_id> \
  -H "X-API-Key: dev-api-key"
```

Healthcheck:

```bash
curl -i http://localhost:8000/api/public/v1/health
```

## Переменные окружения

См. `.env.example`.

Ключевые настройки:

- `API_KEY` - статический ключ для заголовка `X-API-Key`.
- `DATABASE_URL` - async SQLAlchemy URL. В Docker Compose используется `postgres:5432`.
- `RABBITMQ_URL` - AMQP URL.
- `CONSUMER_MAX_ATTEMPTS` - число попыток consumer до DLQ.
- `RETRY_BASE_DELAY_SECONDS` - базовая задержка для экспоненциального retry.
- `WEBHOOK_TIMEOUT_SECONDS` - timeout HTTP-запроса webhook.

## Миграции

В Docker Compose миграции применяются автоматически перед стартом API:

```bash
alembic upgrade head
```

Локально с PostgreSQL, проброшенным из compose:

```bash
DATABASE_URL=postgresql+asyncpg://payments:payments@localhost:5435/payments alembic upgrade head
```

## Consumer

Consumer запускается отдельным compose через console script:

```bash
payments-consumer
```

Скрипт объявлен в `pyproject.toml` как `main:run_consumer`.
