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

interface ChatState {
  sessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  abortController: (() => void) | null;

  setSessionId: (id: string | null) => void;
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

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      sessionId: null,
      messages: [],
      isStreaming: false,
      abortController: null,

      setSessionId: (id) => set({ sessionId: id }),
      addMessage: (msg) =>
        set((state) => ({ messages: [...state.messages, msg] })),
      updateLastMessage: (content) =>
        set((state) => {
          const msgs = [...state.messages];
          if (msgs.length > 0) {
            msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content };
          }
          return { messages: msgs };
        }),
      appendToLastMessage: (content) =>
        set((state) => {
          const msgs = [...state.messages];
          if (msgs.length > 0) {
            const last = msgs[msgs.length - 1];
            msgs[msgs.length - 1] = { ...last, content: last.content + content };
          }
          return { messages: msgs };
        }),
      appendToLastMessageThinking: (content) =>
        set((state) => {
          const msgs = [...state.messages];
          if (msgs.length > 0) {
            const last = msgs[msgs.length - 1];
            msgs[msgs.length - 1] = {
              ...last,
              thinking: (last.thinking || "") + content,
            };
          }
          return { messages: msgs };
        }),
      moveContentToThinking: () =>
        set((state) => {
          const msgs = [...state.messages];
          if (msgs.length > 0) {
            const last = msgs[msgs.length - 1];
            msgs[msgs.length - 1] = {
              ...last,
              thinking: (last.thinking || "") + last.content,
              content: "",
            };
          }
          return { messages: msgs };
        }),
      setStreaming: (streaming) => set({ isStreaming: streaming }),
      setAbortController: (abort) => set({ abortController: abort }),
      clearMessages: () => set({ messages: [], sessionId: null }),
      setMessages: (msgs) => set({ messages: msgs }),
      setResumeIdOnLastMessage: (resumeId) =>
        set((state) => {
          const msgs = [...state.messages];
          if (msgs.length > 0) {
            msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], resumeId };
          }
          return { messages: msgs };
        }),
      setResumeDataOnLastMessage: (resumeId, data, templateHint, suggestions, resumePrefix) =>
        set((state) => {
          const msgs = [...state.messages];
          if (msgs.length > 0) {
            const last = msgs[msgs.length - 1];
            // 如果当前消息已有 resumeData，说明是多轮优化，保存上一版内容用于差异对比
            const prevResumeContent = last.resumeData
              ? _resumeDataToMarkdown(last.resumeData)
              : undefined;
            // 当 resumePrefix 有值时，将 content 中对应的前缀文本移到 thinking
            // 这确保降级路径（模型未输出 <!--RESUME--> 标记）下也能正确分离引导语和简历内容
            let newContent = last.content;
            let newThinking = last.thinking || "";
            if (resumePrefix && last.content.startsWith(resumePrefix)) {
              newContent = last.content.slice(resumePrefix.length).trimStart();
              newThinking = (newThinking + resumePrefix).trimStart();
            } else if (resumePrefix && !newThinking.includes(resumePrefix)) {
              // 前缀不完全匹配时（如流式传输中的微小差异），仍尝试移到 thinking
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
          return { messages: msgs };
        }),
      setResumeScoreOnLastMessage: (score) =>
        set((state) => {
          const msgs = [...state.messages];
          if (msgs.length > 0) {
            msgs[msgs.length - 1] = {
              ...msgs[msgs.length - 1],
              resumeScore: score,
            };
          }
          return { messages: msgs };
        }),
    }),
    {
      name: "resume-chat-store",
      // 只持久化这些字段，abortController 和 isStreaming 不持久化
      partialize: (state) => ({
        sessionId: state.sessionId,
        messages: state.messages,
      }),
    },
  ),
);
