"""Rouge Ports Hunter (RPH) — audyt portów netlogin na EXOS."""

import pathlib
from typing import Callable
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException
from ipaddress import IPv4Address

from export_results import Exporter
from globals import Globals
from input_data_reciever import InputDataReciever
from netlogin_mac_parser import NetloginMacRecord
from ports_parser import PortRecord
from ssh_data_retriever import OutputData, SSHDataRetriever


class RougePortsHunter:
    """Porównuje ``show ports`` z ``show netlogin mac`` na wielu hostach."""

    APP_NAME = "Rouge Ports Hunter"
    APP_SHORT = "RPH"

    # Wykluczenia dla labowej próbki (10G). Stack (1:1, 1:2, …) — w produkcji per host.
    LAB_SAMPLE_SKIP_PORTS = [
        "1:49",
        "1:50",
        "1:51",
        "1:52",
        "2:49",
        "2:50",
        "2:51",
        "2:52",
    ]

    def compare_lists(
        self,
        mac_records: list[NetloginMacRecord],
        ports_records: list[PortRecord],
        skip_ports: list[str] | set[str],
    ) -> list[str]:
        """Porty z ``show ports`` bez wpisu w ``show netlogin mac``, poza ``skip_ports``."""
        mac_ports = {record.port for record in mac_records}
        skip = set(skip_ports)

        findings: list[str] = []
        for record in ports_records:
            port = record.port
            if port not in mac_ports and port not in skip:
                findings.append(port)
        return findings

    def get_all_devices(self) -> list[IPv4Address]:
        try:
            receiver = InputDataReciever()
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
                self.LAB_SAMPLE_SKIP_PORTS,
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

    def export_results(self, output_data: list[OutputData]) -> pathlib.Path | None:
        try:
            return Exporter(output_data).export()
        except OSError as e:
            print(f"Błąd zapisu raportu CSV: {e}")
            return None

    def run(self) -> None:
        try:
            devices = self.get_all_devices()
            if not devices:
                print("Brak poprawnych urządzeń w inventory — kończę.")
                return
            output_data = self.fetch_non_netlogin_ports(devices)
            if not output_data:
                print("Brak wyników do eksportu (wszystkie hosty z błędem?).")
                return
            self.export_results(output_data)
        except KeyboardInterrupt:
            print("\nPrzerwano przez użytkownika.")
        except Exception as e:
            print(f"Nieoczekiwany błąd: {e}")

    def fetch_and_export(
        self, on_progress: Callable[[int, int, IPv4Address], None] | None = None
    ) -> tuple[list[OutputData], pathlib.Path | None]:
        output_data: list[OutputData] = self.fetch_non_netlogin_ports(Globals.devices, on_progress)
        if not output_data:
            print("Brak wyników do eksportu (wszystkie hosty z błędem?).")
            return output_data, None
        path = self.export_results(output_data)
        return output_data, path
