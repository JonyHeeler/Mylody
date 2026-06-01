/**
 * 轻量 Markdown 渲染器。
 * 仅支持音乐人格需要的标题、段落、列表、粗体和斜体。
 */

const MarkdownRenderer = {
    /**
     * 将可信的本地 Markdown 文本渲染为安全 HTML。
     * @param {string} text - Markdown 文本
     * @returns {string} 安全 HTML
     */
    render(text) {
        const lines = String(text || '').replace(/\r\n/g, '\n').split('\n');
        const html = [];
        let paragraph = [];
        let list = [];

        const flushParagraph = () => {
            if (!paragraph.length) return;
            html.push(`<p>${this.inline(paragraph.join(' '))}</p>`);
            paragraph = [];
        };

        const flushList = () => {
            if (!list.length) return;
            html.push(`<ul>${list.map((item) => `<li>${this.inline(item)}</li>`).join('')}</ul>`);
            list = [];
        };

        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) {
                flushParagraph();
                flushList();
                continue;
            }

            const heading = line.match(/^(#{2,4})\s+(.+)$/);
            if (heading) {
                flushParagraph();
                flushList();
                const level = Math.min(heading[1].length, 4);
                html.push(`<h${level}>${this.inline(heading[2])}</h${level}>`);
                continue;
            }

            const bullet = line.match(/^[-*]\s+(.+)$/);
            if (bullet) {
                flushParagraph();
                list.push(bullet[1]);
                continue;
            }

            flushList();
            paragraph.push(line);
        }

        flushParagraph();
        flushList();
        return html.join('');
    },

    /**
     * 渲染行内 Markdown，并先转义 HTML。
     * @param {string} text - 行内文本
     * @returns {string} 安全 HTML
     */
    inline(text) {
        return this.escape(text)
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>');
    },

    /**
     * 转义 HTML 特殊字符。
     * @param {string} text - 原始文本
     * @returns {string} 转义后的文本
     */
    escape(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },
};
