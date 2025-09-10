# Aplikacja dostępności urządzeń

Minimalna aplikacja FastAPI do obliczania dostępności urządzeń na podstawie pliku `DostepnoscWTygodniach.xlsx`.

## Funkcjonalność (etap 1)
- Wczytanie pliku dostępności.
- Normalizacja danych tygodniowych.
- Agregacja do poziomu miesiąca (uwzględnia wyłącznie dni robocze).
- API endpoint: `/availability/{device_id}?month=YYYY-MM` zwraca:
  - Tygodniowe dostępności (lista)
  - Liczbę dni roboczych w miesiącu
  - Łączną dostępność miesięczną (suma godzin tygodniowych z przycięciem do faktycznej liczby dni roboczych)

## Następne kroki
- Walidacja wejścia.
- GUI (np. Streamlit lub prosty frontend).
- Import danych produkcyjnych i porównanie obciążenia z dostępnością.
