/**
 * AI 辅助页面组件
 * 
 * 提供 AI 设置面板和各种 AI 工作流
 */

import Alpine from 'alpinejs';
import { 
  chat, 
  chatStream, 
  getModels, 
  testConnection, 
  TypewriterEffect,
  AI_PROMPTS,
} from '../components/ai_client.js';
import { deepClone, createEmptyCard } from '../store.js';

// ============================================================
// AI Store 初始化
// ============================================================

export function initAIStore() {
  Alpine.store('ai', {
    // 配置
    baseUrl: '',
    apiKey: '',
    model: '',
    useProxy: true,
    
    // 模型列表
    models: [],
    isLoadingModels: false,
    
    // 连接状态
    isConnected: false,
    connectionError: '',
    
    // 生成状态
    isGenerating: false,
    abortController: null,
    currentOutput: '',
    
    // 当前工作流
    currentWorkflow: null,
    workflowTarget: null,
    
    /**
     * 获取配置对象
     */
    getConfig() {
      return {
        baseUrl: this.baseUrl,
        apiKey: this.apiKey,
        model: this.model,
        useProxy: this.useProxy,
      };
    },
    
    /**
     * 加载保存的设置
     */
    loadSettings() {
      try {
        const saved = localStorage.getItem('cardforge_ai_settings');
        if (saved) {
          const parsed = JSON.parse(saved);
          this.baseUrl = parsed.baseUrl || '';
          this.model = parsed.model || '';
          this.useProxy = parsed.useProxy ?? true;
        }
      } catch (e) {
        console.warn('Failed to load AI settings:', e);
      }
    },
    
    /**
     * 保存设置
     */
    saveSettings() {
      try {
        localStorage.setItem('cardforge_ai_settings', JSON.stringify({
          baseUrl: this.baseUrl,
          model: this.model,
          useProxy: this.useProxy,
        }));
      } catch (e) {
        console.warn('Failed to save AI settings:', e);
      }
    },
    
    /**
     * 测试连接
     */
    async testConnection() {
      if (!this.baseUrl || !this.apiKey) {
        this.connectionError = '请填写 API URL 和 API Key';
        return false;
      }
      
      this.isLoadingModels = true;
      this.connectionError = '';
      
      const result = await testConnection(this.getConfig());
      
      this.isLoadingModels = false;
      this.isConnected = result.success;
      
      if (result.success) {
        this.models = result.models;
        if (!this.model && this.models.length > 0) {
          this.model = this.models[0].id;
        }
        Alpine.store('toast').success(result.message);
      } else {
        this.connectionError = result.message;
        Alpine.store('toast').error(result.message);
      }
      
      return result.success;
    },
    
    /**
     * 加载模型列表
     */
    async loadModels() {
      if (!this.baseUrl || !this.apiKey) return;
      
      this.isLoadingModels = true;
      
      try {
        this.models = await getModels(this.getConfig());
        this.isConnected = true;
      } catch (e) {
        console.error('Failed to load models:', e);
        this.connectionError = e.message;
      } finally {
        this.isLoadingModels = false;
      }
    },
    
    /**
     * 停止生成
     */
    stopGenerating() {
      if (this.abortController) {
        this.abortController.abort();
        this.abortController = null;
      }
      this.isGenerating = false;
    },
    
    /**
     * 字段优化
     */
    async enhance(field) {
      const card = Alpine.store('card');
      if (!card.data) return;
      
      const text = this._getFieldValue(card.data, field);
      if (!text) {
        Alpine.store('toast').error('该字段为空');
        return;
      }
      
      await this._runWorkflow('enhance', field, AI_PROMPTS.enhance(text, field));
    },
    
    /**
     * 字段扩写
     */
    async expand(field) {
      const card = Alpine.store('card');
      if (!card.data) return;
      
      const text = this._getFieldValue(card.data, field);
      if (!text) {
        Alpine.store('toast').error('该字段为空');
        return;
      }
      
      await this._runWorkflow('expand', field, AI_PROMPTS.expand(text, field));
    },
    
    /**
     * 字段翻译
     */
    async translate(field, targetLang = '中文') {
      const card = Alpine.store('card');
      if (!card.data) return;
      
      const text = this._getFieldValue(card.data, field);
      if (!text) {
        Alpine.store('toast').error('该字段为空');
        return;
      }
      
      await this._runWorkflow('translate', field, AI_PROMPTS.translate(text, targetLang));
    },
    
    /**
     * 打开自定义指令对话框
     */
    openChat(field) {
      this.currentWorkflow = 'custom';
      this.workflowTarget = field;
      Alpine.store('ui').openModal('ai-chat', { field });
    },
    
    /**
     * 获取字段值
     */
    _getFieldValue(card, field) {
      const parts = field.split('.');
      let value = card.data;
      for (const part of parts) {
        if (value === null || value === undefined) return '';
        value = value[part];
      }
      return typeof value === 'string' ? value : '';
    },
    
    /**
     * 设置字段值
     */
    _setFieldValue(card, field, value) {
      const parts = field.split('.');
      let target = card.data;
      for (let i = 0; i < parts.length - 1; i++) {
        target = target[parts[i]];
      }
      target[parts[parts.length - 1]] = value;
    },
    
    /**
     * 运行工作流
     */
    async _runWorkflow(type, field, messages) {
      if (!this.isConnected) {
        Alpine.store('toast').error('请先配置并测试 AI 连接');
        return;
      }
      
      this.isGenerating = true;
      this.currentOutput = '';
      this.currentWorkflow = type;
      this.workflowTarget = field;
      
      const toast = Alpine.store('toast');
      const toastId = toast.loading(`AI 正在${this._getWorkflowName(type)}...`);
      
      try {
        this.abortController = chatStream(this.getConfig(), messages, {
          onMessage: (delta, full) => {
            this.currentOutput = full;
          },
          onError: (error) => {
            toast.update(toastId, { message: error.message, type: 'error' });
            setTimeout(() => toast.dismiss(toastId), 3000);
            this.isGenerating = false;
          },
          onDone: (fullContent) => {
            toast.dismiss(toastId);
            this.isGenerating = false;
            
            if (fullContent) {
              // 更新字段
              const card = Alpine.store('card');
              const history = Alpine.store('history');
              
              // 记录历史
              history.push(deepClone(card.data));
              
              // 更新字段值
              this._setFieldValue(card, field, fullContent);
              card.checkChanges();
              
              toast.success(`${this._getWorkflowName(type)}完成`);
            }
          },
        });
      } catch (error) {
        toast.update(toastId, { message: error.message, type: 'error' });
        setTimeout(() => toast.dismiss(toastId), 3000);
        this.isGenerating = false;
      }
    },
    
    /**
     * 获取工作流名称
     */
    _getWorkflowName(type) {
      const names = {
        enhance: '优化润色',
        expand: '扩写',
        translate: '翻译',
        modernize: '焕新',
        generate: '生成',
        custom: '处理',
      };
      return names[type] || '处理';
    },
  });
}

// ============================================================
// AI 页面组件
// ============================================================

export function aiPage() {
  return {
    // 设置面板
    showSettings: true,
    
    // 新卡生成
    cardConcept: '',
    generatedCard: null,
    
    // 开场白裂变
    greetingCount: 3,
    generatedGreetings: [],
    
    // 翻译
    translateLang: '中文',
    
    // 打字机效果
    typewriter: null,
    outputText: '',
    
    init() {
      // 初始化 AI Store
      if (!Alpine.store('ai')) {
        initAIStore();
      }
      
      // 加载设置
      Alpine.store('ai').loadSettings();
      
      // 初始化打字机
      this.typewriter = new TypewriterEffect({
        onUpdate: (text) => {
          this.outputText = text;
        },
      });
    },
    
    destroy() {
      if (this.typewriter) {
        this.typewriter.destroy();
      }
    },
    
    // ============================================================
    // 设置相关
    // ============================================================
    
    get ai() {
      return Alpine.store('ai');
    },
    
    get isConfigured() {
      return this.ai.baseUrl && this.ai.apiKey;
    },
    
    async testConnection() {
      await this.ai.testConnection();
    },
    
    saveSettings() {
      this.ai.saveSettings();
      Alpine.store('toast').success('设置已保存');
    },
    
    // ============================================================
    // 工作流
    // ============================================================
    
    /**
     * 生成新角色卡
     */
    async generateNewCard() {
      if (!this.cardConcept.trim()) {
        Alpine.store('toast').error('请输入角色概念');
        return;
      }
      
      if (!this.ai.isConnected) {
        Alpine.store('toast').error('请先配置并测试 AI 连接');
        return;
      }
      
      this.ai.isGenerating = true;
      this.generatedCard = null;
      this.outputText = '';
      this.typewriter.reset();
      
      const toast = Alpine.store('toast');
      const toastId = toast.loading('正在生成角色卡...');
      
      try {
        this.ai.abortController = chatStream(
          this.ai.getConfig(),
          AI_PROMPTS.generateCard(this.cardConcept),
          {
            onMessage: (delta, full) => {
              this.typewriter.append(delta);
            },
            onError: (error) => {
              toast.update(toastId, { message: error.message, type: 'error' });
              setTimeout(() => toast.dismiss(toastId), 3000);
              this.ai.isGenerating = false;
            },
            onDone: (fullContent) => {
              this.typewriter.flush();
              toast.dismiss(toastId);
              this.ai.isGenerating = false;
              
              // 解析 JSON
              try {
                const parsed = JSON.parse(fullContent);
                this.generatedCard = {
                  spec: 'chara_card_v3',
                  spec_version: '3.0',
                  data: {
                    ...createEmptyCard().data,
                    name: parsed.name || '',
                    description: parsed.description || '',
                    personality: parsed.personality || '',
                    scenario: parsed.scenario || '',
                    first_mes: parsed.first_mes || '',
                    mes_example: parsed.mes_example || '',
                    tags: parsed.tags || [],
                  },
                };
                toast.success('角色卡生成成功！');
              } catch (e) {
                console.error('Failed to parse generated card:', e);
                toast.error('生成结果解析失败');
              }
            },
          }
        );
      } catch (error) {
        toast.update(toastId, { message: error.message, type: 'error' });
        setTimeout(() => toast.dismiss(toastId), 3000);
        this.ai.isGenerating = false;
      }
    },
    
    /**
     * 使用生成的卡片
     */
    useGeneratedCard() {
      if (!this.generatedCard) return;
      
      const card = Alpine.store('card');
      card.loadCard({ card: this.generatedCard }, null, null);
      Alpine.store('history').init(deepClone(this.generatedCard));
      Alpine.store('toast').success('已加载到工作台');
      Alpine.store('ui').currentPage = 'workshop';
    },
    
    /**
     * 生成备选开场白
     */
    async generateGreetings() {
      const card = Alpine.store('card');
      if (!card.data) {
        Alpine.store('toast').error('请先加载角色卡');
        return;
      }
      
      if (!this.ai.isConnected) {
        Alpine.store('toast').error('请先配置并测试 AI 连接');
        return;
      }
      
      const characterInfo = {
        name: card.data.data.name,
        description: card.data.data.description,
        personality: card.data.data.personality,
      };
      const originalGreeting = card.data.data.first_mes;
      
      this.ai.isGenerating = true;
      this.generatedGreetings = [];
      this.outputText = '';
      this.typewriter.reset();
      
      const toast = Alpine.store('toast');
      const toastId = toast.loading('正在生成备选开场白...');
      
      try {
        this.ai.abortController = chatStream(
          this.ai.getConfig(),
          AI_PROMPTS.generateGreetings(characterInfo, originalGreeting, this.greetingCount),
          {
            onMessage: (delta) => {
              this.typewriter.append(delta);
            },
            onError: (error) => {
              toast.update(toastId, { message: error.message, type: 'error' });
              setTimeout(() => toast.dismiss(toastId), 3000);
              this.ai.isGenerating = false;
            },
            onDone: (fullContent) => {
              this.typewriter.flush();
              toast.dismiss(toastId);
              this.ai.isGenerating = false;
              
              try {
                this.generatedGreetings = JSON.parse(fullContent);
                toast.success(`已生成 ${this.generatedGreetings.length} 条备选开场白`);
              } catch (e) {
                console.error('Failed to parse greetings:', e);
                toast.error('生成结果解析失败');
              }
            },
          }
        );
      } catch (error) {
        toast.update(toastId, { message: error.message, type: 'error' });
        setTimeout(() => toast.dismiss(toastId), 3000);
        this.ai.isGenerating = false;
      }
    },
    
    /**
     * 添加备选开场白到卡片
     */
    addGreetingToCard(greeting) {
      const card = Alpine.store('card');
      if (!card.data) return;
      
      const history = Alpine.store('history');
      history.push(deepClone(card.data));
      
      if (!card.data.data.alternate_greetings) {
        card.data.data.alternate_greetings = [];
      }
      card.data.data.alternate_greetings.push(greeting);
      card.checkChanges();
      
      Alpine.store('toast').success('已添加到备选开场白');
    },
    
    /**
     * 翻译当前卡片
     */
    async translateCard() {
      const card = Alpine.store('card');
      if (!card.data) {
        Alpine.store('toast').error('请先加载角色卡');
        return;
      }
      
      if (!this.ai.isConnected) {
        Alpine.store('toast').error('请先配置并测试 AI 连接');
        return;
      }
      
      // 翻译所有文本字段
      const fieldsToTranslate = ['description', 'personality', 'scenario', 'first_mes'];
      const toast = Alpine.store('toast');
      const toastId = toast.loading('正在翻译卡片...');
      
      const history = Alpine.store('history');
      history.push(deepClone(card.data));
      
      try {
        for (const field of fieldsToTranslate) {
          const text = card.data.data[field];
          if (!text) continue;
          
          toast.update(toastId, { message: `正在翻译 ${field}...` });
          
          const translated = await chat(
            this.ai.getConfig(),
            AI_PROMPTS.translate(text, this.translateLang)
          );
          
          if (translated) {
            card.data.data[field] = translated;
          }
        }
        
        card.checkChanges();
        toast.dismiss(toastId);
        toast.success('卡片翻译完成');
        
      } catch (error) {
        toast.update(toastId, { message: error.message, type: 'error' });
        setTimeout(() => toast.dismiss(toastId), 3000);
      }
    },
    
    /**
     * 旧卡焕新
     */
    async modernizeCard() {
      const card = Alpine.store('card');
      if (!card.data) {
        Alpine.store('toast').error('请先加载角色卡');
        return;
      }
      
      if (!this.ai.isConnected) {
        Alpine.store('toast').error('请先配置并测试 AI 连接');
        return;
      }
      
      const description = card.data.data.description;
      if (!description) {
        Alpine.store('toast').error('描述字段为空');
        return;
      }
      
      // 检测是否是 W++ 格式
      if (!description.includes('[') && !description.includes('{')) {
        Alpine.store('toast').info('该描述似乎不是 W++ 格式');
      }
      
      const toast = Alpine.store('toast');
      const toastId = toast.loading('正在焕新卡片描述...');
      
      const history = Alpine.store('history');
      history.push(deepClone(card.data));
      
      try {
        const modernized = await chat(
          this.ai.getConfig(),
          AI_PROMPTS.modernize(description)
        );
        
        if (modernized) {
          card.data.data.description = modernized;
          card.checkChanges();
          toast.dismiss(toastId);
          toast.success('描述焕新完成');
        } else {
          toast.dismiss(toastId);
          toast.error('焕新失败');
        }
      } catch (error) {
        toast.update(toastId, { message: error.message, type: 'error' });
        setTimeout(() => toast.dismiss(toastId), 3000);
      }
    },
    
    /**
     * 停止生成
     */
    stopGenerating() {
      this.ai.stopGenerating();
      this.typewriter.flush();
    },
  };
}

// ============================================================
// 注册组件
// ============================================================

export function registerAIComponents() {
  // 初始化 AI Store
  initAIStore();
  
  // 注册页面组件
  Alpine.data('aiPage', aiPage);
}

// ============================================================
// 导出
// ============================================================

export default {
  aiPage,
  initAIStore,
  registerAIComponents,
};
