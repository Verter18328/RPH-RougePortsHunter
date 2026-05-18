# Rouge Ports Hunter (RPH)

Narzędzie do audytu portów access na przełącznikach Extreme EXOS: wykrywa porty, na których MAC netlogin powinien być włączony lub wyłączony, a konfiguracja tego nie odzwierciedla.

## Skrót

| | |
|---|---|
| **Pełna nazwa** | Rouge Ports Hunter |
| **Skrót** | RPH |

## Stan projektu

Lab first — parsery i audyt offline na próbkach CLI w `samples/`. Plan mentorskiego wdrożenia: [`docs/plan-python-netlogin-audit-exos.md`](docs/plan-python-netlogin-audit-exos.md).

## Uruchomienie (docelowo)

```bash
python main.py
```

## Struktura

```
samples/     # próbki show ports / show netlogin mac
main.py      # logika audytu
docs/        # plan i notatki
```

Dane operacyjne (`inventory.csv`, `output/`, `logs/`) nie trafiają do repozytorium — patrz `.gitignore`.
