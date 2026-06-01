/**
 * Mylody 前端入口
 * 负责初始化、轮询调度和事件绑定
 */

const POLL_INTERVAL = 2000;
let pollTimer = null;
let backendLogLines = [];

/**
 * 判断当前页面是否处于 Aurora 预览模式
 * @returns {boolean}
 */
function isAuroraPreview() {
    return new URLSearchParams(window.location.search).get('aurora') === 'active';
}

/**
 * 主轮询逻辑：获取状态并协调各模块更新
 */
async function poll() {
    try {
        const data = await API.fetchStatus();
        Display.setConnected(true);
        Display.updateUptime(data.uptime_seconds);
        await loadBackendLogs();
        Display.updateStatusLog(data.status_events, backendLogLines);

        if (!data.current_track) {
            Display.updateTrack(null);
            Display.hideReview();
            Skeleton.resetReview();
            AuroraController.reset();
            AppState.lastTrackId = null;
            return;
        }

        const trackId = AppState.getTrackId(data.current_track);
        const isNewTrack = trackId !== AppState.lastTrackId;

        if (isNewTrack) {
            AppState.lastTrackId = trackId;
            AuroraController.reset();
            Skeleton.showTrack();
            Skeleton.showReview();
            Display.updateTrack(data.current_track);
        } else {
            Display.updateTrack(data.current_track);
        }

        if (data.is_generating) {
            if (AppState.auroraPhase !== 'active') {
                AuroraController.activate();
                Skeleton.showReview();
            }
            AppState.isGenerating = true;
        } else {
            AppState.isGenerating = false;
            if (AppState.auroraPhase === 'active') {
                AuroraController.freeze();
            }
            const quoteMissing = !document.getElementById('reviewQuote')?.textContent?.trim();
            if (isNewTrack || !document.getElementById('reviewContent')?.style.display ||
                document.getElementById('reviewContent')?.style.display === 'none' ||
                quoteMissing) {
                await loadReview();
            }
        }
    } catch {
        Display.setConnected(false);
    }
}

/**
 * 加载后端日志尾部内容
 */
async function loadBackendLogs() {
    try {
        const data = await API.fetchLogs();
        backendLogLines = data.lines || [];
    } catch {
        backendLogLines = backendLogLines.length
            ? backendLogLines
            : ['后端日志读取失败'];
    }
}

/**
 * 加载乐评数据并更新显示
 */
async function loadReview() {
    try {
        const review = await API.fetchReview();
        if (review) {
            Skeleton.resetReview();
            Display.updateReview(review);
            Toast.show(review);
        } else {
            Skeleton.resetReview();
            Display.hideReview();
            AuroraController.reset();
        }
    } catch {
        Skeleton.resetReview();
        Display.hideReview();
        AuroraController.reset();
    }
}

/**
 * 刷新乐评（手动触发）
 */
async function refreshReview() {
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '刷新中...';
    }

    AuroraController.activate();
    Skeleton.showReview();

    try {
        const review = await API.refreshReview();
        if (!review) throw new Error('乐评为空');
        Skeleton.resetReview();
        Display.updateReview(review);
        Toast.show(review);
    } catch (err) {
        console.error('刷新失败:', err);
        Skeleton.resetReview();
        Display.hideReview();
    } finally {
        AuroraController.freeze();
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🔄 刷新乐评';
        }
    }
}

/**
 * 切换运行状态日志的展开/收起
 */
function toggleStatusLog() {
    const el = document.getElementById('statusLog');
    if (el) el.classList.toggle('collapsed');
}

/**
 * 绑定所有 DOM 事件
 */
function bindEvents() {
    document.getElementById('refreshBtn')?.addEventListener('click', refreshReview);
    document.getElementById('personalityBtn')?.addEventListener('click', () => PersonalityModal.open());
    document.getElementById('settingsBtn')?.addEventListener('click', () => SettingsModal.open());
    document.getElementById('closePersonalityBtn')?.addEventListener('click', () => PersonalityModal.close());
    document.getElementById('cancelPersonalityBtn')?.addEventListener('click', () => PersonalityModal.close());
    document.getElementById('closeSettingsBtn')?.addEventListener('click', () => SettingsModal.close());
    document.getElementById('cancelSettingsBtn')?.addEventListener('click', () => SettingsModal.close());
    document.getElementById('closeDetailBtn')?.addEventListener('click', () => DetailModal.close());
    document.getElementById('cancelDetailBtn')?.addEventListener('click', () => DetailModal.close());

    document.getElementById('statusLogToggle')?.addEventListener('click', toggleStatusLog);

    document.getElementById('personalityModal')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) PersonalityModal.close();
    });

    document.getElementById('settingsModal')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) SettingsModal.close();
    });

    document.getElementById('detailModal')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) DetailModal.close();
    });
}

/**
 * 启动轮询
 */
function startPolling() {
    if (isAuroraPreview()) return;
    poll();
    pollTimer = setInterval(poll, POLL_INTERVAL);
}

/**
 * 初始化应用
 */
function init() {
    AuroraController.reset();
    if (isAuroraPreview()) {
        AuroraController.activate();
        return;
    }
    startPolling();
    bindEvents();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
