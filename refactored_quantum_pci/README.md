# QUANTUM-PCI Configuration Tool v2.0

Рефакторированный инструмент для настройки и мониторинга устройств QUANTUM-PCI с улучшенной архитектурой и современным интерфейсом.

## Особенности

- **Модульная архитектура**: Разделение на core, GUI, API модули
- **Улучшенная обработка ошибок**: Централизованная система исключений
- **Менеджер конфигураций**: Сохранение/загрузка настроек в JSON/YAML
- **Мониторинг в реальном времени**: Автоматическое отслеживание изменений
- **Проверка состояния**: Комплексные health checks
- **Экспорт данных**: Поддержка JSON и CSV форматов
- **CLI и GUI режимы**: Гибкость использования

## Структура проекта

```
refactored_quantum_pci/
├── src/
│   ├── core/               # Основная логика
│   │   ├── device.py       # Класс устройства
│   │   ├── config_manager.py # Управление конфигурацией
│   │   └── exceptions.py   # Исключения
│   ├── api/                # API для работы с устройством
│   │   ├── status_reader.py # Чтение статусов
│   │   └── web_api.py      # Web API (планируется)
│   └── gui/                # Графический интерфейс
│       ├── main_window.py  # Главное окно
│       └── components/     # Компоненты GUI
├── config/                 # Конфигурационные файлы
├── docs/                   # Документация
├── tests/                  # Тесты
├── examples/               # Примеры использования
├── main.py                # Главный исполняемый файл
├── requirements.txt       # Зависимости
└── README.md             # Этот файл
```

## Требования

- Python 3.6+
- Linux с ядром 5.12+ (рекомендуется)
- Драйвер ptp_ocp загружен
- Права доступа к `/sys/class/timecard/`

## Установка

1. Клонирование репозитория:
```bash
git clone <repository_url>
cd refactored_quantum_pci
```

2. Установка зависимостей:
```bash
pip install -r requirements.txt
```

3. Проверка доступности устройства:
```bash
ls /sys/class/timecard/
```

## Использование

### GUI режим (по умолчанию)
```bash
python main.py
```

### CLI режим
```bash
# Просмотр статуса устройства
python main.py --cli

# Экспорт статуса в файл
python main.py --cli --export status.json

# Указание конкретного устройства
python main.py --cli --device /sys/class/timecard/ocp0
```

### Программное использование

```python
from src.core.device import QuantumPCIDevice
from src.api.status_reader import StatusReader
from src.core.config_manager import ConfigManager

# Инициализация устройства
device = QuantumPCIDevice()

# Получение информации об устройстве
device_info = device.get_device_info()
print(f"Serial: {device_info['serial_number']}")

# Настройка источника синхронизации
device.set_clock_source("PPS")

# Настройка SMA портов
device.set_sma_input(1, "PPS1")
device.set_sma_output(1, "PHC")

# Мониторинг статуса
status_reader = StatusReader(device)
status = status_reader.get_full_status()

# Работа с конфигурациями
config_manager = ConfigManager()
config = {
    "clock_settings": {"source": "PPS"},
    "sma_settings": {
        "inputs": {"sma1": "PPS1"},
        "outputs": {"sma1": "PHC"}
    }
}
config_manager.save_config(config, "my_config")
```

## Основные классы

### QuantumPCIDevice
Основной класс для работы с устройством:
- `get_device_info()` - информация об устройстве
- `set_clock_source(source)` - установка источника синхронизации
- `set_sma_input/output(port, signal)` - настройка SMA портов
- `is_healthy()` - проверка состояния

### StatusReader
Класс для мониторинга и чтения статусов:
- `get_full_status()` - полный статус устройства
- `start_monitoring()` - запуск мониторинга
- `export_status()` - экспорт статуса в файл

### ConfigManager
Менеджер конфигураций:
- `save_config()` - сохранение конфигурации
- `load_config()` - загрузка конфигурации
- `validate_config()` - валидация конфигурации

## Изменения в рефакторинге

### Улучшения архитектуры:
- Разделение ответственности между модулями
- Централизованная обработка ошибок
- Типизация с использованием type hints
- Улучшенное логирование

### Новые возможности:
- Система health checks
- Автоматический мониторинг изменений
- Валидация конфигураций
- Экспорт в различные форматы
- CLI интерфейс

### Улучшения GUI:
- Модульная структура компонентов
- Автоматическое обновление статуса
- Улучшенная обработка ошибок
- Поддержка горячих клавиш

## Совместимость

Рефакторированная версия полностью совместима с оригинальными устройствами QUANTUM-PCI и поддерживает все функции предыдущих версий.

## Лицензия

© 2024 QUANTUM-PCI Development Team

## Поддержка

Для получения поддержки обращайтесь к документации или создавайте issue в репозитории.