/**
 * Keywords management component.
 */
const Keywords = {
    init() {
        // Add keyword button
        const addBtn = document.getElementById('btn-add-keyword');
        const input = document.getElementById('new-keyword-input');

        if (addBtn) {
            addBtn.addEventListener('click', () => this.addKeyword());
        }

        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this.addKeyword();
            });
        }
    },

    async load() {
        try {
            const data = await API.getKeywords();
            this.render(data);
        } catch (error) {
            Utils.toast(I18n.t('general.error'), 'error');
        }
    },

    render(data) {
        const list = document.getElementById('keywords-list');
        const countEl = document.getElementById('keyword-count');
        const maxEl = document.getElementById('keyword-max');

        if (countEl) countEl.textContent = data.total;
        if (maxEl) maxEl.textContent = data.max_allowed;

        if (!list) return;

        if (data.keywords.length === 0) {
            list.innerHTML = `
                <div class="empty-state" style="padding:40px">
                    <p class="text-muted">${I18n.t('keywords.empty')}</p>
                </div>
            `;
            return;
        }

        list.innerHTML = '';
        data.keywords.forEach(kw => {
            list.appendChild(this.renderKeywordItem(kw));
        });
    },

    renderKeywordItem(kw) {
        const item = document.createElement('div');
        item.className = 'keyword-item';
        item.setAttribute('data-keyword-id', kw.id);

        const lastScraped = kw.last_scraped_at
            ? Utils.formatDate(kw.last_scraped_at)
            : I18n.t('keywords.never');

        item.innerHTML = `
            <label class="switch" title="Active/Inactive">
                <input type="checkbox" ${kw.is_active ? 'checked' : ''} data-toggle-id="${kw.id}">
                <span class="slider"></span>
            </label>
            <span class="keyword-text">${Utils.escapeHtml(kw.keyword)}</span>
            <div class="keyword-meta">
                <span>📊 ${kw.post_count} ${I18n.t('keywords.posts')}</span>
                <span>🕐 ${lastScraped}</span>
            </div>
            <div class="keyword-actions">
                <button class="btn btn-sm btn-outline" data-scrape-id="${kw.id}" title="${I18n.t('keywords.scrape_now')}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="23 4 23 10 17 10"/>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                </button>
                <button class="btn btn-sm btn-outline btn-danger" data-delete-id="${kw.id}" title="${I18n.t('keywords.delete')}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            </div>
        `;

        // Toggle active
        const toggle = item.querySelector(`[data-toggle-id="${kw.id}"]`);
        if (toggle) {
            toggle.addEventListener('change', async (e) => {
                try {
                    await API.updateKeyword(kw.id, { is_active: e.target.checked });
                } catch (error) {
                    e.target.checked = !e.target.checked;
                    Utils.toast(I18n.t('general.error'), 'error');
                }
            });
        }

        // Scrape now
        const scrapeBtn = item.querySelector(`[data-scrape-id="${kw.id}"]`);
        if (scrapeBtn) {
            scrapeBtn.addEventListener('click', async () => {
                scrapeBtn.disabled = true;
                scrapeBtn.innerHTML = '<span class="skeleton" style="width:14px;height:14px;display:inline-block;border-radius:50%"></span>';
                try {
                    const result = await API.scrapeKeywordNow(kw.id);
                    Utils.toast(`${result.message}`, 'success');
                    this.load();
                    Timeline.load(true);
                } catch (error) {
                    Utils.toast(error.message, 'error');
                } finally {
                    scrapeBtn.disabled = false;
                }
            });
        }

        // Delete
        const deleteBtn = item.querySelector(`[data-delete-id="${kw.id}"]`);
        if (deleteBtn) {
            deleteBtn.addEventListener('click', async () => {
                if (!confirm(I18n.t('general.confirm_delete'))) return;
                try {
                    await API.deleteKeyword(kw.id);
                    Utils.toast(I18n.t('keywords.deleted'), 'success');
                    item.style.animation = 'fadeIn 0.3s ease reverse forwards';
                    setTimeout(() => {
                        item.remove();
                        this.load();
                    }, 300);
                } catch (error) {
                    Utils.toast(error.message, 'error');
                }
            });
        }

        return item;
    },

    async addKeyword() {
        const input = document.getElementById('new-keyword-input');
        const keyword = input.value.trim();

        if (!keyword) return;

        try {
            await API.addKeyword(keyword);
            input.value = '';
            Utils.toast(I18n.t('keywords.added'), 'success');
            this.load();
            Timeline.loadKeywordChips();
        } catch (error) {
            Utils.toast(error.message, 'error');
        }
    },
};
