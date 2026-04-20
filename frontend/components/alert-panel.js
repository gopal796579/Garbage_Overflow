/**
 * Alert Panel Component
 * Manages real-time alert display with sound notifications.
 */
class AlertPanel {
    constructor() {
        this.alertList = document.getElementById('alertList');
        this.alertCountBadge = document.getElementById('alertCountBadge');
        this.alerts = [];
        this.maxAlerts = 50;
        this.soundEnabled = true;

        // Create audio context for alert sounds
        this._audioCtx = null;
    }

    addAlert(alertData) {
        this.alerts.unshift(alertData);
        if (this.alerts.length > this.maxAlerts) {
            this.alerts = this.alerts.slice(0, this.maxAlerts);
        }

        this._render();
        this._updateBadge();

        // Play sound for critical alerts
        if (alertData.severity === 'critical' && this.soundEnabled) {
            this._playAlertSound();
        }
    }

    loadAlerts(alertsArray) {
        this.alerts = alertsArray || [];
        this._render();
        this._updateBadge();
    }

    async resolveAlert(alertId) {
        try {
            const resp = await fetch(`/api/alerts/${alertId}/resolve`, { method: 'POST' });
            if (resp.ok) {
                const alert = this.alerts.find(a => a.id === alertId);
                if (alert) {
                    alert.resolved = true;
                    this._render();
                    this._updateBadge();
                }
            }
        } catch (err) {
            console.error('[AlertPanel] Resolve error:', err);
        }
    }

    _render() {
        if (this.alerts.length === 0) {
            this.alertList.innerHTML = `
                <div class="empty-state">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    <p>No alerts — all bins operating normally</p>
                </div>
            `;
            return;
        }

        this.alertList.innerHTML = this.alerts.map(alert => {
            const timeStr = this._formatTime(alert.timestamp);
            const severityClass = `severity-${alert.severity}`;
            const resolvedClass = alert.resolved ? 'resolved' : '';
            const icon = alert.severity === 'critical' ? '🚨' : '⚠️';

            return `
                <div class="alert-item ${severityClass} ${resolvedClass}" data-id="${alert.id}">
                    <span class="alert-icon">${icon}</span>
                    <div class="alert-content">
                        <div class="alert-message">${this._escapeHtml(alert.message)}</div>
                        <div class="alert-meta">
                            <span>${timeStr}</span>
                            <span>•</span>
                            <span>${alert.bin_id || 'BIN-001'}</span>
                            <span>•</span>
                            <span>${Math.round(alert.fill_percentage || 0)}%</span>
                            ${!alert.resolved ? `<button class="alert-resolve-btn" onclick="window._alertPanel.resolveAlert(${alert.id})">Resolve</button>` : '<span style="color: var(--green)">✓ Resolved</span>'}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    _updateBadge() {
        const unresolved = this.alerts.filter(a => !a.resolved).length;
        this.alertCountBadge.textContent = unresolved;
        this.alertCountBadge.classList.toggle('zero', unresolved === 0);
    }

    _formatTime(timestamp) {
        if (!timestamp) return '';
        try {
            const d = new Date(timestamp);
            return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        } catch {
            return timestamp;
        }
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    _playAlertSound() {
        try {
            if (!this._audioCtx) {
                this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            const ctx = this._audioCtx;

            // Create a short alert beep
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.setValueAtTime(660, ctx.currentTime + 0.1);
            osc.frequency.setValueAtTime(880, ctx.currentTime + 0.2);

            gain.gain.setValueAtTime(0.15, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);

            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.4);
        } catch (err) {
            // Audio not available — silently fail
        }
    }

    destroy() {
        if (this._audioCtx) this._audioCtx.close();
    }
}

// Export as global
window.AlertPanel = AlertPanel;
