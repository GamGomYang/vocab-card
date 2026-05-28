import type {
  AnswerResult,
  ExcelExportResult,
  ExcelImportResult,
  QuizMode,
  QuizQuestion,
  StatsSummary,
  VocabWord,
  WrongDateSummary,
} from "../types/vocab";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type DesktopApi = {
  getSources: () => Promise<string[]>;
  getQuiz: (source: string, count: number, mode: QuizMode) => Promise<QuizQuestion[]>;
  getWrongQuiz?: (count: number, mode: QuizMode, daysAgo?: number | null) => Promise<QuizQuestion[]>;
  submitAnswer: (wordId: number, selectedAnswer: string, mode: QuizMode) => Promise<AnswerResult>;
  getWrongWords: () => Promise<VocabWord[]>;
  getWrongWordsByDate?: (daysAgo: number) => Promise<VocabWord[]>;
  getWrongDates?: (limit: number) => Promise<WrongDateSummary[]>;
  getStats: () => Promise<StatsSummary>;
  importExcel: () => Promise<ExcelImportResult>;
  exportExcel: () => Promise<ExcelExportResult>;
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

function isDesktopBuild() {
  return window.location.protocol === "file:";
}

function desktopApiError(method: string) {
  return new Error(`데스크톱 API ${method}를 사용할 수 없습니다. 앱을 완전히 종료한 뒤 최신 빌드로 다시 실행하세요.`);
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
    if (!api && isDesktopBuild()) throw desktopApiError("getSources");
    return api?.getSources() ?? request<string[]>("/sources");
  },

  getQuiz: async (source: string, count: number, mode: QuizMode) => {
    const api = await waitForDesktopApi();
    if (api) return api.getQuiz(source, count, mode);
    if (isDesktopBuild()) throw desktopApiError("getQuiz");
    const params = new URLSearchParams({ count: String(count), mode });
    if (source) params.set("source", source);
    return request<QuizQuestion[]>(`/quiz?${params.toString()}`);
  },

  getWrongQuiz: async (count: number, mode: QuizMode, daysAgo?: number | null) => {
    const api = await waitForDesktopApi();
    if (api?.getWrongQuiz) return api.getWrongQuiz(count, mode, daysAgo ?? null);
    if (isDesktopBuild()) throw desktopApiError("getWrongQuiz");
    const params = new URLSearchParams({ count: String(count), mode });
    if (daysAgo !== null && daysAgo !== undefined) params.set("daysAgo", String(daysAgo));
    return request<QuizQuestion[]>(`/quiz/wrong?${params.toString()}`);
  },

  submitAnswer: async (wordId: number, selectedAnswer: string, mode: QuizMode) => {
    const api = await waitForDesktopApi();
    if (!api && isDesktopBuild()) throw desktopApiError("submitAnswer");
    return api?.submitAnswer(wordId, selectedAnswer, mode) ?? request<AnswerResult>("/quiz/answer", {
      method: "POST",
      body: JSON.stringify({ wordId, selectedAnswer, mode }),
    });
  },

  getWrongWords: async () => {
    const api = await waitForDesktopApi();
    if (!api && isDesktopBuild()) throw desktopApiError("getWrongWords");
    return api?.getWrongWords() ?? request<VocabWord[]>("/review/wrong");
  },

  getWrongWordsByDate: async (daysAgo: number) => {
    const api = await waitForDesktopApi();
    if (api?.getWrongWordsByDate) return api.getWrongWordsByDate(daysAgo);
    if (isDesktopBuild()) throw desktopApiError("getWrongWordsByDate");
    return request<VocabWord[]>(`/review/wrong/date?daysAgo=${daysAgo}`);
  },

  getWrongDates: async (limit: number) => {
    const api = await waitForDesktopApi();
    if (api?.getWrongDates) return api.getWrongDates(limit);
    if (isDesktopBuild()) throw desktopApiError("getWrongDates");
    return request<WrongDateSummary[]>(`/review/wrong/dates?limit=${limit}`);
  },

  getStats: async () => {
    const api = await waitForDesktopApi();
    if (!api && isDesktopBuild()) throw desktopApiError("getStats");
    return api?.getStats() ?? request<StatsSummary>("/stats");
  },

  importExcel: async () => {
    const api = await waitForDesktopApi();
    if (api) return api.importExcel();
    if (isDesktopBuild()) throw desktopApiError("importExcel");
    return request<ExcelImportResult>("/excel/import", { method: "POST" });
  },

  exportExcel: async () => {
    const api = await waitForDesktopApi();
    if (api) return api.exportExcel();
    if (isDesktopBuild()) throw desktopApiError("exportExcel");
    return request<ExcelExportResult>("/excel/export", { method: "POST" });
  },
};
