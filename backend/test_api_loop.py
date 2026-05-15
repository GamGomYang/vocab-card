from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REQUIRED_WORD_FIELDS = {
    "id",
    "source",
    "word",
    "meaning",
    "example",
    "exampleMeaning",
    "note",
    "correctCount",
    "wrongCount",
    "totalCount",
}


class ApiTestFailure(RuntimeError):
    pass


def request_json(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ApiTestFailure(f"{method} {path} failed with {error.code}: {detail}") from error
    except URLError as error:
        raise ApiTestFailure(
            f"Cannot connect to {base_url}. Start the backend first: "
            r".\.venv\Scripts\python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
        ) from error


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise ApiTestFailure(message)


def find_word(words: list[dict[str, Any]], word_id: int) -> dict[str, Any]:
    for word in words:
        if word["id"] == word_id:
            return word
    raise ApiTestFailure(f"wordId {word_id} was not found in GET /words")


def test_once(args: argparse.Namespace, run_number: int) -> None:
    print(f"\n--- API test run {run_number} ---")

    health = request_json(args.base_url, "GET", "/health")
    excel_path = Path(health["excelPath"])
    print(f"health ok, excel={excel_path}")

    backup_path = None
    if not args.keep_changes and not args.skip_answer:
        backup_path = excel_path.with_suffix(f".api-test-backup{excel_path.suffix}")
        shutil.copy2(excel_path, backup_path)
        print(f"temporary backup created: {backup_path.name}")

    try:
        words = request_json(args.base_url, "GET", "/words")
        assert_true(isinstance(words, list) and len(words) > 0, "GET /words returned no words")
        missing = REQUIRED_WORD_FIELDS - set(words[0].keys())
        assert_true(not missing, f"GET /words missing fields: {sorted(missing)}")
        print(f"GET /words ok: {len(words)} words")

        sources = request_json(args.base_url, "GET", "/sources")
        assert_true(isinstance(sources, list), "GET /sources did not return a list")
        assert_true(len(sources) == len(set(sources)), "GET /sources contains duplicate values")
        print(f"GET /sources ok: {len(sources)} sources")

        source = args.source or ("Day 27" if "Day 27" in sources else (sources[0] if sources else ""))
        quiz_params = {"count": str(args.count), "mode": args.mode}
        if source:
            quiz_params["source"] = source
        quiz = request_json(args.base_url, "GET", f"/quiz?{urlencode(quiz_params)}")
        assert_true(isinstance(quiz, list) and len(quiz) > 0, "GET /quiz returned no questions")
        assert_true(len(quiz) <= args.count, f"GET /quiz returned more than {args.count} questions")
        for question in quiz:
            assert_true(question["answer"] in question["choices"], "quiz answer is not included in choices")
            assert_true(len(question["choices"]) == len(set(question["choices"])), "quiz choices contain duplicates")
            assert_true(len(question["choices"]) == min(4, len(words)), "quiz choice count is not 4")
            if source:
                assert_true(question["source"] == source, f"quiz included a word outside source={source}")
        print(f"GET /quiz ok: {len(quiz)} questions from {source or 'all sources'}")

        if not args.skip_answer:
            correct_question = quiz[0]
            before_words = request_json(args.base_url, "GET", "/words")
            before = find_word(before_words, correct_question["wordId"])
            answer_result = request_json(
                args.base_url,
                "POST",
                "/quiz/answer",
                {
                    "wordId": correct_question["wordId"],
                    "selectedAnswer": correct_question["answer"],
                    "mode": args.mode,
                },
            )
            assert_true(answer_result["isCorrect"] is True, "POST /quiz/answer did not mark correct answer as correct")
            after_words = request_json(args.base_url, "GET", "/words")
            after = find_word(after_words, correct_question["wordId"])
            assert_true(after["correctCount"] == before["correctCount"] + 1, "correctCount was not incremented")
            assert_true(after["totalCount"] == before["totalCount"] + 1, "totalCount was not incremented for correct answer")
            print("POST /quiz/answer correct path ok")

            wrong_question = quiz[1] if len(quiz) > 1 else quiz[0]
            before_words = request_json(args.base_url, "GET", "/words")
            before = find_word(before_words, wrong_question["wordId"])
            wrong_result = request_json(
                args.base_url,
                "POST",
                "/quiz/answer",
                {
                    "wordId": wrong_question["wordId"],
                    "selectedAnswer": "__definitely_wrong__",
                    "mode": args.mode,
                },
            )
            assert_true(wrong_result["isCorrect"] is False, "POST /quiz/answer did not mark wrong answer as wrong")
            after_words = request_json(args.base_url, "GET", "/words")
            after = find_word(after_words, wrong_question["wordId"])
            assert_true(after["wrongCount"] == before["wrongCount"] + 1, "wrongCount was not incremented")
            assert_true(after["totalCount"] == before["totalCount"] + 1, "totalCount was not incremented for wrong answer")
            print("POST /quiz/answer wrong path ok")

        wrong_review = request_json(args.base_url, "GET", "/review/wrong")
        assert_true(isinstance(wrong_review, list), "GET /review/wrong did not return a list")
        assert_true(all(word["wrongCount"] > 0 for word in wrong_review), "review contains a word with wrongCount <= 0")
        assert_true(
            all(wrong_review[index]["wrongCount"] >= wrong_review[index + 1]["wrongCount"] for index in range(len(wrong_review) - 1)),
            "review is not sorted by wrongCount descending",
        )
        print(f"GET /review/wrong ok: {len(wrong_review)} wrong words")

        stats = request_json(args.base_url, "GET", "/stats")
        for key in ["totalWords", "testedWords", "wrongWords", "averageAccuracy", "topWrongWords"]:
            assert_true(key in stats, f"GET /stats missing {key}")
        assert_true(stats["totalWords"] == len(request_json(args.base_url, "GET", "/words")), "stats totalWords mismatch")
        print("GET /stats ok")

    finally:
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, excel_path)
            backup_path.unlink()
            print("Excel restored after mutation tests")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a backend-only API test loop against the FastAPI server.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--source", default="")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--mode", choices=["word_to_meaning", "meaning_to_word"], default="word_to_meaning")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--skip-answer", action="store_true", help="Do not call POST /quiz/answer.")
    parser.add_argument("--keep-changes", action="store_true", help="Keep answer-count changes in Excel.")
    args = parser.parse_args()

    for run_number in range(1, args.repeat + 1):
        test_once(args, run_number)
        if run_number < args.repeat:
            time.sleep(args.interval)

    print("\nAll backend API tests passed.")


if __name__ == "__main__":
    main()
