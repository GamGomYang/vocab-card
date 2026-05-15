import type { AnswerResult, QuizMode, QuizQuestion, StatsSummary, VocabWord } from "../types/vocab";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type DesktopApi = {
  getSources: () => Promise<string[]>;
  getQuiz: (source: string, count: number, mode: QuizMode) => Promise<QuizQuestion[]>;
  submitAnswer: (wordId: number, selectedAnswer: string, mode: QuizMode) => Promise<AnswerResult>;
  getWrongWords: () => Promise<VocabWord[]>;
  getStats: () => Promise<StatsSummary>;
};

declare global {
  interface Window {
    pywebview?: {
      api: DesktopApi;
    };
  }
}

function waitForDesktopApi(): Promise<DesktopApi | null> {
  if (window.pywebview?.api) {
    return Promise.resolve(window.pywebview.api);
  }

  const isDesktopBuild = window.location.protocol === "file:";
  if (!isDesktopBuild) {
    return Promise.resolve(null);
  }

  return new Promise<DesktopApi | null>((resolve) => {
    const timeout = window.setTimeout(() => resolve(null), 5000);
    window.addEventListener(
      "pywebviewready",
      () => {
        window.clearTimeout(timeout);
        resolve(window.pywebview?.api ?? null);
      },
      { once: true },
    );
  });
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const vocabApi = {
  getSources: async () => {
    const api = await waitForDesktopApi();
    return api?.getSources() ?? request<string[]>("/sources");
  },

  getQuiz: async (source: string, count: number, mode: QuizMode) => {
    const api = await waitForDesktopApi();
    if (api) return api.getQuiz(source, count, mode);
    const params = new URLSearchParams({ count: String(count), mode });
    if (source) params.set("source", source);
    return request<QuizQuestion[]>(`/quiz?${params.toString()}`);
  },

  submitAnswer: async (wordId: number, selectedAnswer: string, mode: QuizMode) => {
    const api = await waitForDesktopApi();
    return api?.submitAnswer(wordId, selectedAnswer, mode) ?? request<AnswerResult>("/quiz/answer", {
      method: "POST",
      body: JSON.stringify({ wordId, selectedAnswer, mode }),
    });
  },

  getWrongWords: async () => {
    const api = await waitForDesktopApi();
    return api?.getWrongWords() ?? request<VocabWord[]>("/review/wrong");
  },

  getStats: async () => {
    const api = await waitForDesktopApi();
    return api?.getStats() ?? request<StatsSummary>("/stats");
  },
};
