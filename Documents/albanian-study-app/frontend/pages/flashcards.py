from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QStackedWidget, QMessageBox, QComboBox,
    QSpinBox, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import frontend.api_client as api
from frontend.theme import DARK
from frontend.i18n import t

# Unicode subscript digits U+2080–U+2089 → <sub>n</sub>
_SUBSCRIPT = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
# Common Unicode superscripts
_SUPERSCRIPT_MAP = {"²": "2", "³": "3", "¹": "1", "⁰": "0", "⁴": "4", "⁵": "5"}


def _calc_font_size(char_count: int) -> int:
    if char_count <= 80:
        return 16
    if char_count <= 160:
        return 14
    if char_count <= 260:
        return 12
    if char_count <= 380:
        return 10
    return 9


def _format_card_text(text: str) -> str:
    """Convert raw card text to safe HTML for QLabel rich-text rendering."""
    if not text:
        return text
    import html as _html
    result = _html.escape(text)
    result = result.replace("\n", "<br>")
    for uni, digit in zip("₀₁₂₃₄₅₆₇₈₉", "0123456789"):
        result = result.replace(uni, f"<sub>{digit}</sub>")
    for uni, digit in _SUPERSCRIPT_MAP.items():
        result = result.replace(uni, f"<sup>{digit}</sup>")
    return result


class _GenerateWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, text: str, subject: str, count: int):
        super().__init__()
        self.text = text
        self.subject = subject
        self.count = count

    def run(self):
        try:
            cards = api.post(
                "/api/flashcards/generate",
                json={"text": self.text, "subject": self.subject, "count": self.count},
            )
            self.finished.emit(cards if isinstance(cards, list) else [])
        except Exception as e:
            self.error.emit(str(e))


class FlashcardWidget(QFrame):
    def __init__(self, front: str, back: str, colors: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.front = front
        self.back = back
        self.showing_front = True
        self.colors = colors
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.side_label = QLabel(t("flash.question"))
        self.side_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.side_label.setContentsMargins(0, 16, 0, 8)
        self.side_label.setStyleSheet(
            f"color: {self.colors['text_muted']}; font-size: 11px; letter-spacing: 2px; font-weight: 600;"
        )
        outer.addWidget(self.side_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.text_label = QLabel(_format_card_text(self.front))
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setContentsMargins(32, 12, 32, 12)
        self._update_font(self.front)
        scroll.setWidget(self.text_label)
        outer.addWidget(scroll, stretch=1)

        self.flip_btn = QPushButton(t("flash.flip"))
        self.flip_btn.setObjectName("secondary")
        self.flip_btn.setContentsMargins(0, 0, 0, 0)
        self.flip_btn.clicked.connect(self.flip)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 8, 0, 16)
        btn_row.addStretch()
        btn_row.addWidget(self.flip_btn)
        btn_row.addStretch()
        outer.addLayout(btn_row)

    def _update_font(self, text: str):
        size = _calc_font_size(len(text))
        self.text_label.setFont(QFont("Noto Sans", size))

    def flip(self):
        self.showing_front = not self.showing_front
        if self.showing_front:
            self.side_label.setText(t("flash.question"))
            self.text_label.setText(_format_card_text(self.front))
            self._update_font(self.front)
            self.flip_btn.setText(t("flash.flip"))
        else:
            self.side_label.setText(t("flash.answer"))
            self.text_label.setText(_format_card_text(self.back))
            self._update_font(self.back)
            self.flip_btn.setText(t("flash.flip_back"))


class FlashcardsPage(QWidget):
    def __init__(self, colors: dict = DARK, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.cards = []
        self.current_index = 0
        self._workers = []
        self._docs = []
        self._build_ui()
        self._load_documents()
        self._load_due()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(t("flash.title"))
        title.setObjectName("title")
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setObjectName("subtitle")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.progress_label)
        layout.addLayout(header)

        gen_frame = QFrame()
        gen_frame.setObjectName("card")
        gen_layout = QHBoxLayout(gen_frame)
        gen_layout.setSpacing(12)

        gen_lbl = QLabel(t("flash.gen_label"))
        gen_lbl.setStyleSheet(f"color: {self.colors['text_muted']};")
        gen_layout.addWidget(gen_lbl)

        self.doc_combo = QComboBox()
        self.doc_combo.setMinimumWidth(220)
        gen_layout.addWidget(self.doc_combo)

        count_lbl = QLabel(t("flash.cards_label"))
        count_lbl.setStyleSheet(f"color: {self.colors['text_muted']};")
        gen_layout.addWidget(count_lbl)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(3, 30)
        self.count_spin.setValue(10)
        self.count_spin.setFixedWidth(60)
        gen_layout.addWidget(self.count_spin)

        self.gen_btn = QPushButton(t("flash.gen_btn"))
        self.gen_btn.clicked.connect(self._generate_from_pdf)
        gen_layout.addWidget(self.gen_btn)

        self.gen_status = QLabel("")
        self.gen_status.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
        gen_layout.addWidget(self.gen_status)
        gen_layout.addStretch()

        layout.addWidget(gen_frame)

        subtitle = QLabel(t("flash.subtitle"))
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        self.stack = QStackedWidget()

        self.empty_widget = QLabel(t("flash.no_cards"))
        self.empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_widget.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 15px;")

        self.card_widget = QFrame()
        self.card_widget.setObjectName("card")
        self.card_widget.setMinimumHeight(280)
        self.card_layout = QVBoxLayout(self.card_widget)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.stack.addWidget(self.empty_widget)
        self.stack.addWidget(self.card_widget)
        layout.addWidget(self.stack, stretch=1)

        rating_frame = QFrame()
        rating_frame.setObjectName("card")
        rating_layout = QHBoxLayout(rating_frame)
        rating_layout.setSpacing(8)

        rating_label = QLabel(t("flash.rating_label"))
        rating_label.setStyleSheet(f"color: {self.colors['text_muted']};")
        rating_layout.addWidget(rating_label)
        rating_layout.addStretch()

        ratings = [
            (t("flash.r0"), 0, self.colors["error"]),
            (t("flash.r1"), 1, self.colors["error"]),
            (t("flash.r2"), 2, self.colors["warning"]),
            (t("flash.r3"), 3, self.colors["warning"]),
            (t("flash.r4"), 4, self.colors["success"]),
            (t("flash.r5"), 5, self.colors["success"]),
        ]

        self.rating_buttons = []
        for label, quality, color in ratings:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"background: {color}22; color: {color}; border: 1px solid {color}55;"
                "border-radius: 6px; padding: 8px 12px; font-size: 12px;"
            )
            btn.clicked.connect(lambda checked, q=quality: self._submit_rating(q))
            rating_layout.addWidget(btn)
            self.rating_buttons.append(btn)

        layout.addWidget(rating_frame)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton(t("flash.prev"))
        self.prev_btn.setObjectName("secondary")
        self.prev_btn.clicked.connect(self._prev)
        self.next_btn = QPushButton(t("flash.next"))
        self.next_btn.setObjectName("secondary")
        self.next_btn.clicked.connect(self._next)
        reload_btn = QPushButton(t("flash.reload"))
        reload_btn.setObjectName("secondary")
        reload_btn.clicked.connect(self._load_due)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(reload_btn)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)

    def _load_documents(self):
        try:
            self._docs = api.get("/api/pdf/documents")
            self.doc_combo.clear()
            analyzed = [d for d in self._docs if d.get("analyzed")]
            if not analyzed:
                self.doc_combo.addItem(t("flash.no_docs"), None)
                self.gen_btn.setEnabled(False)
            else:
                self.gen_btn.setEnabled(True)
                for d in analyzed:
                    label = f"{d['filename']} ({d.get('subject', '?')})"
                    self.doc_combo.addItem(label, d["id"])
        except Exception:
            self.doc_combo.addItem(t("flash.load_err"), None)

    def _generate_from_pdf(self):
        doc_id = self.doc_combo.currentData()
        if doc_id is None:
            QMessageBox.warning(self, t("flash.title"), t("flash.select_doc"))
            return

        self.gen_btn.setEnabled(False)
        self.gen_status.setText(t("flash.generating"))

        try:
            analysis = api.get(f"/api/pdf/analyze/{doc_id}")
        except Exception as e:
            self.gen_btn.setEnabled(True)
            self.gen_status.setText("")
            QMessageBox.critical(self, t("flash.ai_err"), str(e))
            return

        questions = analysis.get("questions", [])
        subject = analysis.get("subject", "e pergjithshme")

        if not questions:
            self.gen_btn.setEnabled(True)
            self.gen_status.setText("")
            QMessageBox.information(self, t("flash.title"), t("flash.no_questions"))
            return

        text = "\n".join(q["text"] for q in questions)
        count = self.count_spin.value()

        worker = _GenerateWorker(text, subject, count)
        worker.finished.connect(self._on_generated)
        worker.error.connect(self._on_generate_error)
        self._workers.append(worker)
        worker.start()

    def _on_generated(self, cards: list):
        self.gen_btn.setEnabled(True)
        self.gen_status.setText(t("flash.gen_done", n=len(cards)))
        self._load_due()

    def _on_generate_error(self, msg: str):
        self.gen_btn.setEnabled(True)
        self.gen_status.setText("")
        QMessageBox.critical(self, t("flash.ai_err"), msg)

    def _load_due(self):
        try:
            self.cards = api.get("/api/flashcards/due")
            self.current_index = 0
            self._show_current()
        except Exception:
            self.stack.setCurrentWidget(self.empty_widget)

    def _show_current(self):
        if not self.cards:
            self.stack.setCurrentWidget(self.empty_widget)
            self.progress_label.setText("0 / 0")
            return

        card = self.cards[self.current_index]
        for i in reversed(range(self.card_layout.count())):
            self.card_layout.itemAt(i).widget().deleteLater()

        fw = FlashcardWidget(card["front"], card["back"], self.colors)
        self.card_layout.addWidget(fw)
        self.stack.setCurrentWidget(self.card_widget)
        self.progress_label.setText(f"{self.current_index + 1} / {len(self.cards)}")

    def _prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._show_current()

    def _next(self):
        if self.current_index < len(self.cards) - 1:
            self.current_index += 1
            self._show_current()

    def _submit_rating(self, quality: int):
        if not self.cards:
            return
        card = self.cards[self.current_index]
        try:
            api.put(f"/api/flashcards/{card['id']}/review", json={"quality": quality})
            self.cards.pop(self.current_index)
            if self.current_index >= len(self.cards):
                self.current_index = max(0, len(self.cards) - 1)
            self._show_current()
        except Exception as e:
            QMessageBox.warning(self, t("flash.ai_err"), str(e))
