const API_BASE_URL = "http://localhost:8000";

const healthButton = document.getElementById("healthButton");
const healthStatus = document.getElementById("healthStatus");
const healthDetails = document.getElementById("healthDetails");

const documentsButton = document.getElementById("documentsButton");
const reindexButton = document.getElementById("reindexButton");
const documentsStatus = document.getElementById("documentsStatus");
const reindexResult = document.getElementById("reindexResult");
const documentsList = document.getElementById("documentsList");

const searchForm = document.getElementById("searchForm");
const queryInput = document.getElementById("queryInput");
const topKInput = document.getElementById("topKInput");
const modeInputs = document.querySelectorAll('input[name="answerMode"]');
const searchButton = document.getElementById("searchButton");
const resultsTitle = document.getElementById("results-title");
const resultsDescription = document.getElementById("resultsDescription");
const searchStatus = document.getElementById("searchStatus");
const searchMeta = document.getElementById("searchMeta");
const resultsList = document.getElementById("resultsList");

async function apiRequest(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });
  } catch (error) {
    throw new Error("Backend недоступен. Проверьте, что сервер запущен на http://localhost:8000");
  }

  if (!response.ok) {
    const errorText = await response.text();
    const error = new Error(`HTTP ${response.status}${errorText ? `: ${errorText}` : ""}`);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function setMessage(element, message, isError = false) {
  element.textContent = message;
  element.classList.toggle("error", isError);
  element.classList.toggle("muted", !isError);
}

function clearElement(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function appendTextRow(container, label, value) {
  if (value === undefined || value === null || value === "") {
    return;
  }

  const row = document.createElement("div");
  const labelEl = document.createElement("dt");
  const valueEl = document.createElement("dd");

  labelEl.textContent = label;
  valueEl.textContent = value;

  row.append(labelEl, valueEl);
  container.appendChild(row);
}

function appendSummaryRow(container, label, value) {
  if (value === undefined || value === null || value === "") {
    return;
  }

  const row = document.createElement("div");
  row.className = "summary-row";

  const labelEl = document.createElement("div");
  labelEl.className = "summary-label";
  labelEl.textContent = label;

  const valueEl = document.createElement("div");
  valueEl.className = "summary-value";
  valueEl.textContent = Array.isArray(value) ? formatArray(value) : value;

  row.append(labelEl, valueEl);
  container.appendChild(row);
}

function formatBoolean(value) {
  if (value === true) {
    return "доступна";
  }

  if (value === false) {
    return "недоступна";
  }

  return value ?? "нет данных";
}

function formatDate(value) {
  if (!value) {
    return "дата не указана";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("ru-RU", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatNumber(value, digits = 6) {
  if (value === undefined || value === null || value === "") {
    return null;
  }

  const number = Number(value);
  if (Number.isNaN(number)) {
    return String(value);
  }

  return number.toFixed(digits).replace(/0+$/, "").replace(/\.$/, "");
}

function formatArray(value) {
  if (!value.length) {
    return "нет";
  }

  return value.join(", ");
}

function normalizeTopK(value) {
  const number = Number.parseInt(value, 10);

  if (Number.isNaN(number)) {
    return 5;
  }

  return Math.min(20, Math.max(1, number));
}

function getSelectedMode() {
  const selected = document.querySelector('input[name="answerMode"]:checked');
  return selected?.value === "chat" ? "chat" : "retrieval";
}

function updateSearchModeText() {
  const mode = getSelectedMode();

  if (mode === "chat") {
    searchButton.textContent = "Сформировать ответ";
    resultsTitle.textContent = "Ответ системы";
    resultsDescription.textContent = "Ответ сформирован на основе найденных фрагментов и не является юридической консультацией.";
    return;
  }

  searchButton.textContent = "Найти фрагменты";
  resultsTitle.textContent = "Найденные фрагменты";
  resultsDescription.textContent = "Фрагменты отображаются без генерации ответа.";
}

async function checkHealth() {
  healthButton.disabled = true;
  healthDetails.hidden = true;
  clearElement(healthDetails);
  setMessage(healthStatus, "Проверяем систему...");

  try {
    const data = await apiRequest("/health");

    appendTextRow(healthDetails, "status", data?.status ?? "нет данных");
    appendTextRow(healthDetails, "database", formatBoolean(data?.database));
    appendTextRow(healthDetails, "pgvector", formatBoolean(data?.pgvector));

    healthDetails.hidden = false;
    setMessage(healthStatus, "Система ответила успешно.");
  } catch (error) {
    setMessage(healthStatus, error.message, true);
  } finally {
    healthButton.disabled = false;
  }
}

async function loadDocuments() {
  documentsButton.disabled = true;
  clearElement(documentsList);
  setMessage(documentsStatus, "Загружаем документы...");

  try {
    const documents = await apiRequest("/api/documents");
    renderDocuments(Array.isArray(documents) ? documents : []);
  } catch (error) {
    setMessage(documentsStatus, error.message, true);
  } finally {
    documentsButton.disabled = false;
  }
}

async function reindexDocuments() {
  reindexButton.disabled = true;
  reindexButton.textContent = "Идет индексация...";
  reindexResult.hidden = true;
  clearElement(reindexResult);
  setMessage(documentsStatus, "Переиндексируем документы...");

  try {
    const result = await apiRequest("/api/documents/reindex", {
      method: "POST"
    });

    renderReindexResult(result || {});
    setMessage(documentsStatus, "Индексация завершена.");
    await loadDocuments();
  } catch (error) {
    setMessage(documentsStatus, error.message, true);
  } finally {
    reindexButton.disabled = false;
    reindexButton.textContent = "Переиндексировать документы";
  }
}

function renderDocuments(documents) {
  clearElement(documentsList);

  if (!documents.length) {
    setMessage(documentsStatus, "Документы пока не проиндексированы");
    return;
  }

  setMessage(documentsStatus, `Документов найдено: ${documents.length}.`);

  documents.forEach((documentItem) => {
    const card = document.createElement("article");
    card.className = "card";

    const header = document.createElement("div");
    header.className = "card-header";

    const titleBlock = document.createElement("div");
    const title = document.createElement("h3");
    title.className = "card-title";
    title.textContent = documentItem.filename || "Документ без имени";
    titleBlock.appendChild(title);

    if (documentItem.title) {
      const documentTitle = document.createElement("div");
      documentTitle.className = "card-meta";
      documentTitle.textContent = documentItem.title;
      titleBlock.appendChild(documentTitle);
    }

    const chunksBadge = document.createElement("span");
    chunksBadge.className = "badge";
    chunksBadge.textContent = `Фрагментов: ${documentItem.chunks_count ?? 0}`;

    header.append(titleBlock, chunksBadge);

    const meta = document.createElement("div");
    meta.className = "card-meta";

    const date = document.createElement("span");
    date.textContent = `Дата: ${formatDate(documentItem.updated_at || documentItem.created_at)}`;
    meta.appendChild(date);

    const chunksButton = document.createElement("button");
    chunksButton.type = "button";
    chunksButton.className = "secondary";
    chunksButton.textContent = "Показать фрагменты";

    const chunksContainer = document.createElement("div");
    chunksContainer.className = "compact-list";
    chunksContainer.hidden = true;

    chunksButton.addEventListener("click", () => toggleDocumentChunks(documentItem, chunksButton, chunksContainer));

    card.append(header, meta, chunksButton, chunksContainer);
    documentsList.appendChild(card);
  });
}

function renderReindexResult(result) {
  clearElement(reindexResult);

  appendSummaryRow(reindexResult, "files_found", result.files_found);
  appendSummaryRow(reindexResult, "files_processed", result.files_processed);
  appendSummaryRow(reindexResult, "documents_created", result.documents_created);
  appendSummaryRow(reindexResult, "chunks_created", result.chunks_created);
  appendSummaryRow(reindexResult, "skipped_files", result.skipped_files);
  appendSummaryRow(reindexResult, "processed_files", result.processed_files);
  appendSummaryRow(reindexResult, "message", result.message);

  reindexResult.hidden = false;
}

async function toggleDocumentChunks(documentItem, button, container) {
  if (!container.hidden) {
    container.hidden = true;
    button.textContent = "Показать фрагменты";
    return;
  }

  button.disabled = true;
  button.textContent = "Загружаем...";
  clearElement(container);

  try {
    const chunks = await apiRequest(`/api/documents/${documentItem.id}/chunks`);
    renderDocumentChunks(Array.isArray(chunks) ? chunks : [], container);
    container.hidden = false;
    button.textContent = "Скрыть фрагменты";
  } catch (error) {
    const errorEl = document.createElement("div");
    errorEl.className = "message error";
    errorEl.textContent = error.message;
    container.appendChild(errorEl);
    container.hidden = false;
    button.textContent = "Показать фрагменты";
  } finally {
    button.disabled = false;
  }
}

function renderDocumentChunks(chunks, container) {
  clearElement(container);

  if (!chunks.length) {
    const empty = document.createElement("div");
    empty.className = "message muted";
    empty.textContent = "Фрагменты для документа не найдены.";
    container.appendChild(empty);
    return;
  }

  chunks.forEach((chunk) => {
    const chunkCard = document.createElement("div");
    chunkCard.className = "chunk-card";

    const title = document.createElement("p");
    title.className = "chunk-title";
    title.textContent = `Фрагмент #${chunk.chunk_index ?? "без номера"}`;
    chunkCard.appendChild(title);

    if (chunk.article_number) {
      const articleNumber = document.createElement("div");
      articleNumber.className = "card-meta";
      articleNumber.textContent = `Статья: ${chunk.article_number}`;
      chunkCard.appendChild(articleNumber);
    }

    if (chunk.article_title) {
      const articleTitle = document.createElement("div");
      articleTitle.className = "card-meta";
      articleTitle.textContent = chunk.article_title;
      chunkCard.appendChild(articleTitle);
    }

    const content = document.createElement("div");
    content.className = "content";
    content.textContent = chunk.content || "";
    chunkCard.appendChild(content);

    container.appendChild(chunkCard);
  });
}

async function searchDocuments(event) {
  event.preventDefault();

  const query = queryInput.value.trim();
  const topK = normalizeTopK(topKInput.value);
  const mode = getSelectedMode();
  topKInput.value = topK;

  clearElement(resultsList);
  searchMeta.hidden = true;
  clearElement(searchMeta);

  if (!query) {
    setMessage(searchStatus, "Введите вопрос для поиска.", true);
    queryInput.focus();
    return;
  }

  searchButton.disabled = true;
  setMessage(
    searchStatus,
    mode === "chat" ? "Формируем ответ на основе найденных фрагментов..." : "Ищем фрагменты..."
  );

  try {
    const endpoint = mode === "chat" ? "/api/chat" : "/api/search";
    const data = await apiRequest(endpoint, {
      method: "POST",
      body: JSON.stringify({
        query,
        top_k: topK
      })
    });

    if (mode === "chat") {
      renderChatAnswer(data || {});
    } else {
      renderSearchResults(data || {});
    }
  } catch (error) {
    if (mode === "chat" && error.status === 503) {
      setMessage(searchStatus, "LLM не настроена. Проверьте LLM_API_KEY в backend/.env", true);
    } else {
      setMessage(searchStatus, error.message, true);
    }
  } finally {
    searchButton.disabled = false;
    updateSearchModeText();
  }
}

function renderSearchResults(data) {
  clearElement(resultsList);
  clearElement(searchMeta);

  const results = Array.isArray(data.results) ? data.results : [];

  appendSummaryRow(searchMeta, "note", data.note);
  appendSummaryRow(searchMeta, "total_results", data.total_results ?? results.length);
  searchMeta.hidden = false;

  if (!results.length) {
    setMessage(searchStatus, "По вашему запросу фрагменты не найдены.");
    return;
  }

  setMessage(searchStatus, `Найдено фрагментов: ${data.total_results ?? results.length}.`);

  results.forEach((item) => {
    const card = document.createElement("article");
    card.className = "card";

    const header = document.createElement("div");
    header.className = "card-header";

    const titleBlock = document.createElement("div");
    const title = document.createElement("h3");
    title.className = "card-title";
    title.textContent = item.filename || "Документ без имени";
    titleBlock.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "card-meta";
    appendInlineMeta(meta, `Фрагмент #${item.chunk_index ?? "без номера"}`);

    if (item.article_number) {
      appendInlineMeta(meta, `Статья: ${item.article_number}`);
    }

    if (item.article_title) {
      appendInlineMeta(meta, item.article_title);
    }

    titleBlock.appendChild(meta);

    const metrics = document.createElement("div");
    metrics.className = "card-meta";

    const similarity = formatNumber(item.similarity, 6);
    const distance = formatNumber(item.distance, 6);

    if (similarity !== null) {
      appendInlineMeta(metrics, `similarity: ${similarity}`);
    }

    if (distance !== null) {
      appendInlineMeta(metrics, `distance: ${distance}`);
    }

    header.append(titleBlock, metrics);

    const content = document.createElement("div");
    content.className = "content";
    content.textContent = item.content || "";

    card.append(header, content);
    resultsList.appendChild(card);
  });
}

function renderChatAnswer(data) {
  clearElement(resultsList);
  clearElement(searchMeta);

  const sources = Array.isArray(data.sources) ? data.sources : [];

  appendSummaryRow(searchMeta, "total_sources", data.total_sources ?? sources.length);
  searchMeta.hidden = false;

  const answerCard = document.createElement("article");
  answerCard.className = "card answer-card";

  const answerTitle = document.createElement("h3");
  answerTitle.className = "card-title";
  answerTitle.textContent = "Ответ";

  const answerContent = document.createElement("div");
  answerContent.className = "answer-content";
  answerContent.textContent = data.answer || "Backend вернул пустой ответ.";

  answerCard.append(answerTitle, answerContent);
  resultsList.appendChild(answerCard);

  const sourcesTitle = document.createElement("h3");
  sourcesTitle.className = "sources-title";
  sourcesTitle.textContent = "Источники";
  resultsList.appendChild(sourcesTitle);

  if (!sources.length) {
    const empty = document.createElement("div");
    empty.className = "message muted";
    empty.textContent = "Источники не найдены.";
    resultsList.appendChild(empty);
    setMessage(searchStatus, "Ответ сформирован без источников.");
    return;
  }

  setMessage(searchStatus, `Ответ сформирован. Источников: ${data.total_sources ?? sources.length}.`);

  sources.forEach((source) => {
    const card = document.createElement("article");
    card.className = "card source-card";

    const title = document.createElement("h4");
    title.className = "card-title";
    title.textContent = source.filename || "Документ без имени";
    card.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "card-meta source-meta";

    appendInlineMeta(meta, `Фрагмент #${source.chunk_index ?? "без номера"}`);

    if (source.article_number) {
      appendInlineMeta(meta, `Статья: ${source.article_number}`);
    }

    if (source.article_title) {
      appendInlineMeta(meta, source.article_title);
    }

    if (Array.isArray(source.referenced_articles) && source.referenced_articles.length) {
      appendInlineMeta(meta, `Связанные статьи: ${source.referenced_articles.join(", ")}`);
    }

    card.appendChild(meta);
    resultsList.appendChild(card);
  });
}

function appendInlineMeta(container, value) {
  const item = document.createElement("span");
  item.textContent = value;
  container.appendChild(item);
}

healthButton.addEventListener("click", checkHealth);
documentsButton.addEventListener("click", loadDocuments);
reindexButton.addEventListener("click", reindexDocuments);
searchForm.addEventListener("submit", searchDocuments);
modeInputs.forEach((input) => input.addEventListener("change", updateSearchModeText));
updateSearchModeText();
