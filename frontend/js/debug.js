/**
 * Debug Console module.
 * Menampilkan log detail dari backend scraper + log lokal dari frontend.
 * Mendukung filter by level (all/info/warning/error).
 */
const DebugConsole = {
    _logs: [],       // cache log dari backend
    _filter: 'all',  // filter aktif

    init() {
        // Refresh button
        const refreshBtn = document.getElementById('btn-refresh-debug');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadFromServer());
        }

        // Clear button
        const clearBtn = document.getElementById('btn-clear-debug');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clear());
        }

        // Filter buttons
        document.querySelectorAll('.debug-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.debug-filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this._filter = btn.getAttribute('data-level');
                this.applyFilter();
            });
        });
    },

    /**
     * Tambah log baru dari kode frontend (auth.js, dll).
     */
    addLog(level, message) {
        const entry = {
            timestamp: new Date().toISOString(),
            level: level,
            message: message,
            source: 'frontend',
        };
        this._logs.push(entry);
        this._renderEntry(entry);
        this._scrollToBottom();
    },

    /**
     * Load logs dari backend (scraper engine logs).
     */
    async loadFromServer() {
        try {
            const data = await API.getScraperLogs(100);
            if (!data.logs || data.logs.length === 0) return;

            // Tambah logs baru yang belum ada (by timestamp + message)
            const existingKeys = new Set(
                this._logs.filter(l => l.source === 'backend').map(l => `${l.timestamp}|${l.message}`)
            );

            let added = 0;
            data.logs.forEach(log => {
                const key = `${log.timestamp}|${log.message}`;
                if (!existingKeys.has(key)) {
                    const entry = {
                        timestamp: log.timestamp,
                        level: (log.level || 'info').toLowerCase(),
                        message: log.message,
                        source: 'backend',
                    };
                    this._logs.push(entry);
                    added++;
                }
            });

            if (added > 0) {
                this._rerender();
            }
        } catch (e) {
            // Silently fail — server mungkin belum ready
        }
    },

    _renderEntry(entry) {
        const container = document.getElementById('debug-console');
        if (!container) return;

        // Hapus placeholder jika ada
        const placeholder = container.querySelector('.log-empty');
        if (placeholder) placeholder.remove();

        const el = this._createEntryEl(entry);
        container.appendChild(el);
    },

    _createEntryEl(entry) {
        const el = document.createElement('div');
        el.className = 'log-entry';
        el.setAttribute('data-level', entry.level);

        const time = entry.timestamp
            ? new Date(entry.timestamp).toLocaleTimeString('id-ID', { hour12: false })
            : '--:--:--';

        const sourceTag = entry.source === 'frontend'
            ? `<span style="color:var(--text-muted);font-size:0.7rem">[FE]</span>`
            : `<span style="color:var(--text-muted);font-size:0.7rem">[BE]</span>`;

        el.innerHTML = `
            <span class="log-time">${time}</span>
            ${sourceTag}
            <span class="log-level ${entry.level}">${entry.level.toUpperCase()}</span>
            <span class="log-message">${Utils.escapeHtml(entry.message)}</span>
        `;

        // Terapkan filter
        if (this._filter !== 'all' && entry.level !== this._filter) {
            el.classList.add('hidden-by-filter');
        }

        return el;
    },

    _rerender() {
        const container = document.getElementById('debug-console');
        if (!container) return;

        container.innerHTML = '';

        if (this._logs.length === 0) {
            container.innerHTML = '<div class="log-empty">Belum ada log debug.</div>';
            return;
        }

        // Sort by timestamp
        const sorted = [...this._logs].sort((a, b) =>
            new Date(a.timestamp) - new Date(b.timestamp)
        );

        sorted.forEach(entry => {
            container.appendChild(this._createEntryEl(entry));
        });

        this._scrollToBottom();
    },

    applyFilter() {
        document.querySelectorAll('#debug-console .log-entry').forEach(el => {
            const level = el.getAttribute('data-level');
            if (this._filter === 'all' || level === this._filter) {
                el.classList.remove('hidden-by-filter');
            } else {
                el.classList.add('hidden-by-filter');
            }
        });
    },

    clear() {
        this._logs = this._logs.filter(l => l.source === 'backend'); // hapus frontend logs
        this._logs = []; // hapus semua
        const container = document.getElementById('debug-console');
        if (container) {
            container.innerHTML = '<div class="log-empty">Log dibersihkan.</div>';
        }
    },

    _scrollToBottom() {
        const container = document.getElementById('debug-console');
        if (container) {
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 50);
        }
    },

    /**
     * Auto-refresh dari server setiap 5 detik saat di halaman settings.
     */
    startAutoRefresh() {
        this.loadFromServer();
        this._autoRefreshTimer = setInterval(() => this.loadFromServer(), 5000);
    },

    stopAutoRefresh() {
        if (this._autoRefreshTimer) {
            clearInterval(this._autoRefreshTimer);
            this._autoRefreshTimer = null;
        }
    },
};
