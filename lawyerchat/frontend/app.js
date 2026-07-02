const API_BASE_URL = "http://localhost:8000";
const CHAT_HISTORY_STORAGE_KEY = "lawyerchat.chatHistory.v1";
const MAX_CHAT_HISTORY_MESSAGES = 100;
const WELCOME_MESSAGE =
  "Здравствуйте. Задайте вопрос по загруженным нормативным документам, и я отвечу по найденному контексту.";

let chatHistory = [];

const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const topKInput = document.getElementById("topKInput");
const sendButton = document.getElementById("sendButton");
const chatMessages = document.getElementById("chatMessages");
const clearChatHistoryButton = document.getElementById("clear-chat-history-button");
const retrievalModeSelect = document.getElementById("retrieval-mode-select");

const openSearchPanel = document.getElementById("openSearchPanel");
const closeSearchPanel = document.getElementById("closeSearchPanel");
const searchPanel = document.getElementById("searchPanel");
const technicalSearchForm = document.getElementById("technicalSearchForm");
const technicalQueryInput = document.getElementById("technicalQueryInput");
const technicalTopKInput = document.getElementById("technicalTopKInput");
const technicalSearchButton = document.getElementById("technicalSearchButton");
const technicalStatus = document.getElementById("technicalStatus");
const technicalResults = document.getElementById("technicalResults");

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

  return response.status === 204 ? null : response.json();
}

function clearElement(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}

function createMessageId() {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function sanitizeHistorySource(source) {
  if (!source || typeof source !== "object" || Array.isArray(source)) {
    return null;
  }

  const allowedFields = [
    "document_title",
    "filename",
    "source_filename",
    "section_title",
    "subsection_title",
    "chapter_title",
    "paragraph_title",
    "article_number",
    "article_title"
  ];
  const sanitized = {};

  allowedFields.forEach((field) => {
    const value = source[field];
    if (typeof value === "string" || typeof value === "number") {
      sanitized[field] = value;
    }
  });

  return Object.keys(sanitized).length ? sanitized : null;
}

function normalizeRetrievalMode(value, fallback = null) {
  if (value === "semantic" || value === "hybrid") {
    return value;
  }
  return fallback;
}

function selectedRetrievalMode() {
  return normalizeRetrievalMode(retrievalModeSelect?.value, "hybrid");
}

function retrievalModeLabel(mode) {
  return mode === "semantic" ? "семантический" : "гибридный";
}

function createHistoryMessage(
  role,
  content,
  sources = [],
  retrievalMode = null
) {
  const normalizedRole = role === "assistant" ? "assistant" : "user";
  const normalizedSources =
    normalizedRole === "assistant" && Array.isArray(sources)
      ? sources.map(sanitizeHistorySource).filter(Boolean)
      : [];

  const message = {
    id: createMessageId(),
    role: normalizedRole,
    content: String(content ?? ""),
    sources: normalizedSources,
    createdAt: new Date().toISOString()
  };

  const normalizedMode = normalizeRetrievalMode(retrievalMode);
  if (normalizedRole === "assistant" && normalizedMode) {
    message.retrievalMode = normalizedMode;
  }

  return message;
}

function saveChatHistory() {
  chatHistory = chatHistory.slice(-MAX_CHAT_HISTORY_MESSAGES);

  try {
    localStorage.setItem(
      CHAT_HISTORY_STORAGE_KEY,
      JSON.stringify(chatHistory)
    );
  } catch (error) {
    // localStorage может быть отключён политикой браузера или переполнен.
  }
}

function loadChatHistory() {
  chatHistory = [];

  try {
    const storedHistory = localStorage.getItem(CHAT_HISTORY_STORAGE_KEY);
    if (!storedHistory) {
      return;
    }

    const parsedHistory = JSON.parse(storedHistory);
    if (!Array.isArray(parsedHistory)) {
      throw new Error("Invalid chat history format");
    }

    chatHistory = parsedHistory
      .filter(
        (message) =>
          message &&
          typeof message === "object" &&
          (message.role === "user" || message.role === "assistant") &&
          typeof message.content === "string"
      )
      .map((message) => {
        const normalized = createHistoryMessage(
          message.role,
          message.content,
          message.sources,
          message.retrievalMode
        );

        if (typeof message.id === "string" && message.id) {
          normalized.id = message.id;
        }
        if (typeof message.createdAt === "string" && message.createdAt) {
          normalized.createdAt = message.createdAt;
        }

        return normalized;
      })
      .slice(-MAX_CHAT_HISTORY_MESSAGES);

    if (parsedHistory.length > MAX_CHAT_HISTORY_MESSAGES) {
      saveChatHistory();
    }
  } catch (error) {
    chatHistory = [];
    try {
      localStorage.removeItem(CHAT_HISTORY_STORAGE_KEY);
    } catch (storageError) {
      // Приложение продолжает работать, даже если localStorage недоступен.
    }
  }
}

function addMessageToHistory(message) {
  if (!message || !["user", "assistant"].includes(message.role)) {
    return;
  }

  chatHistory.push(
    createHistoryMessage(
      message.role,
      message.content,
      message.sources,
      message.retrievalMode
    )
  );
  chatHistory = chatHistory.slice(-MAX_CHAT_HISTORY_MESSAGES);
}

function normalizeTopK(value) {
  const number = Number.parseInt(value, 10);
  if (Number.isNaN(number)) {
    return 5;
  }
  return Math.min(20, Math.max(1, number));
}

function formatNumber(value, digits = 4) {
  if (value === undefined || value === null || value === "") {
    return null;
  }

  const number = Number(value);
  if (Number.isNaN(number)) {
    return String(value);
  }

  return number.toFixed(digits).replace(/0+$/, "").replace(/\.$/, "");
}

function appendMessage(role, text, options = {}) {
  const row = document.createElement("article");
  row.className = `message-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  if (options.loading) {
    bubble.classList.add("loading");
  }
  if (options.error) {
    bubble.classList.add("error");
  }

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.appendChild(paragraph);
  row.appendChild(bubble);
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return row;
}

function replaceMessage(row, role, text, options = {}) {
  row.className = `message-row ${role}`;
  clearElement(row);

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  if (options.error) {
    bubble.classList.add("error");
  }

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.appendChild(paragraph);
  row.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function knownDocumentName(value) {
  if (!value) {
    return null;
  }

  const normalized = String(value).toLowerCase();
  if (normalized.includes("tk_rf") || normalized.includes("trud")) {
    return "Трудовой кодекс Российской Федерации";
  }
  if (normalized.includes("uk_rf") || normalized.includes("ugol")) {
    return "Уголовный кодекс Российской Федерации";
  }
  if (normalized.includes("gk_rf") || normalized.includes("grazhd")) {
    return "Гражданский кодекс Российской Федерации";
  }
  if (normalized.includes("nk_rf") || normalized.includes("nalog")) {
    return "Налоговый кодекс Российской Федерации";
  }

  return null;
}

function sourceDocumentTitle(source) {
  return (
    source.document_title ||
    knownDocumentName(source.filename) ||
    knownDocumentName(source.source_filename) ||
    "Нормативный документ"
  );
}

function articleLabel(source) {
  if (!source.article_number && !source.article_title) {
    return null;
  }

  if (source.article_number && source.article_title) {
    return `Статья ${source.article_number}. ${source.article_title}`;
  }

  if (source.article_number) {
    return `Статья ${source.article_number}`;
  }

  return source.article_title;
}

function appendSourceLine(container, value) {
  if (!value) {
    return;
  }

  const line = document.createElement("div");
  line.textContent = value;
  container.appendChild(line);
}

function renderSources(sources, hostRow) {
  const block = document.createElement("div");
  block.className = "sources-block";

  const title = document.createElement("h3");
  title.className = "sources-title";
  title.textContent = "Использованные нормы";
  block.appendChild(title);

  if (!sources.length) {
    const empty = document.createElement("div");
    empty.className = "source-card";
    empty.textContent = "Источники не найдены.";
    block.appendChild(empty);
    hostRow.appendChild(block);
    return;
  }

  sources.forEach((source) => {
    const card = document.createElement("article");
    card.className = "source-card";

    const documentTitle = document.createElement("strong");
    documentTitle.textContent = sourceDocumentTitle(source);
    card.appendChild(documentTitle);

    appendSourceLine(card, source.section_title);
    appendSourceLine(card, source.subsection_title);
    appendSourceLine(card, source.chapter_title);
    appendSourceLine(card, source.paragraph_title);
    appendSourceLine(card, articleLabel(source));

    block.appendChild(card);
  });

  hostRow.appendChild(block);
}

function renderRetrievalMode(mode, hostRow) {
  const normalizedMode = normalizeRetrievalMode(mode);
  if (!normalizedMode) {
    return;
  }

  const note = document.createElement("div");
  note.className = "retrieval-mode-note";
  note.textContent = `Режим поиска: ${retrievalModeLabel(normalizedMode)}`;
  hostRow.appendChild(note);
}

function renderChatMessage(message) {
  const row = appendMessage(message.role, message.content);
  if (message.role === "assistant") {
    renderRetrievalMode(message.retrievalMode, row);
    renderSources(Array.isArray(message.sources) ? message.sources : [], row);
  }
  return row;
}

function restoreChatHistory() {
  if (!chatHistory.length) {
    return;
  }

  clearElement(chatMessages);
  chatHistory.forEach(renderChatMessage);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderWelcomeMessage() {
  appendMessage("assistant", WELCOME_MESSAGE);
}

function clearChatHistory() {
  chatHistory = [];

  try {
    localStorage.removeItem(CHAT_HISTORY_STORAGE_KEY);
  } catch (error) {
    // Очистка UI всё равно должна работать без доступа к localStorage.
  }

  clearElement(chatMessages);
  renderWelcomeMessage();
  chatInput.focus();
}

async function submitChat(event) {
  event.preventDefault();

  const query = chatInput.value.trim();
  const topK = normalizeTopK(topKInput.value);
  const retrievalMode = selectedRetrievalMode();
  topKInput.value = topK;

  if (!query) {
    chatInput.focus();
    return;
  }

  appendMessage("user", query);
  addMessageToHistory({ role: "user", content: query, sources: [] });
  saveChatHistory();
  chatInput.value = "";
  sendButton.disabled = true;
  clearChatHistoryButton.disabled = true;

  const pendingRow = appendMessage("assistant", "Формируется ответ...", {
    loading: true
  });

  try {
    const data = await apiRequest("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        query,
        top_k: topK,
        retrieval_mode: retrievalMode
      })
    });

    const answer = data?.answer || "Backend вернул пустой ответ.";
    const sources = Array.isArray(data?.sources) ? data.sources : [];
    const usedRetrievalMode = normalizeRetrievalMode(
      data?.retrieval_mode,
      retrievalMode
    );

    replaceMessage(pendingRow, "assistant", answer);
    renderRetrievalMode(usedRetrievalMode, pendingRow);
    renderSources(sources, pendingRow);
    addMessageToHistory({
      role: "assistant",
      content: answer,
      sources,
      retrievalMode: usedRetrievalMode
    });
    saveChatHistory();
  } catch (error) {
    const message =
      error.status === 503
        ? "LLM не настроена. Проверьте LLM_API_KEY в backend/.env."
        : error.message;
    replaceMessage(pendingRow, "assistant", message, { error: true });
  } finally {
    sendButton.disabled = false;
    clearChatHistoryButton.disabled = false;
    chatInput.focus();
  }
}

function openTechnicalSearch() {
  searchPanel.classList.add("open");
  searchPanel.setAttribute("aria-hidden", "false");
  if (!technicalQueryInput.value.trim()) {
    technicalQueryInput.value = chatInput.value.trim();
  }
  technicalQueryInput.focus();
}

function closeTechnicalSearch() {
  searchPanel.classList.remove("open");
  searchPanel.setAttribute("aria-hidden", "true");
  openSearchPanel.focus();
}

function setTechnicalStatus(message, isError = false) {
  technicalStatus.textContent = message;
  technicalStatus.classList.toggle("error", isError);
  technicalStatus.classList.toggle("muted", !isError);
}

function renderTechnicalResults(data) {
  clearElement(technicalResults);
  const results = Array.isArray(data.results) ? data.results : [];

  if (!results.length) {
    setTechnicalStatus("По вашему запросу фрагменты не найдены.");
    return;
  }

  const mode = normalizeRetrievalMode(data.retrieval_mode);
  const modeText = mode ? ` Режим: ${retrievalModeLabel(mode)}.` : "";
  setTechnicalStatus(
    `Найдено фрагментов: ${data.total_results ?? results.length}.${modeText}`
  );

  results.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = "result-card";

    const title = document.createElement("h3");
    title.className = "result-title";
    title.textContent = sourceDocumentTitle(item);
    card.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "result-meta";

    const article = articleLabel(item);
    if (article) {
      appendTechnicalMeta(meta, article);
    }

    const similarity = formatNumber(item.similarity, 4);
    const distance = formatNumber(item.distance, 4);
    appendTechnicalMeta(meta, `Фрагмент ${index + 1}`);
    if (similarity !== null) {
      appendTechnicalMeta(meta, `similarity: ${similarity}`);
    }
    if (distance !== null) {
      appendTechnicalMeta(meta, `distance: ${distance}`);
    }
    [
      ["hybrid_score", item.hybrid_score],
      ["semantic_score", item.semantic_score],
      ["keyword_score", item.keyword_score],
      ["article_boost", item.article_boost],
      ["document_boost", item.document_boost]
    ].forEach(([label, value]) => {
      const formatted = formatNumber(value, 4);
      if (formatted !== null) {
        appendTechnicalMeta(meta, `${label}: ${formatted}`);
      }
    });

    card.appendChild(meta);

    const content = document.createElement("p");
    content.className = "result-content";
    content.textContent = item.content || "";
    card.appendChild(content);

    technicalResults.appendChild(card);
  });
}

function appendTechnicalMeta(container, text) {
  const item = document.createElement("span");
  item.textContent = text;
  container.appendChild(item);
}

async function submitTechnicalSearch(event) {
  event.preventDefault();

  const query = technicalQueryInput.value.trim();
  const topK = normalizeTopK(technicalTopKInput.value);
  const retrievalMode = selectedRetrievalMode();
  technicalTopKInput.value = topK;

  clearElement(technicalResults);

  if (!query) {
    setTechnicalStatus("Введите запрос для поиска.", true);
    technicalQueryInput.focus();
    return;
  }

  technicalSearchButton.disabled = true;
  setTechnicalStatus("Ищем фрагменты...");

  try {
    const data = await apiRequest("/api/search", {
      method: "POST",
      body: JSON.stringify({
        query,
        top_k: topK,
        retrieval_mode: retrievalMode
      })
    });
    renderTechnicalResults(data || {});
  } catch (error) {
    setTechnicalStatus(error.message, true);
  } finally {
    technicalSearchButton.disabled = false;
  }
}

chatForm.addEventListener("submit", submitChat);
clearChatHistoryButton.addEventListener("click", () => {
  if (confirm("Очистить локальную историю диалога?")) {
    clearChatHistory();
  }
});
openSearchPanel.addEventListener("click", openTechnicalSearch);
closeSearchPanel.addEventListener("click", closeTechnicalSearch);
searchPanel.addEventListener("click", (event) => {
  if (event.target.matches("[data-close-search]")) {
    closeTechnicalSearch();
  }
});
technicalSearchForm.addEventListener("submit", submitTechnicalSearch);

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    chatForm.requestSubmit();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && searchPanel.classList.contains("open")) {
    closeTechnicalSearch();
  }
});

loadChatHistory();
restoreChatHistory();
