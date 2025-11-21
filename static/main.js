function onMonthSelectChange(selectEl) {
  const value = selectEl.value; // "YYYY-MM"
  const [yearStr, monthStr] = value.split("-");
  const yearInput = document.getElementById("month-year-input");
  const monthInput = document.getElementById("month-month-input");
  if (yearInput && monthInput) {
    yearInput.value = yearStr;
    monthInput.value = parseInt(monthStr, 10);
  }
}

// DOMが準備できたらグラフを描画
document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("chartContainer");
  const canvas = document.getElementById("categoryChart");
  if (!container || !canvas) return;

  const labels = JSON.parse(container.dataset.labels || "[]");
  const values = JSON.parse(container.dataset.values || "[]");

  if (!labels.length) {
    // データが無いときは Chart.js 呼ばない
    container.style.display = "none";
    return;
  }

  const ctx = canvas.getContext("2d");

  // 適当に色を用意（カテゴリ数に応じてループ）
  const baseColors = [
    "#4a8cff",
    "#fb7185",
    "#22c55e",
    "#facc15",
    "#a855f7",
    "#06b6d4",
    "#f97316",
  ];
  const backgroundColors = labels.map(
    (_, i) => baseColors[i % baseColors.length]
  );

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: backgroundColors,
        },
      ],
    },
    options: {
      plugins: {
        legend: {
          position: "right",
          labels: {
            boxWidth: 14,
          },
        },
      },
    },
  });
});
