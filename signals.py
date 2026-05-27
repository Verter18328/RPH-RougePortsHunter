from ipaddress import IPv4Address
import pathlib

from PySide6.QtCore import Qt, QObject, Signal, QThread, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QMessageBox, QTableWidgetItem, QHeaderView

from business_logic import RougePortsHunter
from globals import Globals
from ssh_data_retriever import OutputData


class FetchWorker(QObject):
    progress = Signal(int)
    finished = Signal(object)  # list[OutputData]
    failed = Signal(str)

    @Slot()
    def run(self) -> None:
        try:
            hunter = RougePortsHunter()

            def on_progress(idx: int, total: int, host: IPv4Address) -> None:
                percent = int((idx / total) * 100) if total else 0
                self.progress.emit(percent)
                print(f"Fetching data from {host} ... {percent}%")

            output_data = hunter.fetch_non_netlogin_ports(
                Globals.devices, on_progress=on_progress
            )
            self.finished.emit(output_data)
        except Exception as e:
            self.failed.emit(str(e))


class MainWindowSignals(QObject):
    """Sygnały dla głównego okna aplikacji (musi być QObject dla queued cross-thread slots)."""

    def __init__(self, ui: QMainWindow):
        super().__init__(ui)
        self.ui = ui
        self._thread: QThread | None = None
        self._worker: FetchWorker | None = None
        self._is_fetching = False
        self.connect_signals()

    def connect_signals(self) -> None:
        self.ui.huntButton.clicked.connect(self.hunt_ports)
        self.ui.loginButton.clicked.connect(self.loginClicked)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.ui)
        esc_shortcut.activated.connect(self.go_home)

    def go_home(self) -> None:
        if self.ui.stackedWidget.currentWidget() == self.ui.homePage:
            return
        if self._is_fetching or (self._thread is not None and self._thread.isRunning()):
            return
        self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)

    def hunt_ports(self) -> None:
        self.ui.stackedWidget.setCurrentWidget(self.ui.waitingForFilePage)
        Globals.devices = RougePortsHunter().get_all_devices()
        if not Globals.devices:
            QMessageBox.warning(self.ui, "Warning", "No devices found")
            self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)
            return
        self.ui.stackedWidget.setCurrentWidget(self.ui.loginPage)
        self.ui.usernameInput.setFocus()

    def loginClicked(self) -> None:
        if self._is_fetching or (self._thread is not None and self._thread.isRunning()):
            QMessageBox.information(self.ui, "Info", "Fetching is already in progress.")
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
        self.ui.progressBar.setRange(0, 100)
        self.ui.progressBar.setValue(0)
        self.start_fetch_thread()

    def start_fetch_thread(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            QMessageBox.information(self.ui, "Info", "Fetching is already running.")
            return

        self._thread = QThread()
        self._worker = FetchWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(
            self.ui.progressBar.setValue,
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
        self._thread = None
        self._worker = None

    @Slot(object)
    def on_fetch_finished(self, output_data: object) -> None:
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

            export_path = RougePortsHunter().export_results(normalized_output)
            self.ui.stackedWidget.setCurrentWidget(self.ui.resultsPage)
            self.resultsPage_entered(normalized_output, export_path)
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"Failed to process fetch results: {e}")
            self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)

    @Slot(str)
    def on_fetch_failed(self, error: str) -> None:
        QMessageBox.warning(self.ui, "Warning", f"Failed to fetch data: {error}")
        self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)

    def resultsPage_entered(
        self, output_data: list[OutputData], path: pathlib.Path | None
    ) -> None:
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
                    self.ui.tableWidget.setItem(i, 0, QTableWidgetItem(str(data.host)))
                    self.ui.tableWidget.setItem(i, 1, QTableWidgetItem(port))
                    self.ui.tableWidget.item(i, 0).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.ui.tableWidget.item(i, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    i += 1

            if path is not None:
                QMessageBox.information(
                    self.ui, "Info", f"Results exported to {path}"
                )
            else:
                QMessageBox.warning(
                    self.ui,
                    "Warning",
                    "Could not save CSV file. Results are shown in the table only.",
                )
        except Exception as e:
            QMessageBox.critical(self.ui, "Error", f"Failed to render results table: {e}")
            self.ui.stackedWidget.setCurrentWidget(self.ui.homePage)
