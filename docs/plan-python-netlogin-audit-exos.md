---
name: Rouge Ports Hunter (RPH)
overview: Plan mentorski RPH od zera — najpierw lab (próbki CLI, parser, audyt offline). Cursor prowadzi Ciebie krok po kroku; nie buduje całego projektu sam. Droga do ~500 switchy tylko zarys na końcu.
todos:
  - id: phase-1-understand
    content: "Faza 1: Przeczytaj «Po co to robimy»; zadaj pytania jeśli niejasne (ETL, kruchość CLI)."
    status: pending
  - id: phase-2-samples
    content: "Faza 2: Masz próbki w samples/ — przejrzyj je; upewnij się, że rozumiesz dwie komendy i 92 vs 104 porty."
    status: pending
  - id: phase-3-rule
    content: "Faza 3: Zrozum regułę audytu labu (brak w show = wyłączone); jedno pytanie jeśli coś nie gra."
    status: pending
  - id: phase-4-parser-mac
    content: "Faza 4: Parser linii Port: z show_netlogin_mac_sample → 92 porty."
    status: completed
  - id: phase-5-parser-ports
    content: "Faza 5: Parser portów z show_ports_sample → 104 porty."
    status: completed
  - id: phase-6-audit
    content: "Faza 6 (TERAZ): Audyt „dziur” (show ports − MAC show − wykluczenia). Uwaga: porty stack per host — patrz sekcja poniżej."
    status: in_progress
  - id: phase-7-main
    content: "Faza 7: main.py wczytuje samples/ i wypisuje wynik — gdy fazy 4–6 działają."
    status: pending
  - id: phase-8-ssh
    content: "Później: SSH, dwie komendy na host, bez 500 hostów naraz."
    status: pending
isProject: false
---

# Rouge Ports Hunter (RPH) — audyt netlogin EXOS, plan od zera (lab first)

## Jak z tego korzystasz

| Kto | Co robi |
|-----|---------|
| **Ty** | Jedna faza → jeden mały krok kodu lub ćwiczenie → **pytasz**, gdy coś niejasne |
| **Cursor** | Tłumaczy, podpowiada następny krok, **nie** pisze całego repo bez Twojej prośby |

**Nie** traktuj tego pliku jako zlecenia „zaimplementuj projekt”. To mapa nauki.

**Formuła pytania:** „[kontekst]. [pytanie]?” — np. „Mam 92 porty w parserze. Czemu test ma oczekiwać 0 findings?”

---

## Po co to robimy (1 minuta)

Chcesz **sprawdzić**, czy na portach access MAC netlogin jest **włączony tam, gdzie powinien**, a na uplinku/stacku **wyłączony** — na wielu switchach, automatycznie.

To jest mini-**ETL**:

1. **Extract** — tekst z CLI (`show …`)
2. **Transform** — parser + reguła (porównanie z polityką)
3. **Load** — raport (CSV/JSON), później logi błędów SSH

CLI jest **kruche**: format `show` może się zmienić → trzymasz **próbki** w `samples/` i testy.

---

## Cel na teraz vs później

| | Zakres |
|---|--------|
| **Teraz (lab)** | EXOS **37.x**, stos 2× X440, pliki w `samples/`, Python offline |
| **Później** | SSH (Netmiko), `inventory.csv`, limit równoległości, ~500 hostów — **osobny rozdział na końcu** |

---

## Materiał, który już masz

Nie zaczynasz od pustki — masz złote próbki:

| Plik | Komenda na switchu | Do czego |
|------|-------------------|----------|
| [`samples/show_netlogin_mac_sample`](../samples/show_netlogin_mac_sample) | `show netlogin mac` | Porty **z** MAC netlogin w show (**92**: `1:3`–`1:48`, `2:3`–`2:48`) |
| [`samples/show_ports_sample`](../samples/show_ports_sample) | `show ports no-refresh` | Wszystkie porty stosu (**104**: `1:1`–`1:52`, `2:1`–`2:52`) |

**Ważne (37.x):**

- Nie ma `show netlogin ports` → jest `show netlogin mac` lub `show netlogin port <lista>`.
- Port **wyłączony** z MAC netlogin **nie pojawia się** w `show netlogin mac` (nie szukaj `State: Disabled` na liście portów w tej próbce).
- `Port State E` w `show ports` ≠ netlogin — to admin L2.

---

## Reguła audytu (lab) — do zapamiętania

**Polityka:**

- **Musi być** w `show netlogin mac` (Enabled): `1:3–1:48`, `2:3–2:48`
- **Nie może być** w show: `1:1`, `1:2`, `2:1`, `2:2`, `1:49`, `1:50`, `2:49`, `2:50`, `1:51`, `1:52`, `2:51`, `2:52`

**Sprawdzenie:**

- Zbiór **B** = porty z linii `Port: 1:15,  Vlan: …,  State: Enabled, …`
- Brak wymaganego portu w B → **problem**
- Obecność wykluczonego portu w B → **problem**

Na **obecnych próbkach** → **0 problemów**.

**Możesz zapytać:** czemu nie wystarczy samo `show netlogin mac`; czy `show ports` jest konieczne.

---

## Fazy (kolejność)

### Faza 1 — Po co i co to jest ETL

**Zrób:** przeczytaj sekcję „Po co to robimy” powyżej.

**Pytaj o:** ETL, kruchość CLI, różnica config vs `show`.

---

### Faza 2 — Poznaj próbki

**Zrób:** otwórz oba pliki w `samples/`; znajdź jedną linię `Port: 1:15, …` i jedną linię `1:15` w tabeli portów.

**Pytaj o:** notacja `slot:port`, pager, skąd 92 vs 104.

---

### Faza 3 — Reguła w głowie

**Zrób:** powiedz własnymi słowami: „co raportuję jako błąd?” (jedno zdanie).

**Pytaj o:** wyjątki uplink/stack, wiele VLAN na porcie.

---

### Faza 4 — Parser MAC (pierwszy kod)

**Zrób:** funkcja czytająca tekst → lista rekordów z linii zaczynających się od `Port:` (port, vlan, state).

**Sprawdź:** **92** unikalne porty na `show_netlogin_mac_sample`.

**Pytaj o:** regex vs `split`, co ignorować (prompt, `Failure Vlan … Disabled`).

**Stop** — dopóki 92 nie działa, nie idź dalej.

---

### Faza 5 — Parser portów (opcjonalnie na start)

**Zrób:** z `show_ports_sample` wyciągnij listę `1:1`, `1:2`, … (**104** porty).

**Pytaj o:** czy potrzebujesz tego do audytu, skoro masz już politykę zakresów.

---

### Faza 6 — Audyt + test

**Zrób:** porównaj zbiór B z polityką (wymagane / wykluczone) → lista findings.

**Sprawdź:** na obecnych próbkach **pusta** lista.

**Pytaj o:** pytest, struktura plików (`parser_…`, `policy`, `audit`).

---

### Faza 7 — `main.py` offline

**Zrób:** wczytaj oba pliki z `samples/`, wypisz findings (print lub prosty CSV).

**Pytaj o:** argparse, gdzie trzymać politykę (stałe vs YAML).

---

## Później: SSH i skala (tylko zarys)

Gdy lab offline działa:

1. Jedna sesja SSH: `disable cli paging` → `show ports no-refresh` + `show netlogin mac`
2. Ten sam parser co na próbkach
3. `inventory.csv` (nie w repo), Netmiko, limit równoległości (np. 20–50), timeout
4. Pilot 3–10 hostów → dopiero potem ~500

**Pytaj wtedy o:** semafory, bastion, sekrety w `.env`, Netmiko `device_type`.

---

## Repo RPH (minimalnie)

```
samples/          ← próbki (już są)
main.py           ← budujesz w Fazie 7
docs/             ← ten plan
README.md         ← nazwa projektu: Rouge Ports Hunter (RPH)
inventory.csv     ← później, w .gitignore
output/ logs/     ← później, w .gitignore
```

---

## Co teraz? (jedna rzecz)

**Faza 4:** napisz parser linii `Port:` z [`show_netlogin_mac_sample`](../samples/show_netlogin_mac_sample) i policz, czy wychodzi **92**.

Jak utkniesz — wklej fragment kodu lub pytanie; w Agent mode możesz poprosić o pomoc tylko z tym krokiem.

---

## Dla Cursora

- Czytaj ten plik przy prowadzeniu użytkownika.
- Aktualna faza: **4** (parser MAC).
- Nie przeskakuj na SSH / 500 hostów bez działającego audytu offline.
