/**
 * 通用全文查看弹窗。
 */

const DetailModal = {
    /**
     * 打开全文弹窗。
     * @param {string} title - 弹窗标题
     * @param {string} body - 弹窗正文
     */
    open(title, body) {
        const modal = document.getElementById('detailModal');
        const heading = document.getElementById('detailTitle');
        const content = document.getElementById('detailContent');
        if (heading) heading.textContent = title || '详情';
        if (content) content.textContent = body || '暂无内容';
        if (modal) modal.classList.add('active');
    },

    /**
     * 关闭全文弹窗。
     */
    close() {
        const modal = document.getElementById('detailModal');
        if (modal) modal.classList.remove('active');
    },
};
