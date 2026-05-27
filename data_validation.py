"""Walidacja adresów hostów z pliku inventory."""

import ipaddress
from ipaddress import IPv4Address


class DeviceValidation:
    """Sprawdza poprawność adresu IPv4."""

    def __init__(self, host: IPv4Address) -> None:
        self.host = host
        self.is_valid, self.error_message = self._validate()

    def _validate(self) -> tuple[bool, str]:
        try:
            ipaddress.IPv4Address(self.host)
        except ValueError:
            return False, "Host is not a valid IP address"

        return True, "Host is valid"
