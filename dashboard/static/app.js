const TIME_ZONE = "Etc/GMT+6";
const VIEWS = {
  normalized_events: {
    title: "Normalizados",
    caption: "Solo access_control con UserID útil.",
    idField: "id",
    columns: [
      ["event_occurred_at_utc", "Hora"],
      ["user_id_on_device", "UserID"],
      ["card_name", "Nombre"],
      ["device_id_resolved", "DeviceID"],
      ["identity_resolution", "Resolución"],
      ["source_ip", "IP"],
      ["door_name", "Puerta"],
      ["direction", "Dirección"],
      ["granted", "Granted"],
      ["method_code", "Método"],
      ["reader_id", "Reader"],
    ],
  },
  quarantine_events: {
    title: "Cuarentena",
    caption: "Eventos fuera del flujo normalizado, para análisis técnico.",
    idField: "id",
    columns: [
      ["id", "ID"],
      ["raw_received_at_utc", "Hora"],
      ["event_kind", "Tipo"],
      ["reason", "Razón"],
      ["source_ip", "IP"],
      ["candidate_device_id", "DeviceID candidato"],
      ["listener_port", "Puerto"],
    ],
  },
  raw_requests: {
    title: "Crudos",
    caption: "Requests capturados por el edge antes de normalización.",
    idField: "id",
    columns: [
      ["id", "ID"],
      ["received_at_utc", "Hora"],
      ["source_ip", "IP"],
      ["path", "Path"],
      ["event_kind_detected", "Tipo detectado"],
      ["device_id_hint", "Hint DeviceID"],
      ["listener_port", "Puerto"],
      ["method", "Método"],
    ],
  },
  devices: {
    title: "Devices",
    caption: "door_status, heartbeat_connect y unknown para análisis técnico del dispositivo.",
    idField: "id",
    columns: [
      ["received_at_utc", "Hora"],
      ["event_kind_detected", "Tipo"],
      ["device_id_hint", "DeviceID heartbeat"],
      ["device_id_resolved", "DeviceID resuelto"],
      ["candidate_device_id", "DeviceID candidato"],
      ["source_ip", "IP"],
      ["outcome", "Outcome"],
      ["reason", "Razón"],
      ["path", "Path"],
    ],
  },
};

const state = {
  activeView: "normalized_events",
  page: 1,
  pageSize: 25,
  search: "",
  selectedId: null,
  filters: {},
  loading: false,
  requestToken: 0,
};

const elements = {
  tabs: document.getElementById("tabs"),
  filterBar: document.getElementById("filter-bar"),
  searchInput: document.getElementById("search-input"),
  pageSizeSelect: document.getElementById("page-size-select"),
  table: document.getElementById("data-table"),
  tableHead: document.querySelector("#data-table thead"),
  tableBody: document.querySelector("#data-table tbody"),
  tableTitle: document.getElementById("table-title"),
  tableCaption: document.getElementById("table-caption"),
  prevButton: document.getElementById("prev-button"),
  nextButton: document.getElementById("next-button"),
  pageIndicator: document.getElementById("page-indicator"),
  sourceMode: document.getElementById("source-mode"),
  refreshButton: document.getElementById("refresh-button"),
  loadingIndicator: document.getElementById("loading-indicator"),
  loadingText: document.getElementById("loading-text"),
  detailDialog: document.getElementById("detail-dialog"),
  detailCaption: document.getElementById("detail-caption"),
  detailJson: document.getElementById("detail-json"),
  detailCloseButton: document.getElementById("detail-close-button"),
};

const dateFormatter = new Intl.DateTimeFormat("es-MX", {
  timeZone: TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: true,
});

function formatDate(value) {
  if (!value) return "";
  try {
    return dateFormatter.format(new Date(value));
  } catch {
    return value;
  }
}

function formatValue(field, value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "Sí" : "No";
  }
  if (field.includes("_utc") || field.endsWith("_at")) {
    return formatDate(value);
  }
  if (field === "status") {
    return `<span class="pill ${statusClass(value)}">${value}</span>`;
  }
  if (field === "outcome") {
    const cssClass = value === "normalized" ? "ok" : value === "quarantine" ? "warn" : "danger";
    return `<span class="pill ${cssClass}">${value}</span>`;
  }
  if (field === "granted") {
    return `<span class="pill ${value ? "ok" : "danger"}">${value ? "true" : "false"}</span>`;
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function statusClass(value) {
  if (value === "online" || value === "true") return "ok";
  if (value === "stale") return "warn";
  if (value === "offline" || value === "false") return "danger";
  return "warn";
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }
  return response.json();
}

function buildQuery() {
  const params = new URLSearchParams({
    page: String(state.page),
    page_size: String(state.pageSize),
    search: state.search,
  });
  for (const [key, value] of Object.entries(state.filters)) {
    if (value) params.set(key, value);
  }
  return params.toString();
}

function renderTabs() {
  elements.tabs.innerHTML = "";
  for (const [view, config] of Object.entries(VIEWS)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tab-button ${state.activeView === view ? "active" : ""}`;
    button.textContent = config.title;
    button.addEventListener("click", () => {
      state.activeView = view;
      state.page = 1;
      state.selectedId = null;
      state.filters = {};
      renderTabs();
      loadView();
    });
    elements.tabs.appendChild(button);
  }
}

function renderSummary(summary) {
  elements.sourceMode.textContent = summary.source_mode;
}

function setLoading(isLoading, message = "Cargando datos…") {
  state.loading = isLoading;
  elements.loadingIndicator.hidden = !isLoading;
  elements.loadingText.textContent = message;
  elements.refreshButton.disabled = isLoading;
  if (isLoading) {
    elements.prevButton.disabled = true;
    elements.nextButton.disabled = true;
  }
}

function renderFilters(filterOptions) {
  elements.filterBar.innerHTML = "";
  const view = state.activeView;
  const definitions = [];
  if (view === "raw_requests" && filterOptions.event_kind?.length) {
    definitions.push(["event_kind", "Tipo detectado", filterOptions.event_kind]);
  }
  if (view === "normalized_events") {
    if (filterOptions.identity_resolution?.length) {
      definitions.push(["identity_resolution", "Resolución", filterOptions.identity_resolution]);
    }
  }
  if (view === "quarantine_events") {
    if (filterOptions.event_kind?.length) {
      definitions.push(["event_kind", "Tipo", filterOptions.event_kind]);
    }
    if (filterOptions.reason?.length) {
      definitions.push(["reason", "Razón", filterOptions.reason]);
    }
  }
  if (view === "devices") {
    if (filterOptions.event_kind?.length) {
      definitions.push(["event_kind", "Tipo", filterOptions.event_kind]);
    }
    if (filterOptions.outcome?.length) {
      definitions.push(["outcome", "Outcome", filterOptions.outcome]);
    }
  }

  for (const [key, label, options] of definitions) {
    const wrapper = document.createElement("label");
    wrapper.innerHTML = `${label}<select data-filter="${key}"><option value="">Todos</option>${options
      .map((value) => `<option value="${value}">${value}</option>`)
      .join("")}</select>`;
    const select = wrapper.querySelector("select");
    select.value = state.filters[key] || "";
    select.addEventListener("change", () => {
      state.filters[key] = select.value;
      state.page = 1;
      loadView();
    });
    elements.filterBar.appendChild(wrapper);
  }
}

function renderTable(pageResult) {
  const config = VIEWS[state.activeView];
  elements.tableTitle.textContent = config.title;
  elements.tableCaption.textContent = `${config.caption} Total: ${pageResult.total} registros.`;

  elements.tableHead.innerHTML = `<tr>${config.columns
    .map(([, label]) => `<th>${label}</th>`)
    .join("")}<th>Detalle</th></tr>`;
  elements.tableBody.innerHTML = pageResult.items
    .map((item) => {
      const recordId = item[config.idField];
      const cells = config.columns
        .map(([field]) => `<td>${formatValue(field, item[field])}</td>`)
        .join("");
      return `<tr data-id="${recordId}">${cells}<td><button type="button" class="ghost-button detail-button" data-detail-id="${recordId}">Ver detalle</button></td></tr>`;
    })
    .join("");

  for (const button of elements.tableBody.querySelectorAll(".detail-button")) {
    button.addEventListener("click", async () => {
      state.selectedId = button.dataset.detailId;
      await loadDetail(state.activeView, button.dataset.detailId);
    });
  }

  const totalPages = Math.max(1, Math.ceil(pageResult.total / pageResult.page_size));
  elements.pageIndicator.textContent = `Página ${pageResult.page} de ${totalPages}`;
  elements.prevButton.disabled = pageResult.page <= 1;
  elements.nextButton.disabled = pageResult.page >= totalPages;
}

async function loadDetail(view, id) {
  const record = await fetchJson(`/api/${view}/${encodeURIComponent(id)}`);
  elements.detailCaption.textContent = `${view} / ${id}`;
  elements.detailJson.textContent = JSON.stringify(record, null, 2);
  elements.detailDialog.showModal();
}

async function loadSummary() {
  const summary = await fetchJson("/api/summary");
  renderSummary(summary);
}

async function loadView() {
  const requestToken = ++state.requestToken;
  setLoading(true);
  try {
    const pageResult = await fetchJson(`/api/${state.activeView}?${buildQuery()}`);
    if (requestToken !== state.requestToken) {
      return;
    }
    renderFilters(pageResult.filter_options || {});
    renderTable(pageResult);
    state.selectedId = null;
    elements.detailCaption.textContent = "Selecciona un registro para inspeccionar el payload.";
    elements.detailJson.textContent = pageResult.items.length
      ? "Haz clic en “Ver detalle” para inspeccionar el payload."
      : "No hay datos para los filtros actuales.";
  } finally {
    if (requestToken === state.requestToken) {
      setLoading(false);
    }
  }
}

function attachEvents() {
  elements.searchInput.addEventListener("input", () => {
    state.search = elements.searchInput.value;
    state.page = 1;
    loadView().catch(showError);
  });

  elements.pageSizeSelect.addEventListener("change", () => {
    state.pageSize = Number(elements.pageSizeSelect.value);
    state.page = 1;
    loadView().catch(showError);
  });

  elements.prevButton.addEventListener("click", () => {
    if (state.page > 1) {
      state.page -= 1;
      loadView().catch(showError);
    }
  });

  elements.nextButton.addEventListener("click", () => {
    state.page += 1;
    loadView().catch(showError);
  });

  elements.refreshButton.addEventListener("click", () => {
    loadSummary().then(loadView).catch(showError);
  });

  elements.detailCloseButton.addEventListener("click", () => {
    elements.detailDialog.close();
  });

  elements.detailDialog.addEventListener("click", (event) => {
    const bounds = elements.detailDialog.getBoundingClientRect();
    const inside =
      event.clientX >= bounds.left &&
      event.clientX <= bounds.right &&
      event.clientY >= bounds.top &&
      event.clientY <= bounds.bottom;
    if (!inside) {
      elements.detailDialog.close();
    }
  });
}

function showError(error) {
  console.error(error);
  setLoading(false);
  elements.tableCaption.textContent = `Error: ${error.message}`;
  elements.detailJson.textContent = error.stack || error.message;
  if (!elements.detailDialog.open) {
    elements.detailDialog.showModal();
  }
}

async function bootstrap() {
  renderTabs();
  attachEvents();
  await Promise.all([loadSummary(), loadView()]);
}

bootstrap().catch(showError);
