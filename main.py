"""Rouge Ports Hunter (RPH) — audyt portów netlogin na EXOS."""

from export_results import Exporter
from input_data_reciever import InputDataReciever
from netlogin_mac_parser import NetloginMacRecord
from ports_parser import PortRecord
from ssh_data_retriever import Device, OutputData, SSHDataRetriever


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

    def get_all_devices(self) -> list[Device]:
        receiver = InputDataReciever()
        return receiver.get_inventory_data()

    def fetch_non_netlogin_ports(self, devices: list[Device]) -> list[OutputData]:
        output_data: list[OutputData] = []
        for device in devices:
            print(f"Fetching data from {device.host} ...\n")
            data_retriever = SSHDataRetriever(device)
            try:
                mac_records = data_retriever.get_netlogin_mac()
                ports_records = data_retriever.get_ports()
                findings = self.compare_lists(
                    mac_records,
                    ports_records,
                    self.LAB_SAMPLE_SKIP_PORTS,
                )
                output_data.append(OutputData(device.host, findings))
            finally:
                data_retriever.close()
        return output_data

    def export_results(self, output_data: list[OutputData]) -> None:
        Exporter(output_data).export()

    def run(self) -> None:
        devices = self.get_all_devices()
        if not devices:
            print("Brak poprawnych urządzeń w inventory — kończę.")
            return
        output_data = self.fetch_non_netlogin_ports(devices)
        self.export_results(output_data)


if __name__ == "__main__":
    RougePortsHunter().run()
