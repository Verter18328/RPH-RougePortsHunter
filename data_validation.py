"""Walidacja rekordów urządzeń z pliku inventory."""

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
        if len(self.device.host.split(".")) != 4:
            return False, "Host is not a valid IP address"
        for part in self.device.host.split("."):
            if not part.isdecimal():
                return False, "Host is not a valid IP address"
            if int(part) < 0 or int(part) > 255:
                return False, "Host is not a valid IP address"

        return True, "Device is valid"
