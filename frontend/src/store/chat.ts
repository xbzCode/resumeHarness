import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  /** 思考/推理过程 */
  thinking?: string;
  /** 工具调用信息 */
  toolCalls?: { name: string; args: string; result?: string }[];
  /** 简历生成事件 */
  resumeId?: string;
  /** 简历结构化数据（resume_data SSE 事件推送） */
  resumeData?: ResumeData;
  /** 推荐的模板 */
  templateHint?: string;
  /** 优化建议（标记外的建议内容） */
  suggestions?: string;
  /** 简历前缀内容（标记前的引导语） */
  resumePrefix?: string;
  /** 简历评分数据（resume_score SSE 事件推送） */
  resumeScore?: ResumeScoreData;
  /** 上一版简历 Markdown 内容（用于多轮优化时的差异对比） */
  prevResumeContent?: string;
}

/** 简历结构化数据（与后端 ResumeData 模型对应） */
export interface ResumeData {
  name: string;
  contact: {
    email?: string;
    phone?: string;
    location?: string;
    website?: string;
    linkedin?: string;
    wechat?: string;
    raw_text?: string;
  };
  summary?: string;
  experience: {
    title: string;
    company: string;
    period: string;
    highlights: string[];
  }[];
  education: {
    degree: string;
    major: string;
    school: string;
    period: string;
    achievements: string[];
  }[];
  skills: {
    category: string;
    skills: string[];
  }[];
  projects: {
    name: string;
    role?: string;
    period?: string;
    description?: string;
    contributions: string[];
  }[];
  section_order?: string[];
}

/** 简历评分数据（与后端 ResumeScoreResult 对应） */
export interface ResumeScoreData {
  overall_score: number;
  dimensions: {
    structure: number;
    content: number;
    quantification: number;
    keyword_match: number;
    format: number;
  };
  suggestions: string[];
  jd_keywords_matched?: string[];
  jd_keywords_missing?: string[];
}

// ---------------------------------------------------------------------------
// 多会话架构：每个会话独立维护消息、流式状态和中止控制器
// ---------------------------------------------------------------------------

/** 单个会话的运行时状态（不持久化） */
export interface SessionData {
  messages: ChatMessage[];
  isStreaming: boolean;
  abortController: (() => void) | null;
}

/** 待分配真实 session_id 前使用的临时键前缀 */
const PENDING_PREFIX = "__pending_";
let _pendingCounter = 0;

/** 创建新的待定会话键 */
export function newPendingKey(): string {
  return `${PENDING_PREFIX}${++_pendingCounter}_${Date.now().toString(36)}`;
}

/** 判断是否为待定会话键 */
export function isPendingKey(key: string): boolean {
  return key.startsWith(PENDING_PREFIX);
}

/** 创建空白 SessionData */
function createEmptySession(): SessionData {
  return { messages: [], isStreaming: false, abortController: null };
}

/** 确保 sessions[key] 存在（不存在则创建空白） */
function ensureSession(sessions: Record<string, SessionData>, key: string): SessionData {
  if (!sessions[key]) {
    sessions[key] = createEmptySession();
  }
  return sessions[key];
}

/** 将 ResumeData 转换为简单 Markdown 文本（用于差异对比） */
function _resumeDataToMarkdown(data: ResumeData): string {
  const parts: string[] = [];
  parts.push(`# ${data.name}`);
  const contactParts = [data.contact.email, data.contact.phone, data.contact.location].filter(Boolean);
  if (contactParts.length > 0) parts.push(contactParts.join(" | "));
  if (data.summary) { parts.push(""); parts.push("## 个人简介"); parts.push(data.summary); }
  if (data.experience.length > 0) {
    parts.push(""); parts.push("## 工作经历");
    for (const exp of data.experience) {
      parts.push(`### ${exp.title} - ${exp.company}（${exp.period}）`);
      for (const h of exp.highlights) parts.push(`- ${h}`);
    }
  }
  if (data.education.length > 0) {
    parts.push(""); parts.push("## 教育背景");
    for (const edu of data.education) {
      parts.push(`### ${edu.degree} - ${edu.major} - ${edu.school}（${edu.period}）`);
      for (const a of edu.achievements) parts.push(`- ${a}`);
    }
  }
  if (data.skills.length > 0) {
    parts.push(""); parts.push("## 专业技能");
    for (const cat of data.skills) parts.push(`- **${cat.category}**：${cat.skills.join("、")}`);
  }
  if (data.projects.length > 0) {
    parts.push(""); parts.push("## 项目经历");
    for (const proj of data.projects) {
      parts.push(`### ${proj.name}${proj.role ? ` - ${proj.role}` : ""}${proj.period ? `（${proj.period}）` : ""}`);
      if (proj.description) parts.push(`- 项目描述：${proj.description}`);
      for (const c of proj.contributions) parts.push(`- ${c}`);
    }
  }
  return parts.join("\n");
}

// ---------------------------------------------------------------------------
// Store 接口
// ---------------------------------------------------------------------------

interface ChatState {
  /** 当前显示的会话键（可能是真实 session_id 或 pending key） */
  activeSessionId: string | null;
  /** 所有会话的运行时数据 */
  sessions: Record<string, SessionData>;
  /** 对话流完成后递增，供侧边栏监听刷新会话列表 */
  refreshKey: number;

  // ---- 会话管理 ----

  /** 设置当前活跃会话 */
  setActiveSessionId: (id: string | null) => void;
  /** 创建新的待定会话并设为活跃，返回其键 */
  newPendingSession: () => string;
  /** 将待定会话迁移到真实 session_id（SSE session_started 时调用） */
  migrateSession: (oldKey: string, newSessionId: string) => void;

  // ---- 按会话操作（用于 SSE 后台路由） ----

  getSessionData: (key: string) => SessionData | undefined;
  addMessageToSession: (key: string, msg: ChatMessage) => void;
  appendToLastMessageOfSession: (key: string, content: string) => void;
  appendToLastMessageThinkingOfSession: (key: string, content: string) => void;
  moveContentToThinkingOfSession: (key: string) => void;
  setStreamingOfSession: (key: string, streaming: boolean) => void;
  setAbortControllerOfSession: (key: string, abort: (() => void) | null) => void;
  setMessagesOfSession: (key: string, msgs: ChatMessage[]) => void;
  setResumeIdOnLastMessageOfSession: (key: string, resumeId: string) => void;
  setResumeDataOnLastMessageOfSession: (key: string, resumeId: string, data: ResumeData, templateHint: string, suggestions?: string, resumePrefix?: string) => void;
  setResumeScoreOnLastMessageOfSession: (key: string, score: ResumeScoreData) => void;
  /** 中止指定会话的 SSE 流 */
  abortSessionStream: (key: string) => void;
  /** 清除指定会话的所有数据 */
  clearSession: (key: string) => void;

  // ---- 活跃会话便捷操作（委托到 activeSessionId 对应的会话） ----

  addMessage: (msg: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  appendToLastMessage: (content: string) => void;
  appendToLastMessageThinking: (content: string) => void;
  moveContentToThinking: () => void;
  setStreaming: (streaming: boolean) => void;
  setAbortController: (abort: (() => void) | null) => void;
  clearMessages: () => void;
  setMessages: (msgs: ChatMessage[]) => void;
  setResumeIdOnLastMessage: (resumeId: string) => void;
  setResumeDataOnLastMessage: (resumeId: string, data: ResumeData, templateHint: string, suggestions?: string, resumePrefix?: string) => void;
  setResumeScoreOnLastMessage: (score: ResumeScoreData) => void;
}

/** 获取活跃会话的键，无活跃会话时返回 null */
function _activeKey(state: { activeSessionId: string | null }): string | null {
  return state.activeSessionId;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      activeSessionId: null,
      sessions: {},
      refreshKey: 0,

      // ---- 会话管理 ----

      setActiveSessionId: (id) => set({ activeSessionId: id }),

      newPendingSession: () => {
        const key = newPendingKey();
        set((state) => ({
          activeSessionId: key,
          sessions: { ...state.sessions, [key]: createEmptySession() },
        }));
        return key;
      },

      migrateSession: (oldKey, newSessionId) => {
        set((state) => {
          const oldData = state.sessions[oldKey];
          if (!oldData) return state;
          const sessions = { ...state.sessions };
          // 如果目标键已有数据（比如之前加载过该会话），合并消息
          const existing = sessions[newSessionId];
          const merged: SessionData = existing
            ? { ...existing, messages: [...existing.messages, ...oldData.messages], isStreaming: oldData.isStreaming, abortController: oldData.abortController }
            : { ...oldData };
          delete sessions[oldKey];
          sessions[newSessionId] = merged;
          return {
            sessions,
            activeSessionId: state.activeSessionId === oldKey ? newSessionId : state.activeSessionId,
          };
        });
      },

      // ---- 按会话操作 ----

      getSessionData: (key) => get().sessions[key],

      addMessageToSession: (key, msg) => set((state) => {
        const sessions = { ...state.sessions };
        const session = { ...ensureSession(sessions, key), messages: [...(sessions[key]?.messages || []), msg] };
        sessions[key] = session;
        return { sessions };
      }),

      appendToLastMessageOfSession: (key, content) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        const msgs = [...session.messages];
        if (msgs.length > 0) {
          const last = msgs[msgs.length - 1];
          msgs[msgs.length - 1] = { ...last, content: last.content + content };
        }
        sessions[key] = { ...session, messages: msgs };
        return { sessions };
      }),

      appendToLastMessageThinkingOfSession: (key, content) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        const msgs = [...session.messages];
        if (msgs.length > 0) {
          const last = msgs[msgs.length - 1];
          msgs[msgs.length - 1] = { ...last, thinking: (last.thinking || "") + content };
        }
        sessions[key] = { ...session, messages: msgs };
        return { sessions };
      }),

      moveContentToThinkingOfSession: (key) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        const msgs = [...session.messages];
        if (msgs.length > 0) {
          const last = msgs[msgs.length - 1];
          msgs[msgs.length - 1] = {
            ...last,
            thinking: (last.thinking || "") + last.content,
            content: "",
          };
        }
        sessions[key] = { ...session, messages: msgs };
        return { sessions };
      }),

      setStreamingOfSession: (key, streaming) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        const refreshInc = session.isStreaming && !streaming ? 1 : 0;
        sessions[key] = { ...session, isStreaming: streaming };
        return { sessions, refreshKey: state.refreshKey + refreshInc };
      }),

      setAbortControllerOfSession: (key, abort) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        sessions[key] = { ...session, abortController: abort };
        return { sessions };
      }),

      setMessagesOfSession: (key, msgs) => set((state) => {
        const sessions = { ...state.sessions };
        sessions[key] = { ...ensureSession(sessions, key), messages: msgs };
        return { sessions };
      }),

      setResumeIdOnLastMessageOfSession: (key, resumeId) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        const msgs = [...session.messages];
        if (msgs.length > 0) {
          msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], resumeId };
        }
        sessions[key] = { ...session, messages: msgs };
        return { sessions };
      }),

      setResumeDataOnLastMessageOfSession: (key, resumeId, data, templateHint, suggestions, resumePrefix) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        const msgs = [...session.messages];
        if (msgs.length > 0) {
          const last = msgs[msgs.length - 1];
          const prevResumeContent = last.resumeData
            ? _resumeDataToMarkdown(last.resumeData)
            : undefined;
          let newContent = last.content;
          let newThinking = last.thinking || "";
          if (resumePrefix && last.content.startsWith(resumePrefix)) {
            newContent = last.content.slice(resumePrefix.length).trimStart();
            newThinking = (newThinking + resumePrefix).trimStart();
          } else if (resumePrefix && !newThinking.includes(resumePrefix)) {
            newThinking = (newThinking + "\n" + resumePrefix).trim();
          }
          msgs[msgs.length - 1] = {
            ...last,
            content: newContent,
            thinking: newThinking || undefined,
            resumeId,
            resumeData: data,
            templateHint,
            suggestions,
            resumePrefix,
            prevResumeContent: prevResumeContent || last.prevResumeContent,
          };
        }
        sessions[key] = { ...session, messages: msgs };
        return { sessions };
      }),

      setResumeScoreOnLastMessageOfSession: (key, score) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        const msgs = [...session.messages];
        if (msgs.length > 0) {
          msgs[msgs.length - 1] = {
            ...msgs[msgs.length - 1],
            resumeScore: score,
          };
        }
        sessions[key] = { ...session, messages: msgs };
        return { sessions };
      }),

      abortSessionStream: (key) => {
        const session = get().sessions[key];
        if (session) {
          session.abortController?.();
          set((state) => {
            const sessions = { ...state.sessions };
            sessions[key] = { ...sessions[key], isStreaming: false, abortController: null };
            return { sessions };
          });
        }
      },

      clearSession: (key) => set((state) => {
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (session) {
          session.abortController?.();
        }
        delete sessions[key];
        const refreshInc = state.activeSessionId === key ? 1 : 0;
        return {
          sessions,
          activeSessionId: state.activeSessionId === key ? null : state.activeSessionId,
          refreshKey: state.refreshKey + refreshInc,
        };
      }),

      // ---- 活跃会话便捷操作 ----

      addMessage: (msg) => {
        const key = _activeKey(get());
        if (key) get().addMessageToSession(key, msg);
      },

      updateLastMessage: (content) => set((state) => {
        const key = _activeKey(state);
        if (!key) return {};
        const sessions = { ...state.sessions };
        const session = sessions[key];
        if (!session) return {};
        const msgs = [...session.messages];
        if (msgs.length > 0) {
          msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content };
        }
        sessions[key] = { ...session, messages: msgs };
        return { sessions };
      }),

      appendToLastMessage: (content) => {
        const key = _activeKey(get());
        if (key) get().appendToLastMessageOfSession(key, content);
      },

      appendToLastMessageThinking: (content) => {
        const key = _activeKey(get());
        if (key) get().appendToLastMessageThinkingOfSession(key, content);
      },

      moveContentToThinking: () => {
        const key = _activeKey(get());
        if (key) get().moveContentToThinkingOfSession(key);
      },

      setStreaming: (streaming) => {
        const key = _activeKey(get());
        if (key) get().setStreamingOfSession(key, streaming);
      },

      setAbortController: (abort) => {
        const key = _activeKey(get());
        if (key) get().setAbortControllerOfSession(key, abort);
      },

      clearMessages: () => {
        const key = _activeKey(get());
        if (key) {
          get().abortSessionStream(key);
          get().clearSession(key);
        }
        set({ activeSessionId: null });
      },

      setMessages: (msgs) => {
        const key = _activeKey(get());
        if (key) get().setMessagesOfSession(key, msgs);
      },

      setResumeIdOnLastMessage: (resumeId) => {
        const key = _activeKey(get());
        if (key) get().setResumeIdOnLastMessageOfSession(key, resumeId);
      },

      setResumeDataOnLastMessage: (resumeId, data, templateHint, suggestions, resumePrefix) => {
        const key = _activeKey(get());
        if (key) get().setResumeDataOnLastMessageOfSession(key, resumeId, data, templateHint, suggestions, resumePrefix);
      },

      setResumeScoreOnLastMessage: (score) => {
        const key = _activeKey(get());
        if (key) get().setResumeScoreOnLastMessageOfSession(key, score);
      },
    }),
    {
      name: "resume-chat-store",
      partialize: (state) => ({
        activeSessionId: state.activeSessionId,
        // 只持久化消息，不持久化流式状态和 abortController
        sessions: Object.fromEntries(
          Object.entries(state.sessions).map(([key, session]) => [
            key,
            {
              messages: session.messages.filter(
                (m) => !(m.role === "assistant" && !m.content && !m.thinking && !m.resumeData),
              ),
              // 不持久化 isStreaming 和 abortController
              isStreaming: false,
              abortController: null,
            },
          ]),
        ),
      }),
    },
  ),
);
