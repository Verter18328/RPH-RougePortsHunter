import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
from PySide6.QtUiTools import QUiLoader

from globals import Globals
from signals import MainWindowSignals


def _set_windows_app_user_model_id(app_id: str) -> None:
    """Pozwala Windowsowi traktować proces jako osobną aplikację, dzięki
    czemu w pasku zadań pokazuje się ustawiona ikona okna, a nie ikona
    interpretera Pythona. Bez tego wywołania `setWindowIcon` nie ma efektu
    na pasku zadań Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (OSError, AttributeError):
        # Brak shell32 lub starsze Windows - aplikacja dalej działa,
        # po prostu ikona w pasku zadań może być generyczna.
        pass


class MainWindow(QMainWindow):
    """Główne okno aplikacji."""

    def __init__(self) -> None:
        super().__init__()
        loader = QUiLoader()
        self.ui = loader.load(Globals.MAIN_WINDOW_PATH)

        self.ui.setWindowIcon(QIcon(str(Globals.LOGO_PATH)))
        self._apply_page_logos()

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

    def _apply_page_logos(self) -> None:
        """Wstawia logo na wszystkich ekranach aplikacji.

        Strona startowa dostaje większe logo (akcent wizualny),
        a pozostałe strony spójny, mniejszy rozmiar — tu logo
        ma być sygnaturą marki, nie dominować nad zawartością.
        """
        source = QPixmap(str(Globals.LOGO_PATH))
        if source.isNull():
            return

        placements: list[tuple[str, int]] = [
            ("homeLogo", 128),
            ("waitingLogo", 64),
            ("loginLogo", 64),
            ("fetchingLogo", 64),
            ("resultsLogo", 56),
        ]

        for object_name, logical_height_px in placements:
            label = self.ui.findChild(QLabel, object_name)
            if label is None:
                # Brak labelki w UI - cicho pomijamy, żeby brak jednego
                # widgetu nie blokował wyświetlenia pozostałych.
                continue
            self._set_dpi_aware_pixmap(label, source, logical_height_px)

    def _set_dpi_aware_pixmap(
        self,
        label: "QLabel",
        source: QPixmap,
        logical_height_px: int,
    ) -> None:
        """Skaluje pixmapę do fizycznych pikseli wynikających z DPI ekranu
        i ustawia `devicePixelRatio`, dzięki czemu Qt nie upscale'uje
        obrazka po raz drugi (ostre krawędzie przy skalowaniu 125%/150%)."""
        dpr = label.devicePixelRatioF()
        device_height = int(round(logical_height_px * dpr))
        scaled = source.scaledToHeight(device_height, Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)
        label.setPixmap(scaled)

    def show_window(self) -> None:
        """Pokazuje okno główne aplikacji."""
        self.ui.show()


if __name__ == "__main__":
    _set_windows_app_user_model_id("RoguePortsHunter.App")
    app = QApplication([])
    app.setWindowIcon(QIcon(str(Globals.LOGO_PATH)))
    window = MainWindow()
    window.show_window()
    app.exec()
