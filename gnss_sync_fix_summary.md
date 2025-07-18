# Исправление проблемы мониторинга GNSS синхронизации

## Проблема
Функция мониторинга синхронизации всегда показывала статус `SYNCHRONIZED` в веб-интерфейсе, даже когда GNSS фактически потерял синхронизацию.

## Причина
Неправильная логика проверки статуса синхронизации в коде:

### Старая логика (неправильная):
```python
gnss_status["synchronized"] = "1" in sync_value or "sync" in sync_value.lower()
```

### Проблема:
- Драйвер возвращает `"SYNC"` при синхронизации
- Драйвер возвращает `"LOST @ <timestamp>"` при потере сигнала
- Старая логика неправильно определяла строки с timestamp'ами как синхронизированные, если они содержали символ "1"

### Пример ошибочного срабатывания:
- `"LOST @ 2024-01-01 01:01:01"` → старая логика возвращает `True` (содержит "1")
- `"LOST @ 2024-01-15 10:30:25"` → старая логика возвращает `True` (содержит "1")

## Решение

### Новая логика (правильная):
```python
gnss_status["synchronized"] = sync_value.strip().upper() == "SYNC"
```

## Исправленные файлы

1. **`/workspace/extracted_project/quantum_pci_status_reader.py`**
   - Исправлена логика в методе `get_gnss_status()`

2. **`/workspace/extracted_project/quantum_pci_configurator.py`**
   - Исправлена логика в методе `refresh_gnss_status()`
   - Добавлено отдельное отображение для статуса "LOST"

3. **`/workspace/refactored_quantum_pci/src/api/status_reader.py`**
   - Исправлена логика проверки синхронизации GNSS

4. **`/workspace/extracted_project/templates/index.html`**
   - Улучшено отображение статуса в веб-интерфейсе
   - Добавлено различение между "NOT SYNCHRONIZED" и "LOST"

5. **GUI компоненты в рефакторенной версии:**
   - `/workspace/refactored_quantum_pci/src/gui/components/status_panel.py`
   - `/workspace/refactored_quantum_pci/src/gui/components/clock_panel.py`
   - Добавлена цветовая индикация статуса

## Результат

Теперь статус синхронизации отображается корректно:
- ✅ `"SYNC"` → `SYNCHRONIZED` (зеленый)
- ❌ `"LOST @ <timestamp>"` → `LOST` (красный)
- ❌ Любое другое значение → `NOT SYNCHRONIZED` (красный)

## Тестирование

Создан тестовый скрипт `test_gnss_sync_logic.py` для проверки логики исправления.