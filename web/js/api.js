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
        return data.review || data;
    },

    /**
     * 强制刷新乐评
     * @returns {Promise<Object>} 新乐评数据
     */
    async refreshReview() {
        const res = await fetch('/api/review/refresh', { method: 'POST' });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        return data.review || data;
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
     * 保存配置
     * @param {Object} config - 配置对象
     * @returns {Promise<Object>} 保存结果
     */
    async saveConfig(config) {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
    },
};
