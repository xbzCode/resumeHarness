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
  setStreaming: (streaming: boolean) => void;
  setAbortController: (abort: (() => void) | null) => void;
  clearMessages: () => void;
  setMessages: (msgs: ChatMessage[]) => void;
  setResumeIdOnLastMessage: (resumeId: string) => void;
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
