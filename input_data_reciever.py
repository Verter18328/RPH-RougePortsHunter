"""Wczytywanie listy urządzeń z pliku CSV (wybór przez okno dialogowe)."""

import csv
import pathlib
from tkinter import Tk, filedialog

from data_validation import DeviceValidation
from ssh_data_retriever import Device

INVENTORY_HEADER = ["host", "username", "password"]


class InputDataReciever:
    """Odczyt inventory CSV: kolumny host, username, password."""

    def __init__(self) -> None:
        self.inventory_path = self._get_inventory_path()

    def _get_inventory_path(self) -> pathlib.Path:
        root = Tk()
        root.withdraw()
        try:
            path = filedialog.askopenfilename(
                title="Select inventory file",
                filetypes=[("CSV files", "*.csv")],
            )
        finally:
            root.destroy()

        if not path:
            raise FileNotFoundError(
                "Nie wybrano pliku inventory (anulowano wybór)."
            )
        return pathlib.Path(path)

    def get_inventory_data(self) -> list[Device]:
        if not self.inventory_path.exists():
            raise FileNotFoundError(
                f"Inventory file not found at {self.inventory_path}"
            )

        print(f"Reading inventory data from {self.inventory_path}...")
        inventory_data: list[Device] = []

        try:
            with open(self.inventory_path, newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row or row == INVENTORY_HEADER:
                        continue
                    if len(row) < 3:
                        print(f"Pominięto niepełny wiersz: {row}")
                        continue
                    try:
                        device = Device(
                            host=row[0].strip(),
                            username=row[1].strip(),
                            password=row[2].strip(),
                        )
                        validation = DeviceValidation(device)
                        if not validation.is_valid:
                            print(
                                f"Pominięto {device.host}: "
                                f"{validation.error_message}"
                            )
                            continue
                        inventory_data.append(device)
                    except Exception as e:
                        print(f"Błąd wiersza inventory {row}: {e}")
                        continue
        except OSError as e:
            print(f"Błąd odczytu pliku inventory: {e}")
            return []

        print(
            f"Inventory data read successfully. "
            f"{len(inventory_data)} devices found."
        )
        return inventory_data
