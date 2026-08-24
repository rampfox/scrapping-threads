/**
 * Internationalization (i18n) module.
 * Supports Bahasa Indonesia (default) and English.
 */
const I18n = {
    currentLang: 'id',

    translations: {
        id: {
            // Navigation
            'nav.timeline': 'Timeline',
            'nav.keywords': 'Kata Kunci',
            'nav.settings': 'Pengaturan',

            // Status
            'status.running': 'Berjalan',
            'status.stopped': 'Berhenti',
            'status.error': 'Error',

            // Stats
            'stats.posts': 'Post',
            'stats.today': 'Hari Ini',

            // Timeline
            'timeline.search_placeholder': 'Cari dalam hasil...',
            'timeline.all': 'Semua',
            'timeline.empty_title': 'Belum ada post',
            'timeline.empty_desc': 'Tambahkan kata kunci dan mulai scraping untuk melihat timeline.',
            'timeline.load_more': 'Muat Lebih Banyak',
            'timeline.likes': 'suka',
            'timeline.replies': 'balasan',
            'timeline.just_now': 'Baru saja',
            'timeline.minutes_ago': '{n} menit yang lalu',
            'timeline.hours_ago': '{n} jam yang lalu',
            'timeline.days_ago': '{n} hari yang lalu',

            // Keywords
            'keywords.title': 'Manajemen Kata Kunci',
            'keywords.subtitle': 'Kelola kata kunci yang akan dipantau di Threads.',
            'keywords.input_placeholder': 'Masukkan kata kunci baru...',
            'keywords.add': 'Tambah',
            'keywords.limit': 'Batas',
            'keywords.posts': 'post',
            'keywords.last_scraped': 'Terakhir scrape',
            'keywords.never': 'Belum pernah',
            'keywords.scrape_now': 'Scrape Sekarang',
            'keywords.delete': 'Hapus',
            'keywords.added': 'Kata kunci ditambahkan!',
            'keywords.deleted': 'Kata kunci dihapus!',
            'keywords.empty': 'Belum ada kata kunci. Tambahkan kata kunci untuk mulai memantau Threads.',

            // Settings
            'settings.title': 'Pengaturan',
            'settings.login_title': 'Akun Threads',
            'settings.not_logged_in': 'Belum Login',
            'settings.logged_in': 'Sudah Login',
            'settings.login_desc': 'Login diperlukan untuk fitur pencarian keyword di Threads.',
            'settings.username': 'Username',
            'settings.password': 'Password',
            'settings.login_btn': 'Login',
            'settings.logout_btn': 'Logout',
            'settings.interval_title': 'Interval Polling',
            'settings.interval_desc': 'Seberapa sering bot akan memeriksa post baru.',
            'settings.recommended': '⭐ Disarankan: 2m',
            'settings.save': 'Simpan',
            'settings.proxy_title': 'Konfigurasi Proxy',
            'settings.proxy_desc': 'Gunakan proxy untuk rotasi IP dan menghindari deteksi.',
            'settings.proxy_list': 'Daftar Proxy (satu per baris)',
            'settings.captcha_title': 'CAPTCHA Solver',
            'settings.captcha_desc': 'Konfigurasi solver CAPTCHA otomatis (opsional).',
            'settings.captcha_service': 'Service',
            'settings.export_title': 'Ekspor Data',
            'settings.export_desc': 'Download semua data scraping.',
            'settings.logs_title': 'Log Scraper',
            'settings.logs_empty': 'Belum ada log.',
            'settings.saved': 'Pengaturan disimpan!',
            'settings.login_success': 'Login berhasil!',
            'settings.login_failed': 'Login gagal!',
            'settings.logout_success': 'Berhasil logout!',

            // General
            'general.confirm_delete': 'Yakin ingin menghapus?',
            'general.error': 'Terjadi kesalahan',
            'general.success': 'Berhasil!',
        },

        en: {
            // Navigation
            'nav.timeline': 'Timeline',
            'nav.keywords': 'Keywords',
            'nav.settings': 'Settings',

            // Status
            'status.running': 'Running',
            'status.stopped': 'Stopped',
            'status.error': 'Error',

            // Stats
            'stats.posts': 'Posts',
            'stats.today': 'Today',

            // Timeline
            'timeline.search_placeholder': 'Search results...',
            'timeline.all': 'All',
            'timeline.empty_title': 'No posts yet',
            'timeline.empty_desc': 'Add keywords and start scraping to see the timeline.',
            'timeline.load_more': 'Load More',
            'timeline.likes': 'likes',
            'timeline.replies': 'replies',
            'timeline.just_now': 'Just now',
            'timeline.minutes_ago': '{n} minutes ago',
            'timeline.hours_ago': '{n} hours ago',
            'timeline.days_ago': '{n} days ago',

            // Keywords
            'keywords.title': 'Keyword Management',
            'keywords.subtitle': 'Manage keywords to monitor on Threads.',
            'keywords.input_placeholder': 'Enter new keyword...',
            'keywords.add': 'Add',
            'keywords.limit': 'Limit',
            'keywords.posts': 'posts',
            'keywords.last_scraped': 'Last scraped',
            'keywords.never': 'Never',
            'keywords.scrape_now': 'Scrape Now',
            'keywords.delete': 'Delete',
            'keywords.added': 'Keyword added!',
            'keywords.deleted': 'Keyword deleted!',
            'keywords.empty': 'No keywords yet. Add keywords to start monitoring Threads.',

            // Settings
            'settings.title': 'Settings',
            'settings.login_title': 'Threads Account',
            'settings.not_logged_in': 'Not Logged In',
            'settings.logged_in': 'Logged In',
            'settings.login_desc': 'Login is required for keyword search on Threads.',
            'settings.username': 'Username',
            'settings.password': 'Password',
            'settings.login_btn': 'Login',
            'settings.logout_btn': 'Logout',
            'settings.interval_title': 'Polling Interval',
            'settings.interval_desc': 'How often the bot checks for new posts.',
            'settings.recommended': '⭐ Recommended: 2m',
            'settings.save': 'Save',
            'settings.proxy_title': 'Proxy Configuration',
            'settings.proxy_desc': 'Use proxies for IP rotation and detection avoidance.',
            'settings.proxy_list': 'Proxy List (one per line)',
            'settings.captcha_title': 'CAPTCHA Solver',
            'settings.captcha_desc': 'Configure automatic CAPTCHA solver (optional).',
            'settings.captcha_service': 'Service',
            'settings.export_title': 'Export Data',
            'settings.export_desc': 'Download all scraped data.',
            'settings.logs_title': 'Scraper Logs',
            'settings.logs_empty': 'No logs yet.',
            'settings.saved': 'Settings saved!',
            'settings.login_success': 'Login successful!',
            'settings.login_failed': 'Login failed!',
            'settings.logout_success': 'Logged out successfully!',

            // General
            'general.confirm_delete': 'Are you sure you want to delete?',
            'general.error': 'An error occurred',
            'general.success': 'Success!',
        },
    },

    init() {
        const saved = localStorage.getItem('threads-bot-lang');
        if (saved && this.translations[saved]) {
            this.currentLang = saved;
        }
        this.apply();
    },

    t(key, params = {}) {
        let text = this.translations[this.currentLang]?.[key] || this.translations.id[key] || key;
        for (const [k, v] of Object.entries(params)) {
            text = text.replace(`{${k}}`, v);
        }
        return text;
    },

    toggle() {
        this.currentLang = this.currentLang === 'id' ? 'en' : 'id';
        localStorage.setItem('threads-bot-lang', this.currentLang);
        this.apply();
        this.updateToggleButton();
    },

    apply() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = this.t(key);
        });

        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });
    },

    updateToggleButton() {
        const btn = document.getElementById('lang-toggle');
        if (btn) {
            const flag = btn.querySelector('.lang-flag');
            const code = btn.querySelector('.lang-code');
            if (this.currentLang === 'id') {
                flag.textContent = '🇮🇩';
                code.textContent = 'ID';
            } else {
                flag.textContent = '🇬🇧';
                code.textContent = 'EN';
            }
        }
    },
};
