import netmiko
from dataclasses import dataclass
from netlogin_mac_parser import NetloginMacParser, NetloginMacRecord
from ports_parser import PortsParser, PortRecord


@dataclass(frozen=True)
class Device:
    device_type: str
    host: str
    username: str
    password: str

class SSHDataRetriever:
    def __init__(self, device: Device) -> None:
        self.device = device
        self.connection = self._connect()
    def _connect(self) -> netmiko.BaseConnection:
        return netmiko.ConnectHandler(
            device_type=self.device.device_type,
            host=self.device.host,
            username=self.device.username,
            password=self.device.password,
        )
    def _prepare_cli(self) -> None:
        self.connection.send_command("disable cli paging")

    def get_netlogin_mac(self) -> list[NetloginMacRecord]:
        self._prepare_cli()
        command = "show netlogin mac"
        output = self.connection.send_command(command, read_timeout=300)
        parser = NetloginMacParser()
        return parser.parse(output)
    def get_ports(self) -> list[PortRecord]:
        self._prepare_cli()
        command = "show ports no-refresh"
        output = self.connection.send_command(command)
        parser = PortsParser()
        return parser.parse(output)
    def close(self) -> None:
        self.connection.disconnect()