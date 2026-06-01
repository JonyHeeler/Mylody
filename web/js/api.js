/**
 * API 通信模块
 * 封装所有与后端的 HTTP 请求
 */

const API = {
    /**
     * 获取服务状态
     * @returns {Promise<Object>} 状态数据（running, current_track, uptime_seconds, is_generating）
     */
    async fetchStatus() {
        const res = await fetch('/api/status');
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
    },

    /**
     * 获取当前乐评
     * @returns {Promise<Object>} 乐评数据
     */
    async fetchReview() {
        const res = await fetch('/api/review/current');
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '获取乐评失败');
        }
        return data.review || null;
    },

    /**
     * 强制刷新乐评
     * @returns {Promise<Object>} 新乐评数据
     */
    async refreshReview() {
        const res = await fetch('/api/review/refresh', { method: 'POST' });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '刷新乐评失败');
        }
        return data.review || null;
    },

    /**
     * 生成音乐人格与音乐旅程回顾
     * @returns {Promise<Object>} 音乐人格文本和使用的乐评数量
     */
    async generatePersonality(force = false) {
        const url = force ? '/api/personality/generate?force=1' : '/api/personality/generate';
        const res = await fetch(url, { method: 'POST' });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '音乐人格生成失败');
        }
        return data;
    },

    async fetchPersonalityHistory() {
        const res = await fetch('/api/personality/history');
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '获取音乐人格历史失败');
        }
        return data.items || [];
    },

    async fetchPersonalityDetail(id) {
        const res = await fetch(`/api/personality/history/${encodeURIComponent(id)}`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '获取音乐人格失败');
        }
        return data.item;
    },

    /**
     * 获取当前配置
     * @returns {Promise<Object>} 配置数据
     */
    async fetchConfig() {
        const res = await fetch('/api/config');
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
    },

    /**
     * 获取后端日志尾部内容
     * @returns {Promise<Object>} 日志数据
     */
    async fetchLogs() {
        const res = await fetch('/api/logs?lines=120');
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
    },

    /**
     * 获取缓存乐评列表
     * @returns {Promise<Array<Object>>} 缓存项列表
     */
    async fetchCachedReviews() {
        const res = await fetch('/api/cache/reviews');
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '获取缓存失败');
        }
        return data.items || [];
    },

    async fetchCachedReview(cacheKey) {
        const res = await fetch(`/api/cache/reviews/${encodeURIComponent(cacheKey)}`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '获取乐评失败');
        }
        return data.item;
    },

    /**
     * 删除指定缓存乐评
     * @param {string} cacheKey - 缓存键
     */
    async deleteCachedReview(cacheKey) {
        const res = await fetch(`/api/cache/reviews/${encodeURIComponent(cacheKey)}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '删除缓存失败');
        }
        return data;
    },

    /**
     * 清空全部缓存乐评
     */
    async clearCachedReviews() {
        const res = await fetch('/api/cache/reviews', { method: 'DELETE' });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        if (data.status && data.status !== 'ok') {
            throw new Error(data.message || '清空缓存失败');
        }
        return data;
    },

};
