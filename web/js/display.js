/**
 * DOM 显示更新模块
 * 负责更新页面上所有文本和状态显示
 */

const Display = {
    /**
     * 清除曲目区域的骨架屏样式
     */
    clearTrackSkeleton() {
        const title = document.getElementById('trackTitle');
        const artist = document.getElementById('trackArtist');
        const album = document.getElementById('trackAlbum');

        if (title) {
            title.className = 'track-title';
            title.style.width = '';
        }
        if (artist) {
            artist.className = 'track-artist';
            artist.style.width = '';
        }
        if (album) {
            album.className = 'track-album';
            album.style.width = '';
        }
    },

    /**
     * 设置指定元素的文本内容
     * @param {string} id - 元素 ID
     * @param {string} text - 文本内容
     */
    setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    },

    /**
     * 更新曲目信息
     * @param {Object|null} track - 曲目信息，null 表示无播放
     */
    updateTrack(track) {
        this.clearTrackSkeleton();

        if (!track) {
            this.setText('trackTitle', '等待播放...');
            this.setText('trackArtist', '');
            this.setText('trackAlbum', '');
            this.setText('trackStatus', '监听中');
            this.setText('sourceApp', '来源: --');
            return;
        }

        this.setText('trackTitle', track.title || '未知歌曲');
        this.setText('trackArtist', track.artist || '未知艺术家');
        this.setText('trackAlbum', track.album || '');
        this.setText('trackStatus', AppState.getStatusText(track.playback_status));
        this.setText('sourceApp', `来源: ${track.source_app || '--'}`);
    },

    /**
     * 更新乐评内容
     * @param {Object} review - 乐评数据
     */
    updateReview(review) {
        const placeholder = document.getElementById('reviewPlaceholder');
        const content = document.getElementById('reviewContent');
        if (!placeholder || !content) return;

        placeholder.style.display = 'none';
        content.style.display = 'block';

        const score = review.rating ?? review.score ?? 0;
        const scoreEl = document.getElementById('reviewScore');
        if (scoreEl) {
            scoreEl.textContent = score;
            scoreEl.className = 'review-score';
            if (score < 6) scoreEl.classList.add('low');
            else if (score < 8) scoreEl.classList.add('mid');
        }

        this.setText('reviewEmotion', review.emotion || '');
        this.setText('reviewSummary', review.summary || '');
        this.setText('reviewTheory', review.musicology || review.theory || '');
        this.setText('reviewBackground', review.background || '');
        this.setText('reviewScene', review.why_listen || review.scene || '');

        this._updateSimilar(review.similar_songs || review.similar || []);
    },

    /**
     * 更新相似推荐区域
     * @param {Array<string>} songs - 相似歌曲列表
     */
    _updateSimilar(songs) {
        const section = document.getElementById('similarSection');
        const container = document.getElementById('reviewSimilar');
        if (!section || !container) return;

        if (songs.length > 0) {
            section.style.display = 'block';
            container.innerHTML = songs.map(s =>
                `<div class="similar-item">${s}</div>`
            ).join('');
        } else {
            section.style.display = 'none';
        }
    },

    /**
     * 隐藏乐评，显示占位状态
     */
    hideReview() {
        const placeholder = document.getElementById('reviewPlaceholder');
        const content = document.getElementById('reviewContent');
        if (placeholder) placeholder.style.display = 'block';
        if (content) content.style.display = 'none';
    },

    /**
     * 更新运行时间显示
     * @param {number} seconds - 运行秒数
     */
    updateUptime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        const parts = [];
        if (h > 0) parts.push(`${h}小时`);
        if (m > 0) parts.push(`${m}分`);
        parts.push(`${s}秒`);
        this.setText('uptime', `运行时间: ${parts.join('')}`);
    },

    /**
     * 更新连接状态指示灯
     * @param {boolean} connected - 是否已连接
     */
    setConnected(connected) {
        AppState.isConnected = connected;
        const dot = document.getElementById('statusDot');
        if (dot) dot.classList.toggle('active', connected);
    },
};
