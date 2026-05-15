from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from openpyxl import Workbook, load_workbook


HEADERS = [
    "출처",
    "단어",
    "뜻",
    "예문",
    "예문뜻",
    "비고",
    "정답횟수",
    "오답횟수",
    "총시도",
    "최근결과",
    "최근테스트일",
    "연속정답",
    "암기상태",
]

NUMERIC_HEADERS = {"정답횟수", "오답횟수", "총시도", "연속정답"}


@dataclass
class Word:
    row: int
    source: str
    word: str
    meaning: str
    example: str
    example_meaning: str
    note: str
    correct_count: int
    wrong_count: int
    total_count: int
    last_result: str
    last_tested_at: str
    streak_correct: int
    memory_state: str

    @property
    def accuracy(self) -> str:
        if self.total_count == 0:
            return "0.0%"
        return f"{self.correct_count / self.total_count * 100:.1f}%"


class WorkbookStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.ensure_file()

    def ensure_file(self) -> None:
        if not self.path.exists():
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Words"
            sheet.append(HEADERS)
            workbook.save(self.path)
            return

        workbook = load_workbook(self.path)
        sheet = workbook.active
        existing = [sheet.cell(1, col).value for col in range(1, sheet.max_column + 1)]
        changed = False
        for header in HEADERS:
            if header not in existing:
                sheet.cell(1, len(existing) + 1, header)
                existing.append(header)
                changed = True

        columns = self.columns(sheet)
        for row in range(2, sheet.max_row + 1):
            for header in NUMERIC_HEADERS:
                cell = sheet.cell(row, columns[header])
                if cell.value in (None, ""):
                    cell.value = 0
                    changed = True
            state = sheet.cell(row, columns["암기상태"])
            if state.value in (None, ""):
                state.value = "미학습"
                changed = True

        if changed:
            workbook.save(self.path)

    @staticmethod
    def columns(sheet) -> dict[str, int]:
        return {
            str(sheet.cell(1, col).value): col
            for col in range(1, sheet.max_column + 1)
            if sheet.cell(1, col).value
        }

    @staticmethod
    def text(value) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def number(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def list_words(self) -> list[Word]:
        workbook = load_workbook(self.path)
        sheet = workbook.active
        columns = self.columns(sheet)
        words: list[Word] = []
        for row in range(2, sheet.max_row + 1):
            word = self.text(sheet.cell(row, columns["단어"]).value)
            meaning = self.text(sheet.cell(row, columns["뜻"]).value)
            if not word or not meaning:
                continue
            words.append(
                Word(
                    row=row,
                    source=self.text(sheet.cell(row, columns["출처"]).value),
                    word=word,
                    meaning=meaning,
                    example=self.text(sheet.cell(row, columns["예문"]).value),
                    example_meaning=self.text(sheet.cell(row, columns["예문뜻"]).value),
                    note=self.text(sheet.cell(row, columns["비고"]).value),
                    correct_count=self.number(sheet.cell(row, columns["정답횟수"]).value),
                    wrong_count=self.number(sheet.cell(row, columns["오답횟수"]).value),
                    total_count=self.number(sheet.cell(row, columns["총시도"]).value),
                    last_result=self.text(sheet.cell(row, columns["최근결과"]).value),
                    last_tested_at=self.text(sheet.cell(row, columns["최근테스트일"]).value),
                    streak_correct=self.number(sheet.cell(row, columns["연속정답"]).value),
                    memory_state=self.text(sheet.cell(row, columns["암기상태"]).value) or "미학습",
                )
            )
        return words

    def save_result(self, word: Word, is_correct: bool) -> None:
        workbook = load_workbook(self.path)
        sheet = workbook.active
        columns = self.columns(sheet)

        correct = word.correct_count + (1 if is_correct else 0)
        wrong = word.wrong_count + (0 if is_correct else 1)
        total = word.total_count + 1
        streak = word.streak_correct + 1 if is_correct else 0
        result = "정답" if is_correct else "오답"
        state = self.memory_state(correct, wrong, total, streak)

        sheet.cell(word.row, columns["정답횟수"], correct)
        sheet.cell(word.row, columns["오답횟수"], wrong)
        sheet.cell(word.row, columns["총시도"], total)
        sheet.cell(word.row, columns["최근결과"], result)
        sheet.cell(word.row, columns["최근테스트일"], datetime.now().strftime("%Y-%m-%d %H:%M"))
        sheet.cell(word.row, columns["연속정답"], streak)
        sheet.cell(word.row, columns["암기상태"], state)
        workbook.save(self.path)

    @staticmethod
    def memory_state(correct: int, wrong: int, total: int, streak: int) -> str:
        if total == 0:
            return "미학습"
        if wrong >= 1 and streak < 3:
            return "복습필요"
        if streak >= 3 or (total >= 3 and correct / total >= 0.8):
            return "암기완료"
        return "학습중"


class VocabApp(tk.Tk):
    def __init__(self, store: WorkbookStore) -> None:
        super().__init__()
        self.store = store
        self.words: list[Word] = []
        self.filtered: list[Word] = []
        self.current: Word | None = None
        self.answer_var = tk.StringVar()
        self.source_var = tk.StringVar(value="전체")
        self.search_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="단어 -> 뜻")

        self.title("단어 테스트")
        self.geometry("980x660")
        self.minsize(820, 560)
        self.configure(bg="#f7f8fb")

        self.build_ui()
        self.refresh_words()

    def build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f7f8fb")
        style.configure("TLabel", background="#f7f8fb", font=("Malgun Gothic", 10))
        style.configure("Title.TLabel", font=("Malgun Gothic", 18, "bold"))
        style.configure("TButton", font=("Malgun Gothic", 10), padding=8)
        style.configure("Treeview", rowheight=28, font=("Malgun Gothic", 10))
        style.configure("Treeview.Heading", font=("Malgun Gothic", 10, "bold"))

        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=tk.X)
        ttk.Label(header, text="단어 테스트", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="새로고침", command=self.refresh_words).pack(side=tk.RIGHT)

        controls = ttk.Frame(root)
        controls.pack(fill=tk.X, pady=(14, 10))
        ttk.Label(controls, text="출처").pack(side=tk.LEFT)
        self.source_combo = ttk.Combobox(controls, textvariable=self.source_var, state="readonly", width=18)
        self.source_combo.pack(side=tk.LEFT, padx=(8, 14))
        self.source_combo.bind("<<ComboboxSelected>>", lambda _: self.apply_filter())

        ttk.Label(controls, text="검색").pack(side=tk.LEFT)
        search = ttk.Entry(controls, textvariable=self.search_var, width=28)
        search.pack(side=tk.LEFT, padx=(8, 14))
        search.bind("<KeyRelease>", lambda _: self.apply_filter())

        ttk.Label(controls, text="모드").pack(side=tk.LEFT)
        mode = ttk.Combobox(
            controls,
            textvariable=self.mode_var,
            values=["단어 -> 뜻", "뜻 -> 단어"],
            state="readonly",
            width=14,
        )
        mode.pack(side=tk.LEFT, padx=(8, 14))

        ttk.Button(controls, text="문제 시작", command=self.next_question).pack(side=tk.LEFT)

        body = ttk.Frame(root)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        columns = ("source", "word", "meaning", "state", "accuracy")
        self.tree = ttk.Treeview(left, columns=columns, show="headings")
        self.tree.heading("source", text="출처")
        self.tree.heading("word", text="단어")
        self.tree.heading("meaning", text="뜻")
        self.tree.heading("state", text="상태")
        self.tree.heading("accuracy", text="정답률")
        self.tree.column("source", width=90, anchor=tk.W)
        self.tree.column("word", width=150, anchor=tk.W)
        self.tree.column("meaning", width=260, anchor=tk.W)
        self.tree.column("state", width=90, anchor=tk.CENTER)
        self.tree.column("accuracy", width=80, anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        quiz = ttk.Frame(body, padding=14)
        quiz.pack(side=tk.RIGHT, fill=tk.BOTH)
        ttk.Label(quiz, text="문제", style="Title.TLabel").pack(anchor=tk.W)
        self.question_label = ttk.Label(quiz, text="문제 시작을 누르세요.", wraplength=310, font=("Malgun Gothic", 16, "bold"))
        self.question_label.pack(fill=tk.X, pady=(18, 12))
        self.meta_label = ttk.Label(quiz, text="", wraplength=310)
        self.meta_label.pack(fill=tk.X, pady=(0, 12))

        self.choice_frame = ttk.Frame(quiz)
        self.choice_frame.pack(fill=tk.X)
        self.choice_buttons: list[ttk.Radiobutton] = []
        for _ in range(4):
            button = ttk.Radiobutton(self.choice_frame, variable=self.answer_var, value="", text="")
            button.pack(anchor=tk.W, fill=tk.X, pady=5)
            self.choice_buttons.append(button)

        actions = ttk.Frame(quiz)
        actions.pack(fill=tk.X, pady=(18, 0))
        ttk.Button(actions, text="정답 확인", command=self.submit_answer).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(actions, text="다음 문제", command=self.next_question).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        self.result_label = ttk.Label(quiz, text="", wraplength=310, font=("Malgun Gothic", 11, "bold"))
        self.result_label.pack(fill=tk.X, pady=(18, 0))
        self.example_label = ttk.Label(quiz, text="", wraplength=310)
        self.example_label.pack(fill=tk.X, pady=(10, 0))

    def refresh_words(self) -> None:
        try:
            self.words = self.store.list_words()
        except Exception as exc:
            messagebox.showerror("단어 테스트", f"단어DB.xlsx를 읽을 수 없습니다.\n\n{exc}")
            return

        sources = ["전체"] + sorted({word.source for word in self.words if word.source})
        self.source_combo["values"] = sources
        if self.source_var.get() not in sources:
            self.source_var.set("전체")
        self.apply_filter()

    def apply_filter(self) -> None:
        source = self.source_var.get()
        keyword = self.search_var.get().strip().lower()
        self.filtered = []
        for word in self.words:
            if source != "전체" and word.source != source:
                continue
            searchable = " ".join([word.word, word.meaning, word.example, word.note]).lower()
            if keyword and keyword not in searchable:
                continue
            self.filtered.append(word)

        self.tree.delete(*self.tree.get_children())
        for word in self.filtered:
            self.tree.insert(
                "",
                tk.END,
                values=(word.source, word.word, word.meaning, word.memory_state, word.accuracy),
            )

    def next_question(self) -> None:
        if not self.filtered:
            messagebox.showinfo("단어 테스트", "출제할 단어가 없습니다.")
            return

        self.current = random.choice(self.filtered)
        reverse = self.mode_var.get() == "뜻 -> 단어"
        question = self.current.meaning if reverse else self.current.word
        answer = self.current.word if reverse else self.current.meaning
        candidates = [word.word if reverse else word.meaning for word in self.words if word.row != self.current.row]
        choices = random.sample(candidates, min(3, len(candidates)))
        choices.append(answer)
        random.shuffle(choices)

        self.answer_var.set("")
        self.question_label.configure(text=question)
        self.meta_label.configure(text=f"{self.current.source} | {self.current.memory_state} | 정답률 {self.current.accuracy}")
        self.result_label.configure(text="")
        self.example_label.configure(text="")
        for index, button in enumerate(self.choice_buttons):
            if index < len(choices):
                button.configure(text=choices[index], value=choices[index], state=tk.NORMAL)
                button.pack(anchor=tk.W, fill=tk.X, pady=5)
            else:
                button.pack_forget()

    def submit_answer(self) -> None:
        if self.current is None:
            return
        selected = self.answer_var.get()
        if not selected:
            messagebox.showinfo("단어 테스트", "답을 선택하세요.")
            return

        reverse = self.mode_var.get() == "뜻 -> 단어"
        answer = self.current.word if reverse else self.current.meaning
        is_correct = selected.strip() == answer.strip()
        self.store.save_result(self.current, is_correct)
        self.result_label.configure(text=("정답입니다." if is_correct else f"오답입니다. 정답: {answer}"))
        example = self.current.example
        if self.current.example_meaning:
            example = f"{example}\n{self.current.example_meaning}" if example else self.current.example_meaning
        self.example_label.configure(text=example)
        self.refresh_words()


def app_root() -> Path:
    cwd_db = Path.cwd() / "단어DB.xlsx"
    if cwd_db.exists():
        return Path.cwd()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


if __name__ == "__main__":
    db_path = app_root() / "단어DB.xlsx"
    app = VocabApp(WorkbookStore(db_path))
    app.mainloop()
