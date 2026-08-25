/**
 * Authentication component.
 * Mengelola login/logout Threads dan menampilkan error detail.
 */
const Auth = {
    init() {
        const loginBtn = document.getElementById('btn-login');
        const logoutBtn = document.getElementById('btn-logout');

        if (loginBtn) loginBtn.addEventListener('click', () => this.login());
        if (logoutBtn) logoutBtn.addEventListener('click', () => this.logout());
    },

    async load() {
        try {
            const data = await API.getAuthStatus();
            this.updateUI(data);

            // Tampilkan error terakhir dari akun yang gagal
            const failedAccount = data.accounts?.find(a =>
                a.status !== 'logged_in' && a.error
            );
            if (failedAccount) {
                this.showErrorBanner(failedAccount.error, failedAccount.status);
            } else if (data.is_logged_in) {
                this.hideErrorBanner();
            }
        } catch (error) {
            console.error('Failed to load auth status:', error);
        }
    },

    updateUI(data) {
        const badge = document.getElementById('login-badge');
        if (badge) {
            if (data.is_logged_in) {
                badge.textContent = I18n.t('settings.logged_in');
                badge.className = 'login-badge logged-in';
            } else {
                badge.textContent = I18n.t('settings.not_logged_in');
                badge.className = 'login-badge';
            }
        }

        // Isi username jika sudah ada akun
        if (data.accounts?.length > 0) {
            const usernameInput = document.getElementById('threads-username');
            if (usernameInput && data.accounts[0].username && !usernameInput.value) {
                usernameInput.value = data.accounts[0].username;
            }
        }
    },

    showErrorBanner(errorMsg, status) {
        const banner = document.getElementById('login-error-banner');
        const msgEl = document.getElementById('login-error-msg');
        if (!banner || !msgEl) return;

        // Format status label
        const statusLabels = {
            '2fa_required': '🔐 Diperlukan verifikasi 2FA',
            'wrong_credentials': '🔑 Username/password salah',
            'account_locked': '🔒 Akun dikunci sementara',
            'checkpoint': '🚧 Checkpoint Instagram terdeteksi',
            'timeout': '⏱️ Koneksi timeout',
            'failed': '❌ Login tidak berhasil',
            'error': '💥 Terjadi error',
        };

        const statusLabel = statusLabels[status] || `Status: ${status}`;
        msgEl.textContent = `${statusLabel}\n${errorMsg}`;
        banner.style.display = 'flex';
    },

    hideErrorBanner() {
        const banner = document.getElementById('login-error-banner');
        if (banner) banner.style.display = 'none';
    },

    async login() {
        const usernameEl = document.getElementById('threads-username');
        const passwordEl = document.getElementById('threads-password');
        const loginBtn = document.getElementById('btn-login');

        const username = usernameEl ? usernameEl.value.trim() : '';
        const password = passwordEl ? passwordEl.value : '';

        if (!username || !password) {
            Utils.toast('Username dan password diperlukan', 'warning');
            return;
        }

        // Sembunyikan error banner lama
        this.hideErrorBanner();

        // Update button state
        loginBtn.disabled = true;
        const originalText = loginBtn.textContent;
        loginBtn.textContent = '⏳ Logging in...';

        // Log ke debug console
        DebugConsole.addLog('info', `Memulai login untuk @${username}...`);
        DebugConsole.addLog('info', 'Membuka browser Playwright + stealth mode...');

        try {
            const result = await API.login(username, password);

            if (result.success) {
                Utils.toast(I18n.t('settings.login_success'), 'success');
                passwordEl.value = '';
                this.hideErrorBanner();
                DebugConsole.addLog('info', `✅ Login berhasil untuk @${username}`);
            } else {
                // Tampilkan error detail
                const errDetail = result.error_detail || result.message || 'Login gagal';
                Utils.toast(`${I18n.t('settings.login_failed')} ${result.status || ''}`, 'error');
                this.showErrorBanner(errDetail, result.status);
                DebugConsole.addLog('error', `❌ Login gagal: ${errDetail}`);

                // Tip berdasarkan status
                const tips = {
                    '2fa_required': 'Tip: Nonaktifkan 2FA sementara di akun Threads/Instagram, lalu coba login lagi.',
                    'wrong_credentials': 'Tip: Pastikan username dan password benar. Coba login manual di browser untuk verifikasi.',
                    'account_locked': 'Tip: Tunggu beberapa jam lalu coba lagi, atau buka Instagram di browser untuk unlock.',
                    'checkpoint': 'Tip: Buka Instagram/Threads di browser biasa, selesaikan checkpoint, lalu coba lagi.',
                };
                const tip = tips[result.status];
                if (tip) {
                    DebugConsole.addLog('warning', `💡 ${tip}`);
                }
            }

            this.load();
        } catch (error) {
            const errMsg = error.message || 'Network error';
            Utils.toast(errMsg, 'error');
            this.showErrorBanner(errMsg, 'error');
            DebugConsole.addLog('error', `Network/Server error: ${errMsg}`);
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = originalText || I18n.t('settings.login_btn');
        }
    },

    async logout() {
        try {
            await API.logout();
            Utils.toast(I18n.t('settings.logout_success'), 'success');
            this.hideErrorBanner();
            DebugConsole.addLog('info', 'Berhasil logout dari Threads');
            this.load();
        } catch (error) {
            Utils.toast(error.message, 'error');
        }
    },
};
