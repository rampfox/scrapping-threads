/**
 * API client module - communicates with FastAPI backend.
 */
const API = {
    baseUrl: '',

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // Posts
    async getPosts(page = 1, limit = 20, keyword = '', search = '') {
        let url = `/api/posts?page=${page}&limit=${limit}`;
        if (keyword) url += `&keyword=${encodeURIComponent(keyword)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        return this.request(url);
    },

    async getPostStats() {
        return this.request('/api/posts/stats');
    },

    async deletePost(id) {
        return this.request(`/api/posts/${id}`, { method: 'DELETE' });
    },

    // Keywords
    async getKeywords() {
        return this.request('/api/keywords');
    },

    async addKeyword(keyword) {
        return this.request('/api/keywords', {
            method: 'POST',
            body: { keyword },
        });
    },

    async updateKeyword(id, data) {
        return this.request(`/api/keywords/${id}`, {
            method: 'PUT',
            body: data,
        });
    },

    async deleteKeyword(id) {
        return this.request(`/api/keywords/${id}`, { method: 'DELETE' });
    },

    async scrapeKeywordNow(id) {
        return this.request(`/api/keywords/${id}/scrape-now`, { method: 'POST' });
    },

    // Settings
    async getSettings() {
        return this.request('/api/settings');
    },

    async updateSettings(data) {
        return this.request('/api/settings', {
            method: 'PUT',
            body: data,
        });
    },

    async updateProxy(data) {
        return this.request('/api/settings/proxy', {
            method: 'PUT',
            body: data,
        });
    },

    async exportData(format = 'json') {
        const response = await fetch(`/api/settings/export?format=${format}`, { method: 'POST' });
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `threads_data.${format}`;
        a.click();
        URL.revokeObjectURL(url);
    },

    // Auth
    async getAuthStatus() {
        return this.request('/api/auth/status');
    },

    async login(username, password) {
        return this.request('/api/auth/login', {
            method: 'POST',
            body: { username, password },
        });
    },

    async logout() {
        return this.request('/api/auth/logout', { method: 'POST' });
    },

    // Scraper
    async getScraperStatus() {
        return this.request('/api/scraper/status');
    },

    async startScraper() {
        return this.request('/api/scraper/start', { method: 'POST' });
    },

    async stopScraper() {
        return this.request('/api/scraper/stop', { method: 'POST' });
    },

    async getScraperLogs(limit = 50) {
        return this.request(`/api/scraper/logs?limit=${limit}`);
    },

    // Health
    async health() {
        return this.request('/api/health');
    },
};
