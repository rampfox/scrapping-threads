/**
 * Settings component.
 */
const Settings = {
    init() {
        // Interval slider
        const slider = document.getElementById('interval-slider');
        if (slider) {
            slider.addEventListener('input', (e) => {
                this.updateIntervalDisplay(parseInt(e.target.value));
            });
        }

        // Save interval
        const saveIntervalBtn = document.getElementById('btn-save-interval');
        if (saveIntervalBtn) {
            saveIntervalBtn.addEventListener('click', () => this.saveInterval());
        }

        // Proxy toggle
        const proxyToggle = document.getElementById('proxy-toggle');
        if (proxyToggle) {
            proxyToggle.addEventListener('change', (e) => {
                const config = document.getElementById('proxy-config');
                if (config) config.style.display = e.target.checked ? 'block' : 'none';
            });
        }

        // Save proxy
        const saveProxyBtn = document.getElementById('btn-save-proxy');
        if (saveProxyBtn) {
            saveProxyBtn.addEventListener('click', () => this.saveProxy());
        }

        // Save CAPTCHA
        const saveCaptchaBtn = document.getElementById('btn-save-captcha');
        if (saveCaptchaBtn) {
            saveCaptchaBtn.addEventListener('click', () => this.saveCaptcha());
        }

        // Export buttons
        const exportJsonBtn = document.getElementById('btn-export-json');
        const exportCsvBtn = document.getElementById('btn-export-csv');
        if (exportJsonBtn) {
            exportJsonBtn.addEventListener('click', () => {
                API.exportData('json');
                Utils.toast('Exporting JSON...', 'info');
            });
        }
        if (exportCsvBtn) {
            exportCsvBtn.addEventListener('click', () => {
                API.exportData('csv');
                Utils.toast('Exporting CSV...', 'info');
            });
        }

        // Refresh logs
        const refreshLogsBtn = document.getElementById('btn-refresh-logs');
        if (refreshLogsBtn) {
            refreshLogsBtn.addEventListener('click', () => this.loadLogs());
        }
    },

    async load() {
        try {
            const data = await API.getSettings();

            // Interval
            const slider = document.getElementById('interval-slider');
            if (slider) {
                slider.value = data.polling_interval;
                this.updateIntervalDisplay(data.polling_interval);
            }

            // Proxy
            const proxyToggle = document.getElementById('proxy-toggle');
            if (proxyToggle) {
                proxyToggle.checked = data.proxy.enabled;
                const config = document.getElementById('proxy-config');
                if (config) config.style.display = data.proxy.enabled ? 'block' : 'none';
            }

            // Proxy stats
            const proxyCount = document.getElementById('proxy-count');
            const proxyHealthy = document.getElementById('proxy-healthy');
            if (proxyCount) proxyCount.textContent = `${data.proxy.total} proxy`;
            if (proxyHealthy) proxyHealthy.textContent = `${data.proxy.healthy} healthy`;

            // CAPTCHA
            const captchaService = document.getElementById('captcha-service');
            if (captchaService && data.captcha.service) {
                captchaService.value = data.captcha.service === 'none' ? '' : data.captcha.service;
            }

            // Load logs
            this.loadLogs();

        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    },

    updateIntervalDisplay(seconds) {
        const display = document.getElementById('interval-value');
        if (display) {
            display.textContent = Utils.formatInterval(seconds);
        }
    },

    async saveInterval() {
        const slider = document.getElementById('interval-slider');
        if (!slider) return;

        try {
            await API.updateSettings({
                polling_interval: parseInt(slider.value),
            });
            Utils.toast(I18n.t('settings.saved'), 'success');
        } catch (error) {
            Utils.toast(error.message, 'error');
        }
    },

    async saveProxy() {
        const toggle = document.getElementById('proxy-toggle');
        const textarea = document.getElementById('proxy-list');

        try {
            const proxies = textarea ? textarea.value.split('\n').filter(p => p.trim()) : [];
            await API.updateProxy({
                enabled: toggle ? toggle.checked : false,
                proxies: proxies,
            });
            Utils.toast(I18n.t('settings.saved'), 'success');
            this.load();
        } catch (error) {
            Utils.toast(error.message, 'error');
        }
    },

    async saveCaptcha() {
        const service = document.getElementById('captcha-service');
        const apiKey = document.getElementById('captcha-api-key');

        try {
            await API.updateSettings({
                captcha_service: service ? service.value : '',
                captcha_api_key: apiKey ? apiKey.value : '',
            });
            Utils.toast(I18n.t('settings.saved'), 'success');
        } catch (error) {
            Utils.toast(error.message, 'error');
        }
    },

    async loadLogs() {
        try {
            const data = await API.getScraperLogs();
            const container = document.getElementById('logs-container');
            if (!container) return;

            if (!data.logs || data.logs.length === 0) {
                container.innerHTML = `<div class="log-empty">${I18n.t('settings.logs_empty')}</div>`;
                return;
            }

            container.innerHTML = data.logs.map(log => {
                const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString('id-ID') : '';
                return `
                    <div class="log-entry">
                        <span class="log-time">${time}</span>
                        <span class="log-level ${log.level}">${log.level}</span>
                        <span class="log-message">${Utils.escapeHtml(log.message)}</span>
                    </div>
                `;
            }).join('');

            // Auto-scroll to bottom
            container.scrollTop = container.scrollHeight;

        } catch (error) {
            console.error('Failed to load logs:', error);
        }
    },
};
