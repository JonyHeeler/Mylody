/**
 * 应用状态管理模块
 * 集中管理所有前端状态，各模块通过此对象读写状态
 */

const AppState = {
    isConnected: false,
    lastTrackId: null,
    isGenerating: false,
    auroraPhase: 'idle',

    STATUS_MAP: {
        4: '▶ 播放中',
        5: '⏸ 已暂停',
        1: '⏹ 已停止',
    },

    /**
     * 生成曲目的唯一标识
     * @param {Object} track - 曲目信息对象
     * @returns {string} 曲目唯一 ID
     */
    getTrackId(track) {
        return `${track.title}-${track.artist}`;
    },

    /**
     * 获取播放状态的显示文本
     * @param {number} status - 播放状态码
     * @returns {string} 状态显示文本
     */
    getStatusText(status) {
        return this.STATUS_MAP[status] || '未知';
    },
};
