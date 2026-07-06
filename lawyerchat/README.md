# LawyerChat

LawyerChat — MVP web-приложения для первичной юридической помощи на основе RAG-подхода. Система принимает вопрос пользователя на русском языке, ищет релевантные фрагменты нормативно-правовых документов в локальной базе знаний и формирует ответ с указанием использованных источников.

Ответы строятся только на основании загруженного и проиндексированного корпуса. Использованные нормы права отображаются отдельно от ответа.

> LawyerChat не заменяет профессиональную юридическую консультацию. Ответы зависят от полноты и актуальности корпуса и качества поиска, поэтому их необходимо проверять по первоисточникам и при необходимости уточнять у специалиста.

## Возможности

- чат-интерфейс для вопросов по правовым темам;
- подготовка корпуса из HTML/HTM и DOCX;
- преобразование документов в структурированный JSONL с сохранением документа, раздела, подраздела, главы, параграфа, номера и названия статьи;
- создание embeddings и индексация фрагментов в PostgreSQL + pgvector;
- семантический и гибридный поиск;
- гибридное ранжирование по векторной близости, PostgreSQL full-text search и метаданным;
- отображение использованных норм права;
- технический режим поиска с оценками найденных фрагментов;
- локальная история диалога в `localStorage`;
- evaluation retrieval на контрольных вопросах и генерация отчётов.

## Ограничения MVP

- нет авторизации, личного кабинета и админ-панели;
- нет серверного хранения истории диалога: она хранится только в браузере пользователя;
- нет автоматического скачивания документов и обновления законодательства;
- нет Telegram-бота;
- ответы требуют проверки специалистом;
- качество ответа зависит от качества корпуса и retrieval.

## Архитектура

```text
HTML/HTM документы        DOCX документы
          \                  /
           v                v
convert_html_to_jsonl.py / convert_docx_to_jsonl.py
                       |
                       v
                  JSONL corpus
                       |
                       v
             ingest_documents.py
                       |
                       v
             PostgreSQL + pgvector
                       |
                       v
          semantic / hybrid retrieval
                       |
                       v
                      LLM
                       |
                       v
            Frontend chat + sources
```

HTML и DOCX напрямую не индексируются. Сначала конвертер приводит их к единому JSONL-формату, затем ingestion создаёт записи документов и фрагментов, вычисляет embeddings и сохраняет их в pgvector.

## Структура проекта

```text
lawyerchat/
├── backend/
│   ├── app/
│   │   ├── api/          # HTTP endpoints
│   │   ├── llm/          # клиент LLM и сборка RAG-ответа
│   │   ├── models/       # модели SQLAlchemy
│   │   ├── rag/          # ingestion, embeddings и retrieval
│   │   ├── schemas/      # схемы Pydantic
│   │   ├── config.py
│   │   ├── db.py
│   │   └── main.py
│   ├── data/
│   │   ├── raw_html/     # исходные HTML/HTM
│   │   ├── raw_docx/     # исходные DOCX
│   │   ├── legal_docs/   # готовый JSONL-корпус
│   │   └── evaluation/   # контрольные вопросы
│   ├── scripts/
│   │   ├── convert_html_to_jsonl.py
│   │   ├── convert_docx_to_jsonl.py
│   │   ├── ingest_documents.py
│   │   ├── inspect_chunks.py
│   │   └── evaluate_retrieval.py
│   ├── reports/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── docker/
│   └── postgres/
│       └── init.sql
└── docker-compose.yml
```

## Технологический стек

- **Backend:** Python, FastAPI, Uvicorn, SQLAlchemy, Pydantic.
- **База данных:** PostgreSQL 16, pgvector.
- **NLP/RAG:** `sentence-transformers`, semantic search, hybrid search.
- **LLM:** OpenAI-compatible клиент и DeepSeek API.
- **Frontend:** HTML, CSS, JavaScript, `localStorage`; без React, Vite и npm.
- **Документы:** BeautifulSoup/lxml для HTML, `python-docx` для DOCX, JSONL как промежуточный формат.

## Быстрый запуск

Команды ниже предназначены для Windows PowerShell.

### 1. PostgreSQL

Из корня проекта:

```powershell
cd C:\Users\Gleb\law_chat\lawyerchat
docker compose up -d postgres
docker ps
```

Контейнер `legal_rag_postgres` публикует PostgreSQL на порту `5433` хоста.

### 2. Окружение backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Если виртуальное окружение проекта называется `venv`, используйте:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Переменные окружения

Создайте `backend/.env`:

```dotenv
DATABASE_URL=postgresql+psycopg2://legal_user:legal_password@localhost:5433/legal_rag

EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
TOP_K=5

RETRIEVAL_MODE=hybrid
HYBRID_SEMANTIC_WEIGHT=0.60
HYBRID_KEYWORD_WEIGHT=0.30
HYBRID_METADATA_WEIGHT=0.10

LLM_PROVIDER=deepseek
LLM_API_KEY=...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-v4-flash
LLM_TEMPERATURE=0.2
```

`DATABASE_URL` обязателен. Остальные переменные имеют показанные значения по умолчанию. Имена соответствуют `backend/app/config.py`.

Файл `.env` не должен попадать в Git. API-ключ LLM хранится только на backend и не передаётся во frontend или `localStorage`.

### 4. Подготовка и индексация корпуса

Поместите исходные документы в `backend/data/raw_html/` и/или `backend/data/raw_docx/`, преобразуйте их в JSONL, затем из папки `backend` запустите:

```powershell
python -m scripts.ingest_documents
```

Подробнее конвертация описана в разделе [Подготовка корпуса](#подготовка-корпуса).

### 5. Backend

Из папки `backend`:

```powershell
python -m uvicorn app.main:app --reload
```

После запуска доступны:

- health check: <http://localhost:8000/health>;
- Swagger UI: <http://localhost:8000/docs>.

При старте backend создаёт таблицы, но не запускает ingestion автоматически.

### 6. Frontend

В отдельном окне PowerShell из корня проекта:

```powershell
cd frontend
python -m http.server 3000
```

Откройте <http://localhost:3000>. Frontend обращается к backend по адресу `http://localhost:8000`.

## Подготовка корпуса

`raw_html` и `raw_docx` содержат исходные документы. `legal_docs` содержит готовые JSONL-файлы; именно они являются основным форматом для индексации. Код также читает legacy-файлы `.txt`, но для нормативного корпуса рекомендуется JSONL, сохраняющий структуру документа.

### HTML/HTM → JSONL

Исходные файлы:

```text
backend/data/raw_html/
```

Один файл, из папки `backend`:

```powershell
python -m scripts.convert_html_to_jsonl `
  --input "data/raw_html/Трудовой кодекс Российской Федерации.htm" `
  --output "data/legal_docs/trudovoy_kodeks_rf.jsonl" `
  --document-id "tk_rf" `
  --document-title "Трудовой кодекс Российской Федерации"
```

Вся папка:

```powershell
python -m scripts.convert_html_to_jsonl `
  --input-dir "data/raw_html" `
  --output-dir "data/legal_docs"
```

### DOCX → JSONL

Исходные файлы:

```text
backend/data/raw_docx/
```

Один файл, из папки `backend`:

```powershell
python -m scripts.convert_docx_to_jsonl `
  --input "data/raw_docx/Семейный кодекс Российской Федерации.docx" `
  --output "data/legal_docs/semeynyy_kodeks_rf.jsonl" `
  --document-id "sk_rf" `
  --document-title "Семейный кодекс Российской Федерации"
```

Вся папка:

```powershell
python -m scripts.convert_docx_to_jsonl `
  --input-dir "data/raw_docx" `
  --output-dir "data/legal_docs"
```

Конвертеры выделяют структуру нормативного акта и записывают каждую статью отдельной строкой JSONL.

## Индексация документов

Из папки `backend`:

```powershell
python -m scripts.ingest_documents
```

Скрипт:

1. читает `.jsonl` и legacy `.txt` из `data/legal_docs`;
2. создаёт записи `documents` и `chunks`;
3. вычисляет embeddings по текстам фрагментов;
4. сохраняет embeddings в PostgreSQL + pgvector.

Повторную индексацию можно также запустить через `POST /api/documents/reindex` при работающем backend.

## API

### `GET /health`

Проверяет доступность backend, соединение с базой данных и расширение pgvector.

### `POST /api/chat`

Основной endpoint чата. Принимает `query`, `top_k` и необязательный `retrieval_mode`, выполняет retrieval, формирует ответ через LLM и возвращает `answer`, `sources` и фактически использованный режим поиска.

Пример тела запроса:

```json
{
  "query": "Какие основания для увольнения работника?",
  "top_k": 5,
  "retrieval_mode": "hybrid"
}
```

### `POST /api/search`

Технический поиск по корпусу без генерации ответа LLM. Возвращает фрагменты и scores, используемые для анализа retrieval. Принимает те же `query`, `top_k` и необязательный `retrieval_mode`.

### `GET /api/documents`

Возвращает список документов в базе и количество их фрагментов.

### `GET /api/documents/{document_id}/chunks`

Возвращает упорядоченный список фрагментов выбранного документа.

### `POST /api/documents/reindex`

Повторно запускает индексацию файлов из `backend/data/legal_docs`.

## Режимы retrieval

### Semantic

Вопрос преобразуется в embedding, после чего pgvector ищет ближайшие chunks по косинусному расстоянию. Режим полезен для вопросов, переформулированных относительно текста закона.

### Hybrid

Гибридный поиск объединяет:

- semantic search через pgvector;
- PostgreSQL full-text search с русской конфигурацией;
- metadata boosts для номера статьи и названия документа.

Такой режим лучше учитывает точные юридические формулировки, номера статей и названия законов. Веса компонентов задаются переменными `HYBRID_SEMANTIC_WEIGHT`, `HYBRID_KEYWORD_WEIGHT` и `HYBRID_METADATA_WEIGHT`.

Режим по умолчанию задаёт `RETRIEVAL_MODE`. Запросы `/api/chat` и `/api/search` могут переопределить его полем `retrieval_mode`. Во frontend по умолчанию выбран `hybrid`; пользователь может переключаться между `semantic` и `hybrid`.

## Embedding model

Текущая baseline-модель:

```dotenv
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Она формирует векторы размерности 384, а модель данных содержит колонку `vector(384)`. Через `EMBEDDING_MODEL_NAME` можно выбрать другую модель `sentence-transformers`, возвращающую вектор той же размерности.

Текущая реализация не содержит переменных `EMBEDDING_DIMENSION` и `EMBEDDING_MODEL_TYPE` и не добавляет E5-префиксы `query:`/`passage:`. Для модели другой размерности необходимо изменить размерность в модели `Chunk`, пересоздать базу и заново выполнить `python -m scripts.ingest_documents`. Смена модели при сохранении размерности также требует полной переиндексации.

## Локальная история диалога

Frontend хранит в `localStorage` до 100 последних сообщений:

- вопросы пользователя;
- ответы ассистента;
- показанные источники;
- режим retrieval для ответов ассистента.

История восстанавливается после перезагрузки страницы и удаляется кнопкой «Очистить историю». Она относится только к текущему браузеру и исчезает при очистке его данных.

В `localStorage` не сохраняются API-ключи, технические scores или серверные данные. История не отправляется на сервер как история диалога; backend получает только текущий вопрос и параметры поиска.

## Тестирование retrieval

Контрольные вопросы находятся в:

```text
backend/data/evaluation/retrieval_cases.json
```

Evaluation не вызывает LLM: он проверяет результаты поиска в PostgreSQL + pgvector.

Semantic, из папки `backend`:

```powershell
python -m scripts.evaluate_retrieval `
  --cases "data/evaluation/retrieval_cases.json" `
  --top-k 20 `
  --mode semantic `
  --output-dir "reports/semantic"
```

Hybrid:

```powershell
python -m scripts.evaluate_retrieval `
  --cases "data/evaluation/retrieval_cases.json" `
  --top-k 20 `
  --mode hybrid `
  --output-dir "reports/hybrid"
```

Отдельного скрипта автоматического сравнения режимов в проекте нет; результаты находятся в соответствующих каталогах отчётов.

### Метрики

- **Recall@K / Top-K accuracy** — доля вопросов, для которых ожидаемая статья попала в первые K результатов.
- **MRR** — учитывает позицию первого правильного результата.
- **Mean Rank** — средняя позиция первого правильного результата среди вопросов, где он найден.
- **Document Recall@5** — доля вопросов, для которых нужный нормативный акт попал в первые пять результатов независимо от совпадения статьи.
- **Wrong Document@1** — доля вопросов, где первым оказался документ не из ожидаемого закона.

В `expected_sources` источники делятся на `primary`, `secondary` и `acceptable`. Первые два уровня считаются полным совпадением; `acceptable` отмечается как `partial_match` и не увеличивает Recall@K или MRR.

### Отчёты

В указанном `--output-dir` создаются:

```text
retrieval_report.md
retrieval_report.docx
retrieval_results.csv
retrieval_results.json
```

Например, hybrid-отчёты сохраняются в `backend/reports/hybrid/`.

## Unit tests

Из папки `backend`:

```powershell
python -m unittest discover -s tests
```

Тесты используют стандартный модуль `unittest`; pytest в проекте не требуется.

## Типовой workflow

1. Запустить PostgreSQL.
2. Создать или активировать виртуальное окружение и установить зависимости.
3. Настроить `backend/.env`.
4. Положить HTML/HTM и DOCX в `raw_html` и `raw_docx`.
5. Конвертировать документы в JSONL.
6. Запустить ingestion.
7. Запустить backend.
8. Запустить frontend.
9. Задать вопрос и проверить ответ по показанным источникам.
10. При необходимости запустить retrieval evaluation.

## Troubleshooting

### PowerShell не находит activate

Используйте путь, соответствующий имени окружения:

```powershell
.\.venv\Scripts\Activate.ps1
# или
.\venv\Scripts\Activate.ps1
```

Если PowerShell блокирует скрипты, разрешите их только для текущего процесса:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

### Backend не подключается к PostgreSQL

Проверьте `docker ps` и `DATABASE_URL`. При локальном запуске backend контейнер PostgreSQL доступен на `localhost:5433`, а не на стандартном порту `5432`.

### Frontend не получает ответ

Проверьте <http://localhost:8000/health> и убедитесь, что backend запущен именно на порту `8000`.

### В ответе нет источников

Проверьте наличие JSONL в `backend/data/legal_docs` и выполните:

```powershell
python -m scripts.ingest_documents
```

### Документы дублируются или устарели

Проверьте содержимое `backend/data/legal_docs`, удалите ненужные старые JSONL и заново выполните ingestion.

### Изменилась embedding model или размерность

После смены модели требуется полная переиндексация. Размерность схемы сейчас фиксирована как 384; модель с другой размерностью несовместима без изменения модели данных и пересоздания базы.
