from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import frontend.api_client as api
from frontend.theme import DARK
from frontend.i18n import t


class StatCard(QFrame):
    def __init__(self, label: str, value: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName("subtitle")
        val = QLabel(value)
        val.setObjectName("stat_value")
        val.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 700;")

        layout.addWidget(lbl)
        layout.addWidget(val)
        self.value_label = val

    def update_value(self, value: str):
        self.value_label.setText(value)


class DashboardPage(QWidget):
    def __init__(self, colors: dict = DARK, parent=None):
        super().__init__(parent)
        self.colors = colors
        self._build_ui()
        self._load_data()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load_data)
        self._timer.start(30000)

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        title = QLabel(t("dash.title"))
        title.setObjectName("title")
        subtitle = QLabel(t("dash.subtitle"))
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(16)

        self.xp_card = StatCard(t("dash.xp"), "0", self.colors["accent"])
        self.level_card = StatCard(t("dash.level"), "1", self.colors["success"])
        self.streak_card = StatCard(t("dash.streak"), "0", self.colors["warning"])
        self.flashcard_card = StatCard(t("dash.due"), "0", self.colors["accent2"])

        grid.addWidget(self.xp_card, 0, 0)
        grid.addWidget(self.level_card, 0, 1)
        grid.addWidget(self.streak_card, 0, 2)
        grid.addWidget(self.flashcard_card, 0, 3)
        layout.addLayout(grid)

        recent_label = QLabel(t("dash.recent"))
        recent_label.setObjectName("title")
        recent_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(recent_label)

        self.recent_frame = QFrame()
        self.recent_frame.setObjectName("card")
        self.recent_layout = QVBoxLayout(self.recent_frame)
        layout.addWidget(self.recent_frame)

        badges_label = QLabel(t("dash.badges"))
        badges_label.setObjectName("title")
        badges_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(badges_label)

        self.badges_frame = QFrame()
        self.badges_frame.setObjectName("card")
        self.badges_layout = QHBoxLayout(self.badges_frame)
        self.badges_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.badges_frame)
        layout.addStretch()

    def _load_data(self):
        try:
            data = api.get("/api/analytics/dashboard")
            self.xp_card.update_value(str(data.get("xp", 0)))
            self.level_card.update_value(str(data.get("level", 1)))
            self.streak_card.update_value(str(data.get("streak_days", 0)))
            self.flashcard_card.update_value(str(data.get("due_flashcards", 0)))

            for i in reversed(range(self.recent_layout.count())):
                self.recent_layout.itemAt(i).widget().deleteLater()

            quizzes = data.get("recent_quizzes", [])
            if not quizzes:
                self.recent_layout.addWidget(QLabel(t("dash.no_quizzes")))
            for q in quizzes:
                row = QLabel(
                    f"{q.get('subject', '')}: {q.get('score', 0)}%"
                    f"  —  {q.get('created_at', '')[:10]}"
                )
                self.recent_layout.addWidget(row)

            for i in reversed(range(self.badges_layout.count())):
                w = self.badges_layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

            badge_keys = {
                "para_hapa": "badge.para_hapa",
                "kuizmast": "badge.kuizmast",
                "perseverance": "badge.perseverance",
                "lexues": "badge.lexues",
            }
            badges = data.get("badges", [])
            if not badges:
                self.badges_layout.addWidget(QLabel(t("dash.no_badges")))
            for b in badges:
                lbl = QLabel(t(badge_keys.get(b, b)))
                lbl.setStyleSheet(
                    f"background:{self.colors['accent']}22; color:{self.colors['accent']};"
                    "border-radius:8px; padding:6px 12px; font-weight:600;"
                )
                self.badges_layout.addWidget(lbl)
        except Exception:
            pass
