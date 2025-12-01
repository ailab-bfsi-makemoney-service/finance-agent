// Finance Agent Modern UI – RAG v2

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
  // Prefer explicit chart from backend
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

  const data = response.data || {};
  const details = response.details || {};

  // Try categories
  const cats = details.top_categories || data.top_categories || [];
  if (cats.length) {
    return {
      label: "Category breakdown",
      type: "bar",
      data: {
        labels: cats.map(([name]) => name),
        values: cats.map(([, val]) => val),
      },
    };
  }

  // Try merchants
  const merchants =
    details.top_merchants || data.top_merchants || data.top_restaurants || [];
  if (merchants.length) {
    return {
      label: "Top merchants",
      type: "bar",
      data: {
        labels: merchants.map(([name]) => name),
        values: merchants.map(([, val]) => val),
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

  // total spend
  const total =
    data.total_spend ??
    data.total ??
    null;
  if (typeof total === "number") {
    lines.push(`Total spend: $${total.toFixed(2)}`);
  }

  // matches
  const matches =
    details.matches ??
    data.matches ??
    null;
  if (typeof matches === "number") {
    lines.push(`Transactions: ${matches}`);
  }

  // Top categories
  const cats = details.top_categories || data.top_categories || [];
  if (cats.length) {
    lines.push("Top categories:");
    cats.slice(0, 5).forEach(([name, amt]) => {
      const v = typeof amt === "number" ? amt.toFixed(2) : amt;
      lines.push(` • ${name}: $${v}`);
    });
  }

  // Top merchants
  const merchants =
    details.top_merchants || data.top_merchants || data.top_restaurants || [];
  if (merchants.length) {
    lines.push("Top merchants:");
    merchants.slice(0, 5).forEach(([name, amt]) => {
      const v = typeof amt === "number" ? amt.toFixed(2) : amt;
      lines.push(` • ${name}: $${v}`);
    });
  }

  // Top cuisines
  const cuisines = details.top_cuisines || data.top_cuisines || [];
  if (cuisines.length) {
    lines.push("Top cuisines:");
    cuisines.slice(0, 5).forEach(([name, amt]) => {
      const v = typeof amt === "number" ? amt.toFixed(2) : amt;
      lines.push(` • ${name}: $${v}`);
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
