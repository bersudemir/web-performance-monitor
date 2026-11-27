"use strict";
if (typeof Chart === "undefined") {
  document.getElementById("response-chart").hidden = true;
  document.getElementById("chart-fallback").hidden = false;
} else {
  const data = JSON.parse(document.getElementById("chart-data").textContent);
  new Chart(document.getElementById("response-chart"), {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [{ label: "Yanıt süresi (ms)", data: data.values, borderColor: "#4f46e5", backgroundColor: "rgba(79,70,229,0.07)", fill: true, tension: 0.25, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      locale: "tr-TR",
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, title: { display: true, text: "Milisaniye (ms)" }, grid: { color: "#eef0f5" } },
        x: { grid: { display: false }, ticks: { maxTicksLimit: 6, maxRotation: 0 } }
      }
    }
  });
}
