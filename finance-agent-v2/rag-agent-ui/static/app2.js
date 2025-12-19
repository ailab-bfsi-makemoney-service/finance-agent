// Finance Agent Modern UI – Final Version

let currentChart = null;

// elements
const questionInput = document.getElementById("questionInput");
const askButton = document.getElementById("askButton");
const statusMessage = document.getElementById("statusMessage");
const summaryBody = document.getElementById("summaryBody");
const detailsBody = document.getElementById("detailsBody");
const intentTag = document.getElementById("intentTag");
const metaTag = document.getElementById("metaTag");
const chartSection = document.getElementById("chartSection");
const chartLabel = document.getElementById("chartLabel");
const chartPlaceholder = document.getElementById("chartPlaceholder");
const quickQuestions = document.getElementById("quickQuestions");

const chartCanvas = document.getElementById("resultChart");
const ctx = chartCanvas.getContext("2d");

// status updates
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

function clearChart() {
  if (currentChart) {
    currentChart.destroy();
    currentChart = null;
  }
}

function buildChartConfig(response) {
  const { intent, data } = response || {};
  if (!data) return null;

  if (intent === "restaurant_spend" && data.top_restaurants?.length) {
    return {
      label: "Top restaurants",
      type: "bar",
      data: {
        labels: data.top_restaurants.map(([n]) => n),
        values: data.top_restaurants.map(([, a]) => a)
      }
    };
  }

  if (data.chartData) return data.chartData;

  return null;
}

function renderSummary(response) {
  summaryBody.textContent = response.answer ?? "No answer received.";
  summaryBody.classList.remove("summary-placeholder");

  intentTag.innerHTML = "";

  if (response.intent) {
    let t = document.createElement("span");
    t.className = "tag";
    t.textContent = `intent: ${response.intent}`;
    intentTag.appendChild(t);
  }

  if (response.data?.period) {
    let t = document.createElement("span");
    t.className = "tag";
    t.textContent = `period: ${response.data.period}`;
    intentTag.appendChild(t);
  }
}

function renderDetails(response) {
  metaTag.textContent = response.intent ? `Detected intent: ${response.intent}` : "";

  const d = response.data;
  if (!d) {
    detailsBody.innerHTML = "No details.";
    return;
  }

  const lines = [];

  if (d.total) lines.push(`Total spend: $${d.total.toFixed(2)}`);
  if (d.transactions) lines.push(`Transactions: ${d.transactions}`);
  if (d.category) lines.push(`Category: ${d.category}`);
  if (d.period) lines.push(`Period: ${d.period}`);

  if (d.top_restaurants?.length) {
    lines.push("Top restaurants:");
    d.top_restaurants.slice(0, 5).forEach(([n, a]) => {
      lines.push(` • ${n}: $${a.toFixed(2)}`);
    });
  }

  detailsBody.innerHTML = `<ul>${lines.map(l => `<li>${l}</li>`).join("")}</ul>`;
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
          data: cfg.data.values
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

async function askAgent(question) {
  setStatus("loading", "Thinking...");
  askButton.disabled = true;

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });

    const payload = await res.json();

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

askButton.addEventListener("click", () => {
  let q = questionInput.value.trim();
  if (q) askAgent(q);
});

questionInput.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
    askAgent(questionInput.value.trim());
  }
});

quickQuestions.addEventListener("click", (e) => {
  const target = e.target?.closest?.("[data-question]");
  if (!target) return;
  questionInput.value = target.dataset.question;
  questionInput.focus();
});

clearChart();
chartPlaceholder.classList.remove("hidden");
setStatus("idle", "Ready");
