"""Wczytywanie listy hostów z pliku CSV (wybór przez okno dialogowe)."""

import csv
from ipaddress import IPv4Address
import pathlib

from data_validation import DeviceValidation
from globals import InventoryFileDialog


class InputDataReceiver:
    """Odczyt inventory CSV: jedna kolumna z adresem IPv4 (host)."""

    def __init__(self) -> None:
        self.inventory_path = self._get_inventory_path()

    def _get_inventory_path(self) -> pathlib.Path:
        return InventoryFileDialog.get_inventory_path()

    def get_inventory_data(self) -> list[IPv4Address]:
        if not self.inventory_path.exists():
            raise FileNotFoundError(
                f"Inventory file not found at {self.inventory_path}"
            )

        print(f"Reading inventory data from {self.inventory_path}...")
        inventory_data: list[IPv4Address] = []

        try:
            with open(
                self.inventory_path, newline="", encoding="utf-8"
            ) as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row:
                        continue
                    if row[0].strip().lower() == "host":
                        continue
                    if len(row) != 1:
                        print(
                            "Skipped row with invalid number of columns: "
                            f"{row}"
                        )
                        continue
                    try:
                        host = IPv4Address(row[0].strip())
                        validation = DeviceValidation(host)
                        if not validation.is_valid:
                            print(
                                f"Skipped {host}: "
                                f"{validation.error_message}"
                            )
                            continue
                        inventory_data.append(host)
                    except Exception as e:
                        print(f"Inventory row error {row}: {e}")
                        continue
        except OSError as e:
            print(f"Inventory file read error: {e}")
            return []

        print(
            f"Inventory data read successfully. "
            f"{len(inventory_data)} hosts found."
        )
        return inventory_data


# Backward compatibility for existing imports.
InputDataReciever = InputDataReceiver
