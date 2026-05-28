"""Parser wyjścia ``show netlogin mac`` (EXOS 37.x)."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class NetloginMacRecord:
    port: str
    vlan: str
    state: str


class NetloginMacParser:
    """Linie ``Port: slot:port, Vlan: …, State: …``."""

    PORT_LINE = (
        r"^Port:\s+(?P<port>\S+),\s+Vlan:\s+(?P<vlan>[^,]+),\s+State:"
        r"\s+(?P<state>[^,]+)"
    )

    def parse(self, text: str) -> list[NetloginMacRecord]:
        records: list[NetloginMacRecord] = []
        for line in text.splitlines():
            record = self._parse_line(line)
            if record:
                records.append(record)
        return records

    def _parse_line(self, line: str) -> NetloginMacRecord | None:
        line = line.strip()
        match = re.match(self.PORT_LINE, line)
        if match:
            return NetloginMacRecord(
                port=match.group("port"),
                vlan=match.group("vlan"),
                state=match.group("state"),
            )
        return None
