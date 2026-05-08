# LawyerChat Retrieval MVP

LawyerChat Retrieval MVP — учебное приложение для семантического поиска по вручную загруженным юридическим документам.

На первом этапе это не полноценный чат и не RAG с генерацией ответа. Приложение только индексирует локальные `.txt` документы, считает embeddings локальной моделью `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` и возвращает наиболее релевантные фрагменты через API или простой frontend.

## Важное предупреждение

Система не является юридической консультацией. На первом этапе она только находит релевантные фрагменты документов. Генерация итогового ответа через LLM будет добавлена позднее.

## Архитектура

- FastAPI backend
- PostgreSQL + pgvector
- SQLAlchemy ORM
- `sentence-transformers` для локальных embeddings
- локальные `.txt` документы в `backend/data/legal_docs/`
- статический frontend без React и сборки

## Запуск PostgreSQL

Из корня проекта:

```bash
docker compose up -d postgres
```

Используется контейнер `legal_rag_postgres` на порту `5433` хоста.

## Создание `.env`

```bat
cd backend
copy .env.example .env
```

Локальный `DATABASE_URL` из `.env.example`:

```text
postgresql+psycopg2://legal_user:legal_password@localhost:5433/legal_rag
```

## Venv на Windows

```bat
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Локальный запуск backend

Из папки `backend`:

```bash
uvicorn app.main:app --reload
```

При старте backend создает таблицы `documents` и `chunks`, но не запускает индексацию документов автоматически.

## Health check

Откройте:

```text
http://localhost:8000/health
```

Ожидаемый ответ после запуска PostgreSQL:

```json
{
  "status": "ok",
  "database": true,
  "pgvector": true
}
```

## Добавление юридических документов

Положите `.txt` файлы вручную в:

```text
backend/data/legal_docs/
```

Например:

- `trudovoy_kodeks.txt`
- `grazhdanskiy_kodeks.txt`

Документы не скачиваются автоматически и сайты не парсятся.

## Индексация

Из папки `backend`:

```bash
python -m scripts.ingest_documents
```

Или через Swagger:

```text
POST http://localhost:8000/api/documents/reindex
```

Индексация перечитывает `.txt` файлы, разбивает текст на чанки, считает embeddings и сохраняет данные в PostgreSQL + pgvector. Поле `chunks.embedding` имеет тип `vector(384)`.

## Поиск

Swagger доступен по адресу:

```text
http://localhost:8000/docs
```

Пример запроса:

```text
POST /api/search
```

```json
{
  "query": "Какие основания для увольнения работника?",
  "top_k": 5
}
```

Ответ содержит исходный `query`, массив `results`, `total_results` и `note`. Каждый результат содержит:

- `chunk_id`
- `document_id`
- `filename`
- `chunk_index`
- `content`
- `distance`

В ответе нет сгенерированной юридической консультации, только найденные фрагменты.

## Frontend

Можно открыть файл напрямую:

```text
frontend/index.html
```

Или запустить простой сервер:

```bash
cd frontend
python -m http.server 3000
```

После этого откройте:

```text
http://localhost:3000
```

## Разница `DATABASE_URL`

Для локального запуска backend:

```text
postgresql+psycopg2://legal_user:legal_password@localhost:5433/legal_rag
```

Для backend внутри Docker Compose:

```text
postgresql+psycopg2://legal_user:legal_password@postgres:5432/legal_rag
```

В `docker-compose.yml` значение для Docker backend переопределяется через `environment`.

## Запуск всего через Docker

Перед запуском создайте `backend/.env` из примера, затем из корня проекта:

```bash
docker compose up --build
```

Backend будет доступен на:

```text
http://localhost:8000
```

## Пересоздание базы

```bash
docker compose down -v
docker compose up -d postgres
```

Команда `docker compose down -v` удаляет volume PostgreSQL и все сохраненные данные.

## Endpoints

- `GET /health`
- `POST /api/search`
- `GET /api/documents`
- `GET /api/documents/{document_id}/chunks`
- `POST /api/documents/reindex`

## Второй этап

Во втором этапе можно добавить:

- подключение LLM
- генерацию ответа на основе найденных фрагментов
- ссылки на источники
- историю диалогов
- загрузку PDF/DOCX
- улучшенные индексы pgvector
