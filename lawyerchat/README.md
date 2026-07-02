# LawyerChat Retrieval MVP

LawyerChat Retrieval MVP — учебное приложение для семантического поиска и RAG-ответов по вручную загруженным юридическим документам.

Приложение преобразует локальные `.htm/.html` и `.docx` документы из КонсультантПлюс в структурированный `.jsonl`, индексирует JSONL-фрагменты, считает embeddings локальной моделью `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` и возвращает релевантные фрагменты через API, RAG-чат или простой frontend.

## Важное предупреждение

Система не является юридической консультацией. Она помогает искать релевантные фрагменты документов и формировать RAG-ответ, но итоговый текст нужно проверять по первоисточникам.

## Архитектура

- FastAPI backend
- PostgreSQL + pgvector
- SQLAlchemy ORM
- `sentence-transformers` для локальных embeddings
- исходные `.htm/.html` документы в `backend/data/raw_html/`
- исходные `.docx` документы в `backend/data/raw_docx/`
- структурированные `.jsonl` документы в `backend/data/legal_docs/`
- legacy/fallback `.txt` документы в `backend/data/legal_docs/`
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

Поддерживаются две ветки подготовки нормативно-правового корпуса:

```text
HTML/HTM из КонсультантПлюс
→ backend/data/raw_html/
→ scripts.convert_html_to_jsonl
→ backend/data/legal_docs/*.jsonl

DOCX из КонсультантПлюс
→ backend/data/raw_docx/
→ scripts.convert_docx_to_jsonl
→ backend/data/legal_docs/*.jsonl

Общий этап:
backend/data/legal_docs/*.jsonl
→ scripts.ingest_documents
→ PostgreSQL + pgvector
→ /api/search и /api/chat
```

Положите исходные HTML/HTM или DOCX-файлы вручную в соответствующую папку:

```text
backend/data/raw_html/
backend/data/raw_docx/
```

Эти файлы не индексируются напрямую. Сначала преобразуйте их в JSONL соответствующим конвертером.

Поддерживаемые форматы в `backend/data/legal_docs/`:

- `.jsonl` — рекомендуемый структурированный формат. Каждая строка считается отдельным готовым юридическим фрагментом, обычно одной статьей.
- `.txt` — legacy/fallback режим. Файл читается целиком и разбивается на чанки через `split_legal_text`, но для нормативного корпуса TXT больше не рекомендуется, потому что теряет иерархическую структуру разделов, глав и статей.

Пример JSONL-строки:

```json
{"document_id":"tk_rf","document_title":"Трудовой кодекс Российской Федерации","source_format":"html","source_filename":"Трудовой кодекс Российской Федерации от 30.12.2001 N 197-ФЗ.htm","section_title":"Раздел III. Трудовой договор","subsection_title":null,"chapter_title":"Глава 13. Прекращение трудового договора","paragraph_title":null,"article_number":"80","article_title":"Расторжение трудового договора по инициативе работника","text":"Статья 80. Расторжение трудового договора по инициативе работника\n\nРаботник имеет право расторгнуть трудовой договор...","referenced_articles":["77"],"source_url":null}
```

Документы не скачиваются автоматически и сайты не парсятся.

## Конвертация HTML в JSONL

Из папки `backend` для одного документа:

```powershell
python -m scripts.convert_html_to_jsonl `
  --input "data/raw_html/Трудовой кодекс Российской Федерации от 30.12.2001 N 197-ФЗ.htm" `
  --output "data/legal_docs/trudovoy_kodeks_rf.jsonl" `
  --document-id "tk_rf" `
  --document-title "Трудовой кодекс Российской Федерации"
```

Пакетная конвертация всей папки:

```powershell
python -m scripts.convert_html_to_jsonl `
  --input-dir "data/raw_html" `
  --output-dir "data/legal_docs"
```

Скрипт читает UTF-8, при необходимости пробует cp1251, удаляет служебные HTML-теги и выделяет структуру:

- `Раздел ...`
- `Подраздел ...`
- `Глава ...`
- `Параграф ...`
- `Статья N. Название статьи`

Каждая найденная статья становится отдельной JSONL-строкой. Текст статьи включает заголовок статьи и абзацы до следующей статьи.

## Конвертация DOCX в JSONL

Из папки `backend` для одного документа:

```powershell
python -m scripts.convert_docx_to_jsonl `
  --input "data/raw_docx/Семейный кодекс Российской Федерации.docx" `
  --output "data/legal_docs/semeynyy_kodeks_rf.jsonl" `
  --document-id "sk_rf" `
  --document-title "Семейный кодекс Российской Федерации"
```

Пакетная конвертация всей папки:

```powershell
python -m scripts.convert_docx_to_jsonl `
  --input-dir "data/raw_docx" `
  --output-dir "data/legal_docs"
```

DOCX-конвертер читает абзацы в порядке документа, нормализует пробелы и выделяет разделы, подразделы, главы, параграфы и статьи. Для известных документов автоматически выбираются идентификатор, название и имя выходного JSONL.

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

Индексация перечитывает `.jsonl` и legacy `.txt` файлы из `backend/data/legal_docs/`, удаляет старый `Document` с тем же `filename`, считает embeddings только по тексту фрагмента и сохраняет данные в PostgreSQL + pgvector. Поле `chunks.embedding` имеет тип `vector(384)`.

## Тестирование качества retrieval

Контрольные вопросы находятся в `backend/data/evaluation/retrieval_cases.json`. Оценка использует текущие `Embedder` и `Retriever`, обращается к PostgreSQL + pgvector и не вызывает LLM.

Запуск из папки `backend`:

```powershell
python -m scripts.evaluate_retrieval `
  --cases "data/evaluation/retrieval_cases.json" `
  --top-k 20 `
  --output-dir "reports"
```

Скрипт рассчитывает Top-1, Top-3, Top-5, Top-10 и Top-20 accuracy, MRR, позицию первого правильного результата и среднюю similarity первого результата. Отдельные метрики группируются по законам. Если глубина `top_k` меньше порога метрики, отчёт отмечает такую метрику как не рассчитанную.

Отчеты сохраняются в `backend/reports/`:

- `retrieval_results.csv`;
- `retrieval_results.json`;
- `retrieval_report.md`;
- `retrieval_report.docx`.

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
- `article_number`
- `article_title`
- `section_title`
- `subsection_title`
- `chapter_title`
- `paragraph_title`
- `source_format`
- `source_filename`
- `distance`
- `similarity`

В ответе поиска нет сгенерированной юридической консультации, только найденные фрагменты.

## Frontend

Основной frontend теперь выглядит как чат-бот: вопрос отправляется в `POST /api/chat`, ответ отображается в ленте сообщений, а использованные нормы показываются отдельными карточками под ответом. Технический retrieval-режим `POST /api/search` открыт через маленькую кнопку `Поиск` в правом верхнем углу.

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

## Локальная история диалога

История чата сохраняется в `localStorage` браузера. В неё входят вопросы пользователя, ответы ассистента и отображаемые источники. После перезагрузки страницы сообщения и карточки источников восстанавливаются без повторных запросов к backend.

Пользователь может удалить сохранённые сообщения кнопкой `Очистить историю` в блоке чата. История хранится только в браузере пользователя и не передаётся и не сохраняется на сервере.

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
- загрузку PDF
- улучшенные индексы pgvector
