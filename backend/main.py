from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from excel_repository import DEFAULT_EXCEL_PATH, ExcelRepository
from quiz_service import QuizMode, generate_quiz


app = FastAPI(title="Vocab Card API")
repository = ExcelRepository(DEFAULT_EXCEL_PATH)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnswerRequest(BaseModel):
    word_id: int = Field(alias="wordId")
    selected_answer: str = Field(alias="selectedAnswer")
    mode: Literal["word_to_meaning", "meaning_to_word"] = "word_to_meaning"


@app.get("/health")
def health() -> dict:
    return {"ok": True, "excelPath": str(DEFAULT_EXCEL_PATH)}


@app.get("/words")
def get_words(source: str | None = None, search: str | None = None) -> list[dict]:
    words = repository.list_words()
    if source:
        words = [word for word in words if word.source == source]
    if search:
        normalized = search.strip().lower()
        words = [
            word
            for word in words
            if normalized in word.word.lower()
            or normalized in word.meaning.lower()
            or normalized in word.example.lower()
            or normalized in word.note.lower()
        ]
    return [word.to_api() for word in words]


@app.get("/sources")
def get_sources() -> list[str]:
    sources = sorted({word.source for word in repository.list_words() if word.source})
    return sources


@app.get("/quiz")
def get_quiz(
    source: str | None = None,
    count: int = Query(default=10, ge=1, le=100),
    mode: QuizMode = "word_to_meaning",
) -> list[dict]:
    questions = generate_quiz(repository.list_words(), source=source, count=count, mode=mode)
    if not questions:
        raise HTTPException(status_code=404, detail="No words found for quiz")
    return questions


@app.post("/quiz/answer")
def submit_answer(payload: AnswerRequest) -> dict:
    word = repository.get_word(payload.word_id)
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    correct_answer = word.meaning if payload.mode == "word_to_meaning" else word.word
    is_correct = payload.selected_answer.strip() == correct_answer.strip()

    try:
        updated = repository.update_answer(payload.word_id, is_correct)
    except KeyError:
        raise HTTPException(status_code=404, detail="Word not found") from None

    return {
        "isCorrect": is_correct,
        "correctAnswer": correct_answer,
        "selectedAnswer": payload.selected_answer,
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


@app.get("/review/wrong")
def get_wrong_review() -> list[dict]:
    words = [word for word in repository.list_words() if word.wrong_count > 0]
    words.sort(key=lambda word: (-word.wrong_count, word.word.lower()))
    return [word.to_api() for word in words]


@app.get("/stats")
def get_stats() -> dict:
    words = repository.list_words()
    total_words = len(words)
    tested_words = len([word for word in words if word.total_count > 0])
    wrong_words = len([word for word in words if word.wrong_count > 0])
    total_attempts = sum(word.total_count for word in words)
    total_correct = sum(word.correct_count for word in words)
    average_accuracy = round((total_correct / total_attempts) * 100, 1) if total_attempts else 0.0
    top_wrong_words = sorted(words, key=lambda word: word.wrong_count, reverse=True)[:5]

    return {
        "totalWords": total_words,
        "testedWords": tested_words,
        "wrongWords": wrong_words,
        "averageAccuracy": average_accuracy,
        "topWrongWords": [word.to_api() for word in top_wrong_words if word.wrong_count > 0],
    }
