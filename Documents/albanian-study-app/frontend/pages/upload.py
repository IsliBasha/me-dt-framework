from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QProgressBar, QListWidget,
    QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import frontend.api_client as api
from frontend.theme import DARK
from frontend.i18n import t


class UploadWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            with open(self.file_path, "rb") as f:
                result = api.post(
                    "/api/pdf/upload",
                    files={"file": (self.file_path.split("/")[-1], f, "application/pdf")},
                )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class UploadPage(QWidget):
    def __init__(self, colors: dict = DARK, parent=None):
        super().__init__(parent)
        self.colors = colors
        self._workers = []
        self._build_ui()
        self._load_documents()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        title = QLabel(t("upload.title"))
        title.setObjectName("title")
        subtitle = QLabel(t("upload.subtitle"))
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        upload_frame = QFrame()
        upload_frame.setObjectName("card")
        upload_frame.setMinimumHeight(160)
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        drop_label = QLabel(t("upload.click"))
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 16px;")

        self.upload_btn = QPushButton(t("upload.btn"))
        self.upload_btn.setFixedWidth(160)
        self.upload_btn.clicked.connect(self._pick_file)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)

        upload_layout.addWidget(drop_label)
        upload_layout.addSpacing(12)
        upload_layout.addWidget(self.upload_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        upload_layout.addWidget(self.progress)
        layout.addWidget(upload_frame)

        docs_label = QLabel(t("upload.docs"))
        docs_label.setObjectName("title")
        layout.addWidget(docs_label)

        self.docs_list = QListWidget()
        layout.addWidget(self.docs_list)

        refresh_btn = QPushButton(t("upload.refresh"))
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self._load_documents)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t("upload.btn"), "", "PDF Files (*.pdf)"
        )
        if path:
            self._upload(path)

    def _upload(self, path: str):
        self.upload_btn.setEnabled(False)
        self.progress.setVisible(True)
        worker = UploadWorker(path)
        worker.finished.connect(self._on_upload_done)
        worker.error.connect(self._on_upload_error)
        self._workers.append(worker)
        worker.start()

    def _on_upload_done(self, result: dict):
        self.upload_btn.setEnabled(True)
        self.progress.setVisible(False)
        QMessageBox.information(
            self,
            t("upload.success"),
            t("upload.ok_msg", name=result.get("filename", "")),
        )
        self._load_documents()

    def _on_upload_error(self, msg: str):
        self.upload_btn.setEnabled(True)
        self.progress.setVisible(False)
        QMessageBox.critical(self, t("upload.error"), t("upload.err_msg", msg=msg))

    def _load_documents(self):
        self.docs_list.clear()
        try:
            docs = api.get("/api/pdf/documents")
            for d in docs:
                status = "[OK]" if d.get("analyzed") else "[...]"
                text = (
                    f"{status}  {d.get('filename')}  "
                    f"| {d.get('subject', '-')}  "
                    f"| {d.get('page_count', 0)} faqe  "
                    f"| {d.get('created_at', '')[:10]}"
                )
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, d.get("id"))
                self.docs_list.addItem(item)
        except Exception:
            self.docs_list.addItem(t("upload.err_load"))
