const state = {
  inventory: [],
  report: [],
  chat: []
};

const formatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

const chartColors = ["#0f766e", "#2563eb", "#d97706", "#7c3aed"];

const viewTitles = {
  overview: "Overview",
  products: "Products",
  inventory: "Inventory",
  sales: "Sales",
  reports: "Reports",
  assistant: "Assistant"
};

function qs(selector, root = document) {
  return root.querySelector(selector);
}

function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

function toast(message, type = "success") {
  const node = qs("#toast");
  node.textContent = message;
  node.className = `toast show ${type === "error" ? "error" : ""}`;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => {
    node.className = "toast";
  }, 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : {};

  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }

  return data;
}

function formPayload(form) {
  const data = new FormData(form);
  return Object.fromEntries(data.entries());
}

function numericPayload(form) {
  const payload = formPayload(form);
  return {
    product_id: Number(payload.product_id),
    quantity: Number(payload.quantity)
  };
}

function statusBadge(active) {
  const label = active ? "Active" : "Inactive";
  const className = active ? "active" : "inactive";
  return `<span class="status-pill ${className}">${label}</span>`;
}

function emptyRow(colspan, label) {
  return `<tr><td colspan="${colspan}">${label}</td></tr>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatChartValue(value, unit) {
  return unit === "USD" ? formatter.format(value) : Number(value).toLocaleString("en-US");
}

function shortLabel(label) {
  const value = String(label);
  return value.length > 14 ? `${value.slice(0, 12)}...` : value;
}

function renderBarChart(svg, chart) {
  if (!svg) return;

  const labels = chart.labels || [];
  const series = chart.series || [];
  const values = series.flatMap((item) => item.values || []);
  const maxValue = Math.max(...values, 0);

  svg.setAttribute("viewBox", "0 0 760 300");
  svg.innerHTML = "";

  if (!labels.length || !series.length || maxValue <= 0) {
    svg.innerHTML = `
      <text x="380" y="145" text-anchor="middle" class="chart-empty">No chart data yet</text>
    `;
    return;
  }

  const width = 760;
  const height = 300;
  const left = 46;
  const right = 22;
  const top = 30;
  const bottom = 62;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const groupWidth = plotWidth / labels.length;
  const barGap = 5;
  const barWidth = Math.max(8, Math.min(28, (groupWidth - 18) / series.length - barGap));
  const niceMax = maxValue || 1;

  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const y = top + plotHeight - ratio * plotHeight;
    const value = niceMax * ratio;
    return `
      <line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}" class="chart-grid"></line>
      <text x="${left - 10}" y="${y + 4}" text-anchor="end" class="chart-axis">${formatChartValue(value, chart.unit)}</text>
    `;
  }).join("");

  const bars = labels.map((label, labelIndex) => {
    const groupCenter = left + groupWidth * labelIndex + groupWidth / 2;
    const groupStart = groupCenter - ((barWidth + barGap) * series.length - barGap) / 2;
    const labelText = escapeHtml(shortLabel(label));
    const barNodes = series.map((item, seriesIndex) => {
      const value = Number(item.values[labelIndex] || 0);
      const barHeight = value / niceMax * plotHeight;
      const x = groupStart + seriesIndex * (barWidth + barGap);
      const y = top + plotHeight - barHeight;
      const color = chartColors[seriesIndex % chartColors.length];
      return `
        <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="4" fill="${color}">
          <title>${escapeHtml(item.name)}: ${formatChartValue(value, chart.unit)}</title>
        </rect>
      `;
    }).join("");

    return `
      ${barNodes}
      <text x="${groupCenter}" y="${height - 30}" text-anchor="middle" class="chart-label">${labelText}</text>
    `;
  }).join("");

  const legend = series.map((item, index) => `
    <g transform="translate(${left + index * 118}, 10)">
      <rect width="10" height="10" rx="2" fill="${chartColors[index % chartColors.length]}"></rect>
      <text x="16" y="10" class="chart-legend">${escapeHtml(item.name)}</text>
    </g>
  `).join("");

  svg.innerHTML = `${legend}${gridLines}${bars}`;
}

function renderReportCharts(items) {
  renderBarChart(qs("#sales-chart"), {
    unit: "units",
    labels: items.map((item) => item.name),
    series: [
      { name: "Store", values: items.map((item) => item.store_sales) },
      { name: "Online", values: items.map((item) => item.online_sales) }
    ]
  });

  renderBarChart(qs("#inventory-chart"), {
    unit: "units",
    labels: items.map((item) => item.name),
    series: [
      { name: "Inventory", values: items.map((item) => item.inventory) }
    ]
  });
}

function renderInventoryTable(selector, items, compact = false) {
  const body = qs(selector);
  if (!items.length) {
    body.innerHTML = emptyRow(compact ? 4 : 5, "No inventory found.");
    return;
  }

  body.innerHTML = items.map((item) => {
    const cells = compact
      ? `
        <td>${item.product_id}</td>
        <td>${item.name}</td>
        <td>${item.quantity}</td>
        <td>${statusBadge(item.active)}</td>
      `
      : `
        <td>${item.product_id}</td>
        <td>${item.name}</td>
        <td>${formatter.format(item.price)}</td>
        <td>${item.quantity}</td>
        <td>${statusBadge(item.active)}</td>
      `;

    return `<tr>${cells}</tr>`;
  }).join("");
}

function renderReport(items) {
  const body = qs("#report-body");
  if (!items.length) {
    body.innerHTML = emptyRow(8, "No report data found.");
    return;
  }

  body.innerHTML = items.map((item) => `
    <tr>
      <td>${item.product_id}</td>
      <td>${item.name}</td>
      <td>${formatter.format(item.price)}</td>
      <td>${item.inventory}</td>
      <td>${item.store_sales}</td>
      <td>${item.online_sales}</td>
      <td>${item.total_sales}</td>
      <td>${statusBadge(item.active)}</td>
    </tr>
  `).join("");
}

function visualHtml(visual) {
  const id = `chart-${Math.random().toString(36).slice(2)}`;
  window.requestAnimationFrame(() => renderBarChart(qs(`#${id}`), visual));
  return `
    <div class="message-chart">
      <div class="message-chart-title">${escapeHtml(visual.title || "Chart")}</div>
      <svg id="${id}" class="chart small-chart" role="img" aria-label="${escapeHtml(visual.title || "Assistant chart")}"></svg>
    </div>
  `;
}

function renderMetrics(metrics) {
  Object.entries(metrics).forEach(([key, value]) => {
    const node = qs(`[data-metric="${key}"]`);
    if (!node) return;
    node.textContent = key === "inventory_value" ? formatter.format(value) : value;
  });
}

async function loadData(showToast = false) {
  const [dashboard, inventory, report] = await Promise.all([
    api("/api/dashboard"),
    api("/api/inventory"),
    api("/api/reports/sales")
  ]);

  state.inventory = inventory.items;
  state.report = report.items;

  renderMetrics(dashboard);
  renderInventoryTable("#overview-inventory-body", state.inventory);
  renderInventoryTable("#inventory-body", state.inventory, true);
  renderReport(state.report);
  renderReportCharts(state.report);

  qs("#inventory-count").textContent = `${inventory.count} item${inventory.count === 1 ? "" : "s"}`;
  if (showToast) toast("Data refreshed.");
}

function setView(viewName) {
  qsa(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });

  qsa(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `${viewName}-view`);
  });

  qs("#view-title").textContent = viewTitles[viewName] || "Store";
}

function bindNavigation() {
  qsa(".nav-item").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
}

function bindForms() {
  qs("#product-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = formPayload(form);

    try {
      await api("/api/products", {
        method: "POST",
        body: JSON.stringify({
          name: payload.name.trim(),
          price: Number(payload.price)
        })
      });
      form.reset();
      await loadData();
      toast("Product added.");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  qs("#status-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = formPayload(form);

    try {
      await api(`/api/products/${Number(payload.product_id)}/status`, {
        method: "PATCH",
        body: JSON.stringify({ active: payload.active === "true" })
      });
      form.reset();
      await loadData();
      toast("Status updated.");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  qs("#inventory-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;

    try {
      await api("/api/inventory", {
        method: "POST",
        body: JSON.stringify(numericPayload(form))
      });
      form.reset();
      await loadData();
      toast("Inventory updated.");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  qs("#store-sale-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;

    try {
      await api("/api/sales/store", {
        method: "POST",
        body: JSON.stringify(numericPayload(form))
      });
      form.reset();
      await loadData();
      toast("Store sale recorded.");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  qs("#online-sale-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;

    try {
      await api("/api/sales/online", {
        method: "POST",
        body: JSON.stringify(numericPayload(form))
      });
      form.reset();
      await loadData();
      toast("Online sale recorded.");
    } catch (error) {
      toast(error.message, "error");
    }
  });
}

function renderChat() {
  const log = qs("#chat-log");
  if (!state.chat.length) {
    log.innerHTML = "";
    return;
  }

  log.innerHTML = state.chat
    .filter((message) => message.role !== "system")
    .map((message) => `
      <div class="chat-message ${message.role}">
        <div>${escapeHtml(message.content)}</div>
        ${(message.visuals || []).map(visualHtml).join("")}
      </div>
    `)
    .join("");
  log.scrollTop = log.scrollHeight;
}

function bindChat() {
  qs("#chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = formPayload(form);
    const message = payload.message.trim();
    if (!message) return;

    state.chat.push({ role: "user", content: message });
    renderChat();
    form.reset();
    qs("#chat-status").textContent = "Working";

    try {
      const data = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          history: state.chat.slice(0, -1)
        })
      });
      state.chat = data.messages;
      qs("#chat-status").textContent = data.status || "Ready";
      renderChat();
    } catch (error) {
      state.chat.push({ role: "assistant", content: error.message });
      qs("#chat-status").textContent = "Unavailable";
      renderChat();
    }
  });
}

async function init() {
  bindNavigation();
  bindForms();
  bindChat();
  qs("#refresh-btn").addEventListener("click", () => loadData(true).catch((error) => toast(error.message, "error")));

  try {
    await loadData();
  } catch (error) {
    toast(error.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", init);
