(function () {
    const el = document.getElementById('dashboard-chart-data');
    if (!el || typeof Chart === 'undefined') return;

    const data = JSON.parse(el.textContent);
    const muted = '#7da8cc';
    const grid = 'rgba(30, 58, 95, 0.45)';

    Chart.defaults.color = muted;
    Chart.defaults.borderColor = grid;
    Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif';

    const baseOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { boxWidth: 12, boxHeight: 12, padding: 16 },
            },
        },
    };

    const trendCanvas = document.getElementById('chart-investment-trend');
    if (trendCanvas) {
        new Chart(trendCanvas, {
            type: 'line',
            data: {
                labels: data.investment_trend.labels,
                datasets: [{
                    label: '投资金额 (USDT)',
                    data: data.investment_trend.values,
                    borderColor: '#00b4ff',
                    backgroundColor: 'rgba(0, 180, 255, 0.12)',
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#00b4ff',
                }],
            },
            options: {
                ...baseOptions,
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (v) => v.toLocaleString() },
                    },
                },
                plugins: {
                    ...baseOptions.plugins,
                    legend: { display: false },
                },
            },
        });
    }

    const rankCanvas = document.getElementById('chart-team-ranking');
    if (rankCanvas && data.ranking) {
        new Chart(rankCanvas, {
            type: 'bar',
            data: {
                labels: data.ranking.labels,
                datasets: [{
                    label: '投资 (USDT)',
                    data: data.ranking.values,
                    backgroundColor: 'rgba(0, 102, 255, 0.75)',
                    borderRadius: 6,
                    maxBarThickness: 28,
                }],
            },
            options: {
                indexAxis: 'y',
                ...baseOptions,
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { callback: (v) => v.toLocaleString() },
                    },
                    y: { grid: { display: false } },
                },
                plugins: {
                    ...baseOptions.plugins,
                    legend: { display: false },
                },
            },
        });
    }
})();
