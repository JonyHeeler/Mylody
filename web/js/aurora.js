/**
 * Aurora 背景控制器
 * 管理 Aurora 渐变背景的三种状态：idle（纯色）、active（流动）、frozen（冻结）
 */

const AuroraController = {
    /** @type {HTMLElement|null} */
    _el: null,

    /**
     * 获取 Aurora 背景元素
     * @returns {HTMLElement|null}
     */
    _getElement() {
        if (!this._el) {
            this._el = document.getElementById('auroraBg');
        }
        return this._el;
    },

    /**
     * 获取 Aurora 光斑元素
     * @returns {NodeListOf<HTMLElement>}
     */
    _getGlows() {
        return document.querySelectorAll('.aurora-glow');
    },

    /**
     * 清除冻结时写入的内联动效样式
     */
    _clearFrozenStyles() {
        const el = this._getElement();
        if (el) {
            el.style.backgroundPosition = '';
        }
        this._getGlows().forEach((glow) => {
            glow.style.animation = '';
            glow.style.transform = '';
        });
    },

    /**
     * 激活 Aurora 动画（AI 思考时调用）
     * 渐变背景开始流动，光斑开始浮动
     */
    activate() {
        const el = this._getElement();
        if (!el || AppState.auroraPhase === 'active') return;

        this._clearFrozenStyles();
        el.classList.remove('aurora--frozen');
        el.classList.add('aurora--active');
        AppState.auroraPhase = 'active';
    },

    /**
     * 冻结 Aurora 动画（乐评加载完成后调用）
     * 保持当前渐变位置，停止所有动画
     */
    freeze() {
        const el = this._getElement();
        if (!el || AppState.auroraPhase !== 'active') return;

        const computed = getComputedStyle(el);
        const pos = computed.backgroundPosition;
        const glowTransforms = [...this._getGlows()].map((glow) => ({
            glow,
            transform: getComputedStyle(glow).transform,
        }));

        el.classList.remove('aurora--active');
        el.classList.add('aurora--frozen');
        el.style.backgroundPosition = pos;
        glowTransforms.forEach(({ glow, transform }) => {
            glow.style.animation = 'none';
            glow.style.transform = transform === 'none' ? '' : transform;
        });
        AppState.auroraPhase = 'frozen';
    },

    /**
     * 重置为静态纯色背景
     */
    reset() {
        const el = this._getElement();
        if (!el) return;

        el.classList.remove('aurora--active', 'aurora--frozen');
        this._clearFrozenStyles();
        AppState.auroraPhase = 'idle';
    },
};
