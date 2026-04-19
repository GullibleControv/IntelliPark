/**
 * analytics.js
 *
 * Fetches occupancy trend data from GET /api/parking/analytics and renders
 * a Chart.js line chart on the dashboard.  Also polls GET
 * /api/parking/detection-health to highlight stale detector connections.
 *
 * CONCEPT – Chart.js "Data-driven" pattern:
 *   We keep one `chart` instance alive and call `chart.data.labels = [...]`
 *   + `chart.update()` on each refresh instead of destroying and re-creating.
 *   This avoids a visible flash and is cheaper on the browser.
 */

// Use an empty string so every fetch URL becomes a relative path (e.g.
// "/api/parking/analytics").  Relative paths are always same-origin,
// which eliminates CORS entirely since Flask serves both the frontend
// and the API from the same port.
const API_BASE = '';

// ─── Chart instance (module-level singleton) ──────────────────────────────────
let analyticsChart = null;

/**
 * Format an ISO datetime string into a short "HH:mm" label for the X-axis.
 * @param {string} isoString
 * @returns {string}
 */
function formatHourLabel(isoString) {
    const d = new Date(isoString + 'Z'); // treat as UTC
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Initialise (or re-initialise) the Chart.js instance.
 * Called once on page load; subsequent refreshes just update the data.
 */
function initChart() {
    const ctx = document.getElementById('analyticsChart');
    if (!ctx) return;

    if (analyticsChart) {
        analyticsChart.destroy();
    }

    analyticsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Occupancy %',
                data: [],
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.08)',
                borderWidth: 2,
                pointRadius: 3,
                pointHoverRadius: 5,
                tension: 0.35,   // slight curve — visually smoother
                fill: true
            }]
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.parsed.y.toFixed(1)} % occupied`
                    }
                }
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    ticks: { callback: v => v + '%' },
                    grid: { color: 'rgba(0,0,0,.05)' }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 12,
                        maxRotation: 0
                    },
                    grid: { display: false }
                }
            }
        }
    });
}

// ─── Fetch + render analytics ─────────────────────────────────────────────────
async function loadAnalytics() {
    const location = document.getElementById('analyticsLocation')?.value || '';
    const params = new URLSearchParams({ hours: 24 });
    if (location) params.append('location', location);

    try {
        const res = await fetch(`${API_BASE}/api/parking/analytics?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // Update chart data without destroying the instance
        const labels = data.timeline.map(t => formatHourLabel(t.hour));
        const rates  = data.timeline.map(t => t.occupancy_rate);

        analyticsChart.data.labels = labels;
        analyticsChart.data.datasets[0].data = rates;
        analyticsChart.update('none');  // 'none' = skip animation on refresh

        // Update summary bar
        const s = data.summary;
        document.getElementById('analyticsAvg').textContent = s.avg_occupancy_rate + '%';
        document.getElementById('analyticsPeak').textContent = s.peak_rate + '%';
        document.getElementById('analyticsPeakHour').textContent =
            s.peak_hour ? formatHourLabel(s.peak_hour) : '--';
        document.getElementById('analyticsTotalEvents').textContent = s.total_events;

    } catch (err) {
        console.error('Analytics fetch failed:', err);
    }
}

// ─── Fetch + render detector health ──────────────────────────────────────────
async function loadDetectionHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/parking/detection-health`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // Badge
        const badge = document.getElementById('healthBadge');
        if (data.stale_spaces === 0) {
            badge.textContent = `✓ All ${data.healthy_spaces} spaces live`;
            badge.style.background = '#e8f5e9';
            badge.style.color = '#2e7d32';
        } else {
            badge.textContent = `⚠ ${data.stale_spaces} stale / ${data.healthy_spaces} live`;
            badge.style.background = '#fff3e0';
            badge.style.color = '#e65100';
        }

        // Per-space cards
        const grid = document.getElementById('healthGrid');
        if (!grid) return;
        grid.innerHTML = data.spaces.map(sp => `
            <div style="
                padding:.75rem 1rem;border-radius:10px;
                background:${sp.is_stale ? '#fff8e1' : '#f1f8e9'};
                border:1px solid ${sp.is_stale ? '#ffe082' : '#a5d6a7'};
                font-size:.82rem;
            ">
                <div style="font-weight:600;margin-bottom:.2rem;">${sp.name}</div>
                <div style="color:#777;">${sp.location}</div>
                <div style="margin-top:.35rem;">
                    ${sp.last_detected_at
                        ? `Last seen: ${new Date(sp.last_detected_at + 'Z')
                              .toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                        : '<em>Never detected</em>'}
                </div>
                <div style="margin-top:.3rem;font-weight:600;
                    color:${sp.is_stale ? '#e65100' : '#2e7d32'};">
                    ${sp.is_stale ? '● Stale' : '● Live'}
                </div>
            </div>
        `).join('');

    } catch (err) {
        console.error('Health fetch failed:', err);
    }
}

// ─── Populate location filter from /api/parking/locations ────────────────────
async function populateLocationFilter() {
    try {
        const res = await fetch(`${API_BASE}/api/parking/locations`);
        if (!res.ok) return;
        const data = await res.json();

        const sel = document.getElementById('analyticsLocation');
        if (!sel) return;

        data.locations.forEach(loc => {
            const opt = document.createElement('option');
            opt.value = loc;
            opt.textContent = loc;
            sel.appendChild(opt);
        });
    } catch (err) { /* silent */ }
}

// ─── Wiring ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    // Guard — only run on pages that have the analytics canvas
    if (!document.getElementById('analyticsChart')) return;

    initChart();
    await populateLocationFilter();
    loadAnalytics();
    loadDetectionHealth();

    // Refresh button
    document.getElementById('refreshAnalytics')?.addEventListener('click', () => {
        loadAnalytics();
        loadDetectionHealth();
    });

    // Re-fetch when location filter changes
    document.getElementById('analyticsLocation')?.addEventListener('change', loadAnalytics);

    // Auto-refresh every 60 seconds
    setInterval(() => {
        loadAnalytics();
        loadDetectionHealth();
    }, 60_000);
});
