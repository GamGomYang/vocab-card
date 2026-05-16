from __future__ import annotations

import random
import sys
import ctypes
from pathlib import Path
from typing import Literal

import webview

from native_vocab_app import WorkbookStore, Word


QuizMode = Literal["word_to_meaning", "meaning_to_word"]
ERROR_ALREADY_EXISTS = 183
SINGLE_INSTANCE_MUTEX = "VocabCardDesktopSingleInstance"


def app_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "vocab.db").exists() or (cwd / "단어DB.xlsx").exists():
        return Path.cwd()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def frontend_index(root: Path) -> Path:
    frozen_index = root / "frontend" / "dist" / "index.html"
    if frozen_index.exists():
        return frozen_index
    source_index = root / "frontend" / "dist" / "index.html"
    return source_index


def word_to_api(word: Word) -> dict:
    accuracy = 0 if word.total_count == 0 else round((word.correct_count / word.total_count) * 100, 1)
    return {
        "id": word.row,
        "source": word.source,
        "word": word.word,
        "meaning": word.meaning,
        "example": word.example,
        "exampleMeaning": word.example_meaning,
        "note": word.note,
        "correctCount": word.correct_count,
        "wrongCount": word.wrong_count,
        "totalCount": word.total_count,
        "lastResult": word.last_result,
        "lastTestedAt": word.last_tested_at,
        "streakCorrect": word.streak_correct,
        "memoryState": word.memory_state,
        "accuracy": accuracy,
    }


class Api:
    def __init__(self, store: WorkbookStore) -> None:
        self.store = store

    def getSources(self) -> list[str]:
        return sorted({word.source for word in self.store.list_words() if word.source})

    def getQuiz(self, source: str = "", count: int = 10, mode: QuizMode = "word_to_meaning") -> list[dict]:
        words = self.store.list_words()
        pool = [word for word in words if not source or word.source == source]
        pool = [word for word in pool if word.word and word.meaning]
        if not pool:
            return []

        targets = random.sample(pool, min(max(1, int(count)), len(pool)))
        questions = []
        for target in targets:
            correct = target.meaning if mode == "word_to_meaning" else target.word
            candidates = {
                word.meaning if mode == "word_to_meaning" else word.word
                for word in words
                if word.row != target.row and word.word and word.meaning
            }
            choices = random.sample(list(candidates), min(3, len(candidates)))
            choices.append(correct)
            random.shuffle(choices)
            questions.append(
                {
                    "questionId": target.row,
                    "wordId": target.row,
                    "mode": mode,
                    "source": target.source,
                    "word": target.word,
                    "meaning": target.meaning,
                    "questionText": target.word if mode == "word_to_meaning" else target.meaning,
                    "choices": choices,
                    "answer": correct,
                    "example": target.example,
                    "exampleMeaning": target.example_meaning,
                }
            )
        return questions

    def submitAnswer(self, wordId: int, selectedAnswer: str, mode: QuizMode = "word_to_meaning") -> dict:
        words = self.store.list_words()
        word = next((item for item in words if item.row == int(wordId)), None)
        if word is None:
            raise ValueError("Word not found")

        correct_answer = word.meaning if mode == "word_to_meaning" else word.word
        is_correct = selectedAnswer.strip() == correct_answer.strip()
        self.store.save_result(word, is_correct)
        updated = next(item for item in self.store.list_words() if item.row == word.row)
        return {
            "isCorrect": is_correct,
            "correctAnswer": correct_answer,
            "selectedAnswer": selectedAnswer,
            "word": updated.word,
            "meaning": updated.meaning,
            "example": updated.example,
            "exampleMeaning": updated.example_meaning,
            "correctCount": updated.correct_count,
            "wrongCount": updated.wrong_count,
            "totalCount": updated.total_count,
            "lastResult": updated.last_result,
            "memoryState": updated.memory_state,
        }

    def getWrongWords(self) -> list[dict]:
        words = [word for word in self.store.list_words() if word.wrong_count > 0]
        words.sort(key=lambda item: (item.wrong_count, item.total_count), reverse=True)
        return [word_to_api(word) for word in words]

    def getStats(self) -> dict:
        words = self.store.list_words()
        tested = [word for word in words if word.total_count > 0]
        wrong = [word for word in words if word.wrong_count > 0]
        average = 0
        if tested:
            average = round(
                sum(word.correct_count / word.total_count * 100 for word in tested if word.total_count > 0)
                / len(tested),
                1,
            )
        top_wrong = sorted(wrong, key=lambda item: (item.wrong_count, item.total_count), reverse=True)[:5]
        return {
            "totalWords": len(words),
            "testedWords": len(tested),
            "wrongWords": len(wrong),
            "averageAccuracy": average,
            "topWrongWords": [word_to_api(word) for word in top_wrong],
        }

    def importExcel(self) -> dict:
        return self.store.import_excel()

    def exportExcel(self) -> dict:
        return self.store.export_excel()


if __name__ == "__main__":
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
    if mutex and ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        sys.exit(0)
    if not mutex:
        raise ctypes.WinError()

    root = app_root()
    index = frontend_index(root)
    if not index.exists():
        raise FileNotFoundError(f"Frontend build was not found: {index}")

    api = Api(WorkbookStore(root / "vocab.db", root / "단어DB.xlsx"))
    webview.create_window(
        "단어 테스트",
        index.as_uri(),
        js_api=api,
        width=1180,
        height=780,
        min_size=(900, 620),
    )
    webview.start(debug=False)
