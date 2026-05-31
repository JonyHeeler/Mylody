/**
 * 缓存乐评弹窗组件
 * 展示本地已缓存乐评，并支持按条删除。
 */

const SettingsModal = {
    _items: [],
    _query: '',

    open() {
        const modal = document.getElementById('settingsModal');
        if (modal) modal.classList.add('active');
        this.bindToolbar();
        this.loadCache();
    },

    close() {
        const modal = document.getElementById('settingsModal');
        if (modal) modal.classList.remove('active');
    },

    async loadCache() {
        const list = document.getElementById('cacheList');
        if (!list) return;

        list.innerHTML = '<div class="cache-empty">正在加载缓存...</div>';

        try {
            const items = await API.fetchCachedReviews();
            this._items = items;
            this.renderCache();
        } catch (err) {
            console.error('获取缓存失败:', err);
            list.innerHTML = '<div class="cache-empty">缓存读取失败</div>';
        }
    },

    bindToolbar() {
        const search = document.getElementById('cacheSearch');
        const refresh = document.getElementById('cacheRefreshBtn');
        const clear = document.getElementById('cacheClearBtn');

        if (search && !search.dataset.bound) {
            search.dataset.bound = 'true';
            search.addEventListener('input', () => {
                this._query = search.value.trim().toLowerCase();
                this.renderCache();
            });
        }
        if (refresh && !refresh.dataset.bound) {
            refresh.dataset.bound = 'true';
            refresh.addEventListener('click', () => this.loadCache());
        }
        if (clear && !clear.dataset.bound) {
            clear.dataset.bound = 'true';
            clear.addEventListener('click', () => this.clearCache());
        }
    },

    renderCache() {
        const list = document.getElementById('cacheList');
        if (!list) return;

        const items = this.filteredItems();
        this.updateCount(items.length, this._items.length);

        if (!items.length) {
            list.innerHTML = this._items.length
                ? '<div class="cache-empty">没有匹配的缓存乐评</div>'
                : '<div class="cache-empty">暂无缓存乐评</div>';
            return;
        }

        list.innerHTML = '';
        for (const item of items) {
            const row = document.createElement('div');
            row.className = 'cache-item';

            const meta = document.createElement('div');
            meta.className = 'cache-item-main';

            const title = document.createElement('div');
            title.className = 'cache-item-title';
            title.textContent = item.title || '未知歌曲';

            const sub = document.createElement('div');
            sub.className = 'cache-item-subtitle';
            sub.textContent = [item.artist, item.album].filter(Boolean).join(' / ') || '未知艺术家';

            const excerpt = document.createElement('div');
            excerpt.className = 'cache-item-excerpt';
            excerpt.textContent = item.excerpt || '';

            const details = document.createElement('div');
            details.className = 'cache-item-details';
            const rating = item.rating === null || item.rating === undefined ? '--' : item.rating;
            details.textContent = `评分 ${rating} · ${item.emotion || '无情绪标签'} · ${item.updated_at || ''}`;

            meta.append(title, sub, excerpt, details);

            const actions = document.createElement('div');
            actions.className = 'cache-item-actions';

            const del = document.createElement('button');
            del.className = 'cache-delete-btn';
            del.type = 'button';
            del.textContent = '删除';
            del.addEventListener('click', () => this.deleteCache(item.cache_key));

            actions.append(del);
            row.append(meta, actions);
            list.append(row);
        }
    },

    filteredItems() {
        if (!this._query) return this._items;
        return this._items.filter(item => {
            const haystack = [
                item.title,
                item.artist,
                item.album,
                item.emotion,
                item.excerpt,
                item.model,
            ].filter(Boolean).join(' ').toLowerCase();
            return haystack.includes(this._query);
        });
    },

    updateCount(visible, total) {
        const count = document.getElementById('cacheCount');
        if (!count) return;
        count.textContent = visible === total ? `共 ${total} 条` : `显示 ${visible} / ${total} 条`;
    },

    async deleteCache(cacheKey) {
        if (!cacheKey) return;

        try {
            await API.deleteCachedReview(cacheKey);
            await this.loadCache();
            await loadReview();
        } catch (err) {
            console.error('删除缓存失败:', err);
        }
    },

    async clearCache() {
        if (!this._items.length) return;
        const confirmed = window.confirm(`确定清空 ${this._items.length} 条缓存乐评吗？`);
        if (!confirmed) return;

        try {
            await API.clearCachedReviews();
            this._items = [];
            this.renderCache();
            await loadReview();
        } catch (err) {
            console.error('清空缓存失败:', err);
        }
    },
};
