# Plan refaktoryzacji zbx_tag_manager

## 1. Ekstrakcja wspólnego JavaScript (~2h)
- Utworzyć `/app/static/js/table-manager.js` z klasami:
  - `FilterManager` - uniwersalne filtrowanie tabel
  - `PaginationManager` - obsługa paginacji
  - `BulkOperationsManager` - operacje zbiorcze
  - `SelectionManager` - zaznaczanie wierszy
- Usunąć zduplikowany kod z hosts.html, triggers.html, items.html
- **Efekt:** Redukcja ~300 linii zduplikowanego kodu, łatwiejsze utrzymanie

## 2. Refaktoryzacja zabbix_api.py (~1.5h)
- Utworzyć generyczne metody:
  - `_add_tag(object_type, object_id, tag_name, tag_value)`
  - `_remove_tag(object_type, object_id, tag_name)`
  - `_bulk_add_tags(object_type, object_ids, tag_name, tag_value)`
  - `_bulk_remove_tags(object_type, object_ids, tag_name)`
- Obecne metody jako wrappery do generycznych
- **Efekt:** Redukcja ~450 linii zduplikowanego kodu

## 3. Centralizacja walidacji w app.py (~30min)
- Utworzyć dekorator `@validate_tag_request` do walidacji tagów
- Zastosować w endpointach POST/DELETE
- **Efekt:** Usunięcie powtórzeń walidacji (obecnie 6x ten sam kod)

## 4. Ekstrakcja logiki biznesowej z route'ów (~30min)
- Przenieść logikę grupowania itemów do `zabbix_api.py`
- Metoda: `group_items_by_key(items_data)`
- **Efekt:** Czystsze route handlery, łatwiejsze testowanie

## 5. Konfiguracja do .env (~15min)
- Przenieść `MAX_BULK_SIZE` do zmiennych środowiskowych
- Dodać przykład do `.env.example`
- **Efekt:** Konfigurowalność bez edycji kodu

## 6. Poprawa obsługi błędów (~30min)
- Zamienić `print()` na moduł `logging`
- Dodać Flask error handler dla wyjątków
- **Efekt:** Lepsze debugowanie, bezpieczeństwo (nie expose błędów)

---

**Szacowany czas:** ~5-6h pracy
**Redukcja kodu:** ~750+ linii duplikatów
**Bez:** nowych frameworków, przepisywania architektury, dodawania testów
