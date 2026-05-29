"""Rogue Ports Hunter (RPH) — audyt portów netlogin na EXOS."""

import pathlib
from typing import Callable
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)
from ipaddress import IPv4Address
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

    WORKERS_COUNT = 20

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
            print(f"Inventory error: {e}")
            return []
        except Exception as e:
            print(f"Error loading devices: {e}")
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
            print(f"SSH authentication failed on {host} - skipping host.")
        except NetmikoTimeoutException:
            print(f"SSH timeout on {host} - skipping host.")
        except Exception as e:
            print(f"Error on {host}: {e} - skipping host.")
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
        completed = 0
        progress_lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=self.WORKERS_COUNT) as executor:
            futures_dict = {
                executor.submit(self._fetch_host, host): host for host in hosts
            }
            
            for future in as_completed(futures_dict):
                host = futures_dict[future]
                try:
                    result = future.result()
                    if result is not None:
                        output_data.append(result)
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    print(f"Error on {host}: {e}")
                finally:
                    with progress_lock:
                        completed += 1
                        done = completed
                    if on_progress is not None:
                        on_progress(done, total, host)


        if failed:
            print(f"Finished with errors on {failed} of {len(hosts)} hosts.")
        return output_data

    def export_results(
            self,
            output_data: list[OutputData]) -> pathlib.Path | None:
        """Eksportuje wynik do CSV i zwraca ścieżkę albo ``None``."""
        try:
            return Exporter(output_data).export()
        except OSError as e:
            print(f"Failed to write CSV report: {e}")
            return None


# Backward compatibility for existing imports/usages.
RougePortsHunter = RoguePortsHunter
