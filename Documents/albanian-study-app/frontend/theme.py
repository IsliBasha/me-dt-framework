DARK = {
    "bg": "#0f1117",
    "surface": "#1a1d27",
    "surface2": "#22263a",
    "accent": "#6c63ff",
    "accent2": "#ff6584",
    "success": "#43e97b",
    "warning": "#f9a825",
    "error": "#ef5350",
    "text": "#e8eaf6",
    "text_muted": "#7986cb",
    "border": "#2e3150",
}

LIGHT = {
    "bg": "#f5f6fa",
    "surface": "#ffffff",
    "surface2": "#eef0fb",
    "accent": "#6c63ff",
    "accent2": "#ff6584",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "error": "#e74c3c",
    "text": "#1a1d27",
    "text_muted": "#5c6bc0",
    "border": "#dde1f5",
}


def stylesheet(colors: dict) -> str:
    c = colors
    return f"""
    QMainWindow, QDialog {{
        background-color: {c['bg']};
    }}
    QWidget {{
        background-color: {c['bg']};
        color: {c['text']};
        font-family: 'Segoe UI', 'Ubuntu', sans-serif;
        font-size: 14px;
    }}
    QFrame#sidebar {{
        background-color: {c['surface']};
        border-right: 1px solid {c['border']};
    }}
    QPushButton {{
        background-color: {c['accent']};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: {c['accent']}cc;
    }}
    QPushButton:pressed {{
        background-color: {c['accent']}aa;
    }}
    QPushButton#secondary {{
        background-color: {c['surface2']};
        color: {c['text']};
        border: 1px solid {c['border']};
    }}
    QPushButton#secondary:hover {{
        background-color: {c['border']};
    }}
    QPushButton#nav_btn {{
        background-color: transparent;
        color: {c['text_muted']};
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
    }}
    QPushButton#nav_btn:hover {{
        background-color: {c['surface2']};
        color: {c['text']};
    }}
    QPushButton#nav_btn[active=true] {{
        background-color: {c['accent']}22;
        color: {c['accent']};
        border-left: 3px solid {c['accent']};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {c['surface2']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border: 1px solid {c['accent']};
    }}
    QComboBox {{
        background-color: {c['surface2']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 8px 12px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QScrollBar:vertical {{
        background: {c['surface']};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 4px;
        min-height: 20px;
    }}
    QLabel#title {{
        font-size: 22px;
        font-weight: 700;
        color: {c['text']};
    }}
    QLabel#subtitle {{
        font-size: 13px;
        color: {c['text_muted']};
    }}
    QLabel#stat_value {{
        font-size: 28px;
        font-weight: 700;
        color: {c['accent']};
    }}
    QFrame#card {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 16px;
    }}
    QProgressBar {{
        background-color: {c['surface2']};
        border: none;
        border-radius: 6px;
        height: 10px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
        border-radius: 6px;
    }}
    QListWidget {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 10px;
        border-radius: 6px;
    }}
    QListWidget::item:hover {{
        background-color: {c['surface2']};
    }}
    QListWidget::item:selected {{
        background-color: {c['accent']}33;
        color: {c['accent']};
    }}
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        background-color: {c['surface']};
    }}
    QTabBar::tab {{
        background-color: {c['surface2']};
        color: {c['text_muted']};
        padding: 10px 20px;
        border-radius: 6px 6px 0 0;
        margin-right: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {c['accent']};
        color: white;
    }}
    """
