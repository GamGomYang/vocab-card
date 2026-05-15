from __future__ import annotations

import random
from typing import Literal

from excel_repository import VocabWord


QuizMode = Literal["word_to_meaning", "meaning_to_word"]


def generate_quiz(
    words: list[VocabWord],
    source: str | None = None,
    count: int = 10,
    mode: QuizMode = "word_to_meaning",
) -> list[dict]:
    pool = [word for word in words if not source or word.source == source]
    pool = [word for word in pool if word.word and word.meaning]
    if not pool:
        return []

    count = max(1, min(count, len(pool)))
    targets = random.sample(pool, count)
    questions = []

    for target in targets:
        correct_answer = target.meaning if mode == "word_to_meaning" else target.word
        choices = _build_choices(target, words, mode)
        question_text = target.word if mode == "word_to_meaning" else target.meaning

        questions.append(
            {
                "questionId": target.id,
                "wordId": target.id,
                "mode": mode,
                "source": target.source,
                "word": target.word,
                "meaning": target.meaning,
                "questionText": question_text,
                "choices": choices,
                "answer": correct_answer,
                "example": target.example,
                "exampleMeaning": target.example_meaning,
            }
        )

    return questions


def _build_choices(target: VocabWord, words: list[VocabWord], mode: QuizMode) -> list[str]:
    correct_answer = target.meaning if mode == "word_to_meaning" else target.word
    candidate_answers = {
        word.meaning if mode == "word_to_meaning" else word.word
        for word in words
        if word.id != target.id and word.word and word.meaning
    }
    distractors = random.sample(list(candidate_answers), min(3, len(candidate_answers)))
    choices = [correct_answer, *distractors]
    random.shuffle(choices)
    return choices
