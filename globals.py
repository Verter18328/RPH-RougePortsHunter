"""Współdzielony stan aplikacji i wybór pliku inventory."""

from ipaddress import IPv4Address
import pathlib

from PySide6.QtWidgets import QFileDialog


class InventoryFileDialog:
    """Okno wyboru pliku CSV z listą hostów."""

    @staticmethod
    def get_inventory_path() -> pathlib.Path:
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Select inventory file",
            "",
            "CSV files (*.csv)",
        )
        if not file_path:
            raise FileNotFoundError("Inventory file not selected")
        return pathlib.Path(file_path)


class Globals:
    global_username: str = ""
    global_password: str = ""
    devices: list[IPv4Address] = []

    MAIN_WINDOW_PATH = pathlib.Path(__file__).parent / "Ui_Files" / "main_window.ui"
    THEME_PATH = pathlib.Path(__file__).parent / "Ui_Files" / "app_theme.qss"
