let chartCount, chartAmount;

function updateCharts(period1, period2) {
    let months = period1.months_labels || period2.months_labels || [];
    
    const period1Count = period1.monthly_totals || [];
    const period2Count = period2.monthly_totals || [];
    const period1Amount = (period1.monthly_amounts || []).map(v => Math.round(v / 1000));
    const period2Amount = (period2.monthly_amounts || []).map(v => Math.round(v / 1000));
    
    if (chartCount) chartCount.destroy();
    const ctxCount = document.getElementById('chartCount');
    if (ctxCount && months.length > 0) {
        chartCount = new Chart(ctxCount, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [
                    { label: `Период 1 (${period1.year})`, data: period1Count, backgroundColor: '#4a90e2', borderRadius: 6 },
                    { label: `Период 2 (${period2.year})`, data: period2Count, backgroundColor: '#e74c3c', borderRadius: 6 }
                ]
            },
            options: { responsive: true, maintainAspectRatio: true, scales: { y: { beginAtZero: true } } }
        });
    }
    
    if (chartAmount) chartAmount.destroy();
    const ctxAmount = document.getElementById('chartAmount');
    if (ctxAmount && months.length > 0) {
        chartAmount = new Chart(ctxAmount, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [
                    { label: `Период 1 (${period1.year})`, data: period1Amount, backgroundColor: '#4a90e2', borderRadius: 6 },
                    { label: `Период 2 (${period2.year})`, data: period2Amount, backgroundColor: '#e74c3c', borderRadius: 6 }
                ]
            },
            options: { responsive: true, maintainAspectRatio: true, scales: { y: { beginAtZero: true } } }
        });
    }
}

function updatePeriodUI(data, prefix) {
    let title = `${data.year}`;
    if (data.month_from && data.month_to) title += ` (${data.month_from}-${data.month_to})`;
    else if (data.month_from) title += ` (мес. ${data.month_from})`;
    document.getElementById(`${prefix}Title`).innerText = title;
    
    document.getElementById(`${prefix}Total`).innerText = data.total;
    document.getElementById(`${prefix}Amount`).innerText = formatNumber(data.total_amount);
    document.getElementById(`${prefix}Completed`).innerText = data.completed;
    document.getElementById(`${prefix}InProgress`).innerText = data.in_progress;
    
    document.getElementById(`${prefix}NewCount`).innerText = data.new_count;
    document.getElementById(`${prefix}OldCount`).innerText = data.old_count;
    document.getElementById(`${prefix}CompletedCount`).innerText = data.completed;
    document.getElementById(`${prefix}InProgressCount`).innerText = data.in_progress;
    document.getElementById(`${prefix}TotalCount`).innerText = data.total;
    
    document.getElementById(`${prefix}NewAmount`).innerText = formatNumber(data.new_amount);
    document.getElementById(`${prefix}OldAmount`).innerText = formatNumber(data.old_amount);
    document.getElementById(`${prefix}CompletedAmount`).innerText = formatNumber(data.completed_amount);
    document.getElementById(`${prefix}InProgressAmount`).innerText = formatNumber(data.in_progress_amount);
    document.getElementById(`${prefix}TotalAmount`).innerText = formatNumber(data.total_amount);
}

function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    return num.toLocaleString('ru-RU');
}

function loadComparison() {
    const p1_year = document.getElementById('period1_year').value;
    const p1_from = document.getElementById('period1_month_from').value;
    const p1_to = document.getElementById('period1_month_to').value;
    const p2_year = document.getElementById('period2_year').value;
    const p2_from = document.getElementById('period2_month_from').value;
    const p2_to = document.getElementById('period2_month_to').value;
    
    const url = `/api/stats?period1_year=${p1_year}&period1_month_from=${p1_from}&period1_month_to=${p1_to}&period2_year=${p2_year}&period2_month_from=${p2_from}&period2_month_to=${p2_to}`;
    
    fetch(url).then(r => r.json()).then(data => {
        if (data.period1 && data.period2) {
            updateCharts(data.period1, data.period2);
            updatePeriodUI(data.period1, 'period1');
            updatePeriodUI(data.period2, 'period2');
        }
    }).catch(e => console.error('Ошибка:', e));
}
