/**
 * Bin Status Component
 * Updates the circular gauge, status badge, and stats based on WebSocket data.
 */
class BinStatusPanel {
    constructor() {
        this.gaugeFill = document.getElementById('gaugeFill');
        this.gaugeValue = document.getElementById('gaugeValue');
        this.statusBadge = document.getElementById('statusBadge');
        this.badgeText = document.getElementById('badgeText');
        this.badgeIcon = document.getElementById('badgeIcon');
        this.wasteCount = document.getElementById('wasteCount');
        this.insideCount = document.getElementById('insideCount');
        this.outsideCount = document.getElementById('outsideCount');
        this.uptimeValue = document.getElementById('uptimeValue');
        this.detailText = document.getElementById('detailText');
        this.gaugeRing = document.getElementById('gaugeRing');

        this.startTime = Date.now();
        this._currentFill = 0;
        this._uptimeInterval = null;

        // The circumference of the gauge circle (r=85)
        this.circumference = 2 * Math.PI * 85; // ~534.07

        // Start uptime counter
        this._startUptime();
    }

    update(data) {
        if (!data) return;

        const fillPct = data.fill_percentage || 0; // Already 0-100 from backend
        const status = data.status || 'unknown';

        // Animate gauge fill
        this._animateGauge(fillPct);

        // Update gauge value
        this.gaugeValue.textContent = Math.round(fillPct);

        // Update gauge color class (SVG uses setAttribute, not .className)
        let gaugeClass = 'gauge-fill';
        if (status === 'empty') gaugeClass += ' status-empty';
        else if (status === 'partial') gaugeClass += ' status-partial';
        else if (status === 'overflowing') gaugeClass += ' status-overflowing';
        this.gaugeFill.setAttribute('class', gaugeClass);

        // Update status badge
        this.statusBadge.setAttribute('class', 'status-badge');
        if (status === 'empty') {
            this.statusBadge.classList.add('status-empty');
            this.badgeIcon.textContent = '✓';
            this.badgeText.textContent = 'Empty';
        } else if (status === 'partial') {
            this.statusBadge.classList.add('status-partial');
            this.badgeIcon.textContent = '◐';
            this.badgeText.textContent = 'Partially Filled';
        } else if (status === 'overflowing') {
            this.statusBadge.classList.add('status-overflowing');
            this.badgeIcon.textContent = '⚠';
            this.badgeText.textContent = 'Overflowing';
        } else {
            this.badgeIcon.textContent = '●';
            this.badgeText.textContent = 'Unknown';
        }

        // Update stats
        this.wasteCount.textContent = data.waste_count || 0;
        this.insideCount.textContent = data.waste_inside || 0;
        this.outsideCount.textContent = data.waste_outside || 0;

        // Update detail line
        this.detailText.textContent = data.details || 'Processing…';
    }

    _animateGauge(targetPct) {
        const fraction = Math.min(targetPct / 100, 1);
        const offset = this.circumference * (1 - fraction);
        this.gaugeFill.style.strokeDashoffset = offset;
    }

    _startUptime() {
        this._uptimeInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            if (elapsed < 60) {
                this.uptimeValue.textContent = `${elapsed}s`;
            } else if (elapsed < 3600) {
                const m = Math.floor(elapsed / 60);
                const s = elapsed % 60;
                this.uptimeValue.textContent = `${m}m ${s}s`;
            } else {
                const h = Math.floor(elapsed / 3600);
                const m = Math.floor((elapsed % 3600) / 60);
                this.uptimeValue.textContent = `${h}h ${m}m`;
            }
        }, 1000);
    }

    destroy() {
        if (this._uptimeInterval) clearInterval(this._uptimeInterval);
    }
}

// Export as global
window.BinStatusPanel = BinStatusPanel;
