# Исходные HTML/HTM документы

Сюда вручную кладутся исходные `.htm` и `.html` документы, сохраненные из КонсультантПлюс.

Эти файлы не индексируются напрямую. Перед индексацией их нужно преобразовать в структурированный JSONL:

```bash
python -m scripts.convert_html_to_jsonl --input-dir "data/raw_html" --output-dir "data/legal_docs"
```

После конвертации запустите обычную индексацию:

```bash
python -m scripts.ingest_documents
```
