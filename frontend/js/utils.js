/**
 * Utility functions.
 */
const Utils = {
    /**
     * Format a relative time string from ISO date.
     */
    timeAgo(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);

        if (diffMin < 1) return I18n.t('timeline.just_now');
        if (diffMin < 60) return I18n.t('timeline.minutes_ago', { n: diffMin });
        if (diffHour < 24) return I18n.t('timeline.hours_ago', { n: diffHour });
        if (diffDay < 30) return I18n.t('timeline.days_ago', { n: diffDay });

        return date.toLocaleDateString('id-ID', {
            day: 'numeric', month: 'short', year: 'numeric'
        });
    },

    /**
     * Format a full datetime for display.
     */
    formatDate(dateStr) {
        if (!dateStr) return '-';
        return new Date(dateStr).toLocaleString('id-ID', {
            day: 'numeric', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    },

    /**
     * Format interval seconds to human readable.
     */
    formatInterval(seconds) {
        if (seconds < 60) return `${seconds} detik`;
        const min = Math.floor(seconds / 60);
        const sec = seconds % 60;
        if (sec === 0) return `${min} menit`;
        return `${min}m ${sec}d`;
    },

    /**
     * Show toast notification.
     */
    toast(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container');
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️',
        };

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span>${message}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Debounce function calls.
     */
    debounce(fn, delay = 300) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    },

    /**
     * Escape HTML to prevent XSS.
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Get initials from a name/username for avatar.
     */
    getInitials(name) {
        if (!name) return '?';
        return name.charAt(0).toUpperCase();
    },

    /**
     * Format large numbers (1000 -> 1K).
     */
    formatNumber(num) {
        if (!num) return '0';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    },

    /**
     * Generate skeleton loading HTML.
     */
    skeletonPost() {
        return `
            <div class="skeleton-post">
                <div style="display:flex;gap:12px;margin-bottom:12px">
                    <div class="skeleton skeleton-avatar"></div>
                    <div style="flex:1">
                        <div class="skeleton skeleton-text short"></div>
                        <div class="skeleton skeleton-text" style="width:25%;height:10px"></div>
                    </div>
                </div>
                <div class="skeleton skeleton-text long"></div>
                <div class="skeleton skeleton-text medium"></div>
            </div>
        `;
    },
};
