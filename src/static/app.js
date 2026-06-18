const state = {
  inventory: [],
  report: [],
  chat: []
};

const formatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD"
});

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
    .map((message) => `<div class="chat-message ${message.role}">${message.content}</div>`)
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
