"""Rogue Ports Hunter (RPH) — audyt portów netlogin na EXOS."""

import pathlib
from typing import Callable
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)
from ipaddress import IPv4Address
import re

from export_results import Exporter
from input_data_reciever import InputDataReceiver
from netlogin_mac_parser import NetloginMacRecord
from ports_parser import PortRecord
from ssh_data_retriever import OutputData, SSHDataRetriever


class RoguePortsHunter:
    """Porównuje ``show ports`` z ``show netlogin mac`` na wielu hostach."""

    SKIP_PORTS = [
        "49",
        "50",
        "51",
        "52"
    ]

    def compare_lists(
        self,
        mac_records: list[NetloginMacRecord],
        ports_records: list[PortRecord],
        skip_ports: list[str] | set[str],
    ) -> list[str]:
        """Zwraca porty spoza netlogin z wyłączeniem ``skip_ports``."""
        mac_ports = {record.port for record in mac_records}
        skip_patterns = [self._build_skip_pattern(
            skip_port) for skip_port in skip_ports]

        findings: list[str] = []
        for record in ports_records:
            port = record.port
            if port not in mac_ports and not any(
                    pattern.match(port) for pattern in skip_patterns):
                findings.append(port)
        return findings

    @staticmethod
    def _build_skip_pattern(skip_port: str) -> re.Pattern[str]:
        """Tworzy regex dopasowujący ``slot:port`` albo sam ``port``."""
        token = skip_port.strip()
        if ":" in token:
            return re.compile(rf"^{re.escape(token)}$")
        return re.compile(rf"^(?:\d+:)?{re.escape(token)}$")

    def get_all_devices(self) -> list[IPv4Address]:
        """Zwraca listę hostów inventory; przy błędzie zwraca pustą listę."""
        try:
            receiver = InputDataReceiver()
            return receiver.get_inventory_data()
        except FileNotFoundError as e:
            print(f"Błąd inventory: {e}")
            return []
        except Exception as e:
            print(f"Błąd wczytywania urządzeń: {e}")
            return []

    def _fetch_host(self, host: IPv4Address) -> OutputData | None:
        data_retriever: SSHDataRetriever | None = None
        try:
            data_retriever = SSHDataRetriever(host)
            mac_records = data_retriever.get_netlogin_mac()
            ports_records = data_retriever.get_ports()
            findings = self.compare_lists(
                mac_records,
                ports_records,
                self.SKIP_PORTS,
            )
            return OutputData(host, findings)
        except NetmikoAuthenticationException:
            print(f"Błąd logowania SSH na {host} — pomijam host.")
        except NetmikoTimeoutException:
            print(f"Timeout SSH na {host} — pomijam host.")
        except Exception as e:
            print(f"Błąd na {host}: {e} — pomijam host.")
        finally:
            if data_retriever is not None:
                data_retriever.close()
        return None

    def fetch_non_netlogin_ports(
        self,
        hosts: list[IPv4Address],
        on_progress: Callable[[int, int, IPv4Address], None] | None = None,
    ) -> list[OutputData]:
        """Pobiera dane z hostów i zwraca tylko rekordy zakończone sukcesem."""
        output_data: list[OutputData] = []
        failed = 0
        total = len(hosts)
        for idx, host in enumerate(hosts, start=1):
            if on_progress is not None:
                # Postęp liczony jako liczba zakończonych hostów (idx - 1).
                on_progress(idx - 1, total, host)
            print(f"Fetching data from {host} ...\n")
            result = self._fetch_host(host)
            if result is not None:
                output_data.append(result)
            else:
                failed += 1
            if on_progress is not None:
                on_progress(idx, total, host)
        if failed:
            print(f"Zakończono z błędami na {failed} z {len(hosts)} hostów.")
        return output_data

    def export_results(
            self,
            output_data: list[OutputData]) -> pathlib.Path | None:
        """Eksportuje wynik do CSV i zwraca ścieżkę albo ``None``."""
        try:
            return Exporter(output_data).export()
        except OSError as e:
            print(f"Błąd zapisu raportu CSV: {e}")
            return None


# Backward compatibility for existing imports/usages.
RougePortsHunter = RoguePortsHunter
