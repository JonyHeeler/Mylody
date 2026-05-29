/**
 * 设置弹窗组件
 * 管理配置弹窗的打开、关闭、加载和保存
 */

const SettingsModal = {
    /**
     * 打开设置弹窗并加载当前配置
     */
    open() {
        const modal = document.getElementById('settingsModal');
        if (modal) modal.classList.add('active');
        this.loadConfig();
    },

    /**
     * 关闭设置弹窗
     */
    close() {
        const modal = document.getElementById('settingsModal');
        if (modal) modal.classList.remove('active');
    },

    /**
     * 从后端加载配置并填充表单
     */
    async loadConfig() {
        try {
            const config = await API.fetchConfig();
            const provider = document.getElementById('configProvider');
            const model = document.getElementById('configModel');
            const interval = document.getElementById('configInterval');
            const port = document.getElementById('configPort');

            if (provider) provider.value = config.llm_provider || 'openai';
            if (model) model.value = config.llm_model || '';
            if (interval) interval.value = config.poll_interval || 2;
            if (port) port.value = config.web_port || 8080;
        } catch (err) {
            console.error('获取配置失败:', err);
        }
    },

    /**
     * 收集表单数据并保存到后端
     */
    async save() {
        const config = {
            llm_provider: document.getElementById('configProvider')?.value || 'openai',
            llm_model: document.getElementById('configModel')?.value || '',
            poll_interval: parseInt(document.getElementById('configInterval')?.value || '2'),
            web_port: parseInt(document.getElementById('configPort')?.value || '8080'),
        };

        try {
            await API.saveConfig(config);
            this.close();
        } catch (err) {
            console.error('保存配置失败:', err);
        }
    },
};
