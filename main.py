"""Rouge Ports Hunter (RPH) — audyt portów netlogin na EXOS."""

from pathlib import Path

from netlogin_mac_parser import NetloginMacParser, NetloginMacRecord
from ports_parser import PortsParser, PortRecord
from ssh_data_retriever import SSHDataRetriever, Device

APP_NAME = "Rouge Ports Hunter"
APP_SHORT = "RPH"

SAMPLES_DIR = Path("samples")
MAC_SAMPLE = SAMPLES_DIR / "show_netlogin_mac_sample"
PORTS_SAMPLE = SAMPLES_DIR / "show_ports_sample"

# Wykluczenia dla labowej próbki (10G). Stack (1:1, 1:2, …) — per host, patrz plan.
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


def get_device() -> Device:
    device_type = str(input("Enter the device type: "))
    host = str(input("Enter the host: "))
    username = str(input("Enter the username: "))
    password = str(input("Enter the password: "))
    return Device(device_type, host, username, password)

def get_all_devices() -> list[Device]:
    devices = []
    device_number = int(input("Enter the number of devices: "))
    for i in range(device_number):
        device = get_device()
        devices.append(device)
    return devices

def fetch_non_netlogin_ports(devices: list[Device]) -> list[str]:
    for device in devices:
        print(f"Fetching data from {device.host} ...\n")
        data_retriever = SSHDataRetriever(device)
        mac_records = data_retriever.get_netlogin_mac()
        ports_records = data_retriever.get_ports()
        data_retriever.close()
        findings = compare_lists(mac_records, ports_records, LAB_SAMPLE_SKIP_PORTS)
        for port in findings:
            print(f"Port {port} is not in the netlogin mac list")

if __name__ == "__main__":
    devices = get_all_devices()
    fetch_non_netlogin_ports(devices)
