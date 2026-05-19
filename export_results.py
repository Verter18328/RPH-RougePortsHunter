"""Eksport wyników audytu RPH do pliku CSV."""

import csv
from datetime import datetime
import pathlib

from ssh_data_retriever import OutputData


class Exporter:
    """Zapisuje pary (host, port) do ``~/Downloads/RPH_results_<timestamp>.csv``."""

    DOWNLOADS_DIR = pathlib.Path.home() / "Downloads"

    def __init__(self, output_data: list[OutputData]) -> None:
        self.output_data = output_data
        self.path = self._export_path()

    def _export_path(self) -> pathlib.Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return self.DOWNLOADS_DIR / f"RPH_results_{timestamp}.csv"

    def export(self) -> None:
        with open(self.path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Host", "Ports"])
            for data in self.output_data:
                for port in data.ports:
                    writer.writerow([data.host, port])
        print(f"Results exported to {self.path}")
