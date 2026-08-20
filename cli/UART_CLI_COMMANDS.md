# USB CDC CLI — dokumentacja komend

Interfejs CLI jest dostępny jako USB CDC ACM (wirtualny port szeregowy). W systemie Linux urządzenie zwykle pojawia się jako `/dev/ttyACM0`. Wartość prędkości ustawiona w terminalu jest dla USB CDC umowna; można pozostawić `115200 8N1`.

Komendy należy wpisywać **wielkimi literami** i kończyć klawiszem Enter (`CR`, `LF` albo `CR+LF`). Po aktywacji połączenia oraz po każdej obsłużonej komendzie urządzenie wysyła:

```text
READY
```

## Lista komend

| Komenda | Działanie |
| --- | --- |
| `HELP` | Wyświetla pionową listę dostępnych komend jako linie `OK CMD ...`, zakończoną `OK END`. |
| `RTC GET` | Odczytuje bieżącą datę i czas RTC. |
| `RTC SET YYYY-MM-DD HH:MM:SS` | Ustawia datę i czas RTC. Dozwolone lata: `2000..2099`. |
| `RTC INIT` | Inicjalizuje RTC wartością `2026-01-01 00:00:00`, jeśli nie zapisano wcześniej znacznika inicjalizacji. |
| `LED ON` | Włącza LED na `PC13` (LED jest aktywna stanem niskim). |
| `LED OFF` | Wyłącza LED na `PC13`. |
| `BTN GET` | Odczytuje stan wejścia `PA0`. |
| `FLASH ID` | Odczytuje JEDEC ID opcjonalnej pamięci SPI Flash i rozpoznaje producenta. |
| `FLASH STATUS` | Odczytuje rejestr statusu SR1 (`BUSY` i `WEL`) opcjonalnej pamięci. |
| `FLASH TEST` | Kasuje sektor 4 KiB, zapisuje 256 B i weryfikuje dane; wymaga zamontowanej pamięci. |
| `REBOOT` | Wysyła potwierdzenie i resetuje mikrokontroler. |

## Format daty i czasu

Polecenie `RTC SET` wymaga dokładnie formatu:

```text
RTC SET YYYY-MM-DD HH:MM:SS
```

Przykład:

```text
RTC SET 2026-07-12 14:30:00
RTC GET
```

Wymagania:

- rok: `2000..2099`,
- miesiąc: `01..12`,
- dzień zgodny z miesiącem i rokiem przestępnym,
- godzina: `00..23`,
- minuta i sekunda: `00..59`,
- wszystkie zera wiodące oraz separatory są obowiązkowe.

Przykładowa odpowiedź:

```text
OK RTC 2026-07-12 14:30:00
READY
```

## Test pamięci SPI Flash

Pamięć SPI NOR nie jest montowana fabrycznie. Polecenia `FLASH ID`, `FLASH STATUS` i `FLASH TEST` działają po samodzielnym wlutowaniu zgodnego układu na pola U3. Pola pamięci są podłączone do `SPI1`, a sygnał CS znajduje się na `PA4`. Komenda `FLASH TEST` używa adresu `0x010000`.

Test wykonuje kolejno:

1. odczyt JEDEC ID,
2. skasowanie sektora 4 KiB,
3. sprawdzenie, czy skasowane bajty mają wartość `0xFF`,
4. zapis 256-bajtowego wzorca,
5. ponowny odczyt i porównanie danych.

Uwaga: `FLASH TEST` wymaga zamontowanej pamięci i niszczy wcześniejszą zawartość sektora rozpoczynającego się pod adresem `0x010000`.

## Format odpowiedzi

- powodzenie zaczyna się od `OK`,
- błąd zaczyna się od `ERR`,
- nieznana komenda: `ERR CLI unknown_command: <komenda>`,
- każda odpowiedź kończy się osobną linią `READY`,
- linia dłuższa niż 127 znaków: `ERR LINE_TOO_LONG`.

Przykłady:

```text
OK
READY
ERR RTC bad_format use: RTC SET YYYY-MM-DD HH:MM:SS
READY
OK BTN PA0=1
READY
OK FLASH SR1=0x00 BUSY=0 WEL=0
READY
```
