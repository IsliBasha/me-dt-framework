from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import frontend.api_client as api
from frontend.theme import DARK
from frontend.i18n import t


class AnalyticsPage(QWidget):
    def __init__(self, colors: dict = DARK, parent=None):
        super().__init__(parent)
        self.colors = colors
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        self.layout_ = QVBoxLayout(container)
        self.layout_.setContentsMargins(32, 32, 32, 32)
        self.layout_.setSpacing(24)

        header = QHBoxLayout()
        title = QLabel(t("analytics.title"))
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        refresh_btn = QPushButton(t("analytics.refresh"))
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self._load_data)
        header.addWidget(refresh_btn)
        self.layout_.addLayout(header)

        subtitle = QLabel(t("analytics.subtitle"))
        subtitle.setObjectName("subtitle")
        self.layout_.addWidget(subtitle)

        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("card")
        self.stats_layout = QVBoxLayout(self.stats_frame)
        self.layout_.addWidget(self.stats_frame)

        heatmap_title = QLabel(t("analytics.heatmap"))
        heatmap_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.layout_.addWidget(heatmap_title)

        self.heatmap_frame = QFrame()
        self.heatmap_frame.setObjectName("card")
        self.heatmap_layout = QVBoxLayout(self.heatmap_frame)
        self.layout_.addWidget(self.heatmap_frame)
        self.layout_.addStretch()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_data(self):
        self._clear_layout(self.stats_layout)
        self._clear_layout(self.heatmap_layout)
        try:
            data = api.get("/api/analytics/dashboard")
            self._render_stats(data)
        except Exception:
            self.stats_layout.addWidget(QLabel(t("analytics.err_stats")))

        try:
            heatmap = api.get("/api/analytics/heatmap")
            self._render_heatmap(heatmap)
        except Exception:
            self.heatmap_layout.addWidget(QLabel(t("analytics.err_heatmap")))

    def _render_stats(self, data: dict):
        xp = data.get("xp", 0)
        level = data.get("level", 1)
        streak = data.get("streak_days", 0)
        avg_score = data.get("avg_quiz_score", 0)
        due = data.get("due_flashcards", 0)

        rows = [
            (t("analytics.xp"), str(xp), self.colors["accent"]),
            (t("analytics.level"), str(level), self.colors["success"]),
            (t("analytics.streak"), t("analytics.streak_val", n=streak), self.colors["warning"]),
            (t("analytics.avg"), f"{avg_score}%", self.colors["accent2"]),
            (t("analytics.due"), str(due), self.colors["text_muted"]),
        ]

        for label, value, color in rows:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {self.colors['text_muted']};")
            val = QLabel(value)
            val.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 16px;")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            self.stats_layout.addLayout(row)

        next_level_xp = [0, 100, 250, 500, 1000, 2000, 4000, 8000, 15000, 30000]
        if level < len(next_level_xp):
            current_threshold = next_level_xp[level - 1] if level > 0 else 0
            next_threshold = next_level_xp[level]
            progress_val = int(((xp - current_threshold) / max(1, next_threshold - current_threshold)) * 100)
            progress_bar = QProgressBar()
            progress_bar.setValue(min(100, progress_val))
            lbl = QLabel(t("analytics.progress", n=level + 1, pct=progress_val))
            lbl.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 12px;")
            self.stats_layout.addSpacing(8)
            self.stats_layout.addWidget(lbl)
            self.stats_layout.addWidget(progress_bar)

    def _render_heatmap(self, data: dict):
        topics = data.get("topics", [])
        if not topics:
            self.heatmap_layout.addWidget(QLabel(t("analytics.no_topics")))
            return

        for item in sorted(topics, key=lambda x: x.get("avg_score", 0)):
            topic = item.get("topic", "-")
            score = item.get("avg_score", 0)
            color = (
                self.colors["success"] if score >= 70
                else self.colors["warning"] if score >= 40
                else self.colors["error"]
            )
            row = QHBoxLayout()
            lbl = QLabel(topic.capitalize())
            bar = QProgressBar()
            bar.setValue(int(score))
            bar.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {color}; }}"
            )
            bar.setFixedWidth(200)
            score_lbl = QLabel(f"{score}%")
            score_lbl.setStyleSheet(f"color: {color}; font-weight: 600; min-width: 48px;")
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(bar)
            row.addWidget(score_lbl)
            self.heatmap_layout.addLayout(row)
