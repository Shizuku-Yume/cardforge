/**
 * AI 字段辅助入口组件 (魔法棒)
 * 
 * 在特定文本字段旁提供 AI 辅助按钮，快速调用生成/优化/翻译功能
 */

import Alpine from 'alpinejs';

// ============================================================
// AI 魔法棒组件
// ============================================================

/**
 * AI 魔法棒组件
 * 
 * @param {string} field - 字段路径，如 'description', 'personality'
 * @returns {Object} Alpine.js 组件
 */
export function aiFieldTrigger(field) {
  return {
    field,
    showMenu: false,
    
    get ai() {
      return Alpine.store('ai');
    },
    
    get isConnected() {
      return this.ai?.isConnected ?? false;
    },
    
    get isGenerating() {
      return this.ai?.isGenerating ?? false;
    },
    
    /**
     * 优化润色
     */
    async enhance() {
      this.showMenu = false;
      if (!this.checkConnection()) return;
      await this.ai.enhance(this.field);
    },
    
    /**
     * 扩写内容
     */
    async expand() {
      this.showMenu = false;
      if (!this.checkConnection()) return;
      await this.ai.expand(this.field);
    },
    
    /**
     * 翻译
     */
    async translate() {
      this.showMenu = false;
      if (!this.checkConnection()) return;
      await this.ai.translate(this.field, '中文');
    },
    
    /**
     * 翻译为英文
     */
    async translateToEnglish() {
      this.showMenu = false;
      if (!this.checkConnection()) return;
      await this.ai.translate(this.field, 'English');
    },
    
    /**
     * 打开自定义指令
     */
    openCustom() {
      this.showMenu = false;
      if (!this.checkConnection()) return;
      this.ai.openChat(this.field);
    },
    
    /**
     * 检查连接状态
     */
    checkConnection() {
      if (!this.isConnected) {
        Alpine.store('toast').error('请先在 AI 辅助页面配置并测试 AI 连接');
        return false;
      }
      return true;
    },
    
    /**
     * 切换菜单
     */
    toggleMenu() {
      if (this.isGenerating) return;
      this.showMenu = !this.showMenu;
    },
  };
}

// ============================================================
// HTML 生成器
// ============================================================

/**
 * 生成 AI 魔法棒按钮 HTML
 * 
 * @param {string} field - 字段路径
 * @returns {string} HTML 字符串
 */
// 安全转义字符串
function escapeForJsAttr(str) {
  return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

export function getAITriggerButtonHTML(field) {
  const safeField = escapeForJsAttr(field);
  return `
    <div class="relative" x-data="aiFieldTrigger('${safeField}')">
      <!-- 魔法棒按钮 -->
      <button @click="toggleMenu()"
              :disabled="isGenerating"
              :class="isGenerating ? 'text-zinc-300 cursor-wait' : 'text-zinc-400 hover:text-brand'"
              class="p-1.5 bg-white/80 rounded-neo shadow-sm backdrop-blur transition-colors"
              title="AI 辅助">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
        </svg>
      </button>
      
      <!-- AI 功能菜单 -->
      <div x-show="showMenu" x-cloak
           @click.outside="showMenu = false"
           x-transition:enter="transition ease-out duration-150"
           x-transition:enter-start="opacity-0 scale-95"
           x-transition:enter-end="opacity-100 scale-100"
           x-transition:leave="transition ease-in duration-100"
           x-transition:leave-start="opacity-100 scale-100"
           x-transition:leave-end="opacity-0 scale-95"
           class="absolute right-0 top-full mt-1 w-48 bg-white rounded-neo shadow-neo-lift border border-zinc-100 py-1 z-20">
        
        <!-- 优化润色 -->
        <button @click="enhance()"
                class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
          <svg class="w-4 h-4 text-teal-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          优化润色
        </button>
        
        <!-- 扩写内容 -->
        <button @click="expand()"
                class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
          <svg class="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
          </svg>
          扩写内容
        </button>
        
        <hr class="my-1 border-zinc-100">
        
        <!-- 翻译为中文 -->
        <button @click="translate()"
                class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
          <svg class="w-4 h-4 text-purple-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802" />
          </svg>
          翻译为中文
        </button>
        
        <!-- 翻译为英文 -->
        <button @click="translateToEnglish()"
                class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
          <svg class="w-4 h-4 text-purple-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802" />
          </svg>
          翻译为英文
        </button>
        
        <hr class="my-1 border-zinc-100">
        
        <!-- 自定义指令 -->
        <button @click="openCustom()"
                class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
          <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
          </svg>
          自定义指令...
        </button>
      </div>
    </div>
  `;
}

/**
 * 生成带 AI 魔法棒的 Textarea HTML
 * 
 * @param {Object} options - 配置选项
 * @param {string} options.field - 字段路径
 * @param {string} options.label - 标签文本
 * @param {string} options.placeholder - 占位符
 * @param {number} options.rows - 行数
 * @param {string} options.model - x-model 绑定路径
 * @returns {string} HTML 字符串
 */
export function getTextareaWithAIHTML(options) {
  const {
    field,
    label,
    placeholder = '',
    rows = 4,
    model,
  } = options;

  const safeField = escapeForJsAttr(field);
  const safeLabel = escapeForJsAttr(label);
  const safePlaceholder = escapeForJsAttr(placeholder);
  const safeModel = escapeForJsAttr(model);

  return `
    <div class="space-y-1">
      <label class="text-sm font-medium text-zinc-700 block">${safeLabel}</label>
      <div class="relative" x-data="aiFieldTrigger('${safeField}')">
        <textarea x-model="${safeModel}"
                  rows="${rows}"
                  class="w-full bg-zinc-100/80 shadow-neo-inset rounded-neo px-3 py-2 pr-10 text-sm
                         resize-y outline-none focus:bg-white focus:ring-2 focus:ring-teal-100 transition-all"
                  placeholder="${safePlaceholder}"></textarea>
        <!-- AI 魔法棒按钮 (绝对定位在右上角) -->
        <div class="absolute right-2 top-2">
          <button @click="toggleMenu()"
                  :disabled="isGenerating"
                  :class="isGenerating ? 'text-zinc-300 cursor-wait' : 'text-zinc-400 hover:text-brand'"
                  class="p-1.5 bg-white/80 rounded-neo shadow-sm backdrop-blur transition-colors"
                  title="AI 辅助">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
            </svg>
          </button>
          
          <!-- AI 功能菜单 -->
          <div x-show="showMenu" x-cloak
               @click.outside="showMenu = false"
               x-transition:enter="transition ease-out duration-150"
               x-transition:enter-start="opacity-0 scale-95"
               x-transition:enter-end="opacity-100 scale-100"
               x-transition:leave="transition ease-in duration-100"
               x-transition:leave-start="opacity-100 scale-100"
               x-transition:leave-end="opacity-0 scale-95"
               class="absolute right-0 top-full mt-1 w-48 bg-white rounded-neo shadow-neo-lift border border-zinc-100 py-1 z-20">
            
            <button @click="enhance()"
                    class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
              <svg class="w-4 h-4 text-teal-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              优化润色
            </button>
            
            <button @click="expand()"
                    class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
              <svg class="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
              </svg>
              扩写内容
            </button>
            
            <hr class="my-1 border-zinc-100">
            
            <button @click="translate()"
                    class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
              <svg class="w-4 h-4 text-purple-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802" />
              </svg>
              翻译为中文
            </button>
            
            <button @click="translateToEnglish()"
                    class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
              <svg class="w-4 h-4 text-purple-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="m10.5 21 5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 0 1 6-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 0 1-3.827-5.802" />
              </svg>
              翻译为英文
            </button>
            
            <hr class="my-1 border-zinc-100">
            
            <button @click="openCustom()"
                    class="w-full text-left px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50 flex items-center gap-2 transition-colors">
              <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
              </svg>
              自定义指令...
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

// ============================================================
// 注册组件
// ============================================================

export function registerAIFieldTriggerComponent() {
  Alpine.data('aiFieldTrigger', aiFieldTrigger);
}

// ============================================================
// 导出
// ============================================================

export default {
  aiFieldTrigger,
  getAITriggerButtonHTML,
  getTextareaWithAIHTML,
  registerAIFieldTriggerComponent,
};
