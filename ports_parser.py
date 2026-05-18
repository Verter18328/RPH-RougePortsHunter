"""Parser tabeli ``show ports no-refresh``."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PortRecord:
    port: str
    vlan: str
    port_state: str
    link_state: str


class PortsParser:
    """Wiersze tabeli zaczynające się od ``slot:port``."""

    PORT_ROW = re.compile(
        r"^(?P<port>\d+:\d+)\s+"
        r"(?P<vlan>\([^)]+\)|\S+)\s+"
        r"(?P<port_state>\S+)\s+"
        r"(?P<link_state>\S+)"
        r"(?:\s+(?P<speed>\S+)\s+(?P<duplex>\S+))?"
    )

    def parse(self, text: str) -> list[PortRecord]:
        records: list[PortRecord] = []
        for line in text.splitlines():
            record = self._parse_line(line)
            if record:
                records.append(record)
        return records

    def _parse_line(self, line: str) -> PortRecord | None:
        line = line.strip()
        match = self.PORT_ROW.match(line)
        if match:
            return PortRecord(
                port=match.group("port"),
                vlan=match.group("vlan"),
                port_state=match.group("port_state"),
                link_state=match.group("link_state"),
            )
        return None
