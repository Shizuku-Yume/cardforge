/**
 * Quack 导入页面组件
 * 
 * 支持两种模式:
 * 1. 通过 ID/URL + Cookie 从 Quack API 获取
 * 2. 手动粘贴 JSON 数据 (IP 封禁时的兜底方案)
 */

import Alpine from 'alpinejs';
import { importFromQuack, previewQuack, ApiError } from '../api.js';

/**
 * Quack 导入页面组件
 */
export function quackPage() {
  return {
    // 输入数据
    quackInput: '',
    cookies: '',
    
    // 模式选项
    mode: 'full', // 'full' | 'only_lorebook'
    outputFormat: 'json', // 'json' | 'png'
    inputMode: 'api', // 'api' | 'json'
    
    // 预览数据
    preview: null,
    
    // 结果数据
    result: null,
    resultPngUrl: null,
    
    // 状态
    isPreviewing: false,
    isImporting: false,
    error: null,
    
    // Cookie 本地存储 (用于记住 Cookie)
    rememberCookie: false,
    
    // 计算属性
    get hasInput() {
      return this.quackInput.trim().length > 0;
    },
    
    get isJsonInput() {
      const input = this.quackInput.trim();
      return input.startsWith('{') || input.startsWith('[');
    },
    
    get inputPlaceholder() {
      if (this.inputMode === 'json') {
        return '粘贴从 Quack 导出的完整 JSON 数据...\n\n{\n  "charList": [...],\n  "intro": "...",\n  ...\n}';
      }
      return '输入 Quack 角色 ID 或 URL\n\n例如:\n• 1234567\n• https://quack.ai/character/1234567';
    },
    
    // 初始化
    init() {
      // 恢复记住的 Cookie
      const savedCookie = localStorage.getItem('quack_cookie');
      if (savedCookie) {
        this.cookies = savedCookie;
        this.rememberCookie = true;
      }
      
      // 监听输入变化，自动检测输入类型
      this.$watch('quackInput', (val) => {
        if (this.isJsonInput) {
          this.inputMode = 'json';
        }
      });
    },
    
    // 切换输入模式
    toggleInputMode() {
      this.inputMode = this.inputMode === 'api' ? 'json' : 'api';
      this.quackInput = '';
      this.preview = null;
      this.result = null;
      this.error = null;
    },
    
    // 保存/清除 Cookie
    handleCookieRemember() {
      if (this.rememberCookie) {
        localStorage.setItem('quack_cookie', this.cookies);
      } else {
        localStorage.removeItem('quack_cookie');
      }
    },
    
    // 预览角色信息
    async handlePreview() {
      if (!this.hasInput) return;
      
      this.isPreviewing = true;
      this.error = null;
      this.preview = null;
      
      try {
        const result = await previewQuack({
          quack_input: this.quackInput,
          cookies: this.cookies,
        });
        
        this.preview = result;
        
        // 保存 Cookie (如果勾选)
        if (this.rememberCookie && this.cookies) {
          localStorage.setItem('quack_cookie', this.cookies);
        }
      } catch (err) {
        this.handleError(err);
      } finally {
        this.isPreviewing = false;
      }
    },
    
    // 导入角色
    async handleImport() {
      if (!this.hasInput) return;
      
      this.isImporting = true;
      this.error = null;
      this.result = null;
      this.resultPngUrl = null;
      
      try {
        const result = await importFromQuack({
          quack_input: this.quackInput,
          cookies: this.cookies,
          mode: this.mode,
          output_format: this.outputFormat,
        });
        
        this.result = result;
        
        // 如果返回 PNG Base64，创建 Blob URL
        if (result.png_base64) {
          const binary = atob(result.png_base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: 'image/png' });
          this.resultPngUrl = URL.createObjectURL(blob);
        }
        
        // 显示成功提示
        Alpine.store('toast').success(
          this.mode === 'only_lorebook' 
            ? '世界书导入成功' 
            : '角色卡导入成功'
        );
        
        // 显示警告
        if (result.warnings?.length > 0) {
          result.warnings.forEach(w => {
            Alpine.store('toast').info(w);
          });
        }
        
        // 保存 Cookie
        if (this.rememberCookie && this.cookies) {
          localStorage.setItem('quack_cookie', this.cookies);
        }
      } catch (err) {
        this.handleError(err);
      } finally {
        this.isImporting = false;
      }
    },
    
    // 处理错误
    handleError(err) {
      console.error('Quack import error:', err);
      
      if (err instanceof ApiError) {
        this.error = {
          message: err.message,
          code: err.code,
          hint: err.details?.hint || null,
        };
        
        // 特殊错误提示
        if (err.code === 'UNAUTHORIZED') {
          this.error.hint = '请检查 Cookie 是否有效，或尝试重新登录 Quack 后复制 Cookie';
        } else if (err.code === 'NETWORK_ERROR') {
          this.error.hint = '如果 IP 被封禁，请切换到「手动粘贴 JSON」模式';
        }
      } else {
        this.error = {
          message: err.message || '导入失败',
          code: 'UNKNOWN',
          hint: null,
        };
      }
      
      Alpine.store('toast').error(this.error.message);
    },
    
    // 下载 JSON 结果
    downloadJson() {
      if (!this.result?.card && !this.result?.lorebook) return;
      
      const data = this.result.card || { lorebook: this.result.lorebook };
      const json = JSON.stringify(data, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      
      const name = this.result.card?.data?.name || 'lorebook';
      const filename = `${name}_quack_${this.formatDate()}.json`;
      
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    },
    
    // 下载 PNG 结果
    downloadPng() {
      if (!this.resultPngUrl) return;
      
      const name = this.result?.card?.data?.name || 'character';
      const filename = `${name}_${this.formatDate()}.png`;
      
      const a = document.createElement('a');
      a.href = this.resultPngUrl;
      a.download = filename;
      a.click();
    },
    
    // 发送到工作台编辑
    sendToWorkshop() {
      if (!this.result?.card) return;
      
      // 设置卡片数据到 store
      Alpine.store('card').data = this.result.card;
      Alpine.store('card').hasImage = false;
      Alpine.store('card').originalFile = null;
      
      // 切换到工作台页面
      Alpine.store('ui').currentPage = 'workshop';
      
      Alpine.store('toast').success('已发送到工作台，可以继续编辑');
    },
    
    // 清空结果
    clearResult() {
      this.result = null;
      if (this.resultPngUrl) {
        URL.revokeObjectURL(this.resultPngUrl);
        this.resultPngUrl = null;
      }
    },
    
    // 格式化日期
    formatDate() {
      const now = new Date();
      return now.toISOString().slice(0, 10).replace(/-/g, '');
    },
    
    // 销毁时清理
    destroy() {
      if (this.resultPngUrl) {
        URL.revokeObjectURL(this.resultPngUrl);
      }
    },
  };
}

export default quackPage;
