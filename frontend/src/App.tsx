import { BarChart3, BookOpenCheck, Home, RotateCcw, Search, Trophy } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { vocabApi } from "./api/vocabApi";
import type { AnswerResult, QuizMode, QuizQuestion, QuizResultSummary, StatsSummary, VocabWord } from "./types/vocab";

type Page = "home" | "quiz" | "result" | "review" | "stats";

const modeLabels: Record<QuizMode, string> = {
  word_to_meaning: "단어 -> 뜻",
  meaning_to_word: "뜻 -> 단어",
};

const pages = new Set<Page>(["home", "quiz", "result", "review", "stats"]);

function isPage(value: unknown): value is Page {
  return typeof value === "string" && pages.has(value as Page);
}

function App() {
  const [page, setPage] = useState<Page>("home");
  const [sources, setSources] = useState<string[]>([]);
  const [source, setSource] = useState("");
  const [count, setCount] = useState(10);
  const [mode, setMode] = useState<QuizMode>("word_to_meaning");
  const [summary, setSummary] = useState<QuizResultSummary | null>(null);
  const [loadError, setLoadError] = useState("");
  const [syncStatus, setSyncStatus] = useState("");

  useEffect(() => {
    window.history.replaceState({ page: "home" }, "", window.location.href);

    const handlePopState = (event: PopStateEvent) => {
      setPage(isPage(event.state?.page) ? event.state.page : "home");
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = (nextPage: Page) => {
    setPage(nextPage);
    if (window.history.state?.page !== nextPage) {
      window.history.pushState({ page: nextPage }, "", window.location.href);
    }
  };

  const refreshSources = () => {
    vocabApi
      .getSources()
      .then((items) => {
        setSources(items);
        setSource((current) => (current && items.includes(current) ? current : items[0] ?? ""));
      })
      .catch((error: Error) => setLoadError(error.message));
  };

  useEffect(() => {
    refreshSources();
  }, []);

  const importExcel = async () => {
    setSyncStatus("");
    setLoadError("");
    try {
      const result = await vocabApi.importExcel();
      setSyncStatus(`Excel 가져오기 완료: 추가 ${result.added}개, 갱신 ${result.updated}개, 건너뜀 ${result.skipped}개`);
      refreshSources();
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Excel 가져오기에 실패했습니다.");
    }
  };

  const exportExcel = async () => {
    setSyncStatus("");
    setLoadError("");
    try {
      const result = await vocabApi.exportExcel();
      setSyncStatus(`Excel 내보내기 완료: ${result.exported}개 저장`);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Excel 내보내기에 실패했습니다.");
    }
  };

  return (
    <main className="app-shell">
      <nav className="topbar">
        <button className="brand" onClick={() => navigate("home")}>
          <BookOpenCheck size={24} />
          <span>Vocab 단어 테스트</span>
        </button>
        <div className="nav-actions">
          <IconButton label="홈" active={page === "home"} onClick={() => navigate("home")}>
            <Home size={18} />
          </IconButton>
          <IconButton label="오답노트" active={page === "review"} onClick={() => navigate("review")}>
            <Search size={18} />
          </IconButton>
          <IconButton label="통계" active={page === "stats"} onClick={() => navigate("stats")}>
            <BarChart3 size={18} />
          </IconButton>
        </div>
      </nav>

      {loadError && <div className="error-banner">백엔드 연결 오류: {loadError}</div>}
      {syncStatus && <div className="success-banner">{syncStatus}</div>}

      {page === "home" && (
        <HomePage
          sources={sources}
          source={source}
          count={count}
          mode={mode}
          onSourceChange={setSource}
          onCountChange={setCount}
          onModeChange={setMode}
          onStart={() => navigate("quiz")}
          onReview={() => navigate("review")}
          onStats={() => navigate("stats")}
          onImportExcel={importExcel}
          onExportExcel={exportExcel}
        />
      )}

      {page === "quiz" && (
        <QuizPage
          source={source}
          count={count}
          mode={mode}
          onExit={() => navigate("home")}
          onDone={(result) => {
            setSummary(result);
            navigate("result");
          }}
        />
      )}

      {page === "result" && summary && (
        <ResultPage
          summary={summary}
          onRetry={() => navigate("quiz")}
          onReview={() => navigate("review")}
          onHome={() => navigate("home")}
        />
      )}

      {page === "review" && <ReviewPage />}
      {page === "stats" && <StatsPage />}
    </main>
  );
}

function HomePage(props: {
  sources: string[];
  source: string;
  count: number;
  mode: QuizMode;
  onSourceChange: (value: string) => void;
  onCountChange: (value: number) => void;
  onModeChange: (value: QuizMode) => void;
  onStart: () => void;
  onReview: () => void;
  onStats: () => void;
  onImportExcel: () => void;
  onExportExcel: () => void;
}) {
  return (
    <section className="home-grid">
      <div className="hero-panel">
        <p className="eyebrow">Excel 기반 영단어 테스트</p>
        <h1>Vocab 단어 테스트</h1>
        <div className="quick-stats">
          <StatPill label="선택 Day" value={props.source || "전체"} />
          <StatPill label="문제 수" value={`${props.count}개`} />
          <StatPill label="모드" value={modeLabels[props.mode]} />
        </div>
      </div>

      <section className="setup-panel">
        <label>
          Day 선택
          <select value={props.source} onChange={(event) => props.onSourceChange(event.target.value)}>
            <option value="">전체</option>
            {props.sources.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label>
          문제 수
          <select value={props.count} onChange={(event) => props.onCountChange(Number(event.target.value))}>
            {[5, 10, 20, 30, 50].map((item) => (
              <option key={item} value={item}>
                {item}개
              </option>
            ))}
          </select>
        </label>

        <label>
          테스트 모드
          <div className="segmented">
            {Object.entries(modeLabels).map(([value, label]) => (
              <button
                key={value}
                className={props.mode === value ? "active" : ""}
                onClick={() => props.onModeChange(value as QuizMode)}
              >
                {label}
              </button>
            ))}
          </div>
        </label>

        <button className="primary-action" onClick={props.onStart}>
          테스트 시작
        </button>
        <div className="secondary-actions">
          <button onClick={props.onReview}>오답노트</button>
          <button onClick={props.onStats}>학습 통계</button>
        </div>
        <div className="secondary-actions">
          <button onClick={props.onImportExcel}>Excel에서 가져오기</button>
          <button onClick={props.onExportExcel}>Excel로 내보내기</button>
        </div>
      </section>
    </section>
  );
}

function QuizPage(props: {
  source: string;
  count: number;
  mode: QuizMode;
  onExit: () => void;
  onDone: (summary: QuizResultSummary) => void;
}) {
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [selected, setSelected] = useState("");
  const [answers, setAnswers] = useState<AnswerResult[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    vocabApi
      .getQuiz(props.source, props.count, props.mode)
      .then((items) => {
        setQuestions(items);
        setIndex(0);
        setResult(null);
        setSelected("");
        setAnswers([]);
        setIsSubmitting(false);
      })
      .catch((apiError: Error) => setError(apiError.message))
      .finally(() => setLoading(false));
  }, [props.source, props.count, props.mode]);

  const question = questions[index];
  const correctCount = answers.filter((answer) => answer.isCorrect).length;
  const wrongAnswers = answers.filter((answer) => !answer.isCorrect);
  const accuracy = answers.length === 0 ? 0 : Math.min(100, Math.round((correctCount / answers.length) * 100));

  const submit = async (choice: string) => {
    if (!question || result || isSubmitting) return;
    setIsSubmitting(true);
    setSelected(choice);
    try {
      const answer = await vocabApi.submitAnswer(question.wordId, choice, props.mode);
      setResult(answer);
      setAnswers((value) => [...value, answer]);
    } catch (apiError) {
      setError(apiError instanceof Error ? apiError.message : "Failed to submit answer.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const next = () => {
    const nextIndex = index + 1;
    const finalWrongAnswers = wrongAnswers;

    if (nextIndex >= questions.length) {
      props.onDone({
        total: questions.length,
        correct: correctCount,
        wrong: questions.length - correctCount,
        wrongAnswers: finalWrongAnswers,
        source: props.source,
        count: props.count,
        mode: props.mode,
      });
      return;
    }

    setIndex(nextIndex);
    setResult(null);
    setSelected("");
  };

  if (loading) return <section className="center-panel">문제를 불러오는 중입니다.</section>;
  if (error) return <section className="center-panel error-text">{error}</section>;
  if (!question) return <section className="center-panel">출제할 단어가 없습니다.</section>;

  return (
    <section className="quiz-layout">
      <div className="quiz-meta">
        <span>
          문제 {index + 1} / {questions.length}
        </span>
        <span>현재 정답률 {accuracy}%</span>
        <button className="text-button" onClick={props.onExit}>
          홈으로
        </button>
      </div>

      <article className="quiz-card">
        <p>{props.mode === "word_to_meaning" ? "이 단어의 뜻으로 알맞은 것은?" : "이 뜻에 맞는 단어는?"}</p>
        <h2>{question.questionText}</h2>
        {result && question.example && <span className="example-line">{question.example}</span>}
        {result && question.exampleMeaning && <span className="example-meaning-line">{question.exampleMeaning}</span>}
      </article>

      <div className="choices-grid">
        {question.choices.map((choice) => {
          const isCorrect = result && choice === result.correctAnswer;
          const isWrong = result && choice === selected && !result.isCorrect;
          return (
            <button
              key={choice}
              className={`choice-button ${isCorrect ? "correct" : ""} ${isWrong ? "wrong" : ""}`}
              onClick={() => submit(choice)}
              disabled={Boolean(result) || isSubmitting}
            >
              {choice}
            </button>
          );
        })}
      </div>

      {result && (
        <section className={`quiz-result-bar ${result.isCorrect ? "correct" : "wrong"}`}>
          <div>
            <strong>{result.isCorrect ? "정답입니다." : "오답입니다."}</strong>
            <span>
              정답: {result.word} = {result.meaning}
            </span>
            {!result.isCorrect && <span>선택: {result.selectedAnswer}</span>}
            <span>현재 오답 횟수 {result.wrongCount}회</span>
          </div>
          <button className="primary-action compact" onClick={next}>
            {index + 1 >= questions.length ? "결과 보기" : "다음 문제"}
          </button>
        </section>
      )}
    </section>
  );
}

function ResultPage(props: {
  summary: QuizResultSummary;
  onRetry: () => void;
  onReview: () => void;
  onHome: () => void;
}) {
  const rate = Math.round((props.summary.correct / props.summary.total) * 100);

  return (
    <section className="result-layout">
      <Trophy size={42} />
      <h1>테스트 완료</h1>
      <div className="result-metrics">
        <StatPill label="총 문제" value={`${props.summary.total}개`} />
        <StatPill label="정답" value={`${props.summary.correct}개`} />
        <StatPill label="오답" value={`${props.summary.wrong}개`} />
        <StatPill label="정답률" value={`${rate}%`} />
      </div>

      <section className="table-section">
        <h2>틀린 단어</h2>
        {props.summary.wrongAnswers.length === 0 ? (
          <p className="empty-text">이번 테스트의 오답이 없습니다.</p>
        ) : (
          <WordTable
            words={props.summary.wrongAnswers.map((answer, id) => ({
              id,
              source: "",
              word: answer.word,
              meaning: answer.meaning,
              example: answer.example,
              exampleMeaning: answer.exampleMeaning,
              correctCount: answer.correctCount,
              wrongCount: answer.wrongCount,
              totalCount: answer.totalCount,
              streakCorrect: 0,
              memoryState: answer.memoryState,
              accuracy: 0,
            }))}
          />
        )}
      </section>

      <div className="secondary-actions centered">
        <button onClick={props.onRetry}>
          <RotateCcw size={16} /> 다시 테스트
        </button>
        <button onClick={props.onReview}>오답만 복습</button>
        <button onClick={props.onHome}>홈으로</button>
      </div>
    </section>
  );
}

function ReviewPage() {
  const [words, setWords] = useState<VocabWord[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    vocabApi.getWrongWords().then(setWords).catch((apiError: Error) => setError(apiError.message));
  }, []);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return words;
    return words.filter(
      (word) =>
        word.word.toLowerCase().includes(normalized) ||
        word.meaning.toLowerCase().includes(normalized) ||
        word.example.toLowerCase().includes(normalized),
    );
  }, [query, words]);

  return (
    <section className="table-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Review</p>
          <h1>오답노트</h1>
        </div>
        <label className="search-box">
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="단어, 뜻, 예문 검색" />
        </label>
      </div>
      {error ? <p className="error-text">{error}</p> : <WordTable words={filtered} />}
    </section>
  );
}

function StatsPage() {
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    vocabApi.getStats().then(setStats).catch((apiError: Error) => setError(apiError.message));
  }, []);

  if (error) return <section className="center-panel error-text">{error}</section>;
  if (!stats) return <section className="center-panel">통계를 불러오는 중입니다.</section>;

  return (
    <section className="stats-layout">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Stats</p>
          <h1>학습 현황</h1>
        </div>
      </div>

      <div className="result-metrics">
        <StatPill label="전체 단어" value={`${stats.totalWords}개`} />
        <StatPill label="테스트한 단어" value={`${stats.testedWords}개`} />
        <StatPill label="오답 있는 단어" value={`${stats.wrongWords}개`} />
        <StatPill label="평균 정답률" value={`${stats.averageAccuracy}%`} />
      </div>

      <section className="table-section">
        <h2>가장 많이 틀린 단어 TOP 5</h2>
        <WordTable words={stats.topWrongWords} />
      </section>
    </section>
  );
}

function WordTable({ words }: { words: VocabWord[] }) {
  if (words.length === 0) return <p className="empty-text">표시할 단어가 없습니다.</p>;

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>단어</th>
            <th>뜻</th>
            <th>오답횟수</th>
            <th>상태</th>
            <th>예문</th>
          </tr>
        </thead>
        <tbody>
          {words.map((word) => (
            <tr key={`${word.id}-${word.word}`}>
              <td>{word.word}</td>
              <td>{word.meaning}</td>
              <td>{word.wrongCount}</td>
              <td>
                <span className="state-chip">{word.memoryState}</span>
              </td>
              <td>{word.example}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function IconButton(props: { label: string; active?: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button className={`icon-button ${props.active ? "active" : ""}`} onClick={props.onClick} title={props.label}>
      {props.children}
      <span>{props.label}</span>
    </button>
  );
}

export default App;
