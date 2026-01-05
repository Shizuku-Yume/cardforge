/**
 * AI 客户端模块
 * 
 * 提供 SSE 流式请求、打字机效果、AI 代理 API 调用
 */

import { post, ApiError, ErrorCode } from '../api.js';

// ============================================================
// SSE 客户端
// ============================================================

/**
 * 处理 SSE 流响应 (公共解析逻辑)
 * 
 * @param {Response} response - fetch 响应对象
 * @param {Object} callbacks - 回调函数
 * @param {function} callbacks.onMessage - 消息回调 (delta, fullContent)
 * @param {function} callbacks.onError - 错误回调 (error)
 * @param {function} callbacks.onDone - 完成回调 (fullContent)
 * @param {AbortController} controller - 用于检测中止
 * @returns {Promise<void>}
 */
async function processSSEStream(response, callbacks, controller) {
  const { onMessage, onError, onDone } = callbacks;
  let fullContent = '';

  try {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      // 支持 \r\n 和 \n 两种换行格式
      const lines = buffer.replace(/\r\n/g, '\n').split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;

        // 处理 SSE 事件
        if (line.startsWith('event: error')) {
          continue;
        }

        // 支持 "data: " 和 "data:" 两种格式
        if (line.startsWith('data:')) {
          const data = line.startsWith('data: ') ? line.slice(6) : line.slice(5);

          if (data === '[DONE]') {
            onDone?.(fullContent);
            return;
          }

          try {
            const parsed = JSON.parse(data);

            // 检查是否是错误帧
            if (parsed.code && parsed.message && !parsed.choices) {
              const error = new ApiError(parsed.message, parsed.code, 0);
              onError?.(error);
              return;
            }

            // 提取 delta content
            const delta = parsed.choices?.[0]?.delta?.content || '';
            if (delta) {
              fullContent += delta;
              onMessage?.(delta, fullContent);
            }

            // 检查 finish_reason
            if (parsed.choices?.[0]?.finish_reason) {
              onDone?.(fullContent);
              return;
            }
          } catch (e) {
            console.warn('Failed to parse SSE data:', data, e);
          }
        }
      }
    }

    onDone?.(fullContent);

  } catch (error) {
    if (error.name === 'AbortError' || controller?.signal?.aborted) {
      onDone?.(fullContent);
      return;
    }
    onError?.(error);
  }
}

/**
 * 创建 SSE 流式请求客户端
 * 使用 fetch + ReadableStream 实现 (比 EventSource 更灵活)
 * 
 * @param {Object} options - 请求选项
 * @param {string} options.url - 请求 URL
 * @param {Object} options.body - 请求体
 * @param {AbortController} options.controller - AbortController 用于取消请求
 * @param {function} options.onMessage - 消息回调 (delta, fullContent)
 * @param {function} options.onError - 错误回调 (error)
 * @param {function} options.onDone - 完成回调 (fullContent)
 * @returns {Promise<void>}
 */
export async function streamChat(options) {
  const {
    url = '/api/proxy/chat',
    body,
    controller,
    onMessage,
    onError,
    onDone,
  } = options;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(body),
      signal: controller?.signal,
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { message: `请求失败: ${response.status}` };
      }
      throw new ApiError(
        errorData.detail || errorData.message || `请求失败: ${response.status}`,
        errorData.code || ErrorCode.INTERNAL_ERROR,
        response.status
      );
    }

    await processSSEStream(response, { onMessage, onError, onDone }, controller);

  } catch (error) {
    if (error.name === 'AbortError') {
      onDone?.('');
      return;
    }
    onError?.(error);
  }
}

// ============================================================
// AI API 封装
// ============================================================

/**
 * 发送聊天请求 (非流式)
 * 
 * @param {Object} config - AI 配置
 * @param {string} config.baseUrl - API Base URL
 * @param {string} config.apiKey - API Key
 * @param {string} config.model - 模型名称
 * @param {boolean} config.useProxy - 是否使用代理
 * @param {Array} messages - 消息列表 [{role, content}]
 * @param {Object} options - 可选参数
 * @returns {Promise<string>} 回复内容
 */
export async function chat(config, messages, options = {}) {
  const { baseUrl, apiKey, model, useProxy = false } = config;
  const { temperature = 0.7, maxTokens } = options;

  if (useProxy) {
    const resp = await post('/api/proxy/chat', {
      base_url: baseUrl,
      api_key: apiKey,
      model,
      messages,
      temperature,
      max_tokens: maxTokens,
      stream: false,
    });
    return resp.choices?.[0]?.message?.content || '';
  } else {
    const resp = await fetch(`${baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages,
        temperature,
        max_tokens: maxTokens,
      }),
    });

    if (!resp.ok) {
      let errorData;
      try {
        errorData = await resp.json();
      } catch {
        errorData = {};
      }
      throw new ApiError(
        errorData.error?.message || `请求失败: ${resp.status}`,
        ErrorCode.INTERNAL_ERROR,
        resp.status
      );
    }

    const data = await resp.json();
    return data.choices?.[0]?.message?.content || '';
  }
}

/**
 * 流式聊天请求
 * 
 * @param {Object} config - AI 配置
 * @param {Array} messages - 消息列表
 * @param {Object} options - 流式选项
 * @returns {AbortController} 可用于取消请求
 */
export function chatStream(config, messages, options = {}) {
  const { baseUrl, apiKey, model, useProxy = false } = config;
  const { 
    temperature = 0.7, 
    maxTokens,
    onMessage,
    onError,
    onDone,
  } = options;

  const controller = new AbortController();

  if (useProxy) {
    streamChat({
      url: '/api/proxy/chat',
      body: {
        base_url: baseUrl,
        api_key: apiKey,
        model,
        messages,
        temperature,
        max_tokens: maxTokens,
        stream: true,
      },
      controller,
      onMessage,
      onError,
      onDone,
    });
  } else {
    streamChatDirect({
      url: `${baseUrl}/v1/chat/completions`,
      apiKey,
      body: {
        model,
        messages,
        temperature,
        max_tokens: maxTokens,
        stream: true,
      },
      controller,
      onMessage,
      onError,
      onDone,
    });
  }

  return controller;
}

/**
 * 直接调用 AI API 的流式请求 (不通过代理)
 */
async function streamChatDirect(options) {
  const {
    url,
    apiKey,
    body,
    controller,
    onMessage,
    onError,
    onDone,
  } = options;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(body),
      signal: controller?.signal,
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { error: { message: `请求失败: ${response.status}` } };
      }
      throw new ApiError(
        errorData.error?.message || `请求失败: ${response.status}`,
        ErrorCode.INTERNAL_ERROR,
        response.status
      );
    }

    await processSSEStream(response, { onMessage, onError, onDone }, controller);

  } catch (error) {
    if (error.name === 'AbortError') {
      onDone?.('');
      return;
    }
    onError?.(error);
  }
}

/**
 * 获取模型列表
 * 
 * @param {Object} config - AI 配置
 * @returns {Promise<Array>} 模型列表
 */
export async function getModels(config) {
  const { baseUrl, apiKey, useProxy = false } = config;

  if (useProxy) {
    const resp = await post('/api/proxy/models', {
      base_url: baseUrl,
      api_key: apiKey,
    });
    return resp.data || [];
  } else {
    const resp = await fetch(`${baseUrl}/v1/models`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    });

    if (!resp.ok) {
      throw new ApiError(
        `获取模型列表失败: ${resp.status}`,
        ErrorCode.INTERNAL_ERROR,
        resp.status
      );
    }

    const data = await resp.json();
    return data.data || [];
  }
}

/**
 * 测试 AI 连接
 * 
 * @param {Object} config - AI 配置
 * @returns {Promise<{success: boolean, message: string, models?: Array}>}
 */
export async function testConnection(config) {
  try {
    const models = await getModels(config);
    return {
      success: true,
      message: `连接成功！找到 ${models.length} 个模型`,
      models,
    };
  } catch (error) {
    return {
      success: false,
      message: error.message || '连接失败',
    };
  }
}

// ============================================================
// 打字机效果
// ============================================================

/**
 * 打字机效果类
 */
export class TypewriterEffect {
  constructor(options = {}) {
    this.targetElement = null;
    this.charDelay = options.charDelay || 20;
    this.lineDelay = options.lineDelay || 100;
    this.pendingText = '';
    this.displayedText = '';
    this.isTyping = false;
    this.timeoutId = null;
    this.onUpdate = options.onUpdate || null;
  }

  /**
   * 绑定目标元素
   */
  bind(element) {
    this.targetElement = element;
  }

  /**
   * 追加文本
   */
  append(text) {
    this.pendingText += text;
    if (!this.isTyping) {
      this._startTyping();
    }
  }

  /**
   * 开始打字
   */
  _startTyping() {
    if (this.pendingText.length === 0) {
      this.isTyping = false;
      return;
    }

    this.isTyping = true;
    const char = this.pendingText[0];
    this.pendingText = this.pendingText.slice(1);
    this.displayedText += char;

    if (this.targetElement) {
      this.targetElement.textContent = this.displayedText;
    }
    this.onUpdate?.(this.displayedText);

    // 换行时延迟更长
    const delay = char === '\n' ? this.lineDelay : this.charDelay;
    this.timeoutId = setTimeout(() => this._startTyping(), delay);
  }

  /**
   * 立即显示所有内容
   */
  flush() {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    this.displayedText += this.pendingText;
    this.pendingText = '';
    this.isTyping = false;

    if (this.targetElement) {
      this.targetElement.textContent = this.displayedText;
    }
    this.onUpdate?.(this.displayedText);
  }

  /**
   * 重置
   */
  reset() {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    this.pendingText = '';
    this.displayedText = '';
    this.isTyping = false;

    if (this.targetElement) {
      this.targetElement.textContent = '';
    }
  }

  /**
   * 销毁
   */
  destroy() {
    this.reset();
    this.targetElement = null;
    this.onUpdate = null;
  }
}

// ============================================================
// AI 工作流 Prompts
// ============================================================

export const AI_PROMPTS = {
  /**
   * 生成新角色卡
   */
  generateCard: (concept) => [
    {
      role: 'system',
      content: `You are a creative character card designer for SillyTavern. Generate a detailed character card based on the user's concept.

Output a JSON object with the following structure:
{
  "name": "Character name",
  "description": "Detailed character description including appearance, personality, background",
  "personality": "Personality traits summary",
  "scenario": "The setting/scenario for roleplay",
  "first_mes": "An engaging first message from the character (can include HTML formatting)",
  "mes_example": "Example dialogue demonstrating the character's speaking style",
  "tags": ["tag1", "tag2", "tag3"]
}

Important:
- Be creative and detailed
- The first_mes should be immersive and set the scene
- Include 3-5 relevant tags
- Output ONLY valid JSON, no markdown code blocks`
    },
    {
      role: 'user',
      content: `Create a character card for: ${concept}`
    }
  ],

  /**
   * 开场白裂变 - 生成备选开场白
   */
  generateGreetings: (characterInfo, originalGreeting, count = 3) => [
    {
      role: 'system',
      content: `You are a creative writer. Generate ${count} alternative first messages for a roleplay character.

Character info:
Name: ${characterInfo.name}
Description: ${characterInfo.description}
Personality: ${characterInfo.personality}

Original greeting for reference:
${originalGreeting}

Requirements:
- Each greeting should be unique in tone or scenario
- Maintain character's voice and personality
- Can include HTML formatting like the original
- Make them engaging and immersive

Output a JSON array of ${count} greeting strings:
["greeting1", "greeting2", "greeting3"]

Output ONLY valid JSON, no markdown code blocks.`
    },
    {
      role: 'user',
      content: 'Generate the alternative greetings now.'
    }
  ],

  /**
   * 翻译
   */
  translate: (text, targetLang = '中文') => [
    {
      role: 'system',
      content: `You are a professional translator. Translate the given text to ${targetLang}.
Preserve all HTML tags and formatting exactly as they appear.
Output ONLY the translated text, nothing else.`
    },
    {
      role: 'user',
      content: text
    }
  ],

  /**
   * 旧卡焕新 - W++ 转自然语言
   */
  modernize: (text) => [
    {
      role: 'system',
      content: `You are an expert at rewriting character descriptions. 
Convert the given W++ or PLists format description into natural, flowing prose.
Maintain all the information but make it read naturally.
Output ONLY the rewritten description, nothing else.`
    },
    {
      role: 'user',
      content: text
    }
  ],

  /**
   * 优化润色
   */
  enhance: (text, field = 'description') => [
    {
      role: 'system',
      content: `You are a skilled writer. Enhance and polish the given ${field} text.
Make it more vivid, detailed, and engaging while preserving the core content.
Output ONLY the enhanced text, nothing else.`
    },
    {
      role: 'user',
      content: text
    }
  ],

  /**
   * 扩写
   */
  expand: (text, field = 'description') => [
    {
      role: 'system',
      content: `You are a creative writer. Expand the given ${field} text.
Add more details, descriptions, and depth while maintaining consistency.
Roughly double the length.
Output ONLY the expanded text, nothing else.`
    },
    {
      role: 'user',
      content: text
    }
  ],
};

// ============================================================
// 导出
// ============================================================

export default {
  streamChat,
  chat,
  chatStream,
  getModels,
  testConnection,
  TypewriterEffect,
  AI_PROMPTS,
};
