# LawyerChat Retrieval MVP

LawyerChat Retrieval MVP — учебное приложение для семантического поиска и RAG-ответов по вручную загруженным юридическим документам.

Приложение индексирует локальные `.txt` и `.jsonl` документы, считает embeddings локальной моделью `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` и возвращает релевантные фрагменты через API, RAG-чат или простой frontend.

## Важное предупреждение

Система не является юридической консультацией. Она помогает искать релевантные фрагменты документов и формировать RAG-ответ, но итоговый текст нужно проверять по первоисточникам.

## Архитектура

- FastAPI backend
- PostgreSQL + pgvector
- SQLAlchemy ORM
- `sentence-transformers` для локальных embeddings
- локальные `.txt` и `.jsonl` документы в `backend/data/legal_docs/`
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

Положите документы вручную в:

```text
backend/data/legal_docs/
```

Поддерживаются два формата:

- `.txt` — простой режим. Файл читается целиком и разбивается на чанки через `split_legal_text`.
- `.jsonl` — рекомендуемый структурированный формат для юридического корпуса. Каждая строка считается отдельным готовым юридическим фрагментом и не смешивается с соседними строками.

Примеры файлов:

- `trudovoy_kodeks.txt`
- `grazhdanskiy_kodeks.txt`
- `example_legal_corpus.jsonl`

Пример JSONL-строки:

```json
{"document_id":"tk_rf","document_title":"Трудовой кодекс Российской Федерации","filename":"trudovoy_kodeks.jsonl","section_title":"Раздел III. Трудовой договор","chapter_title":"Глава 13. Прекращение трудового договора","article_number":"80","article_title":"Расторжение трудового договора по инициативе работника","text":"Работник имеет право расторгнуть трудовой договор...","referenced_articles":[],"source_url":null}
```

Для JSONL в базу сохраняются существующие поля чанка: `content` из `text`, `article_number`, `article_title`, `referenced_articles` и `embedding`. Поля `section_title`, `chapter_title` и `source_url` можно держать в корпусе заранее: ingestion спокойно их прочитает, но пока не сохраняет в отдельные колонки.

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

Или из Windows PowerShell при запущенном backend:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/documents/reindex
```

Индексация перечитывает `.txt` и `.jsonl` файлы, удаляет старый `Document` с тем же `filename`, считает embeddings только по тексту фрагмента и сохраняет данные в PostgreSQL + pgvector. Поле `chunks.embedding` имеет тип `vector(384)`.

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
- `POST /api/chat`

## Второй этап

Во втором этапе можно добавить:

- подключение LLM
- генерацию ответа на основе найденных фрагментов
- ссылки на источники
- историю диалогов
- загрузку PDF/DOCX
- улучшенные индексы pgvector
