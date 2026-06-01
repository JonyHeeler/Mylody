/**
 * 音乐人格弹窗组件
 * 负责触发生成请求，并展示音乐人格与旅程回顾。
 */

const PersonalityModal = {
    /**
     * 打开弹窗并开始生成音乐人格
     */
    async open() {
        const modal = document.getElementById('personalityModal');
        if (modal) modal.classList.add('active');
        this.setLoading();
        this.bindActions();
        await this.generate(false);
    },

    /**
     * 关闭音乐人格弹窗
     */
    close() {
        const modal = document.getElementById('personalityModal');
        if (modal) modal.classList.remove('active');
    },

    /**
     * 调用后端生成音乐人格
     */
    async generate(force = false) {
        try {
            const data = await API.generatePersonality(force);
            this.render(data.content, data.count, data.cached, data.created_at);
            await this.loadHistory();
        } catch (err) {
            console.error('音乐人格生成失败:', err);
            this.renderError(err.message || '音乐人格生成失败');
        }
    },

    /**
     * 绑定弹窗内操作按钮。
     */
    bindActions() {
        const regenerate = document.getElementById('regeneratePersonalityBtn');
        if (regenerate && !regenerate.dataset.bound) {
            regenerate.dataset.bound = 'true';
            regenerate.addEventListener('click', async () => {
                this.setLoading('正在重新生成音乐人格...');
                await this.generate(true);
            });
        }
    },

    /**
     * 显示生成中的状态
     */
    setLoading(message = 'AI 正在回看你的音乐旅程。') {
        const meta = document.getElementById('personalityMeta');
        const content = document.getElementById('personalityContent');
        if (meta) meta.textContent = '正在读取乐评时间线...';
        if (content) content.textContent = message;
    },

    /**
     * 渲染生成结果
     * @param {string} text - AI 生成的音乐人格文本
     * @param {number} count - 使用的乐评数量
     */
    render(text, count, cached = false, createdAt = '') {
        const meta = document.getElementById('personalityMeta');
        const content = document.getElementById('personalityContent');
        const source = cached ? '上次生成' : '刚刚生成';
        if (meta) meta.textContent = `${source} · 基于 ${count || 0} 条乐评 · ${createdAt || ''}`;
        if (content) content.innerHTML = MarkdownRenderer.render(text || '暂无内容');
    },

    /**
     * 加载本地保存的音乐人格历史。
     */
    async loadHistory() {
        const list = document.getElementById('personalityHistoryList');
        if (!list) return;
        const items = await API.fetchPersonalityHistory();
        if (!items.length) {
            list.innerHTML = '<div class="cache-empty">暂无历史人格</div>';
            return;
        }
        list.innerHTML = '';
        for (const item of items) {
            const row = document.createElement('button');
            row.className = 'personality-history-item';
            row.type = 'button';
            const date = document.createElement('span');
            date.className = 'personality-history-date';
            date.textContent = `${item.created_at || ''} · ${item.item_count || 0} 条`;
            const excerpt = document.createElement('span');
            excerpt.className = 'personality-history-excerpt';
            excerpt.textContent = item.excerpt || '';
            row.append(date, excerpt);
            row.addEventListener('click', async () => {
                const detail = await API.fetchPersonalityDetail(item.id);
                this.render(detail.content, detail.item_count, true, detail.created_at);
            });
            list.append(row);
        }
    },

    /**
     * 渲染错误状态
     * @param {string} message - 错误信息
     */
    renderError(message) {
        const meta = document.getElementById('personalityMeta');
        const content = document.getElementById('personalityContent');
        if (meta) meta.textContent = '生成失败';
        if (content) content.textContent = message;
    },
};
