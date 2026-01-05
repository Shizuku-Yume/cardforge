/**
 * 安全预览面板组件
 * 
 * 使用 sandboxed iframe 安全渲染 HTML 内容
 * 集成 DOMPurify 进行 XSS 防护
 * 集成 markdown-it 进行 Markdown 渲染
 * 
 * ⚠️ 保真红线: DOMPurify 仅用于预览渲染层，禁止将过滤结果回写到原始数据
 */

import Alpine from 'alpinejs';
import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: false,
  breaks: true,
});

const IFRAME_STYLES = `
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      color: #3f3f46;
      background: #fafafa;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    p { margin: 0 0 1em; }
    p:last-child { margin-bottom: 0; }
    a { color: #0f766e; text-decoration: underline; }
    a:hover { color: #115e59; }
    strong, b { font-weight: 600; }
    em, i { font-style: italic; }
    code {
      background: #f4f4f5;
      padding: 0.2em 0.4em;
      border-radius: 4px;
      font-size: 0.9em;
      font-family: 'SF Mono', Consolas, monospace;
    }
    pre {
      background: #f4f4f5;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 1em 0;
    }
    pre code {
      background: none;
      padding: 0;
    }
    blockquote {
      margin: 1em 0;
      padding: 0.5em 1em;
      border-left: 4px solid #0f766e;
      background: #f0fdfa;
      color: #115e59;
    }
    hr {
      border: none;
      border-top: 1px solid #e4e4e7;
      margin: 1.5em 0;
    }
    ul, ol {
      margin: 1em 0;
      padding-left: 1.5em;
    }
    li { margin: 0.25em 0; }
    h1, h2, h3, h4, h5, h6 {
      margin: 1em 0 0.5em;
      font-weight: 600;
      line-height: 1.3;
    }
    h1 { font-size: 1.5em; }
    h2 { font-size: 1.3em; }
    h3 { font-size: 1.1em; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 1em 0;
    }
    th, td {
      border: 1px solid #e4e4e7;
      padding: 8px 12px;
      text-align: left;
    }
    th { background: #f4f4f5; font-weight: 600; }
    img {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
    }
    /* 空内容提示 */
    .empty-hint {
      color: #a1a1aa;
      font-style: italic;
      text-align: center;
      padding: 32px 16px;
    }
  </style>
`;

/**
 * DOMPurify 配置
 */
const PURIFY_CONFIG = {
  ALLOWED_TAGS: [
    'p', 'br', 'span', 'div', 'a', 'strong', 'b', 'em', 'i', 'u', 's', 'strike',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
    'hr', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'sup', 'sub', 'mark', 'small',
  ],
  ALLOWED_ATTR: [
    'href', 'target', 'rel', 'class', 'id', 'style',
    'src', 'alt', 'title', 'width', 'height',
    'colspan', 'rowspan',
  ],
  ALLOW_DATA_ATTR: false,
  ADD_ATTR: ['target'],
};

DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

/**
 * 清理 HTML (仅用于预览，不修改原始数据)
 * @param {string} html - 原始 HTML
 * @returns {string} 清理后的 HTML
 */
export function sanitizeHTML(html) {
  if (!html) return '';
  return DOMPurify.sanitize(html, PURIFY_CONFIG);
}

/**
 * 渲染 Markdown 为 HTML
 * @param {string} markdown - Markdown 文本
 * @returns {string} HTML 字符串
 */
export function renderMarkdown(markdown) {
  if (!markdown) return '';
  return md.render(markdown);
}

/**
 * 渲染内容 (自动检测 Markdown/HTML)
 * @param {string} content - 内容
 * @param {Object} options - 渲染选项
 * @param {boolean} options.markdown - 是否按 Markdown 渲染
 * @returns {string} 安全的 HTML
 */
export function renderContent(content, options = {}) {
  if (!content) return '<p class="empty-hint">暂无内容</p>';
  
  let html = content;
  
  if (options.markdown) {
    html = renderMarkdown(content);
  }
  
  return sanitizeHTML(html);
}

/**
 * 生成 iframe srcdoc 内容
 * @param {string} content - 要渲染的内容
 * @param {Object} options - 渲染选项
 * @returns {string} 完整的 HTML 文档
 */
export function generateIframeContent(content, options = {}) {
  const renderedContent = renderContent(content, options);
  
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  ${IFRAME_STYLES}
</head>
<body>
  ${renderedContent}
</body>
</html>
  `.trim();
}

/**
 * 预览面板 Alpine 组件
 */
export function previewPanelComponent(options = {}) {
  return {
    content: options.content || '',
    isMarkdown: options.isMarkdown || false,
    isVisible: false,
    
    get iframeContent() {
      return generateIframeContent(this.content, { markdown: this.isMarkdown });
    },
    
    updateContent(content) {
      this.content = content || '';
    },
    
    toggleMarkdown() {
      this.isMarkdown = !this.isMarkdown;
    },
    
    show() {
      this.isVisible = true;
    },
    
    hide() {
      this.isVisible = false;
    },
    
    toggle() {
      this.isVisible = !this.isVisible;
    },
  };
}

/**
 * Greeting 预览组件 (专门用于开场白预览)
 */
export function greetingPreviewComponent() {
  return {
    isVisible: false,
    currentGreeting: '',
    currentIndex: -1,
    isMarkdown: false,
    
    get iframeContent() {
      return generateIframeContent(this.currentGreeting, { markdown: this.isMarkdown });
    },
    
    showFirstMes() {
      const cardStore = Alpine.store('card');
      this.currentGreeting = cardStore?.data?.data?.first_mes || '';
      this.currentIndex = -1;
      this.isVisible = true;
    },
    
    showAlternate(index) {
      const cardStore = Alpine.store('card');
      const greetings = cardStore?.data?.data?.alternate_greetings || [];
      this.currentGreeting = greetings[index] || '';
      this.currentIndex = index;
      this.isVisible = true;
    },
    
    close() {
      this.isVisible = false;
    },
    
    toggleMarkdown() {
      this.isMarkdown = !this.isMarkdown;
    },
    
    get title() {
      if (this.currentIndex === -1) return '开场白预览';
      return `备选开场白 #${this.currentIndex + 1} 预览`;
    },
  };
}

/**
 * 注册预览组件
 */
export function registerPreviewComponents() {
  Alpine.data('previewPanel', previewPanelComponent);
  Alpine.data('greetingPreview', greetingPreviewComponent);
}

/**
 * 生成预览面板 HTML
 * @returns {string} HTML 字符串
 */
export function generatePreviewPanelHTML() {
  return `
<!-- 预览面板 -->
<div x-data="previewPanel()"
     x-show="isVisible"
     x-transition:enter="transition ease-out duration-200"
     x-transition:enter-start="opacity-0"
     x-transition:enter-end="opacity-100"
     x-transition:leave="transition ease-in duration-150"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0"
     class="fixed inset-0 z-50 flex items-center justify-center"
     x-cloak>
  
  <!-- 遮罩 -->
  <div class="absolute inset-0 bg-zinc-900/50 backdrop-blur-sm" @click="hide()"></div>
  
  <!-- 内容 -->
  <div class="relative bg-white rounded-neo-lg shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col mx-4"
       x-transition:enter="transition ease-out duration-200"
       x-transition:enter-start="opacity-0 scale-95"
       x-transition:enter-end="opacity-100 scale-100">
    
    <!-- 头部 -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-100">
      <h3 class="text-lg font-semibold text-zinc-900">内容预览</h3>
      <div class="flex items-center gap-3">
        <!-- Markdown 切换 -->
        <label class="flex items-center gap-2 text-sm text-zinc-600 cursor-pointer">
          <input type="checkbox" x-model="isMarkdown" class="rounded border-zinc-300">
          <span>Markdown 渲染</span>
        </label>
        <!-- 关闭按钮 -->
        <button @click="hide()" class="p-1 text-zinc-400 hover:text-zinc-600">
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- iframe 容器 -->
    <div class="flex-1 overflow-hidden p-4">
      <iframe
        :srcdoc="iframeContent"
        sandbox=""
        class="w-full h-full border-0 rounded-neo bg-zinc-50"
        style="min-height: 300px;">
      </iframe>
    </div>
  </div>
</div>
  `;
}

/**
 * 生成 Greeting 预览面板 HTML
 * @returns {string} HTML 字符串
 */
export function generateGreetingPreviewHTML() {
  return `
<!-- Greeting 预览面板 -->
<div x-data="greetingPreview()"
     x-show="isVisible"
     x-transition:enter="transition ease-out duration-200"
     x-transition:enter-start="opacity-0"
     x-transition:enter-end="opacity-100"
     x-transition:leave="transition ease-in duration-150"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0"
     class="fixed inset-0 z-50 flex items-center justify-center"
     x-cloak
     @greeting-preview.window="currentGreeting = $event.detail.content; currentIndex = $event.detail.index ?? -1; isVisible = true">
  
  <!-- 遮罩 -->
  <div class="absolute inset-0 bg-zinc-900/50 backdrop-blur-sm" @click="close()"></div>
  
  <!-- 内容 -->
  <div class="relative bg-white rounded-neo-lg shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col mx-4">
    
    <!-- 头部 -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-100">
      <h3 class="text-lg font-semibold text-zinc-900" x-text="title"></h3>
      <div class="flex items-center gap-3">
        <!-- Markdown 切换 -->
        <label class="flex items-center gap-2 text-sm text-zinc-600 cursor-pointer">
          <input type="checkbox" x-model="isMarkdown" class="rounded border-zinc-300">
          <span>Markdown</span>
        </label>
        <!-- 关闭按钮 -->
        <button @click="close()" class="p-1 text-zinc-400 hover:text-zinc-600">
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </div>
    
    <!-- iframe 容器 -->
    <div class="flex-1 overflow-hidden p-4">
      <iframe
        :srcdoc="iframeContent"
        sandbox=""
        class="w-full h-full border-0 rounded-neo bg-zinc-50"
        style="min-height: 400px;">
      </iframe>
    </div>
  </div>
</div>
  `;
}

export default {
  sanitizeHTML,
  renderMarkdown,
  renderContent,
  generateIframeContent,
  previewPanelComponent,
  greetingPreviewComponent,
  registerPreviewComponents,
  generatePreviewPanelHTML,
  generateGreetingPreviewHTML,
};
