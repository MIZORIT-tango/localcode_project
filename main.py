import sys
from PyQt6.QtWidgets import QApplication

from src.view import MainWindow

# ================= MAIN =================
def main():
    app = QApplication(sys.argv)

    app.setStyle('Fusion')
    app.setStyleSheet("""
        QToolTip {
            background-color: #16213e;
            color: #ffffff;
            border: 1px solid #0f3460;
            padding: 5px;
            font-size: 12px;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()