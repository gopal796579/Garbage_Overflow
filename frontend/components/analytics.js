/**
 * Analytics Component
 * Renders fill-level timeline chart using Chart.js.
 */
class AnalyticsPanel {
    constructor() {
        this.chartCanvas = document.getElementById('fillChart');
        this.totalAlertsEl = document.getElementById('totalAlerts');
        this.overflowEventsEl = document.getElementById('overflowEvents');
        this.avgFillEl = document.getElementById('avgFill');
        this.chart = null;
        this._refreshInterval = null;

        this._initChart();
        this._startAutoRefresh();
    }

    _initChart() {
        const ctx = this.chartCanvas.getContext('2d');

        // Gradient fill
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(6, 182, 212, 0.3)');
        gradient.addColorStop(1, 'rgba(6, 182, 212, 0.02)');

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Fill Level (%)',
                        data: [],
                        borderColor: '#06b6d4',
                        backgroundColor: gradient,
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        pointHoverBackgroundColor: '#06b6d4',
                        pointHoverBorderColor: '#fff',
                        pointHoverBorderWidth: 2,
                    },
                    {
                        label: 'Waste Count',
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.05)',
                        borderWidth: 1.5,
                        borderDash: [5, 3],
                        tension: 0.4,
                        fill: false,
                        pointRadius: 0,
                        yAxisID: 'y1',
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#94a3b8',
                            font: { family: 'Inter', size: 11, weight: '500' },
                            padding: 15,
                            usePointStyle: true,
                            pointStyleWidth: 8,
                        },
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 22, 41, 0.95)',
                        titleColor: '#f1f5f9',
                        bodyColor: '#94a3b8',
                        borderColor: 'rgba(6, 182, 212, 0.3)',
                        borderWidth: 1,
                        titleFont: { family: 'Inter', weight: '600' },
                        bodyFont: { family: 'Inter' },
                        padding: 10,
                        cornerRadius: 8,
                        displayColors: true,
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#64748b',
                            font: { family: 'Inter', size: 10 },
                            maxTicksLimit: 10,
                            maxRotation: 0,
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.05)',
                        },
                    },
                    y: {
                        position: 'left',
                        min: 0,
                        max: 100,
                        ticks: {
                            color: '#64748b',
                            font: { family: 'Inter', size: 10 },
                            callback: (v) => v + '%',
                        },
                        grid: {
                            color: 'rgba(148, 163, 184, 0.06)',
                        },
                    },
                    y1: {
                        position: 'right',
                        min: 0,
                        ticks: {
                            color: '#64748b',
                            font: { family: 'Inter', size: 10 },
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    },
                },
            },
        });
    }

    async fetchAnalytics() {
        try {
            const resp = await fetch('/api/analytics');
            if (!resp.ok) return;
            const data = await resp.json();
            this._updateSummary(data);
            this._updateChart(data.history || []);
        } catch (err) {
            console.error('[Analytics] Fetch error:', err);
        }
    }

    addRealtimePoint(statusData) {
        if (!this.chart || !statusData) return;

        const now = new Date();
        const label = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const fill = statusData.fill_percentage || 0;
        const count = statusData.waste_count || 0;

        const labels = this.chart.data.labels;
        const fillData = this.chart.data.datasets[0].data;
        const countData = this.chart.data.datasets[1].data;

        labels.push(label);
        fillData.push(fill);
        countData.push(count);

        // Keep last 60 points
        const maxPoints = 60;
        if (labels.length > maxPoints) {
            labels.splice(0, labels.length - maxPoints);
            fillData.splice(0, fillData.length - maxPoints);
            countData.splice(0, countData.length - maxPoints);
        }

        this.chart.update('none'); // No animation for real-time
    }

    _updateChart(history) {
        if (!this.chart || !history.length) return;

        const labels = history.map(h => {
            try {
                const d = new Date(h.timestamp);
                return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            } catch {
                return '';
            }
        });

        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = history.map(h => h.fill_percentage || 0);
        this.chart.data.datasets[1].data = history.map(h => h.waste_count || 0);
        this.chart.update();
    }

    _updateSummary(data) {
        this.totalAlertsEl.textContent = data.total_alerts || 0;
        this.overflowEventsEl.textContent = data.overflow_events || 0;
        this.avgFillEl.textContent = `${Math.round(data.avg_fill || 0)}%`;
    }

    _startAutoRefresh() {
        // Fetch analytics every 30 seconds
        this._refreshInterval = setInterval(() => this.fetchAnalytics(), 30000);
    }

    destroy() {
        if (this._refreshInterval) clearInterval(this._refreshInterval);
        if (this.chart) this.chart.destroy();
    }
}

// Export as global
window.AnalyticsPanel = AnalyticsPanel;
