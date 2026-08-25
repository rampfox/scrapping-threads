/**
 * Main application controller.
 * Handles routing, initialization, and global state.
 */
const App = {
    currentPage: 'timeline',
    scraperRunning: false,
    statusInterval: null,

    init() {
        // Initialize i18n
        I18n.init();
        I18n.updateToggleButton();

        // Initialize components
        Timeline.init();
        Keywords.init();
        Settings.init();
        Auth.init();
        DebugConsole.init();

        // Setup routing
        this.setupRouter();

        // Setup sidebar
        this.setupSidebar();

        // Setup scraper toggle
        this.setupScraperToggle();

        // Setup language toggle
        const langToggle = document.getElementById('lang-toggle');
        if (langToggle) {
            langToggle.addEventListener('click', () => {
                I18n.toggle();
                // Reload current page to apply translations
                this.navigateTo(this.currentPage);
            });
        }

        // Navigate to initial page
        const hash = window.location.hash.replace('#/', '') || 'timeline';
        this.navigateTo(hash === '' ? 'timeline' : hash);

        // Start status polling
        this.startStatusPolling();

        // Initial load
        this.loadInitialData();
    },

    setupRouter() {
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.replace('#/', '') || 'timeline';
            this.navigateTo(hash);
        });
    },

    navigateTo(page) {
        const validPages = ['timeline', 'keywords', 'settings'];
        if (!validPages.includes(page)) page = 'timeline';

        this.currentPage = page;

        // Update active nav
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-page') === page);
        });

        // Show active page
        document.querySelectorAll('.page').forEach(p => {
            p.classList.remove('active');
        });
        const pageEl = document.getElementById(`page-${page}`);
        if (pageEl) pageEl.classList.add('active');

        // Update title
        const titleKey = `nav.${page}`;
        const titleEl = document.getElementById('page-title');
        if (titleEl) titleEl.textContent = I18n.t(titleKey);

        // Load page data
        switch (page) {
            case 'timeline':
                Timeline.load(true);
                DebugConsole.stopAutoRefresh();
                break;
            case 'keywords':
                Keywords.load();
                DebugConsole.stopAutoRefresh();
                break;
            case 'settings':
                Settings.load();
                Auth.load();
                DebugConsole.startAutoRefresh();
                break;
        }

        // Close mobile sidebar
        const sidebar = document.getElementById('sidebar');
        const overlay = document.querySelector('.sidebar-overlay');
        if (sidebar) sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
    },

    setupSidebar() {
        const mobileBtn = document.getElementById('mobile-menu-btn');
        const sidebar = document.getElementById('sidebar');

        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        document.body.appendChild(overlay);

        if (mobileBtn) {
            mobileBtn.addEventListener('click', () => {
                sidebar.classList.toggle('open');
                overlay.classList.toggle('active');
            });
        }

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });
    },

    setupScraperToggle() {
        const toggleBtn = document.getElementById('btn-scraper-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', async () => {
                try {
                    if (this.scraperRunning) {
                        await API.stopScraper();
                        Utils.toast('Scraper dihentikan', 'info');
                    } else {
                        await API.startScraper();
                        Utils.toast('Scraper dimulai!', 'success');
                    }
                    this.updateScraperStatus();
                } catch (error) {
                    Utils.toast(error.message, 'error');
                }
            });
        }
    },

    async updateScraperStatus() {
        try {
            const data = await API.getScraperStatus();
            const isRunning = data.scheduler?.running || false;
            this.scraperRunning = isRunning;

            // Update status dot
            const statusDot = document.querySelector('#scraper-status-dot .status-dot');
            const statusText = document.querySelector('#scraper-status-dot .status-text');
            const toggleBtn = document.getElementById('btn-scraper-toggle');

            if (statusDot) {
                statusDot.className = `status-dot ${isRunning ? 'online' : 'offline'}`;
            }
            if (statusText) {
                statusText.textContent = I18n.t(isRunning ? 'status.running' : 'status.stopped');
            }
            if (toggleBtn) {
                toggleBtn.classList.toggle('running', isRunning);
                toggleBtn.innerHTML = isRunning
                    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>`
                    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;
            }
        } catch (error) {
            // Server might not be ready yet
        }
    },

    startStatusPolling() {
        this.updateScraperStatus();
        this.statusInterval = setInterval(() => {
            this.updateScraperStatus();
            // Also refresh timeline stats if on timeline page
            if (this.currentPage === 'timeline') {
                Timeline.updateStats();
            }
        }, 10000); // Every 10 seconds
    },

    async loadInitialData() {
        try {
            await API.health();
        } catch (e) {
            Utils.toast('Server belum siap, mencoba kembali...', 'warning');
            setTimeout(() => this.loadInitialData(), 3000);
        }
    },
};

// Boot the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => App.init());
