# Исходные DOCX-документы

Сюда вручную кладутся исходные `.docx` документы, сохраненные из КонсультантПлюс.

DOCX-файлы не индексируются напрямую. Перед индексацией их нужно преобразовать в структурированный JSONL:

```bash
python -m scripts.convert_docx_to_jsonl --input-dir "data/raw_docx" --output-dir "data/legal_docs"
```

Готовые JSONL-файлы сохраняются в `backend/data/legal_docs/`. После конвертации запустите общую индексацию:

```bash
python -m scripts.ingest_documents
```
