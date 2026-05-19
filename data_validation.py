"""Walidacja rekordów urządzeń z pliku inventory."""

import ipaddress
from ssh_data_retriever import Device


class DeviceValidation:
    """Sprawdza poprawność hosta (IPv4) i nazwy użytkownika (hasło może być puste)."""

    def __init__(self, device: Device) -> None:
        self.device = device
        self.is_valid, self.error_message = self._validate()

    def _validate(self) -> tuple[bool, str]:
        if not self.device.host:
            return False, "Host is required"
        if not self.device.username:
            return False, "Username is required"
        try:
            ipaddress.IPv4Address(self.device.host)
        except ValueError:
            return False, "Host is not a valid IP address"

        return True, "Device is valid"
