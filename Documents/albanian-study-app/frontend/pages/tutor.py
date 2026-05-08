from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QTextEdit, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import frontend.api_client as api
from frontend.theme import DARK
from frontend.i18n import t


class TutorWorker(QThread):
    reply_received = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, message: str, subject: str, conversation_id: int | None):
        super().__init__()
        self.message = message
        self.subject = subject
        self.conversation_id = conversation_id

    def run(self):
        try:
            result = api.post("/api/tutor/chat", json={
                "content": self.message,
                "subject": self.subject,
                "conversation_id": self.conversation_id,
            })
            self.reply_received.emit(result.get("reply", ""))
        except Exception as e:
            self.error.emit(str(e))


class MessageBubble(QFrame):
    def __init__(self, text: str, is_user: bool, colors: dict, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", 13))
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_user:
            self.setStyleSheet(
                f"background: {colors['accent']}33; border-radius: 12px; "
                f"border-bottom-right-radius: 2px;"
            )
            label.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            self.setStyleSheet(
                f"background: {colors['surface']}; border-radius: 12px; "
                f"border: 1px solid {colors['border']}; border-bottom-left-radius: 2px;"
            )
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(label)


class TutorPage(QWidget):
    def __init__(self, colors: dict = DARK, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.conversation_id = None
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel(t("tutor.title"))
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel(t("tutor.subject")))
        self.subject_combo = QComboBox()
        self.subject_combo.addItems(["matematike", "shqipe"])
        self.subject_combo.setFixedWidth(140)
        header.addWidget(self.subject_combo)

        new_btn = QPushButton(t("tutor.new_conv"))
        new_btn.setObjectName("secondary")
        new_btn.clicked.connect(self._new_conversation)
        header.addWidget(new_btn)
        layout.addLayout(header)

        subtitle = QLabel(t("tutor.subtitle"))
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setSpacing(8)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.addStretch()

        self.scroll.setWidget(self.messages_widget)
        layout.addWidget(self.scroll, stretch=1)

        input_frame = QFrame()
        input_frame.setStyleSheet(
            f"background: {self.colors['surface']}; border-top: 1px solid {self.colors['border']};"
        )
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 12, 0, 12)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText(t("tutor.placeholder"))
        self.input_box.setMaximumHeight(100)
        self.input_box.setFont(QFont("Segoe UI", 13))

        self.send_btn = QPushButton(t("tutor.send"))
        self.send_btn.setFixedWidth(90)
        self.send_btn.setFixedHeight(40)
        self.send_btn.clicked.connect(self._send)

        input_layout.addWidget(self.input_box)
        input_layout.addWidget(self.send_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(input_frame)

        self._add_message(t("tutor.greeting"), is_user=False)

    def _add_message(self, text: str, is_user: bool):
        bubble = MessageBubble(text, is_user, self.colors)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def _send(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
        self.input_box.clear()
        self._add_message(text, is_user=True)
        self.send_btn.setEnabled(False)
        self.send_btn.setText("...")

        self._worker = TutorWorker(text, self.subject_combo.currentText(), self.conversation_id)
        self._worker.reply_received.connect(self._on_reply)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_reply(self, reply: str):
        self.send_btn.setEnabled(True)
        self.send_btn.setText(t("tutor.send"))
        self._add_message(reply, is_user=False)

    def _on_error(self, msg: str):
        self.send_btn.setEnabled(True)
        self.send_btn.setText(t("tutor.send"))
        self._add_message(t("tutor.err", msg=msg), is_user=False)

    def _new_conversation(self):
        self.conversation_id = None
        for i in reversed(range(self.messages_layout.count() - 1)):
            w = self.messages_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._add_message(t("tutor.new_msg"), is_user=False)
