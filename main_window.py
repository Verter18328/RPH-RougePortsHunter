from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtUiTools import QUiLoader

from globals import Globals
from signals import MainWindowSignals


class MainWindow(QMainWindow):
    """Główne okno aplikacji."""

    def __init__(self) -> None:
        super().__init__()
        loader = QUiLoader()
        self.ui = loader.load(Globals.MAIN_WINDOW_PATH)

        try:
            qss_path = Globals.THEME_PATH
            if qss_path.is_file():
                self.ui.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except OSError:
            # W razie problemu z odczytem stylu aplikacja nadal działa na
            # domyślnym wyglądzie.
            pass

        self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)
        # Trzymamy referencję, aby obiekt z połączeniami sygnałów
        # nie został zwolniony przez GC.
        self.signals = MainWindowSignals(self.ui)

    def show_window(self) -> None:
        """Pokazuje okno główne aplikacji."""
        self.ui.show()


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show_window()
    app.exec()
