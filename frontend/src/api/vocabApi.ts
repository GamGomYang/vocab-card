import type { AnswerResult, QuizMode, QuizQuestion, StatsSummary, VocabWord } from "../types/vocab";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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
  getSources: () => request<string[]>("/sources"),

  getQuiz: (source: string, count: number, mode: QuizMode) => {
    const params = new URLSearchParams({ count: String(count), mode });
    if (source) params.set("source", source);
    return request<QuizQuestion[]>(`/quiz?${params.toString()}`);
  },

  submitAnswer: (wordId: number, selectedAnswer: string, mode: QuizMode) =>
    request<AnswerResult>("/quiz/answer", {
      method: "POST",
      body: JSON.stringify({ wordId, selectedAnswer, mode }),
    }),

  getWrongWords: () => request<VocabWord[]>("/review/wrong"),

  getStats: () => request<StatsSummary>("/stats"),
};
