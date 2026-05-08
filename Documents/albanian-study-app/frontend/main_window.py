from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QPushButton, QLabel, QStackedWidget, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from frontend.theme import DARK, stylesheet
from frontend.i18n import t, get_lang, set_lang
from frontend.pages.dashboard import DashboardPage
from frontend.pages.upload import UploadPage
from frontend.pages.flashcards import FlashcardsPage
from frontend.pages.quiz import QuizPage
from frontend.pages.tutor import TutorPage
from frontend.pages.analytics import AnalyticsPage

_NAV_KEYS = [
    ("nav.home", DashboardPage),
    ("nav.upload", UploadPage),
    ("nav.flashcards", FlashcardsPage),
    ("nav.quiz", QuizPage),
    ("nav.tutor", TutorPage),
    ("nav.analytics", AnalyticsPage),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("app.title"))
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self._colors = DARK
        self._nav_buttons: list[QPushButton] = []
        self._pages: list[QWidget] = []
        self._setup_shell()
        self._build_content()
        self._apply_theme()

    def _setup_shell(self):
        root = QWidget()
        self.setCentralWidget(root)
        self._root_layout = QHBoxLayout(root)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self._sidebar = QFrame()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(220)
        self._sidebar_layout = QVBoxLayout(self._sidebar)
        self._sidebar_layout.setContentsMargins(12, 24, 12, 24)
        self._sidebar_layout.setSpacing(4)

        self.stack = QStackedWidget()

        self._root_layout.addWidget(self._sidebar)
        self._root_layout.addWidget(self.stack, stretch=1)

    def _build_content(self):
        # Clear sidebar
        while self._sidebar_layout.count():
            item = self._sidebar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear stack
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        self._nav_buttons = []
        self._pages = []

        brand = QLabel(t("app.name"))
        brand.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        brand.setContentsMargins(8, 0, 0, 16)
        self._sidebar_layout.addWidget(brand)

        for key, PageClass in _NAV_KEYS:
            page = PageClass(colors=self._colors)
            self.stack.addWidget(page)
            self._pages.append(page)

            btn = QPushButton(t(key))
            btn.setObjectName("nav_btn")
            btn.clicked.connect(lambda checked, idx=len(self._nav_buttons): self._navigate(idx))
            self._sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        self._sidebar_layout.addStretch()

        lang_btn = QPushButton(t("lang.switch"))
        lang_btn.setObjectName("secondary")
        lang_btn.clicked.connect(self._toggle_lang)
        self._sidebar_layout.addWidget(lang_btn)

        self._navigate(0)

    def _navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", str(i == index).lower())
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _toggle_lang(self):
        set_lang("en" if get_lang() == "sq" else "sq")
        self.setWindowTitle(t("app.title"))
        self._build_content()

    def _apply_theme(self):
        QApplication.instance().setStyleSheet(stylesheet(self._colors))
