/**
 * Smart Garbage Overflow Detection — Main Application
 * Orchestrates all components and WebSocket connections.
 */
(function () {
    'use strict';

    // ── Component instances ──
    let videoFeed;
    let binStatus;
    let alertPanel;
    let analytics;
    let statusWs = null;
    let statusReconnectTimer = null;
    let statusReconnectDelay = 1000;
    let _statusUpdateCount = 0;

    // ── Initialize ──
    function init() {
        console.log('[App] Initializing Smart Garbage Detection Dashboard…');

        // Create components
        videoFeed = new VideoFeed();
        binStatus = new BinStatusPanel();
        alertPanel = new AlertPanel();
        analytics = new AnalyticsPanel();

        // Store alertPanel globally for resolve buttons
        window._alertPanel = alertPanel;

        // Connect video feed
        videoFeed.connect();

        // Connect status WebSocket
        connectStatusWs();

        // Load initial data
        loadInitialData();

        // Listen for events
        window.addEventListener('video:connected', onVideoConnected);
        window.addEventListener('video:disconnected', onVideoDisconnected);
        window.addEventListener('video:fps', onFpsUpdate);

        console.log('[App] Dashboard initialized');
    }

    // ── Status WebSocket ──
    function connectStatusWs() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws/status`;

        try {
            statusWs = new WebSocket(url);
            statusWs.onopen = () => {
                console.log('[App] Status WS connected');
                statusReconnectDelay = 1000;
                updateConnectionStatus(true);
            };
            statusWs.onmessage = (e) => {
                try {
                    const msg = JSON.parse(e.data);
                    handleStatusMessage(msg);
                } catch (err) {
                    console.error('[App] Status parse error:', err);
                }
            };
            statusWs.onclose = () => {
                console.log('[App] Status WS disconnected');
                updateConnectionStatus(false);
                scheduleStatusReconnect();
            };
            statusWs.onerror = () => {};
        } catch (err) {
            scheduleStatusReconnect();
        }
    }

    function scheduleStatusReconnect() {
        if (statusReconnectTimer) clearTimeout(statusReconnectTimer);
        statusReconnectTimer = setTimeout(() => {
            connectStatusWs();
        }, statusReconnectDelay);
        statusReconnectDelay = Math.min(statusReconnectDelay * 1.5, 10000);
    }

    // ── Message Handling ──
    function handleStatusMessage(msg) {
        switch (msg.type) {
            case 'status':
                binStatus.update(msg.data);
                // Add to real-time chart every 5th update (~every second)
                _statusUpdateCount++;
                if (_statusUpdateCount % 5 === 0) {
                    analytics.addRealtimePoint(msg.data);
                }
                break;

            case 'alert':
                alertPanel.addAlert(msg.data);
                // Flash the alert card
                const alertCard = document.getElementById('alertCard');
                alertCard.classList.add('shake');
                setTimeout(() => alertCard.classList.remove('shake'), 500);
                break;

            default:
                console.log('[App] Unknown message type:', msg.type);
        }
    }

    // ── Load Initial Data ──
    async function loadInitialData() {
        try {
            // Load alerts
            const alertResp = await fetch('/api/alerts');
            if (alertResp.ok) {
                const data = await alertResp.json();
                alertPanel.loadAlerts(data.alerts || []);
            }
        } catch (err) {
            console.error('[App] Failed to load alerts:', err);
        }

        // Load analytics
        analytics.fetchAnalytics();
    }

    // ── Event Handlers ──
    function onVideoConnected() {
        updateConnectionStatus(true);
    }

    function onVideoDisconnected() {
        updateConnectionStatus(false);
    }

    function onFpsUpdate(e) {
        const fps = e.detail;
        document.getElementById('fpsValue').textContent = fps;
    }

    function updateConnectionStatus(connected) {
        const el = document.getElementById('connectionStatus');
        const textEl = el.querySelector('.status-text');

        if (connected) {
            el.classList.add('connected');
            el.classList.remove('disconnected');
            textEl.textContent = 'Connected';
        } else {
            el.classList.remove('connected');
            el.classList.add('disconnected');
            textEl.textContent = 'Disconnected';
        }
    }

    // ── Start on DOM ready ──
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
