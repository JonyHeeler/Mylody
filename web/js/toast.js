/**
 * Toast 通知组件
 * 新乐评生成时弹出通知，3 秒后自动消失
 */

const Toast = {
    /** @type {number} Toast 自动消失延迟（毫秒） */
    DURATION: 3000,

    /**
     * 显示 Toast 通知
     * @param {Object} review - 乐评数据
     */
    show(review) {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `
            <div class="toast-title">${review.title || '新乐评'}</div>
            <div class="toast-artist">${review.artist || ''}</div>
            <div class="toast-score">${review.rating ?? review.score ?? '--'}</div>
        `;
        toast.onclick = () => toast.remove();
        container.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) toast.remove();
        }, this.DURATION);
    },
};
