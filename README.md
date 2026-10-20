# TCrims Playwright Tools

> Edukacyjny zestaw skryptów Python + Playwright do eksperymentowania z automatyzacją interfejsu WWW na ekranach gry TCrims.

Projekt zawiera niezależne moduły dla wybranych widoków gry. Każdy skrypt uruchamia przeglądarkę Chromium i wymaga ręcznego zalogowania przez użytkownika.

> [!IMPORTANT]
> Narzędzia działają lokalnie na komputerze użytkownika. Nie przechowują ani nie przesyłają danych logowania do zewnętrznego serwera.

## Spis treści

- [Moduły](#moduły)
- [Wymagania](#wymagania)
- [Instalacja](#instalacja)
- [Uruchomienie](#uruchomienie)
- [Hunting Grounds](#hunting-grounds)
- [Cel edukacyjny](#cel-edukacyjny)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)

## Moduły

| Plik | Przeznaczenie |
| --- | --- |
| `singlerob.py` | Odczyt staminy i uruchamianie pojedynczego rabunku. |
| `gangrob.py` | Obsługa sekwencji `Accept` → oczekiwanie → `Do the score!`. |
| `hutnin.py` | Eksperymentalna obsługa widoku Hunting Grounds. |

## Wymagania

- Python 3.10 lub nowszy.
- Dostęp do internetu.
- Konto The Crims — logowanie odbywa się ręcznie w otwartym oknie Chromium.
- Zależności z pliku `requirements.txt`.
- Przeglądarka Chromium pobrana przez Playwright.

## Instalacja

1. Pobierz projekt jako ZIP albo sklonuj repozytorium.
2. Otwórz terminal w katalogu projektu.
3. Utwórz i aktywuj środowisko wirtualne:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Zainstaluj wymagane biblioteki oraz Chromium dla Playwright:

   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```

## Uruchomienie

Uruchom wybrany moduł, na przykład Hunting Grounds:

```powershell
python hutin.py
```

Po otwarciu Chromium zaloguj się ręcznie na swoje konto TCrims. Następnie wróć do terminala i naciśnij `Enter`, aby kontynuować działanie skryptu.

## Hunting Grounds

`huntin.py` jest samodzielnym, eksperymentalnym modułem dla widoku Hunting Grounds. Obejmuje:

- ręczne logowanie;
- widoczny, płynnie poruszający się kursor;
- odczyt HP, staminy i Assault Power;
- blokadę działania przy HP niższym niż 10;
- wykrywanie celów oznaczonych `[bot]`;
- odświeżanie listy klubów bez przeładowywania całej strony.

> [!TIP]
> Przed użyciem skryptów uruchom je na koncie testowym lub w ograniczonym zakresie, aby zweryfikować aktualny wygląd interfejsu gry.

## Cel edukacyjny

Projekt ma charakter edukacyjny. Pomaga ćwiczyć:

- automatyzację przeglądarki przy użyciu Python i Playwright;
- pracę z selektorami elementów interfejsu;
- kontrolowanie przepływu działań i obsługę stanów strony;
- bezpieczne testowanie automatyzacji w widocznej przeglądarce.

> [!WARNING]
> Przed użyciem sprawdź aktualne zasady TCrims. Narzędzia nie są przeznaczone do obchodzenia zabezpieczeń, omijania ograniczeń gry ani uzyskiwania nieuczciwej przewagi. Użytkownik korzysta z nich wyłącznie na własną odpowiedzialność i zgodnie z regulaminem serwisu.

## Rozwiązywanie problemów

| Problem | Co sprawdzić |
| --- | --- |
| Playwright nie otwiera Chromium | Uruchom ponownie `playwright install chromium`. |
| Skrypt nie odnajduje elementu | Interfejs gry mógł się zmienić; sprawdź selektory w odpowiednim pliku `.py`. |
| Logowanie nie przechodzi dalej | Zaloguj się ręcznie w oknie Chromium, a dopiero potem naciśnij `Enter` w terminalu. |
