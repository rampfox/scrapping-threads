/**
 * Timeline component - renders the post feed.
 */
const Timeline = {
    currentPage: 1,
    currentKeyword: '',
    currentSearch: '',
    isLoading: false,
    hasMore: true,

    init() {
        // Search input with debounce
        const searchInput = document.getElementById('timeline-search');
        if (searchInput) {
            searchInput.addEventListener('input', Utils.debounce((e) => {
                this.currentSearch = e.target.value;
                this.currentPage = 1;
                this.load(true);
            }, 400));
        }

        // Load more button
        const loadMoreBtn = document.getElementById('btn-load-more');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => this.loadMore());
        }
    },

    async load(reset = false) {
        if (this.isLoading) return;
        this.isLoading = true;

        const feed = document.getElementById('timeline-feed');
        const loadMore = document.getElementById('load-more');
        const emptyState = document.getElementById('empty-state');

        if (reset) {
            this.currentPage = 1;
            feed.innerHTML = Utils.skeletonPost().repeat(3);
            emptyState.style.display = 'none';
        }

        try {
            const data = await API.getPosts(
                this.currentPage, 20,
                this.currentKeyword, this.currentSearch
            );

            if (reset) feed.innerHTML = '';

            if (data.posts.length === 0 && this.currentPage === 1) {
                emptyState.style.display = 'block';
                loadMore.style.display = 'none';
            } else {
                emptyState.style.display = 'none';

                data.posts.forEach(post => {
                    feed.appendChild(this.renderPost(post));
                });

                this.hasMore = this.currentPage < data.pages;
                loadMore.style.display = this.hasMore ? 'block' : 'none';
            }

            // Update stats
            this.updateStats();
            this.loadKeywordChips();

        } catch (error) {
            if (reset) feed.innerHTML = '';
            emptyState.style.display = 'block';
            Utils.toast(I18n.t('general.error'), 'error');
        } finally {
            this.isLoading = false;
        }
    },

    async loadMore() {
        if (!this.hasMore || this.isLoading) return;
        this.currentPage++;
        await this.load(false);
    },

    renderPost(post) {
        const card = document.createElement('div');
        card.className = 'post-card';
        card.setAttribute('data-post-id', post.id);

        const avatarContent = post.user_pic
            ? `<img src="${Utils.escapeHtml(post.user_pic)}" alt="${Utils.escapeHtml(post.username)}" onerror="this.parentElement.innerHTML='${Utils.getInitials(post.display_name || post.username)}'">`
            : Utils.getInitials(post.display_name || post.username);

        const verifiedBadge = post.is_verified
            ? `<svg class="verified-badge" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>`
            : '';

        const imagesHtml = post.images && post.images.length > 0
            ? `<div class="post-images">${post.images.map(img => `<img src="${Utils.escapeHtml(img)}" alt="Post image" loading="lazy">`).join('')}</div>`
            : '';

        card.innerHTML = `
            <div class="post-header">
                <div class="post-avatar">${avatarContent}</div>
                <div class="post-user-info">
                    <div class="post-user-name">
                        ${Utils.escapeHtml(post.display_name || post.username)}
                        ${verifiedBadge}
                    </div>
                    <div class="post-username">@${Utils.escapeHtml(post.username)}</div>
                </div>
                <div class="post-time" title="${Utils.formatDate(post.posted_at)}">
                    ${Utils.timeAgo(post.posted_at || post.scraped_at)}
                </div>
            </div>
            <div class="post-content">${Utils.escapeHtml(post.content)}</div>
            ${imagesHtml}
            <div class="post-footer">
                <span class="post-stat">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                    </svg>
                    ${Utils.formatNumber(post.like_count)} ${I18n.t('timeline.likes')}
                </span>
                <span class="post-stat">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    ${Utils.formatNumber(post.reply_count)} ${I18n.t('timeline.replies')}
                </span>
                ${post.keyword ? `<span class="post-keyword-badge">#${Utils.escapeHtml(post.keyword)}</span>` : ''}
                ${post.url ? `<a href="${Utils.escapeHtml(post.url)}" target="_blank" rel="noopener" class="post-link" title="Open in Threads">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                </a>` : ''}
            </div>
        `;

        return card;
    },

    async updateStats() {
        try {
            const stats = await API.getPostStats();
            document.getElementById('stat-total').textContent = Utils.formatNumber(stats.total_posts);
            document.getElementById('stat-today').textContent = Utils.formatNumber(stats.posts_today);
        } catch (e) {
            // Silently fail
        }
    },

    async loadKeywordChips() {
        try {
            const data = await API.getKeywords();
            const container = document.getElementById('keyword-chips');
            if (!container) return;

            container.innerHTML = `<button class="chip ${this.currentKeyword === '' ? 'active' : ''}" data-keyword="">
                <span>${I18n.t('timeline.all')}</span>
            </button>`;

            data.keywords.forEach(kw => {
                const chip = document.createElement('button');
                chip.className = `chip ${this.currentKeyword === kw.keyword ? 'active' : ''}`;
                chip.setAttribute('data-keyword', kw.keyword);
                chip.innerHTML = `<span>#${Utils.escapeHtml(kw.keyword)}</span>`;
                container.appendChild(chip);
            });

            // Attach click handlers
            container.querySelectorAll('.chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    container.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    this.currentKeyword = chip.getAttribute('data-keyword');
                    this.load(true);
                });
            });
        } catch (e) {
            // Silently fail
        }
    },

    setKeywordFilter(keyword) {
        this.currentKeyword = keyword;
        this.load(true);
    },
};
