export type QuizMode = "word_to_meaning" | "meaning_to_word";
export type AnswerMode = "choice" | "typing";

export type VocabWord = {
  id: number;
  source: string;
  word: string;
  meaning: string;
  example: string;
  exampleMeaning: string;
  note?: string;
  correctCount: number;
  wrongCount: number;
  totalCount: number;
  lastResult?: "정답" | "오답" | "";
  lastTestedAt?: string;
  streakCorrect: number;
  memoryState: "미학습" | "학습중" | "복습필요" | "암기완료" | string;
  accuracy: number;
};

export type QuizQuestion = {
  questionId: number;
  wordId: number;
  mode: QuizMode;
  source: string;
  word: string;
  meaning: string;
  questionText: string;
  choices: string[];
  answer: string;
  example: string;
  exampleMeaning: string;
};

export type AnswerResult = {
  isCorrect: boolean;
  correctAnswer: string;
  selectedAnswer: string;
  word: string;
  meaning: string;
  example: string;
  exampleMeaning: string;
  correctCount: number;
  wrongCount: number;
  totalCount: number;
  lastResult: "정답" | "오답";
  memoryState: string;
};

export type StatsSummary = {
  totalWords: number;
  testedWords: number;
  wrongWords: number;
  averageAccuracy: number;
  topWrongWords: VocabWord[];
};

export type WrongDateSummary = {
  date: string;
  daysAgo: number;
  attempts: number;
  words: number;
};

export type QuizResultSummary = {
  total: number;
  correct: number;
  wrong: number;
  wrongAnswers: AnswerResult[];
  source: string;
  count: number;
  mode: QuizMode;
  answerMode: AnswerMode;
  wrongDaysAgo?: number | null;
};

export type ExcelImportResult = {
  added: number;
  updated: number;
  skipped: number;
  path: string;
};

export type ExcelExportResult = {
  exported: number;
  path: string;
};
