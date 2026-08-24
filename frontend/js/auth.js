/**
 * Authentication component.
 */
const Auth = {
    init() {
        const loginBtn = document.getElementById('btn-login');
        const logoutBtn = document.getElementById('btn-logout');

        if (loginBtn) {
            loginBtn.addEventListener('click', () => this.login());
        }
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }
    },

    async load() {
        try {
            const data = await API.getAuthStatus();
            this.updateUI(data);
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

        // Show username if logged in
        if (data.accounts && data.accounts.length > 0) {
            const usernameInput = document.getElementById('threads-username');
            if (usernameInput && data.accounts[0].username) {
                usernameInput.value = data.accounts[0].username;
            }
        }
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

        loginBtn.disabled = true;
        loginBtn.textContent = 'Logging in...';

        try {
            const result = await API.login(username, password);

            if (result.success) {
                Utils.toast(I18n.t('settings.login_success'), 'success');
                passwordEl.value = '';
            } else {
                Utils.toast(`${I18n.t('settings.login_failed')} ${result.message || ''}`, 'error');
            }

            this.load();
        } catch (error) {
            Utils.toast(error.message, 'error');
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = I18n.t('settings.login_btn');
        }
    },

    async logout() {
        try {
            await API.logout();
            Utils.toast(I18n.t('settings.logout_success'), 'success');
            this.load();
        } catch (error) {
            Utils.toast(error.message, 'error');
        }
    },
};
