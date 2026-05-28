/**
 * Mylody 前端逻辑：轮询服务状态并更新页面显示
 */

const POLL_INTERVAL = 2000;

const STATUS_MAP = {
    4: "▶ 播放中",
    5: "⏸ 已暂停",
    1: "⏹ 已停止",
};

let pollTimer = null;
let isConnected = false;

/**
 * 获取服务状态并更新页面
 */
async function fetchStatus() {
    try {
        const res = await fetch("/api/status");
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        updateDisplay(data);
        setConnected(true);
    } catch {
        setConnected(false);
    }
}

/**
 * 更新页面显示内容
 * @param {Object} data - 服务状态数据
 */
function updateDisplay(data) {
    updateUptime(data.uptime_seconds);

    if (!data.current_track) {
        showNoTrack();
        return;
    }

    const track = data.current_track;
    setText("trackTitle", track.title || "未知歌曲");
    setText("trackArtist", track.artist || "未知艺术家");
    setText("trackAlbum", track.album || "");
    setText("trackStatus", STATUS_MAP[track.playback_status] || "未知");
    setText("sourceApp", `来源: ${track.source_app || "--"}`);
}

/**
 * 显示无播放状态
 */
function showNoTrack() {
    setText("trackTitle", "等待播放...");
    setText("trackArtist", "");
    setText("trackAlbum", "");
    setText("trackStatus", "监听中");
    setText("sourceApp", "来源: --");
}

/**
 * 更新运行时间显示
 * @param {number} seconds - 运行秒数
 */
function updateUptime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const parts = [];
    if (h > 0) parts.push(`${h}小时`);
    if (m > 0) parts.push(`${m}分`);
    parts.push(`${s}秒`);
    setText("uptime", `运行时间: ${parts.join("")}`);
}

/**
 * 设置连接状态指示器
 * @param {boolean} connected - 是否已连接
 */
function setConnected(connected) {
    isConnected = connected;
    const dot = document.getElementById("statusDot");
    if (dot) {
        dot.classList.toggle("active", connected);
    }
}

/**
 * 设置元素文本内容
 * @param {string} id - 元素 ID
 * @param {string} text - 文本内容
 */
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

/**
 * 启动轮询
 */
function startPolling() {
    fetchStatus();
    pollTimer = setInterval(fetchStatus, POLL_INTERVAL);
}

/**
 * 初始化应用
 */
function init() {
    startPolling();
}

document.addEventListener("DOMContentLoaded", init);
