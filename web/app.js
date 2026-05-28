const POLL_INTERVAL = 2000;

const STATUS_MAP = {
    4: "▶ 播放中",
    5: "⏸ 已暂停",
    1: "⏹ 已停止",
};

let pollTimer = null;
let isConnected = false;
let lastTrackId = null;

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

function updateDisplay(data) {
    updateUptime(data.uptime_seconds);

    if (!data.current_track) {
        showNoTrack();
        return;
    }

    const track = data.current_track;
    const trackId = `${track.title}-${track.artist}`;

    setText("trackTitle", track.title || "未知歌曲");
    setText("trackArtist", track.artist || "未知艺术家");
    setText("trackAlbum", track.album || "");
    setText("trackStatus", STATUS_MAP[track.playback_status] || "未知");
    setText("sourceApp", `来源: ${track.source_app || "--"}`);

    if (trackId !== lastTrackId) {
        lastTrackId = trackId;
        fetchReview();
    }
}

function showNoTrack() {
    setText("trackTitle", "等待播放...");
    setText("trackArtist", "");
    setText("trackAlbum", "");
    setText("trackStatus", "监听中");
    setText("sourceApp", "来源: --");
    hideReview();
}

async function fetchReview() {
    try {
        const res = await fetch("/api/review/current");
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        const review = normalizeReviewResponse(data);
        if (!review) {
            hideReview();
            return;
        }
        updateReviewDisplay(review);
        showToast(review);
    } catch {
        hideReview();
    }
}

function normalizeReviewResponse(data) {
    if (!data) return null;
    return data.review || data;
}

function updateReviewDisplay(review) {
    const placeholder = document.getElementById("reviewPlaceholder");
    const content = document.getElementById("reviewContent");
    if (!placeholder || !content) return;

    placeholder.style.display = "none";
    content.style.display = "block";

    const score = review.rating ?? review.score ?? 0;
    const scoreEl = document.getElementById("reviewScore");
    if (scoreEl) {
        scoreEl.textContent = score;
        scoreEl.className = "review-score";
        if (score < 6) scoreEl.classList.add("low");
        else if (score < 8) scoreEl.classList.add("mid");
    }

    setText("reviewEmotion", review.emotion || "");
    setText("reviewSummary", review.summary || "");
    setText("reviewTheory", review.musicology || review.theory || "");
    setText("reviewBackground", review.background || "");
    setText("reviewScene", review.why_listen || review.scene || "");

    const similarSection = document.getElementById("similarSection");
    const similarContainer = document.getElementById("reviewSimilar");
    const similarSongs = review.similar_songs || review.similar || [];
    if (similarSection && similarContainer && similarSongs.length > 0) {
        similarSection.style.display = "block";
        similarContainer.innerHTML = similarSongs.map(s =>
            `<div class="similar-item">${s}</div>`
        ).join("");
    } else if (similarSection) {
        similarSection.style.display = "none";
    }
}

function hideReview() {
    const placeholder = document.getElementById("reviewPlaceholder");
    const content = document.getElementById("reviewContent");
    if (placeholder) placeholder.style.display = "block";
    if (content) content.style.display = "none";
}

function showToast(review) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `
        <div class="toast-title">${review.title || "新乐评"}</div>
        <div class="toast-artist">${review.artist || ""}</div>
        <div class="toast-score">${review.rating ?? review.score ?? "--"}</div>
    `;
    toast.onclick = () => toast.remove();
    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) toast.remove();
    }, 3000);
}

async function refreshReview() {
    const btn = document.getElementById("refreshBtn");
    if (btn) {
        btn.disabled = true;
        btn.textContent = "刷新中...";
    }

    try {
        const res = await fetch("/api/review/refresh", { method: "POST" });
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        const review = normalizeReviewResponse(data);
        if (!review) throw new Error(data.message || "乐评为空");
        updateReviewDisplay(review);
        showToast(review);
    } catch (err) {
        console.error("刷新失败:", err);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = "🔄 刷新乐评";
        }
    }
}

async function fetchConfig() {
    try {
        const res = await fetch("/api/config");
        if (!res.ok) throw new Error(res.statusText);
        const config = await res.json();

        const provider = document.getElementById("configProvider");
        const model = document.getElementById("configModel");
        const interval = document.getElementById("configInterval");
        const port = document.getElementById("configPort");

        if (provider) provider.value = config.llm_provider || "openai";
        if (model) model.value = config.llm_model || "";
        if (interval) interval.value = config.poll_interval || 2;
        if (port) port.value = config.web_port || 8080;
    } catch (err) {
        console.error("获取配置失败:", err);
    }
}

async function saveConfig() {
    const config = {
        llm_provider: document.getElementById("configProvider")?.value || "openai",
        llm_model: document.getElementById("configModel")?.value || "",
        poll_interval: parseInt(document.getElementById("configInterval")?.value || "2"),
        web_port: parseInt(document.getElementById("configPort")?.value || "8080"),
    };

    try {
        const res = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config),
        });
        if (!res.ok) throw new Error(res.statusText);
        closeSettings();
    } catch (err) {
        console.error("保存配置失败:", err);
    }
}

function openSettings() {
    const modal = document.getElementById("settingsModal");
    if (modal) modal.classList.add("active");
    fetchConfig();
}

function closeSettings() {
    const modal = document.getElementById("settingsModal");
    if (modal) modal.classList.remove("active");
}

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

function setConnected(connected) {
    isConnected = connected;
    const dot = document.getElementById("statusDot");
    if (dot) dot.classList.toggle("active", connected);
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function startPolling() {
    fetchStatus();
    pollTimer = setInterval(fetchStatus, POLL_INTERVAL);
}

function init() {
    startPolling();

    document.getElementById("refreshBtn")?.addEventListener("click", refreshReview);
    document.getElementById("settingsBtn")?.addEventListener("click", openSettings);
    document.getElementById("closeSettingsBtn")?.addEventListener("click", closeSettings);
    document.getElementById("cancelSettingsBtn")?.addEventListener("click", closeSettings);
    document.getElementById("saveSettingsBtn")?.addEventListener("click", saveConfig);

    document.getElementById("settingsModal")?.addEventListener("click", (e) => {
        if (e.target === e.currentTarget) closeSettings();
    });
}

document.addEventListener("DOMContentLoaded", init);
