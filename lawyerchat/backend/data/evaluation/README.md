# Контрольные вопросы retrieval

`retrieval_cases.json` содержит 60 автоматически оцениваемых вопросов — по 10 вопросов для каждого из шести законов — и отдельные out-of-scope кейсы для локальной оценки semantic- и hybrid-поиска LawyerChat без участия LLM.

Каждый кейс задает:

- уникальный `id`;
- название закона;
- вопрос пользователя;
- `question_type` и `difficulty`;
- массив `expected_sources` с документом, статьёй, уровнем релевантности и пояснением;
- комментарий для ручной проверки.

Источники `primary` и `secondary` засчитываются в Recall@K и MRR. Источник `acceptable` фиксируется как частичное совпадение, но не считается полноценным retrieval-успехом. Старый формат `expected_article_numbers` остаётся совместимым.

Out-of-scope кейсы задаются через `case_type: "out_of_scope"` и `expected_behavior: "no_answer"`. Они выводятся в отдельном разделе отчёта, но пока не оцениваются автоматически.

Запуск из папки `backend`:

```powershell
python -m scripts.evaluate_retrieval `
  --cases "data/evaluation/retrieval_cases.json" `
  --top-k 20 `
  --mode semantic `
  --output-dir "reports/semantic"
```

Для hybrid-режима укажите `--mode hybrid --output-dir "reports/hybrid"`. Если задать меньшую глубину, метрики выше `top_k` будут отмечены как не рассчитанные. CSV, JSON, Markdown и DOCX-отчёты сохраняются в выбранной папке.
