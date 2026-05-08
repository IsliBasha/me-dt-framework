import sys
import time
import threading
import uvicorn
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt
from config import settings
from backend.app import app as fastapi_app


def _start_backend():
    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=settings.app_port,
        log_level="error",
    )


def _wait_for_backend(timeout: int = 12) -> bool:
    import httpx
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://127.0.0.1:{settings.app_port}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def main():
    backend_thread = threading.Thread(target=_start_backend, daemon=True)
    backend_thread.start()

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("StudimiAI")
    qt_app.setOrganizationName("StudimiShqiptar")

    splash_pix = Qt.GlobalColor.darkBlue
    splash = QSplashScreen()
    splash.showMessage(
        "📚  StudimiAI — Duke u nisur...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
    )
    splash.show()
    qt_app.processEvents()

    ready = _wait_for_backend(timeout=12)
    if not ready:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Gabim",
            "Backend nuk u nis brenda 12 sekondave.\nKontrollo nëse porta është e lirë.",
        )
        sys.exit(1)

    from frontend.main_window import MainWindow
    window = MainWindow()
    splash.finish(window)
    window.show()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
