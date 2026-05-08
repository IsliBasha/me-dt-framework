from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QLineEdit, QRadioButton,
    QButtonGroup, QScrollArea, QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import frontend.api_client as api
from frontend.theme import DARK
from frontend.i18n import t

_DIFFICULTIES = [
    ("quiz.d_easy", "lehtë"),
    ("quiz.d_medium", "mesatar"),
    ("quiz.d_hard", "vështirë"),
]


class _ExplainWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, question: str, subject: str):
        super().__init__()
        self.question = question
        self.subject = subject

    def run(self):
        try:
            result = api.post(
                "/api/tutor/explain",
                json={"question": self.question, "subject": self.subject},
            )
            self.finished.emit(result.get("explanation", ""))
        except Exception as e:
            self.error.emit(str(e))


class QuizPage(QWidget):
    def __init__(self, colors: dict = DARK, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.questions = []
        self.answers = []
        self.current_q = 0
        self.start_time = 0
        self._workers = []
        self._build_setup_ui()

    def _build_setup_ui(self):
        self._clear()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        title = QLabel(t("quiz.title"))
        title.setObjectName("title")
        subtitle = QLabel(t("quiz.subtitle"))
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFrame()
        form.setObjectName("card")
        form_layout = QVBoxLayout(form)
        form_layout.setSpacing(16)

        form_layout.addWidget(QLabel(t("quiz.subject")))
        self.subject_combo = QComboBox()
        self.subject_combo.addItems(["matematike", "shqipe"])
        form_layout.addWidget(self.subject_combo)

        form_layout.addWidget(QLabel(t("quiz.topic")))
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText(t("quiz.topic_hint"))
        form_layout.addWidget(self.topic_input)

        form_layout.addWidget(QLabel(t("quiz.difficulty")))
        self.diff_combo = QComboBox()
        for key, api_val in _DIFFICULTIES:
            self.diff_combo.addItem(t(key), api_val)
        self.diff_combo.setCurrentIndex(1)
        form_layout.addWidget(self.diff_combo)

        form_layout.addWidget(QLabel(t("quiz.count")))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(3, 20)
        self.count_spin.setValue(5)
        form_layout.addWidget(self.count_spin)

        layout.addWidget(form)

        self.start_btn = QPushButton(t("quiz.start"))
        self.start_btn.clicked.connect(self._generate_quiz)
        layout.addWidget(self.start_btn)
        layout.addStretch()

    def _clear(self):
        if self.layout():
            self._clear_layout(self.layout())
            QWidget().setLayout(self.layout())

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            sub = item.layout()
            if sub:
                self._clear_layout(sub)

    def _generate_quiz(self):
        self.start_btn.setEnabled(False)
        self.start_btn.setText(t("quiz.generating"))
        try:
            topic = self.topic_input.text().strip() or "të përgjithshme"
            result = api.post("/api/quiz/generate", json={
                "topic": topic,
                "subject": self.subject_combo.currentText(),
                "count": self.count_spin.value(),
                "difficulty": self.diff_combo.currentData(),
            })
            self.questions = result.get("questions", [])
            self._subject = self.subject_combo.currentText()
            self._topic = topic
            if not self.questions:
                QMessageBox.warning(self, t("quiz.err"), t("quiz.no_q"))
                self.start_btn.setEnabled(True)
                self.start_btn.setText(t("quiz.start"))
                return
            self.answers = [None] * len(self.questions)
            self.current_q = 0
            import time
            self.start_time = time.time()
            self._build_question_ui()
        except Exception as e:
            QMessageBox.critical(self, t("quiz.err"), str(e))
            self.start_btn.setEnabled(True)
            self.start_btn.setText(t("quiz.start"))

    def _build_question_ui(self):
        self._clear()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        q = self.questions[self.current_q]
        header = QHBoxLayout()
        progress = QLabel(t("quiz.question_of", cur=self.current_q + 1, tot=len(self.questions)))
        progress.setObjectName("subtitle")
        header.addWidget(progress)
        header.addStretch()
        layout.addLayout(header)

        q_frame = QFrame()
        q_frame.setObjectName("card")
        q_layout = QVBoxLayout(q_frame)
        q_text = QLabel(q.get("question", ""))
        q_text.setWordWrap(True)
        q_text.setStyleSheet("font-size: 16px; font-weight: 600;")
        q_layout.addWidget(q_text)
        layout.addWidget(q_frame)

        options_frame = QFrame()
        options_frame.setObjectName("card")
        options_layout = QVBoxLayout(options_frame)
        self._btn_group = QButtonGroup(self)
        for i, opt in enumerate(q.get("options", [])):
            rb = QRadioButton(opt)
            rb.setStyleSheet("font-size: 14px; padding: 6px;")
            self._btn_group.addButton(rb, i)
            options_layout.addWidget(rb)
        layout.addWidget(options_frame)
        layout.addStretch()

        nav = QHBoxLayout()
        back_btn = QPushButton(t("quiz.back"))
        back_btn.setObjectName("secondary")
        back_btn.clicked.connect(self._build_setup_ui)
        nav.addWidget(back_btn)
        nav.addStretch()

        if self.current_q < len(self.questions) - 1:
            next_btn = QPushButton(t("quiz.next"))
            next_btn.clicked.connect(self._next_question)
            nav.addWidget(next_btn)
        else:
            finish_btn = QPushButton(t("quiz.finish"))
            finish_btn.clicked.connect(self._finish_quiz)
            nav.addWidget(finish_btn)

        layout.addLayout(nav)

    def _next_question(self):
        self._save_answer()
        self.current_q += 1
        self._build_question_ui()

    def _save_answer(self):
        checked = self._btn_group.checkedButton()
        q = self.questions[self.current_q]
        opts = q.get("options", [])
        if checked and opts:
            self.answers[self.current_q] = checked.text()
        else:
            self.answers[self.current_q] = ""

    def _finish_quiz(self):
        self._save_answer()
        import time
        duration = int(time.time() - self.start_time)
        answer_items = []
        for i, q in enumerate(self.questions):
            answer_items.append({
                "question_text": q.get("question", ""),
                "user_answer": self.answers[i] or "",
                "correct_answer": q.get("correct", ""),
            })
        try:
            result = api.post("/api/quiz/submit", json={
                "subject": self._subject,
                "topic": self._topic,
                "answers": answer_items,
                "duration_seconds": duration,
            })
            self._show_results(result)
        except Exception as e:
            QMessageBox.critical(self, t("quiz.err"), str(e))

    def _show_results(self, result: dict):
        self._clear()
        self._workers = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(16)

        score = result.get("score", 0)
        score_color = "#43e97b" if score >= 80 else "#f9a825" if score >= 50 else "#ef5350"

        score_lbl = QLabel(f"{score}%")
        score_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_lbl.setStyleSheet(f"font-size: 52px; font-weight: 700; color: {score_color};")
        outer.addWidget(score_lbl)

        detail_lbl = QLabel(
            t("quiz.correct_of", cor=result.get("correct", 0), tot=result.get("total", 0))
        )
        detail_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail_lbl.setObjectName("subtitle")
        outer.addWidget(detail_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        rows = QVBoxLayout(container)
        rows.setSpacing(12)
        rows.setContentsMargins(0, 0, 0, 0)

        for i, q in enumerate(self.questions):
            user_ans = (self.answers[i] or "").strip()
            correct_ans = q.get("correct", "").strip()
            is_correct = user_ans.lower() == correct_ans.lower()
            rows.addWidget(self._make_question_row(i, q, user_ans, correct_ans, is_correct))

        rows.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        retry_btn = QPushButton(t("quiz.new"))
        retry_btn.clicked.connect(self._build_setup_ui)
        outer.addWidget(retry_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _make_question_row(
        self, idx: int, q: dict, user_ans: str, correct_ans: str, is_correct: bool
    ) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        header = QHBoxLayout()
        icon_color = self.colors["success"] if is_correct else self.colors["error"]
        icon = QLabel("OK" if is_correct else "X")
        icon.setStyleSheet(f"color: {icon_color}; font-weight: 700; font-size: 14px;")
        num = QLabel(t("quiz.q_n", n=idx + 1))
        num.setStyleSheet("font-weight: 600; font-size: 13px;")
        header.addWidget(icon)
        header.addWidget(num)
        header.addStretch()
        layout.addLayout(header)

        q_text = QLabel(q.get("question", ""))
        q_text.setWordWrap(True)
        q_text.setStyleSheet("font-size: 14px;")
        layout.addWidget(q_text)

        if not is_correct:
            your_lbl = QLabel(t("quiz.your_ans", a=user_ans or t("quiz.no_sel")))
            your_lbl.setStyleSheet("color: #ef5350; font-size: 12px;")
            correct_lbl = QLabel(t("quiz.correct_ans", a=correct_ans))
            correct_lbl.setStyleSheet("color: #43e97b; font-size: 12px;")
            layout.addWidget(your_lbl)
            layout.addWidget(correct_lbl)

        brief = q.get("explanation", "")
        if brief:
            brief_lbl = QLabel(brief)
            brief_lbl.setWordWrap(True)
            brief_lbl.setStyleSheet("font-size: 12px; font-style: italic;")
            layout.addWidget(brief_lbl)

        if not is_correct:
            explain_btn = QPushButton(t("quiz.explain"))
            explain_btn.setObjectName("secondary")
            explain_box = QLabel("")
            explain_box.setWordWrap(True)
            explain_box.setVisible(False)
            explain_box.setStyleSheet("font-size: 12px; padding: 8px; border-radius: 4px;")

            def on_explain(checked, btn=explain_btn, box=explain_box,
                           question=q.get("question", ""), subject=self._subject):
                btn.setEnabled(False)
                btn.setText(t("quiz.explaining"))
                worker = _ExplainWorker(question, subject)

                def on_done(text, b=btn, bx=box):
                    b.setVisible(False)
                    bx.setText(text)
                    bx.setVisible(True)

                def on_err(msg, b=btn):
                    b.setEnabled(True)
                    b.setText(t("quiz.explain"))
                    QMessageBox.warning(None, t("quiz.err"), msg)

                worker.finished.connect(on_done)
                worker.error.connect(on_err)
                self._workers.append(worker)
                worker.start()

            explain_btn.clicked.connect(on_explain)
            layout.addWidget(explain_btn)
            layout.addWidget(explain_box)

        return frame
