/**
 * 移动端头部组件
 * 
 * 提供响应式导航头部，包括汉堡菜单和移动端优化
 * 遵循 frontend_design.md 设计规范
 */

import Alpine from 'alpinejs';

// 导航项配置
const NAV_ITEMS = [
  { id: 'workshop', label: '工作台', icon: 'squares' },
  { id: 'quack', label: 'Quack导入', icon: 'arrow-down-tray' },
  { id: 'ai', label: 'AI辅助', icon: 'sparkles' },
];

// 图标 SVG
const ICONS = {
  squares: `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
  </svg>`,
  
  'arrow-down-tray': `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
  </svg>`,
  
  sparkles: `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
  </svg>`,
  
  menu: `<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
  </svg>`,
  
  close: `<svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
  </svg>`,
};

/**
 * 移动端头部组件
 * 使用方式: <header x-data="mobileHeader()">...</header>
 */
export function mobileHeaderComponent() {
  return {
    navItems: NAV_ITEMS,
    
    get isMenuOpen() {
      return Alpine.store('ui').mobileMenuOpen;
    },
    
    set isMenuOpen(value) {
      Alpine.store('ui').mobileMenuOpen = value;
    },
    
    get currentPage() {
      return Alpine.store('ui').currentPage;
    },
    
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen;
    },
    
    closeMenu() {
      this.isMenuOpen = false;
    },
    
    navigateTo(pageId) {
      Alpine.store('ui').currentPage = pageId;
      this.closeMenu();
    },
    
    isActive(pageId) {
      return this.currentPage === pageId;
    },
    
    getIcon(iconName) {
      return ICONS[iconName] || '';
    },
    
    getMenuIcon() {
      return this.isMenuOpen ? ICONS.close : ICONS.menu;
    },
    
    get appVersion() {
      return Alpine.store('app').version;
    },
  };
}

/**
 * 生成头部 HTML
 * @param {Object} options - 配置选项
 * @returns {string} HTML 字符串
 */
export function getHeaderHTML(options = {}) {
  const { showVersion = true } = options;
  
  return `
    <header x-data="mobileHeader()" 
            class="bg-white shadow-neo-lift border-b border-zinc-100 sticky top-0 z-40 safe-area-inset-top">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo -->
          <div class="flex items-center gap-2">
            <span class="text-xl font-bold text-brand">CardForge</span>
            ${showVersion ? '<span class="text-xs text-zinc-400" x-text="\'v\' + appVersion"></span>' : ''}
          </div>
          
          <!-- Desktop Navigation -->
          <nav class="hidden sm:flex items-center gap-1">
            <template x-for="item in navItems" :key="item.id">
              <button 
                @click="navigateTo(item.id)"
                :class="isActive(item.id) 
                  ? 'bg-zinc-100 text-brand font-medium shadow-neo-inset' 
                  : 'text-zinc-500 hover:text-zinc-700 hover:bg-zinc-50'"
                class="px-4 py-2 rounded-neo transition-all flex items-center gap-2"
              >
                <span x-html="getIcon(item.icon)"></span>
                <span x-text="item.label"></span>
              </button>
            </template>
          </nav>
          
          <!-- Mobile Menu Button -->
          <button class="sm:hidden p-2 text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100 rounded-neo transition-colors"
                  @click="toggleMenu()"
                  :aria-expanded="isMenuOpen"
                  aria-label="菜单">
            <span x-html="getMenuIcon()"></span>
          </button>
        </div>
        
        <!-- Mobile Menu -->
        <div x-show="isMenuOpen" 
             x-collapse
             x-cloak
             class="sm:hidden pb-4">
          <div class="flex flex-col gap-1">
            <template x-for="item in navItems" :key="item.id">
              <button 
                @click="navigateTo(item.id)"
                :class="isActive(item.id) 
                  ? 'bg-zinc-100 text-brand font-medium' 
                  : 'text-zinc-500'"
                class="px-4 py-3 rounded-neo text-left transition-colors flex items-center gap-3"
              >
                <span x-html="getIcon(item.icon)"></span>
                <span x-text="item.label"></span>
              </button>
            </template>
          </div>
        </div>
      </div>
    </header>
  `;
}

/**
 * 生成底部导航 HTML (移动端)
 * @returns {string} HTML 字符串
 */
export function getBottomNavHTML() {
  return `
    <nav x-data="mobileHeader()"
         class="sm:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-zinc-100 z-40 safe-area-inset-bottom">
      <div class="flex items-center justify-around h-16">
        <template x-for="item in navItems" :key="item.id">
          <button 
            @click="navigateTo(item.id)"
            :class="isActive(item.id) 
              ? 'text-brand' 
              : 'text-zinc-400'"
            class="flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors"
          >
            <span x-html="getIcon(item.icon)"></span>
            <span class="text-xs font-medium" x-text="item.label"></span>
          </button>
        </template>
      </div>
    </nav>
  `;
}

/**
 * 简单面包屑组件
 * @param {Array<{label: string, href?: string}>} items - 面包屑项
 * @returns {string} HTML 字符串
 */
export function getBreadcrumbHTML(items) {
  if (!items || items.length === 0) return '';
  
  let html = '<nav class="flex items-center gap-2 text-sm text-zinc-500">';
  
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const isLast = i === items.length - 1;
    
    if (item.href && !isLast) {
      html += `<a href="${item.href}" class="hover:text-brand transition-colors">${item.label}</a>`;
    } else {
      html += `<span class="${isLast ? 'text-zinc-800 font-medium' : ''}">${item.label}</span>`;
    }
    
    if (!isLast) {
      html += `<span class="text-zinc-300">/</span>`;
    }
  }
  
  html += '</nav>';
  return html;
}

/**
 * 注册移动端头部组件
 */
export function registerMobileHeaderComponent() {
  Alpine.data('mobileHeader', mobileHeaderComponent);
}

// ============================================================
// 导出
// ============================================================

export default {
  mobileHeaderComponent,
  registerMobileHeaderComponent,
  getHeaderHTML,
  getBottomNavHTML,
  getBreadcrumbHTML,
  NAV_ITEMS,
  ICONS,
};
