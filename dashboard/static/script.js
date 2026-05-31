// Web Audio API Synthesizer for high-tech sound alerts (no files required!)
class SoundEffectsGenerator {
    constructor() {
        this.ctx = null;
        this.enabled = true; // Enabled by default
    }

    init() {
        if (!this.ctx) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
    }

    playAlert() {
        if (!this.enabled) return;
        this.init();
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }

        const now = this.ctx.currentTime;
        
        // Dynamic Sci-Fi Double Alert Alarm Synthesizer
        const osc1 = this.ctx.createOscillator();
        const osc2 = this.ctx.createOscillator();
        const gainNode = this.ctx.createGain();

        osc1.type = 'sawtooth';
        osc1.frequency.setValueAtTime(880, now); // A5
        osc1.frequency.exponentialRampToValueAtTime(440, now + 0.15);
        
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(440, now); // A4
        osc2.frequency.exponentialRampToValueAtTime(220, now + 0.15);

        gainNode.gain.setValueAtTime(0.12, now);
        gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

        osc1.connect(gainNode);
        osc2.connect(gainNode);
        gainNode.connect(this.ctx.destination);

        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + 0.3);
        osc2.stop(now + 0.3);
    }

    playSuccess() {
        if (!this.enabled) return;
        this.init();
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }

        const now = this.ctx.currentTime;
        
        // Sci-Fi Positive UI Sweep Synthesizer
        const osc = this.ctx.createOscillator();
        const gainNode = this.ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(523.25, now); // C5
        osc.frequency.exponentialRampToValueAtTime(1046.50, now + 0.2); // C6

        gainNode.gain.setValueAtTime(0.08, now);
        gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

        osc.connect(gainNode);
        gainNode.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.3);
    }
}

const sounds = new SoundEffectsGenerator();

// Initialize Chart.js with dynamic Apple Neon Line Gradient
const ctx = document.getElementById('trafficChart').getContext('2d');
Chart.defaults.color = '#8c9cb2';
Chart.defaults.font.family = "'Inter', sans-serif";

// Create linear gradients for beautiful fill under curve
const cyanGradient = ctx.createLinearGradient(0, 0, 0, 240);
cyanGradient.addColorStop(0, 'rgba(0, 240, 255, 0.25)');
cyanGradient.addColorStop(1, 'rgba(0, 240, 255, 0.00)');

const trafficChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: Array(25).fill(''),
        datasets: [{
            label: 'Network Bandwidth (Mbps)',
            data: Array(25).fill(12.5),
            borderColor: '#00f0ff',
            borderWidth: 3,
            backgroundColor: cyanGradient,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointBackgroundColor: '#00f0ff',
            pointBorderColor: '#fff'
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 150 // Slight duration for premium smooth sliding
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255, 255, 255, 0.04)' },
                border: { dash: [5, 5] }
            },
            x: {
                grid: { display: false }
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(10, 15, 30, 0.85)',
                titleFont: { family: "'Outfit', sans-serif", weight: 'bold' },
                bodyFont: { family: "'Inter', sans-serif" },
                borderColor: 'rgba(255, 255, 255, 0.08)',
                borderWidth: 1,
                displayColors: false
            }
        }
    }
});

// State parameters tracking
let knownAlertIds = new Set();
let isFirstLoad = true;

// Tab Navigation Switching
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');

tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        const targetTab = button.getAttribute('data-tab');
        
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabPanes.forEach(pane => pane.classList.remove('active'));
        
        button.classList.add('active');
        document.getElementById(targetTab).classList.add('active');
    });
});

// Update System Clock
function updateClock() {
    const now = new Date();
    document.getElementById('time-display').innerText = now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}
setInterval(updateClock, 1000);
updateClock();

// Fetch Telemetry Stats
async function fetchTelemetry() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        updateKPIs(data.stats);
        updateChart(data.stats.total_bandwidth);
        updateAlerts(data.recent_alerts);
        updateFlows(data.flows);
        updateSystemStatus(data.stats.status, data.stats.simulated_attack_type);
        updateBlockedIPsList(data.stats.blocked_ips_list);
        updateSimulationUI(data.stats.simulated_attack_type);
        
        isFirstLoad = false;
    } catch (error) {
        console.error("Error fetching telemetry:", error);
    }
}

function updateKPIs(stats) {
    document.getElementById('val-bandwidth').innerText = stats.total_bandwidth.toFixed(2);
    document.getElementById('val-flows').innerText = stats.active_flows;
    document.getElementById('val-blocked').innerText = stats.blocked_ips;
    
    // Sync sensitivity slider value on first load
    if (isFirstLoad) {
        const slider = document.getElementById('sensitivity-slider');
        slider.value = stats.sensitivity_threshold;
        document.getElementById('threshold-val').innerText = stats.sensitivity_threshold.toFixed(2);
    }
}

function updateChart(bandwidth) {
    const data = trafficChart.data.datasets[0].data;
    data.push(bandwidth);
    if (data.length > 25) data.shift();
    
    // Set chart dynamic glowing bounds
    const maxVal = Math.max(...data);
    trafficChart.options.scales.y.suggestedMax = maxVal > 100 ? maxVal * 1.1 : 100;
    trafficChart.update();
}

function updateAlerts(alerts) {
    const list = document.getElementById('alerts-list');
    
    if (!alerts || alerts.length === 0) {
        list.innerHTML = '<li class="alert-item empty-state">No anomalous activity detected.</li>';
        return;
    }
    
    list.innerHTML = '';
    
    // Iterate reverse (newest first)
    alerts.slice().reverse().forEach((alert, idx) => {
        const li = document.createElement('li');
        li.className = `alert-item ${alert.type}`;
        
        // Generate an ID for audio triggers
        const alertId = `${alert.timestamp}-${alert.type}-${alert.target_ip}`;
        
        // Sound trigger logic (only on new alarms, skip during page load)
        if (!isFirstLoad && idx === 0 && !knownAlertIds.has(alertId)) {
            if (alert.type !== "Normal") {
                sounds.playAlert();
            } else {
                sounds.playSuccess();
            }
        }
        knownAlertIds.add(alertId);
        
        const actionClass = alert.action ? `alert-badge-${alert.action}` : '';
        const actionHtml = alert.action ? `<span class="alert-badge ${actionClass}">${alert.action}</span>` : '';
        
        let icon = 'fa-triangle-exclamation';
        if (alert.type === 'DDoS') icon = 'fa-cloud-bolt';
        else if (alert.type === 'PortScan') icon = 'fa-radar';
        else if (alert.type === 'Normal') icon = 'fa-circle-check';
        
        li.innerHTML = `
            <div class="alert-head">
                <span class="alert-title"><i class="fa-solid ${icon}"></i> ${alert.type.toUpperCase()} DETECTED</span>
                <span class="alert-time">${alert.timestamp}</span>
            </div>
            <div class="alert-body">
                <span>Target Node: ${alert.target_ip}</span>
                ${actionHtml}
            </div>
        `;
        list.appendChild(li);
    });
}

function updateFlows(flows) {
    const tbody = document.getElementById('flows-body');
    
    if (!flows || flows.length === 0) {
        return;
    }
    
    tbody.innerHTML = '';
    flows.slice().reverse().forEach(flow => {
        const tr = document.createElement('tr');
        
        const isMalicious = flow.is_malicious;
        const badgeClass = isMalicious ? 'badge-threat' : 'badge-clean';
        const badgeText = isMalicious ? 'THREAT ANOMALY' : 'CLEAN TRAFFIC';
        
        tr.innerHTML = `
            <td style="font-family: var(--font-heading); color: var(--text-muted); font-size: 0.8rem;">${flow.timestamp}</td>
            <td style="font-weight: 600;">${flow.source_ip}</td>
            <td style="font-weight: 600;">${flow.dest_ip}</td>
            <td><span style="font-weight: 500; font-size: 0.82rem; padding: 2px 8px; border-radius: 4px; background: rgba(255,255,255,0.03); border: 1px solid var(--glass-border);">${flow.protocol}</span></td>
            <td><span class="flow-badge ${badgeClass}">${badgeText}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function updateSystemStatus(status, attackType) {
    const badge = document.getElementById('status-indicator');
    const text = document.getElementById('system-status-text');
    
    if (attackType !== "None") {
        if (attackType === "DDoS") {
            badge.className = 'system-status glass-badge active-critical';
            text.innerText = 'DDoS ATTACK ACTIVE';
        } else if (attackType === "PortScan") {
            badge.className = 'system-status glass-badge active-warning';
            text.innerText = 'PORT SCAN IN PROGRESS';
        } else {
            badge.className = 'system-status glass-badge active-normal';
            text.innerText = 'NORMAL LOAD TEST';
        }
    } else if (status === 'CRITICAL') {
        badge.className = 'system-status glass-badge active-critical';
        text.innerText = 'THREAT MITIGATED';
    } else if (status === 'WARNING') {
        badge.className = 'system-status glass-badge active-warning';
        text.innerText = 'PROBE INTERCEPTED';
    } else {
        badge.className = 'system-status glass-badge active-normal';
        text.innerText = 'SYSTEM SECURED';
    }
}

// Blocked IPs Firewall Control
function updateBlockedIPsList(blockedList) {
    const container = document.getElementById('blocked-ips-list');
    
    if (!blockedList || blockedList.length === 0) {
        container.innerHTML = '<li class="empty-state">No IP addresses currently blocked.</li>';
        return;
    }
    
    container.innerHTML = '';
    blockedList.forEach(ip => {
        const li = document.createElement('li');
        li.className = 'blocked-ip-item';
        li.innerHTML = `
            <div>
                <i class="fa-solid fa-ban" style="color: var(--red); margin-right: 10px;"></i>
                <strong>${ip}</strong>
            </div>
            <button class="btn-unblock" onclick="unblockIP('${ip}')">Unblock</button>
        `;
        container.appendChild(li);
    });
}

async function unblockIP(ip) {
    try {
        const response = await fetch('/api/unblock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: ip })
        });
        const result = await response.json();
        
        if (result.status === 'success') {
            sounds.playSuccess();
            fetchTelemetry(); // Instant refresh
        } else {
            alert(result.message);
        }
    } catch (e) {
        console.error("Unblock action error:", e);
    }
}

// Range Slider Sensitivity Trigger
const slider = document.getElementById('sensitivity-slider');
const sliderVal = document.getElementById('threshold-val');

slider.addEventListener('input', async (e) => {
    const val = parseFloat(e.target.value);
    sliderVal.innerText = val.toFixed(2);
    
    // Post update to Flask server
    try {
        await fetch('/api/threshold', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sensitivity_threshold: val })
        });
    } catch (err) {
        console.error("Failed to sync sensitivity threshold:", err);
    }
});

// Attack Simulator triggers
const simCards = document.querySelectorAll('.sim-card');
const stopSimBtn = document.getElementById('btn-stop-sim');

simCards.forEach(card => {
    card.addEventListener('click', async () => {
        const attack = card.getAttribute('data-attack');
        triggerSimulation(attack);
    });
});

stopSimBtn.addEventListener('click', () => {
    triggerSimulation('None');
});

async function triggerSimulation(type) {
    try {
        const response = await fetch('/api/simulate-attack', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ attack_type: type })
        });
        const res = await response.json();
        
        if (res.status === 'success') {
            if (type !== 'None') {
                sounds.playAlert();
            } else {
                sounds.playSuccess();
            }
            fetchTelemetry();
        }
    } catch (e) {
        console.error("Simulation trigger failed:", e);
    }
}

function updateSimulationUI(attackType) {
    const activeBadge = document.getElementById('active-sim-badge');
    const simLabel = document.getElementById('current-sim-text');
    
    // Reset all simulation button styles
    simCards.forEach(c => {
        c.classList.remove('selected');
        c.querySelector('.btn-simulate').innerText = 'Trigger';
    });
    
    if (attackType !== "None") {
        stopSimBtn.classList.remove('hide');
        simLabel.innerText = `${attackType.toUpperCase()} Attack Simulation Active`;
        activeBadge.style.borderColor = 'rgba(255, 34, 85, 0.3)';
        
        // Highlight chosen card
        const selectedCard = document.querySelector(`.sim-card[data-attack="${attackType}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
            selectedCard.querySelector('.btn-simulate').innerText = 'Simulating...';
        }
    } else {
        stopSimBtn.classList.add('hide');
        simLabel.innerText = 'No Simulation Active';
        activeBadge.style.borderColor = 'var(--glass-border)';
    }
}

// Audio Alerts Toggle Button
const audioBtn = document.getElementById('audio-toggle-btn');
audioBtn.addEventListener('click', () => {
    sounds.enabled = !sounds.enabled;
    if (sounds.enabled) {
        audioBtn.classList.remove('muted');
        audioBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
        sounds.playSuccess();
    } else {
        audioBtn.classList.add('muted');
        audioBtn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
    }
});

// Load AI Model Statistics dynamic tab components
async function loadAIStats() {
    try {
        const response = await fetch('/api/model-stats');
        const stats = await response.json();
        
        // 1. Render accuracy and parameters details
        document.getElementById('model-accuracy-text').innerText = `${(stats.accuracy * 100).toFixed(2)}%`;
        document.getElementById('best-estimators').innerText = `${stats.best_params.n_estimators || 50} trees`;
        document.getElementById('best-depth').innerText = `${stats.best_params.max_depth || 'None'} layers`;
        document.getElementById('class-weights').innerText = stats.best_params.class_weight || 'Balanced';
        
        // 2. Render classification matrix table
        const tbody = document.getElementById('metrics-classes-body');
        tbody.innerHTML = '';
        for (const [className, metrics] of Object.entries(stats.metrics_by_class)) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 700; color: var(--text-primary);">${className}</td>
                <td>${metrics.precision.toFixed(3)}</td>
                <td>${metrics.recall.toFixed(3)}</td>
                <td style="font-weight: 700; color: var(--cyan);">${metrics.f1_score.toFixed(3)}</td>
            `;
            tbody.appendChild(tr);
        }
        
        // 3. Render Decision tree Feature Importances
        const featContainer = document.getElementById('feature-importance-container');
        featContainer.innerHTML = '';
        
        // Sort feature importances descending
        const sortedFeatures = Object.entries(stats.feature_importances).sort((a, b) => b[1] - a[1]);
        
        sortedFeatures.forEach(([name, val]) => {
            const row = document.createElement('div');
            row.className = 'feat-bar-item';
            
            // Clean up feature name labels
            const cleanName = name.replace('_', ' ');
            
            row.innerHTML = `
                <div class="feat-bar-label">
                    <span class="feat-name">${cleanName}</span>
                    <span class="feat-val">${(val * 100).toFixed(1)}%</span>
                </div>
                <div class="feat-bar-outer">
                    <div class="feat-bar-inner" style="width: 0%;"></div>
                </div>
            `;
            featContainer.appendChild(row);
            
            // Slight delay to trigger CSS transition animation beautifully
            setTimeout(() => {
                row.querySelector('.feat-bar-inner').style.width = `${val * 100}%`;
            }, 100);
        });
        
        // 4. Render Confusion Matrix cells
        const matrixContainer = document.getElementById('confusion-matrix-cells');
        matrixContainer.innerHTML = '';
        
        const matrix = stats.confusion_matrix;
        
        // Loop rows (True labels)
        for (let r = 0; r < matrix.length; r++) {
            const rowSum = matrix[r].reduce((a, b) => a + b, 0);
            
            // Loop columns (Predicted labels)
            for (let c = 0; c < matrix[r].length; c++) {
                const val = matrix[r][c];
                const pct = rowSum > 0 ? (val / rowSum * 100) : 0;
                
                const cell = document.createElement('div');
                cell.className = 'matrix-cell';
                
                // Highlight diagonal cells
                if (r === c) {
                    cell.className += ` diagonal-${r}`;
                }
                
                cell.innerHTML = `
                    <span class="cell-val">${val}</span>
                    <span class="cell-pct">${pct.toFixed(1)}%</span>
                `;
                matrixContainer.appendChild(cell);
            }
        }
        
    } catch (e) {
        console.error("Error loading model stats:", e);
    }
}

// Continuous polling configuration
setInterval(fetchTelemetry, 1000);
fetchTelemetry();

// Load AI Tab details once on startup
loadAIStats();
