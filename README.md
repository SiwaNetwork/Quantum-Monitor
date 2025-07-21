# QUANTUM-PCI Configuration Tools

Комплект инструментов для конфигурации и мониторинга карт QUANTUM-PCI с полной поддержкой драйвера ptp_ocp.

## ✅ Статус проекта: ВСЕ ПРОБЛЕМЫ РЕШЕНЫ

- **Зависание исправлено**: добавлен headless режим
- **Мониторинг расширен**: отслеживаются все 24+ параметра драйвера  
- **Код оптимизирован**: применены все улучшения
- **Тестирование завершено**: работает без зависаний

## 📁 Структура проекта

### `refactored_quantum_pci/` - Полнофункциональный инструмент
- **main.py** - основной файл с GUI/CLI поддержкой
- **src/** - модульная архитектура с полным API
- **test_device/** - тестовые данные для разработки

### `extracted_project/` - Специализированные инструменты  
- **quantum_pci_monitor_pure_cli.py** - pure CLI монитор всех параметров
- **quantum_pci_configurator_fixed.py** - исправленная GUI версия
- **ptp_ocp.c** - исходный код драйвера (референс)

### `ptp_ocp_monitor/` - Дополнительные инструменты мониторинга

## 🚀 Быстрый старт

### Рекомендуемый способ (refactored_quantum_pci)
```bash
cd refactored_quantum_pci

# CLI режим (рекомендуется)
python3 main.py --cli --device /sys/class/timecard/ocp0

# GUI режим с автопроверкой
python3 main.py --headless-test
```

### Pure CLI монитор (extracted_project)
```bash
cd extracted_project

# Полный отчет всех параметров
python3 quantum_pci_monitor_pure_cli.py --device /sys/class/timecard/ocp0 --status

# Непрерывный мониторинг
python3 quantum_pci_monitor_pure_cli.py --device /sys/class/timecard/ocp0 --monitor
```

### Тестирование без устройства
```bash
# Использование тестовых данных
python3 main.py --cli --device test_device
python3 quantum_pci_monitor_pure_cli.py --device /workspace/refactored_quantum_pci/test_device --status
```

## 📊 Мониторируемые параметры

### Основные (13 параметров)
- serialnum, gnss_sync, clock_source, available_clock_sources
- external/internal_pps_cable_delay, holdover, mac_i2c  
- utc_tai_offset, ts_window_adjust, irig_b_mode
- clock_status_drift, clock_status_offset

### SMA интерфейсы (6 параметров)
- sma1, sma2, sma3, sma4
- available_sma_inputs, available_sma_outputs

### TOD протокол (5 параметров)
- tod_protocol, available_tod_protocols
- tod_baud_rate, available_tod_baud_rates, tod_correction

### Динамические (signal1-4, freq1-4)
- Генераторы сигналов: duty, period, phase, polarity, running, start, signal
- Частотные счетчики: frequency, seconds

## 🔧 Решение проблем

### Программа зависает
```bash
# Используйте headless тест
python3 main.py --headless-test

# Или pure CLI версию  
python3 quantum_pci_monitor_pure_cli.py --device /sys/class/timecard/ocp0
```

### Устройство не найдено
```bash
# Проверьте драйвер
sudo modprobe ptp_ocp

# Проверьте права доступа
ls -la /sys/class/timecard/

# Используйте тестовое устройство
python3 main.py --cli --device test_device
```

## 🎯 Ключевые особенности

- **Нет зависаний**: автоматическое переключение CLI/GUI
- **Полный мониторинг**: все параметры драйвера ptp_ocp
- **Headless совместимость**: работает без X11/GUI
- **Отказоустойчивость**: graceful degradation при ошибках
- **Экспорт данных**: JSON/CSV форматы

## 📖 Подробная документация

См. [FINAL_CONSOLIDATED_INSTRUCTIONS.md](FINAL_CONSOLIDATED_INSTRUCTIONS.md) для полного описания всех исправлений и возможностей.

## ⚙️ Системные требования

- Python 3.6+
- Linux с поддержкой sysfs
- Драйвер ptp_ocp (для реальных устройств)
- tkinter (опционально, для GUI)

## 🏆 Результат

Все задачи выполнены:
1. ✅ Устранено зависание при запуске
2. ✅ Добавлен мониторинг всех параметров драйвера
3. ✅ Применены все предыдущие предложения
4. ✅ Код протестирован и очищен от лишних файлов

**Проект готов к продакшен использованию!**