/**
 * 骨架屏加载组件
 * 在数据加载期间显示占位动画
 */

const Skeleton = {
    /**
     * 显示曲目卡片骨架屏
     */
    showTrack() {
        const title = document.getElementById('trackTitle');
        const artist = document.getElementById('trackArtist');
        const album = document.getElementById('trackAlbum');
        if (title) {
            title.textContent = '';
            title.className = 'skeleton skeleton-title';
        }
        if (artist) {
            artist.textContent = '';
            artist.className = 'skeleton skeleton-text';
            artist.style.width = '50%';
        }
        if (album) {
            album.textContent = '';
            album.className = 'skeleton skeleton-text';
            album.style.width = '40%';
        }
    },

    /**
     * 显示乐评卡片骨架屏
     */
    showReview() {
        const placeholder = document.getElementById('reviewPlaceholder');
        const content = document.getElementById('reviewContent');
        if (content) content.style.display = 'none';
        if (placeholder) {
            placeholder.style.display = 'block';
            placeholder.innerHTML = `
                <div class="skeleton-group" style="display:flex;align-items:center;gap:16px;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border)">
                    <div class="skeleton skeleton-score"></div>
                    <div class="skeleton skeleton-tag"></div>
                </div>
                <div class="skeleton-group">
                    <div class="skeleton skeleton-group-label"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text" style="width:70%"></div>
                </div>
                <div class="skeleton-group">
                    <div class="skeleton skeleton-group-label"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text" style="width:80%"></div>
                </div>
            `;
        }
    },

    /**
     * 恢复乐评占位状态
     */
    resetReview() {
        const placeholder = document.getElementById('reviewPlaceholder');
        if (placeholder) {
            placeholder.innerHTML = `
                <span class="review-icon">📝</span>
                <p>等待乐评生成...</p>
            `;
        }
    },
};
