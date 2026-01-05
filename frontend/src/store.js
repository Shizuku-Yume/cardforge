/**
 * Alpine.js 全局状态管理
 * 
 * 提供深层嵌套对象的响应式更新支持
 */

import Alpine from 'alpinejs';

// ============================================================
// 工具函数
// ============================================================

/**
 * 深拷贝对象
 * 优先使用原生 structuredClone，兜底手写实现
 */
export function deepClone(obj) {
  // 优先使用原生 structuredClone (性能更好，支持更多类型)
  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(obj);
    } catch {
      // structuredClone 不支持某些类型 (如函数)，回退手写
    }
  }
  
  // 兜底实现
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => deepClone(item));
  }
  
  const cloned = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      cloned[key] = deepClone(obj[key]);
    }
  }
  return cloned;
}

/**
 * 深度比较两个对象是否相等
 */
export function deepEqual(a, b) {
  if (a === b) return true;
  if (a === null || b === null) return a === b;
  if (typeof a !== 'object' || typeof b !== 'object') return false;
  
  // 数组类型必须一致
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  
  if (keysA.length !== keysB.length) return false;
  
  for (const key of keysA) {
    if (!keysB.includes(key) || !deepEqual(a[key], b[key])) {
      return false;
    }
  }
  
  return true;
}

/**
 * 通过路径获取嵌套对象的值
 * @param {Object} obj - 目标对象
 * @param {string} path - 路径，如 'data.character_book.entries[0].keys'
 * @returns {any} 路径对应的值
 */
export function getByPath(obj, path) {
  const keys = path.replace(/\[(\d+)\]/g, '.$1').split('.');
  let current = obj;
  
  for (const key of keys) {
    if (current === null || current === undefined) {
      return undefined;
    }
    current = current[key];
  }
  
  return current;
}

/**
 * 通过路径设置嵌套对象的值
 * @param {Object} obj - 目标对象
 * @param {string} path - 路径
 * @param {any} value - 要设置的值
 * @param {boolean} autoCreate - 是否自动创建不存在的路径 (默认 true)
 */
export function setByPath(obj, path, value, autoCreate = true) {
  const keys = path.replace(/\[(\d+)\]/g, '.$1').split('.');
  let current = obj;
  
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    const nextKey = keys[i + 1];
    
    // 类型检查：如果 current[key] 存在但不是对象，必须覆盖它
    if (current[key] !== undefined && current[key] !== null && typeof current[key] !== 'object') {
      if (!autoCreate) {
        console.warn(`[store] Cannot traverse path at ${keys.slice(0, i + 1).join('.')}`);
        return;
      }
      console.warn(`[store] Overwriting primitive value at ${keys.slice(0, i + 1).join('.')}`);
      current[key] = /^\d+$/.test(nextKey) ? [] : {};
    }
    
    if (current[key] === undefined || current[key] === null) {
      if (!autoCreate) {
        console.warn(`[store] Path does not exist: ${keys.slice(0, i + 1).join('.')}`);
        return;
      }
      // 判断下一个 key 是否为数字索引
      current[key] = /^\d+$/.test(nextKey) ? [] : {};
    }
    current = current[key];
  }
  
  current[keys[keys.length - 1]] = value;
}

// ============================================================
// 创建默认空卡片结构 (CCv3)
// ============================================================

export function createEmptyCard() {
  return {
    spec: 'chara_card_v3',
    spec_version: '3.0',
    data: {
      name: '',
      description: '',
      personality: '',
      scenario: '',
      first_mes: '',
      mes_example: '',
      creator_notes: '',
      system_prompt: '',
      post_history_instructions: '',
      tags: [],
      creator: '',
      character_version: '',
      alternate_greetings: [],
      group_only_greetings: [],
      character_book: null,
      extensions: {},
      assets: [],
      nickname: '',
      source: [],
    },
  };
}

// ============================================================
// 初始化 Alpine Stores
// ============================================================

export function initStores() {
  // ----- App Store -----
  Alpine.store('app', {
    version: '0.1.0',
    ready: false,
    
    init() {
      this.ready = true;
    },
  });

  // ----- UI Store -----
  Alpine.store('ui', {
    // 导航
    currentPage: 'workshop',
    sidebarOpen: true,
    mobileMenuOpen: false,
    
    // 加载状态
    globalLoading: false,
    loadingMessage: '',
    loadingProgress: 0,
    
    // 模态框状态
    modalOpen: false,
    modalType: null,
    modalData: null,

    // 设置加载状态
    setLoading(loading, message = '') {
      this.globalLoading = loading;
      this.loadingMessage = message;
      this.loadingProgress = 0;
    },

    // 更新加载进度
    setProgress(progress) {
      this.loadingProgress = Math.min(100, Math.max(0, progress));
    },

    // 打开模态框
    openModal(type, data = null) {
      this.modalType = type;
      this.modalData = data;
      this.modalOpen = true;
    },

    // 关闭模态框
    closeModal() {
      this.modalOpen = false;
      this.modalType = null;
      this.modalData = null;
    },
  });

  // ----- Card Store -----
  Alpine.store('card', {
    // 当前编辑的卡片数据
    data: null,
    
    // 原始数据 (用于比较变更)
    originalData: null,
    
    // 源文件信息
    sourceFile: null,
    sourceFormat: null,
    
    // 图片数据
    imageDataUrl: null,
    imageFile: null,
    
    // 状态标记
    hasChanges: false,
    lastSaved: null,

    // 初始化新卡片
    initNew() {
      this.data = createEmptyCard();
      this.originalData = deepClone(this.data);
      this.sourceFile = null;
      this.sourceFormat = null;
      this.imageDataUrl = null;
      this.imageFile = null;
      this.hasChanges = false;
      this.lastSaved = null;
    },

    // 加载解析后的卡片
    loadCard(parseResult, file = null, imageDataUrl = null) {
      this.data = parseResult.card;
      this.originalData = deepClone(parseResult.card);
      this.sourceFile = file;
      this.sourceFormat = parseResult.source_format;
      this.imageDataUrl = imageDataUrl;
      this.imageFile = file?.type?.startsWith('image/') ? file : null;
      this.hasChanges = false;
      this.lastSaved = null;
    },

    // 更新字段 (支持深层路径)
    updateField(path, value) {
      if (!this.data) return;
      setByPath(this.data, path, value);
      this.checkChanges();
    },

    // 获取字段值 (支持深层路径)
    getField(path) {
      if (!this.data) return undefined;
      return getByPath(this.data, path);
    },

    // 防抖定时器
    _checkChangesTimer: null,
    
    // 检查是否有变更 (防抖优化: 500ms 内连续调用只执行一次)
    checkChanges() {
      // 立即设置脏标记 (乐观更新)
      this.hasChanges = true;
      
      // 防抖: 清除之前的定时器
      if (this._checkChangesTimer) {
        clearTimeout(this._checkChangesTimer);
      }
      
      // 延迟执行精确比较
      this._checkChangesTimer = setTimeout(() => {
        this.hasChanges = !deepEqual(this.data, this.originalData);
        this._checkChangesTimer = null;
      }, 500);
    },

    // 标记已保存
    markSaved() {
      this.originalData = deepClone(this.data);
      this.hasChanges = false;
      this.lastSaved = new Date();
    },

    // 重置到原始状态
    reset() {
      if (this.originalData) {
        this.data = deepClone(this.originalData);
        this.hasChanges = false;
      }
    },

    // 清空卡片
    clear() {
      this.data = null;
      this.originalData = null;
      this.sourceFile = null;
      this.sourceFormat = null;
      this.imageDataUrl = null;
      this.imageFile = null;
      this.hasChanges = false;
      this.lastSaved = null;
    },
  });

  // ----- Settings Store -----
  Alpine.store('settings', {
    // AI 设置
    apiKey: '',
    apiUrl: '',
    model: '',
    proxyEnabled: false,
    availableModels: [],
    
    // 编辑器设置
    autoSaveEnabled: true,
    autoSaveInterval: 30, // 秒
    
    // 导出设置
    includeV2Compat: true,
    
    // 加载设置
    load() {
      try {
        const saved = localStorage.getItem('cardforge_settings');
        if (saved) {
          const parsed = JSON.parse(saved);
          // 只恢复非敏感设置
          this.autoSaveEnabled = parsed.autoSaveEnabled ?? true;
          this.autoSaveInterval = parsed.autoSaveInterval ?? 30;
          this.includeV2Compat = parsed.includeV2Compat ?? true;
          this.proxyEnabled = parsed.proxyEnabled ?? false;
        }
      } catch (e) {
        console.warn('Failed to load settings:', e);
      }
    },
    
    // 保存设置
    save() {
      try {
        const toSave = {
          autoSaveEnabled: this.autoSaveEnabled,
          autoSaveInterval: this.autoSaveInterval,
          includeV2Compat: this.includeV2Compat,
          proxyEnabled: this.proxyEnabled,
          // 注意: API Key 不保存到 localStorage
        };
        localStorage.setItem('cardforge_settings', JSON.stringify(toSave));
      } catch (e) {
        console.warn('Failed to save settings:', e);
      }
    },
  });

  // ----- Toast Store -----
  Alpine.store('toast', {
    items: [],
    nextId: 1,

    /**
     * 显示 toast 通知
     * @param {Object} options
     * @param {string} options.message - 消息内容
     * @param {'success'|'error'|'loading'|'info'} options.type - 类型
     * @param {number} options.duration - 持续时间 (毫秒), 0 表示不自动关闭
     * @returns {number} toast ID
     */
    show({ message, type = 'info', duration = 3000 }) {
      const id = this.nextId++;
      this.items.push({ id, message, type, duration });
      
      if (duration > 0) {
        setTimeout(() => this.dismiss(id), duration);
      }
      
      return id;
    },

    // 快捷方法
    success(message, duration = 3000) {
      return this.show({ message, type: 'success', duration });
    },

    error(message, duration = 5000) {
      return this.show({ message, type: 'error', duration });
    },

    loading(message) {
      return this.show({ message, type: 'loading', duration: 0 });
    },

    info(message, duration = 3000) {
      return this.show({ message, type: 'info', duration });
    },

    // 关闭指定 toast
    dismiss(id) {
      const index = this.items.findIndex(item => item.id === id);
      if (index !== -1) {
        this.items.splice(index, 1);
      }
    },

    // 更新 toast 消息
    update(id, { message, type }) {
      const item = this.items.find(item => item.id === id);
      if (item) {
        if (message !== undefined) item.message = message;
        if (type !== undefined) item.type = type;
      }
    },

    // 清空所有 toast
    clear() {
      this.items = [];
    },
  });

  // ----- Undo/Redo Store (历史记录) -----
  // 采用单栈+指针方案（与 undo_redo.js 保持一致）
  Alpine.store('history', {
    stack: [],
    index: -1,
    maxSize: 10,

    /**
     * 记录新状态
     * @param {Object} state - 要记录的状态
     */
    push(state) {
      // 如果当前不在栈顶，裁剪掉指针后面的状态
      if (this.index < this.stack.length - 1) {
        this.stack = this.stack.slice(0, this.index + 1);
      }
      
      // 添加新状态
      this.stack.push(deepClone(state));
      this.index = this.stack.length - 1;
      
      // 限制栈大小
      if (this.stack.length > this.maxSize) {
        this.stack.shift();
        this.index--;
      }
    },

    /**
     * 撤销操作
     * @returns {Object|null} 撤销后的状态
     */
    undo() {
      if (!this.canUndo) return null;
      
      this.index--;
      return deepClone(this.stack[this.index]);
    },

    /**
     * 重做操作
     * @returns {Object|null} 重做后的状态
     */
    redo() {
      if (!this.canRedo) return null;
      
      this.index++;
      return deepClone(this.stack[this.index]);
    },

    /**
     * 清空历史
     */
    clear() {
      this.stack = [];
      this.index = -1;
    },

    /**
     * 初始化（保存当前状态作为初始状态）
     * @param {Object} initialState - 初始状态
     */
    init(initialState) {
      this.clear();
      this.push(initialState);
    },

    /**
     * 是否可以撤销
     */
    get canUndo() {
      return this.index > 0;
    },

    /**
     * 是否可以重做
     */
    get canRedo() {
      return this.index < this.stack.length - 1;
    },
  });
}

// ============================================================
// 导出
// ============================================================

export default {
  initStores,
  createEmptyCard,
  deepClone,
  deepEqual,
  getByPath,
  setByPath,
};
