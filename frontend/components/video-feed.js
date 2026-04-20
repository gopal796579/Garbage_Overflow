/**
 * Video Feed Component
 * Connects to /ws/video WebSocket and renders MJPEG frames on canvas.
 */
class VideoFeed {
    constructor() {
        this.canvas = document.getElementById('videoCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.overlay = document.getElementById('videoOverlay');
        this.liveBadge = document.getElementById('liveBadge');
        this.ws = null;
        this.connected = false;
        this.frameCount = 0;
        this.lastFpsTime = performance.now();
        this.fps = 0;
        this._reconnectTimer = null;
        this._reconnectDelay = 1000;
    }

    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws/video`;

        try {
            this.ws = new WebSocket(url);
            this.ws.onopen = () => this._onOpen();
            this.ws.onmessage = (e) => this._onMessage(e);
            this.ws.onclose = () => this._onClose();
            this.ws.onerror = (e) => this._onError(e);
        } catch (err) {
            console.error('[VideoFeed] Connection error:', err);
            this._scheduleReconnect();
        }
    }

    _onOpen() {
        console.log('[VideoFeed] Connected');
        this.connected = true;
        this._reconnectDelay = 1000;
        this.overlay.classList.add('hidden');
        this.liveBadge.classList.add('active');

        // Notify app
        window.dispatchEvent(new CustomEvent('video:connected'));
    }

    _onMessage(event) {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'frame' && msg.data) {
                this._renderFrame(msg.data);
            }
        } catch (err) {
            console.error('[VideoFeed] Parse error:', err);
        }
    }

    _renderFrame(base64Data) {
        const img = new Image();
        img.onload = () => {
            // Resize canvas to match image if needed
            if (this.canvas.width !== img.width || this.canvas.height !== img.height) {
                this.canvas.width = img.width;
                this.canvas.height = img.height;
            }
            this.ctx.drawImage(img, 0, 0);

            // FPS calculation
            this.frameCount++;
            const now = performance.now();
            const elapsed = now - this.lastFpsTime;
            if (elapsed >= 1000) {
                this.fps = Math.round((this.frameCount * 1000) / elapsed);
                this.frameCount = 0;
                this.lastFpsTime = now;
                window.dispatchEvent(new CustomEvent('video:fps', { detail: this.fps }));
            }
        };
        img.src = 'data:image/jpeg;base64,' + base64Data;
    }

    _onClose() {
        console.log('[VideoFeed] Disconnected');
        this.connected = false;
        this.overlay.classList.remove('hidden');
        this.overlay.querySelector('p').textContent = 'Reconnecting…';
        this.liveBadge.classList.remove('active');
        window.dispatchEvent(new CustomEvent('video:disconnected'));
        this._scheduleReconnect();
    }

    _onError(err) {
        console.error('[VideoFeed] Error:', err);
    }

    _scheduleReconnect() {
        if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
        this._reconnectTimer = setTimeout(() => {
            console.log('[VideoFeed] Attempting reconnect…');
            this.connect();
        }, this._reconnectDelay);
        // Exponential backoff, max 10s
        this._reconnectDelay = Math.min(this._reconnectDelay * 1.5, 10000);
    }

    destroy() {
        if (this._reconnectTimer) clearTimeout(this._reconnectTimer);
        if (this.ws) this.ws.close();
    }
}

// Export as global
window.VideoFeed = VideoFeed;
