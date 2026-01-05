/**
 * 工作台页面组件
 * 
 * 提供卡片上传、编辑、导出的完整工作流
 * 集成 P2 增强功能: Auto-save、Token Badge、文本清洗、安全预览
 */

import Alpine from 'alpinejs';
import { parseCard, injectCard, ApiError } from '../api.js';
import { deepClone } from '../store.js';
import { startAutoSave, stopAutoSave, clearDraft } from '../components/auto_save.js';
import { autoCheckDraft, loadDraft, deleteDraft } from '../components/modal_recover.js';
import { estimateCardTokens, getWarningLevel } from '../components/token_badge.js';
import { cleanCardFields, SAFE_FIELDS, detectDirtyContent } from '../components/text_cleaner.js';

/**
 * 工作台主组件
 */
export function workshopPage() {
  return {
    // 拖拽状态
    dragging: false,
    
    // 当前展开的编辑区域
    activeSection: 'basic',
    
    // 导出设置
    exportSettings: {
      includeV2Compat: true,
    },
    
    // 忙碌锁
    isParsing: false,
    isExporting: false,
    
    // 自动保存状态
    autoSaveStatus: '',
    lastAutoSave: 0,
    
    // Token 估算
    tokenInfo: {
      total: 0,
      breakdown: {},
      level: null,
      percentage: 0,
    },
    
    // 预览状态
    previewVisible: false,
    previewContent: '',
    previewTitle: '',
    previewMarkdown: false,
    
    // 计算属性
    get card() {
      return Alpine.store('card');
    },
    
    get hasCard() {
      return this.card.data !== null;
    },
    
    get cardName() {
      return this.card.data?.data?.name || '未命名角色';
    },
    
    get settings() {
      return Alpine.store('settings');
    },
    
    // Token Badge 样式类
    get tokenBadgeClass() {
      switch (this.tokenInfo.level) {
        case 'danger':
          return 'bg-red-50 text-red-700';
        case 'warning':
          return 'bg-amber-50 text-amber-700';
        default:
          return 'bg-zinc-100 text-zinc-600';
      }
    },
    
    // 初始化
    async init() {
      // 从 localStorage 加载导出设置
      const saved = localStorage.getItem('cardforge_export_settings');
      if (saved) {
        try {
          this.exportSettings = JSON.parse(saved);
        } catch (e) {
          console.warn('Failed to load export settings:', e);
        }
      }
      
      // 检查草稿恢复
      await this.checkDraftRecovery();
      
      // 启动自动保存
      this.initAutoSave();
      
      // 监听卡片变化更新 Token
      this.$watch('$store.card.data', () => {
        this.updateTokenInfo();
      });
    },
    
    // 初始化自动保存
    initAutoSave() {
      startAutoSave({
        getData: () => this.card.data,
        getImageDataUrl: () => this.card.imageDataUrl,
        onSave: (time) => {
          this.lastAutoSave = time;
          this.autoSaveStatus = '已自动保存';
          setTimeout(() => {
            if (this.autoSaveStatus === '已自动保存') {
              this.autoSaveStatus = '';
            }
          }, 3000);
        },
        interval: this.settings?.autoSaveInterval || 30,
      });
    },
    
    // 检查草稿恢复
    async checkDraftRecovery() {
      try {
        await autoCheckDraft({
          onRecover: (draftData) => {
            if (draftData.card) {
              this.card.loadCard({ card: draftData.card }, null, draftData.imageDataUrl);
              Alpine.store('toast').success('草稿已恢复');
            }
          },
          onDiscard: () => {
            Alpine.store('toast').info('草稿已丢弃');
          },
        });
      } catch (e) {
        console.warn('Draft recovery check failed:', e);
      }
    },
    
    // 更新 Token 信息
    updateTokenInfo() {
      if (!this.card.data) {
        this.tokenInfo = { total: 0, breakdown: {}, level: null, percentage: 0 };
        return;
      }
      
      const result = estimateCardTokens(this.card.data);
      const budget = 8000;
      this.tokenInfo = {
        total: result.total,
        breakdown: result.breakdown,
        level: getWarningLevel(result.total, budget),
        percentage: Math.round((result.total / budget) * 100),
      };
    },
    
    // 文件上传处理
    async handleFileSelect(event) {
      const file = event.target.files?.[0];
      if (file) {
        await this.processFile(file);
      }
      event.target.value = '';
    },
    
    // 拖拽处理
    handleDragOver(event) {
      event.preventDefault();
      this.dragging = true;
    },
    
    handleDragLeave(event) {
      event.preventDefault();
      this.dragging = false;
    },
    
    async handleDrop(event) {
      event.preventDefault();
      this.dragging = false;
      
      const file = event.dataTransfer?.files?.[0];
      if (file) {
        await this.processFile(file);
      }
    },
    
    // 处理文件
    async processFile(file) {
      if (this.isParsing) return;
      
      const ext = file.name.split('.').pop()?.toLowerCase();
      const validExts = ['png', 'json'];
      const validMimes = ['image/png', 'application/json'];
      const isValid = validExts.includes(ext) || validMimes.includes(file.type);
      
      if (!isValid) {
        Alpine.store('toast').error('不支持的文件格式，请上传 PNG 或 JSON 文件');
        return;
      }
      
      this.isParsing = true;
      const toastId = Alpine.store('toast').loading('正在解析文件...');
      
      try {
        const result = await parseCard(file);
        
        let imageDataUrl = null;
        if (file.type.startsWith('image/')) {
          imageDataUrl = await this.readAsDataURL(file);
        }
        
        this.card.loadCard(result, file, imageDataUrl);
        Alpine.store('history').clear();
        
        // 更新 Token 信息
        this.updateTokenInfo();
        
        Alpine.store('toast').dismiss(toastId);
        Alpine.store('toast').success(`已加载: ${result.card?.data?.name || '角色卡'}`);
        
      } catch (error) {
        Alpine.store('toast').dismiss(toastId);
        
        if (error instanceof ApiError) {
          Alpine.store('toast').error(error.getUserMessage());
        } else {
          console.error('Parse error:', error);
          Alpine.store('toast').error('解析失败: ' + (error.message || '未知错误'));
        }
      } finally {
        this.isParsing = false;
      }
    },
    
    // 读取文件为 Data URL
    readAsDataURL(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    },
    
    // 更换图片
    async handleImageChange(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      
      if (file.type !== 'image/png') {
        Alpine.store('toast').error('请上传 PNG 格式的图片');
        return;
      }
      
      try {
        const imageDataUrl = await this.readAsDataURL(file);
        this.card.imageDataUrl = imageDataUrl;
        this.card.imageFile = file;
        this.card.checkChanges();
        Alpine.store('toast').success('图片已更换');
      } catch (error) {
        console.error('Image read error:', error);
        Alpine.store('toast').error('读取图片失败');
      }
      
      event.target.value = '';
    },
    
    // 创建新卡片
    createNew() {
      this.card.initNew();
      Alpine.store('history').clear();
      this.updateTokenInfo();
      Alpine.store('toast').info('已创建新角色卡');
    },
    
    // 重置卡片
    resetCard() {
      if (confirm('确定要重置为原始状态吗？所有修改将丢失。')) {
        this.card.reset();
        this.updateTokenInfo();
        Alpine.store('toast').info('已重置到原始状态');
      }
    },
    
    // 关闭卡片
    closeCard() {
      if (this.card.hasChanges) {
        if (!confirm('有未保存的修改，确定要关闭吗？')) {
          return;
        }
      }
      this.card.clear();
      Alpine.store('history').clear();
      this.tokenInfo = { total: 0, breakdown: {}, level: null, percentage: 0 };
    },
    
    // 导出 PNG
    async exportPNG() {
      if (this.isExporting) return;
      
      if (!this.card.data) {
        Alpine.store('toast').error('没有可导出的卡片');
        return;
      }
      
      if (!this.card.imageFile && !this.card.imageDataUrl) {
        Alpine.store('toast').error('需要先上传图片才能导出 PNG');
        return;
      }
      
      this.isExporting = true;
      const toastId = Alpine.store('toast').loading('正在导出...');
      
      try {
        let imageFile = this.card.imageFile;
        if (!imageFile && this.card.imageDataUrl) {
          imageFile = await this.dataURLtoFile(this.card.imageDataUrl, 'card.png');
        }
        
        const blob = await injectCard(
          imageFile,
          this.card.data,
          this.exportSettings.includeV2Compat
        );
        
        const filename = this.generateFilename();
        this.downloadBlob(blob, filename);
        
        // 标记已保存并清除草稿
        this.card.markSaved();
        clearDraft();
        
        Alpine.store('toast').dismiss(toastId);
        Alpine.store('toast').success('导出成功: ' + filename);
        
      } catch (error) {
        Alpine.store('toast').dismiss(toastId);
        
        if (error instanceof ApiError) {
          Alpine.store('toast').error(error.getUserMessage());
        } else {
          console.error('Export error:', error);
          Alpine.store('toast').error('导出失败: ' + (error.message || '未知错误'));
        }
      } finally {
        this.isExporting = false;
      }
    },
    
    // 生成文件名 {Name}_{Date}_{Time}.png
    generateFilename() {
      const name = this.card.data?.data?.name || 'Character';
      const safeName = name.replace(/[<>:"/\\|?*]/g, '_').substring(0, 50);
      const now = new Date();
      const date = now.toISOString().split('T')[0].replace(/-/g, '');
      const time = now.toTimeString().split(' ')[0].replace(/:/g, '').substring(0, 4);
      return `${safeName}_${date}_${time}.png`;
    },
    
    // Data URL 转 File
    async dataURLtoFile(dataURL, filename) {
      const res = await fetch(dataURL);
      const blob = await res.blob();
      return new File([blob], filename, { type: blob.type });
    },
    
    // 下载 Blob
    downloadBlob(blob, filename) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    
    // 导出 JSON
    exportJSON() {
      if (!this.card.data) {
        Alpine.store('toast').error('没有可导出的卡片');
        return;
      }
      
      const json = JSON.stringify(this.card.data, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const filename = this.generateFilename().replace('.png', '.json');
      
      this.downloadBlob(blob, filename);
      this.card.markSaved();
      clearDraft();
      Alpine.store('toast').success('JSON 导出成功');
    },
    
    // 更新字段值 (支持撤销)
    updateField(path, value) {
      Alpine.store('history').push(deepClone(this.card.data));
      this.card.updateField(path, value);
    },
    
    // 切换编辑区域
    setActiveSection(section) {
      this.activeSection = section;
    },
    
    // ===== P2 增强功能 =====
    
    // 打开预览
    showPreview(content, title = '内容预览') {
      this.previewContent = content || '';
      this.previewTitle = title;
      this.previewVisible = true;
    },
    
    // 关闭预览
    closePreview() {
      this.previewVisible = false;
    },
    
    // 预览开场白
    previewFirstMes() {
      this.showPreview(this.card.data?.data?.first_mes, '开场白预览');
    },
    
    // 预览备选开场白
    previewAlternateGreeting(index) {
      const greetings = this.card.data?.data?.alternate_greetings || [];
      const content = greetings[index];
      if (content) {
        this.showPreview(content, `备选开场白 #${index + 1} 预览`);
      }
    },
    
    // 清洗安全字段
    async cleanSafeFields() {
      if (!this.card.data) {
        Alpine.store('toast').error('没有可清洗的卡片');
        return;
      }
      
      Alpine.store('history').push(deepClone(this.card.data));
      
      const { cardData, changes } = cleanCardFields(
        this.card.data,
        SAFE_FIELDS
      );
      
      const changedCount = Object.keys(changes).length;
      
      if (changedCount === 0) {
        Alpine.store('toast').info('未发现需要清洗的内容');
        return;
      }
      
      this.card.data = cardData;
      this.card.checkChanges();
      this.updateTokenInfo();
      
      Alpine.store('toast').success(`已清洗 ${changedCount} 个字段`);
    },
    
    // 检测脏内容
    detectDirty(text) {
      return detectDirtyContent(text);
    },
    
    // 格式化自动保存时间
    formatAutoSaveTime() {
      if (!this.lastAutoSave) return '';
      const date = new Date(this.lastAutoSave);
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    },
    
    // 销毁时清理
    destroy() {
      stopAutoSave();
    },
  };
}

/**
 * 注册工作台组件
 */
export function registerWorkshopComponents() {
  Alpine.data('workshopPage', workshopPage);
}

export default {
  workshopPage,
  registerWorkshopComponents,
};
