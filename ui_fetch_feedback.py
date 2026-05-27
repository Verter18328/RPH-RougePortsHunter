"""Sterowanie paskiem postępu i animacją etykiety podczas fetcha.

Filozofia:
- Zawsze tryb determinate (0-100%). Pasek pokazuje WYŁĄCZNIE realne procenty
  pochodzące z workera; nie kłamiemy, nie symulujemy postępu.
- Przejścia między raportami workera są wygładzane przez QPropertyAnimation
  z easingiem OutCubic — natywne narzędzie Qt, brak własnych timerów.
- Sygnał życia podczas długiego SSH zapewnia animowana etykieta
  "Fetching...", nie pasek.
"""

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QLabel, QProgressBar


class FetchProgressController(QObject):
    """Pasek postępu z gładkimi przejściami między raportami workera."""

    _ANIMATION_DURATION_MS = 400

    def __init__(self, progress_bar: QProgressBar, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._bar = progress_bar
        self._animation = QPropertyAnimation(self._bar, b"value", self)
        self._animation.setDuration(self._ANIMATION_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def start(self, _total_hosts: int = 0) -> None:
        """Inicjalizuje pasek na początku fetcha.

        Parametr ``_total_hosts`` jest zachowany dla zgodności wywołań,
        ale obecna implementacja go nie potrzebuje — pasek zawsze
        startuje w trybie determinate od 0%.
        """
        self._animation.stop()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)

    def set_target(self, percent: int) -> None:
        """Wywoływane z workera po raporcie postępu."""
        target = max(0, min(100, percent))
        if target == self._bar.value():
            return
        self._animation.stop()
        self._animation.setStartValue(self._bar.value())
        self._animation.setEndValue(target)
        self._animation.start()

    def complete(self) -> None:
        """Domknięcie paska na 100% — animowane, nie ucięte."""
        self._animation.stop()
        self._animation.setStartValue(self._bar.value())
        self._animation.setEndValue(100)
        self._animation.start()

    def stop(self) -> None:
        """Reset paska po zakończeniu / przerwaniu fetcha."""
        self._animation.stop()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)

    def completion_delay_ms(self) -> int:
        """Ile czasu daje animacji domknięcia 0→100% (do użycia z QTimer)."""
        return self._ANIMATION_DURATION_MS + 50


class FetchingDotsAnimator(QObject):
    """Animacja kropek w napisie "Fetching" na etykiecie."""

    _BASE_TEXT = "Fetching"
    _INTERVAL_MS = 400
    _CYCLE_LENGTH = 4

    def __init__(self, label: QLabel, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._label = label
        self._timer = QTimer(self)
        self._timer.setInterval(self._INTERVAL_MS)
        self._timer.timeout.connect(self._on_timeout)
        self._step = 0

    def start(self) -> None:
        self._step = 0
        self._timer.start()
        self._update_label()

    def stop(self) -> None:
        self._timer.stop()
        self._step = 0
        self._update_label()

    def _on_timeout(self) -> None:
        self._step = (self._step + 1) % self._CYCLE_LENGTH
        self._update_label()

    def _update_label(self) -> None:
        dots = "." * self._step
        self._label.setText(f"{self._BASE_TEXT}{dots}")
