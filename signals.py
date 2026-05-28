from ipaddress import IPv4Address
import pathlib

from PySide6.QtCore import Qt, QObject, QTimer, Signal, QThread, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
)

from business_logic import RoguePortsHunter
from globals import Globals
from ssh_data_retriever import OutputData
from ui_fetch_feedback import FetchProgressController, FetchingDotsAnimator


class FetchWorker(QObject):
    """Worker uruchamiany w tle, pobierający dane SSH dla listy hostów."""

    progress = Signal(int)
    finished = Signal(object)  # list[OutputData]
    failed = Signal(str)

    @Slot()
    def run(self) -> None:
        try:
            hunter = RoguePortsHunter()

            def on_progress(
                    completed: int,
                    total: int,
                    host: IPv4Address) -> None:
                percent = int((completed / total) * 100) if total else 0
                self.progress.emit(percent)
                print(f"Fetching data from {host} ... {percent}%")

            output_data = hunter.fetch_non_netlogin_ports(
                Globals.devices, on_progress=on_progress
            )
            self.finished.emit(output_data)
        except Exception as e:
            self.failed.emit(str(e))


class MainWindowSignals(QObject):
    """Sygnały dla głównego okna aplikacji."""

    def __init__(self, ui: QMainWindow):
        super().__init__(ui)
        self.ui = ui
        self._thread: QThread | None = None
        self._worker: FetchWorker | None = None
        self._is_fetching = False
        self._progress_controller = FetchProgressController(
            self.ui.progressBar, self)
        self._dots_animator = FetchingDotsAnimator(self.ui.label_6, self)
        self.connect_signals()

    def connect_signals(self) -> None:
        """Podłącza sygnały UI do obsługi przepływu ekranu."""
        self.ui.huntButton.clicked.connect(self.hunt_ports)
        self.ui.loginButton.clicked.connect(self.loginClicked)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.ui)
        esc_shortcut.activated.connect(self.go_home)

    def _start_fetch_feedback(self) -> None:
        self._progress_controller.start(len(Globals.devices))
        self._dots_animator.start()

    def _stop_fetch_feedback(self) -> None:
        """Wywoływane przy zakończeniu QThread.

        Pasek postępu jest celowo POMIJANY, żeby nie zerwać animacji
        domknięcia 0→100% rozpoczętej w on_fetch_finished. Reset paska
        do 0% wykonują: on_fetch_failed, go_home oraz start() przy
        następnym fetchu.
        """
        self._dots_animator.stop()

    def go_home(self) -> None:
        if self.ui.stackedWidget.currentWidget() == self.ui.homePage:
            return
        if self._is_fetching or (
                self._thread is not None and self._thread.isRunning()):
            return
        self._dots_animator.stop()
        self._progress_controller.stop()
        self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)

    def hunt_ports(self) -> None:
        """Wczytuje inventory i przechodzi do ekranu logowania."""
        self.ui.stackedWidget.setCurrentWidget(self.ui.waitingForFilePage)
        Globals.devices = RoguePortsHunter().get_all_devices()
        if not Globals.devices:
            QMessageBox.warning(self.ui, "Warning", "No devices found")
            self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)
            return
        self.ui.stackedWidget.setCurrentWidget(self.ui.loginPage)
        self.ui.usernameInput.setFocus()

    def loginClicked(self) -> None:
        """Waliduje login i uruchamia pobieranie danych z hostów."""
        if self._is_fetching or (
                self._thread is not None and self._thread.isRunning()):
            QMessageBox.information(
                self.ui, "Info", "Fetching is already in progress.")
            return
        Globals.global_username = self.ui.usernameInput.text()
        Globals.global_password = self.ui.passwordInput.text()
        if Globals.global_username == "":
            QMessageBox.warning(self.ui, "Warning", "Username is required")
            self.ui.usernameInput.clear()
            self.ui.passwordInput.clear()
            self.ui.usernameInput.setFocus()
            return
        self.ui.stackedWidget.setCurrentWidget(self.ui.fetchingPage)
        self.fetchingPage_entered()

    def fetchingPage_entered(self) -> None:
        self._start_fetch_feedback()
        self.start_fetch_thread()

    def start_fetch_thread(self) -> None:
        """Tworzy QThread + worker i uruchamia przetwarzanie w tle."""
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(
                self.ui, "Info", "Fetching is already running.")
            return

        self._thread = QThread()
        self._worker = FetchWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(
            self._progress_controller.set_target,
            Qt.ConnectionType.QueuedConnection,
        )

        self._worker.finished.connect(
            self.on_fetch_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        self._worker.failed.connect(
            self.on_fetch_failed,
            Qt.ConnectionType.QueuedConnection,
        )

        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)

        self._is_fetching = True
        self._thread.start()

    @Slot()
    def _on_thread_finished(self) -> None:
        """Clear Python refs only after QThread has fully stopped."""
        self._is_fetching = False
        self._stop_fetch_feedback()
        self._thread = None
        self._worker = None

    @Slot(object)
    def on_fetch_finished(self, output_data: object) -> None:
        # Animowane domknięcie paska 0→100% przed nawigacją do resultsPage.
        # Nawigacja jest opóźniona o czas trwania animacji, żeby użytkownik
        # zdążył ją zobaczyć (efekt 'zakończenia z sukcesem').
        self._progress_controller.complete()
        QTimer.singleShot(
            self._progress_controller.completion_delay_ms(),
            lambda: self._finalize_fetch_success(output_data),
        )

    def _finalize_fetch_success(self, output_data: object) -> None:
        try:
            if not isinstance(output_data, list):
                raise TypeError("Unexpected fetch result format.")

            normalized_output: list[OutputData] = [
                item for item in output_data if isinstance(item, OutputData)
            ]

            if not normalized_output:
                QMessageBox.warning(self.ui, "Warning", "No output data found")
                self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)
                return

            export_path = RoguePortsHunter().export_results(normalized_output)
            self.ui.stackedWidget.setCurrentWidget(self.ui.resultsPage)
            self.resultsPage_entered(normalized_output, export_path)
        except Exception as e:
            QMessageBox.critical(
                self.ui, "Error", f"Failed to process fetch results: {e}")
            self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)

    @Slot(str)
    def on_fetch_failed(self, error: str) -> None:
        self._progress_controller.stop()
        QMessageBox.warning(self.ui, "Warning",
                            f"Failed to fetch data: {error}")
        self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)

    def resultsPage_entered(
        self, output_data: list[OutputData], path: pathlib.Path | None
    ) -> None:
        """Wypełnia tabelę wyników i komunikuje status zapisu CSV."""
        try:
            self.ui.tableWidget.setRowCount(0)
            self.ui.tableWidget.setColumnCount(2)
            self.ui.tableWidget.setHorizontalHeaderLabels(["Host", "Port"])
            self.ui.tableWidget.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Stretch
            )
            self.ui.tableWidget.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeMode.Stretch
            )
            i = 0
            for data in output_data:
                for port in data.ports:
                    self.ui.tableWidget.insertRow(i)
                    self.ui.tableWidget.setItem(
                        i, 0, QTableWidgetItem(str(data.host)))
                    self.ui.tableWidget.setItem(i, 1, QTableWidgetItem(port))
                    self.ui.tableWidget.item(i, 0).setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter)
                    self.ui.tableWidget.item(i, 1).setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter)
                    i += 1

            if path is not None:
                QMessageBox.information(
                    self.ui, "Info", f"Results exported to {path}"
                )
            else:
                QMessageBox.warning(
                    self.ui,
                    "Warning",
                    (
                        "Could not save CSV file. "
                        "Results are shown in the table only."
                    ),
                )
        except Exception as e:
            QMessageBox.critical(
                self.ui, "Error", f"Failed to render results table: {e}")
            self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)
