// Finance Agent Modern UI – RAG v2 (Fully Updated for New Backend Schema)

let currentChart = null;

// DOM elements
const questionInput = document.getElementById("questionInput");
const askButton = document.getElementById("askButton");
const statusMessage = document.getElementById("statusMessage");
const summaryBody = document.getElementById("summaryBody");
const detailsBody = document.getElementById("detailsBody");
const intentTag = document.getElementById("intentTag");
const metaTag = document.getElementById("metaTag");
const chartLabel = document.getElementById("chartLabel");
const chartPlaceholder = document.getElementById("chartPlaceholder");
const quickQuestions = document.getElementById("quickQuestions");
const chartCanvas = document.getElementById("resultChart");
const ctx = chartCanvas.getContext("2d");

// --------------------------------------------------
// Status bar
// --------------------------------------------------
function setStatus(state, text) {
  statusMessage.classList.remove("error", "success", "loading");

  const dot = statusMessage.querySelector(".dot");

  if (state === "loading") {
    statusMessage.classList.add("loading");
    dot.style.background = "var(--accent)";
  } else if (state === "error") {
    statusMessage.classList.add("error");
    dot.style.background = "var(--error)";
  } else if (state === "success") {
    statusMessage.classList.add("success");
    dot.style.background = "var(--success)";
  } else {
    dot.style.background = "var(--accent)";
  }

  statusMessage.querySelector("span:nth-child(2)").textContent = text;
}

// --------------------------------------------------
// Chart helpers
// --------------------------------------------------
function clearChart() {
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }
}

function buildChartConfig(response) {
  const details = response.details || {};
  const data = response.data || {};

  // 1. Backend-provided chart object (preferred)
  if (response.chart && response.chart.labels && response.chart.values) {
    return {
      label: response.chart.title || "Chart",
      type: response.chart.type || "bar",
      data: {
        labels: response.chart.labels,
        values: response.chart.values,
      },
    };
  }

  // 2. Categories (object format)
  const cats = details.top_categories || data.top_categories || [];
  if (cats.length) {
    const isObject = typeof cats[0] === "object";
    return {
      label: "Category breakdown",
      type: "bar",
      data: {
        labels: isObject ? cats.map((c) => c.category) : cats.map(([name]) => name),
        values: isObject
          ? cats.map((c) => c.total_spend)
          : cats.map(([, val]) => val),
      },
    };
  }

  // 3. Restaurants (object format)
  const restaurants = details.top_restaurants || data.top_restaurants || [];
  if (restaurants.length) {
    const isObject = typeof restaurants[0] === "object";
    return {
      label: "Top restaurants",
      type: "bar",
      data: {
        labels: isObject
          ? restaurants.map((r) => r.merchant)
          : restaurants.map(([name]) => name),
        values: isObject
          ? restaurants.map((r) => r.total_spend)
          : restaurants.map(([, val]) => val),
      },
    };
  }

  return null;
}

function renderChart(response) {
  clearChart();

  const cfg = buildChartConfig(response);
  if (!cfg) {
    chartCanvas.classList.add("hidden");
    chartPlaceholder.classList.remove("hidden");
    chartLabel.textContent = "No chart available";
    return;
  }

  chartPlaceholder.classList.add("hidden");
  chartCanvas.classList.remove("hidden");

  chartLabel.textContent = cfg.label || "Chart";

  currentChart = new Chart(ctx, {
    type: cfg.type,
    data: {
      labels: cfg.data.labels,
      datasets: [
        {
          label: cfg.label,
          data: cfg.data.values,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
}

// --------------------------------------------------
// Summary + Details
// --------------------------------------------------
function renderSummary(response) {
  summaryBody.textContent = response.answer || "No answer received.";
  summaryBody.classList.remove("summary-placeholder");

  intentTag.innerHTML = "";

  if (response.intent) {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = `intent: ${response.intent}`;
    intentTag.appendChild(tag);
  }
}

function renderDetails(response) {
  const data = response.data || {};
  const details = response.details || {};

  metaTag.textContent = response.intent
    ? `Detected intent: ${response.intent}`
    : "";

  const lines = [];

  // NEW: restaurant totals
  if (details.total_restaurant_spend !== undefined) {
    lines.push(
      `Restaurant spend: $${details.total_restaurant_spend.toFixed(2)}`
    );
  }

  if (details.total_visits !== undefined) {
    lines.push(`Restaurant visits: ${details.total_visits}`);
  }

  // Legacy total fallback
  const total =
    data.total_restaurant_spend ??
    details.total_restaurant_spend ??
    data.total_spend ??
    data.total ??
    null;

  if (typeof total === "number") {
    lines.push(`Total spend: $${total.toFixed(2)}`);
  }

  // --- Top categories ---
  const categories = details.top_categories || data.top_categories || [];
  if (categories.length) {
    lines.push("Top categories:");
    categories.slice(0, 5).forEach((c) => {
      const name = c.category ?? c[0];
      const amt = c.total_spend ?? c[1];
      lines.push(` • ${name}: $${amt.toFixed(2)}`);
    });
  }

  // --- Top restaurants ---
  const restaurants = details.top_restaurants || data.top_restaurants || [];
  if (restaurants.length) {
    lines.push("Top restaurants:");
    restaurants.slice(0, 5).forEach((r) => {
      const name = r.merchant ?? r[0];
      const amt = r.total_spend ?? r[1];
      lines.push(` • ${name}: $${amt.toFixed(2)}`);
    });
  }

  // --- Top cuisines ---
  const cuisines = details.top_cuisines || data.top_cuisines || [];
  if (cuisines.length) {
    lines.push("Top cuisines:");
    cuisines.slice(0, 5).forEach((c) => {
      const name = c.cuisine ?? c[0];
      const amt = c.total_spend ?? c[1];
      lines.push(` • ${name}: $${amt.toFixed(2)}`);
    });
  }

  if (!lines.length) {
    detailsBody.innerHTML =
      '<div class="summary-placeholder">No additional details for this answer.</div>';
    return;
  }

  detailsBody.innerHTML = `<ul>${lines
    .map((l) => `<li>${l}</li>`)
    .join("")}</ul>`;
}

// --------------------------------------------------
// Backend call
// --------------------------------------------------
async function askAgent(question) {
  if (!question) return;

  setStatus("loading", "Thinking...");
  askButton.disabled = true;

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const payload = await res.json();
    console.log("API response:", payload);

    renderSummary(payload);
    renderDetails(payload);
    renderChart(payload);

    setStatus("success", "Done");
  } catch (err) {
    console.error(err);
    setStatus("error", "Backend error");
  }

  askButton.disabled = false;
}

// --------------------------------------------------
// Event wiring
// --------------------------------------------------
askButton.addEventListener("click", () => {
  const q = questionInput.value.trim();
  if (q) askAgent(q);
});

questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    const q = questionInput.value.trim();
    if (q) askAgent(q);
  }
});

quickQuestions.addEventListener("click", (e) => {
  const target = e.target?.closest?.("[data-question]");
  if (!target) return;
  questionInput.value = target.dataset.question;
  questionInput.focus();
});

// Initial state
clearChart();
chartPlaceholder.classList.remove("hidden");
setStatus("idle", "Ready");
