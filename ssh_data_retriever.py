"""Pobieranie wyjścia CLI z przełączników Extreme EXOS przez SSH (Netmiko)."""

from dataclasses import dataclass
from ipaddress import IPv4Address

import netmiko

from globals import Globals
from netlogin_mac_parser import NetloginMacParser, NetloginMacRecord
from ports_parser import PortsParser, PortRecord


@dataclass(frozen=True)
class OutputData:
    """Wynik audytu dla jednego hosta."""

    host: IPv4Address
    ports: list[str]


class SSHDataRetriever:
    """Sesja SSH i polecenia ``show netlogin mac`` / ``show ports no-refresh``."""

    def __init__(self, host: IPv4Address) -> None:
        self.host = host
        self.username = Globals.global_username
        self.password = Globals.global_password
        self.connection: netmiko.BaseConnection | None = None
        self._connect()

    def _connect(self) -> None:
        self.connection = netmiko.ConnectHandler(
            device_type="extreme",
            host=str(self.host),
            username=self.username,
            password=self.password,
        )

    def _prepare_cli(self) -> None:
        if self.connection is None:
            raise RuntimeError("Brak aktywnej sesji SSH.")
        self.connection.send_command("disable cli paging")

    def get_netlogin_mac(self) -> list[NetloginMacRecord]:
        self._prepare_cli()
        output = self.connection.send_command(  # type: ignore[union-attr]
            "show netlogin mac",
            read_timeout=300,
        )
        return NetloginMacParser().parse(output)

    def get_ports(self) -> list[PortRecord]:
        self._prepare_cli()
        output = self.connection.send_command(  # type: ignore[union-attr]
            "show ports no-refresh",
        )
        return PortsParser().parse(output)

    def close(self) -> None:
        if self.connection is None:
            return
        try:
            self.connection.disconnect()
        except Exception as e:
            print(f"Ostrzeżenie: błąd przy zamykaniu sesji {self.host}: {e}")
        finally:
            self.connection = None
