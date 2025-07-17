# PTP OCP Driver Monitor

Система мониторинга для драйвера PTP OCP (Open Compute Project Precision Time Protocol).

## Описание

Этот проект предоставляет набор инструментов для мониторинга и анализа работы драйвера `ptp_ocp` в Linux. Система позволяет отслеживать:

- Вызовы функций драйвера
- Изменения sysfs атрибутов
- Производительность операций
- Состояние устройства в реальном времени

## Компоненты

### 1. ptp_ocp_monitor.py
Основной скрипт мониторинга, который:
- Читает sysfs атрибуты устройства
- Использует ftrace для отслеживания вызовов функций
- Сохраняет данные в JSON формате
- Поддерживает многопоточный сбор данных

### 2. sysfs_reader.py
Утилита для работы с sysfs интерфейсом:
- Автоматический поиск PTP OCP устройств
- Чтение всех доступных атрибутов
- Мониторинг изменений атрибутов в реальном времени
- Экспорт данных в JSON

### 3. ptp_ocp_trace.py
Трассировщик функций с использованием eBPF:
- Отслеживание вызовов функций драйвера
- Измерение времени выполнения
- Фильтрация по длительности выполнения
- Минимальное влияние на производительность

## Мониторируемые функции

Система отслеживает следующие функции драйвера `ptp_ocp`:

### Основные PTP операции:
- `ptp_ocp_gettimex` - получение времени
- `ptp_ocp_settime` - установка времени
- `ptp_ocp_adjtime` - корректировка времени
- `ptp_ocp_adjfine` - точная подстройка частоты
- `ptp_ocp_enable` - включение/выключение функций

### Управление временными метками:
- `ptp_ocp_ts_enable` - управление временными метками
- `ptp_ocp_ts_irq` - обработка прерываний временных меток

### Управление сигналами:
- `ptp_ocp_signal_enable` - управление выходными сигналами
- `ptp_ocp_signal_from_perout` - конфигурация периодических выходов

### SMA (SubMiniature version A) разъемы:
- `ptp_ocp_sma_store` - запись конфигурации SMA
- `ptp_ocp_sma_show` - чтение конфигурации SMA

### Управление устройством:
- `ptp_ocp_probe` - инициализация устройства
- `ptp_ocp_remove` - удаление устройства
- `ptp_ocp_watchdog` - функция сторожевого таймера
- `ptp_ocp_read_eeprom` - чтение EEPROM

## Sysfs атрибуты

Мониторируются следующие sysfs атрибуты:

### Конфигурация SMA:
- `sma1`, `sma2`, `sma3`, `sma4` - конфигурация SMA разъемов
- `available_sma_inputs` - доступные входы SMA
- `available_sma_outputs` - доступные выходы SMA

### Информация об устройстве:
- `serialnum` - серийный номер
- `gnss_sync` - статус синхронизации GNSS
- `utc_tai_offset` - смещение UTC-TAI
- `holdover` - режим удержания

### Параметры синхронизации:
- `external_pps_cable_delay` - задержка внешнего PPS кабеля
- `internal_pps_cable_delay` - задержка внутреннего PPS кабеля
- `ts_window_adjust` - настройка окна временных меток

### Источники времени:
- `clock_source` - текущий источник времени
- `available_clock_sources` - доступные источники
- `clock_status_drift` - дрейф часов
- `clock_status_offset` - смещение часов

### TOD (Time of Day) протокол:
- `tod_protocol` - протокол TOD
- `available_tod_protocols` - доступные протоколы
- `tod_baud_rate` - скорость передачи TOD
- `tod_correction` - коррекция TOD

## Установка

### Требования:
- Linux с загруженным модулем `ptp_ocp`
- Python 3.6+
- Для eBPF трассировки: BCC (BPF Compiler Collection)
- Права root для некоторых операций

### Установка зависимостей:

```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip
sudo apt-get install bpfcc-tools python3-bpfcc  # для eBPF

# RHEL/CentOS
sudo yum install python3 python3-pip
sudo yum install bcc-tools python-bcc  # для eBPF
```

## Использование

### 1. Базовый мониторинг:

```bash
# Мониторинг sysfs атрибутов и функций
sudo python3 src/ptp_ocp_monitor.py

# С указанием конкретного устройства
sudo python3 src/ptp_ocp_monitor.py -d /sys/bus/pci/devices/0000:01:00.0

# С сохранением в лог файл
sudo python3 src/ptp_ocp_monitor.py -l monitor.log -v
```

### 2. Чтение sysfs атрибутов:

```bash
# Показать все найденные устройства и их атрибуты
python3 src/sysfs_reader.py

# Экспорт данных в JSON
python3 src/sysfs_reader.py -e device_info.json

# Мониторинг конкретного атрибута
python3 src/sysfs_reader.py -m /sys/class/timecard/ocp0 clock_source -i 0.5
```

### 3. Трассировка функций с eBPF:

```bash
# Трассировка всех функций
sudo python3 src/ptp_ocp_trace.py

# Показывать только функции длительностью > 100 мкс
sudo python3 src/ptp_ocp_trace.py -d 100

# Трассировка конкретных функций
sudo python3 src/ptp_ocp_trace.py -f ptp_ocp_adjtime -f ptp_ocp_gettimex
```

## Примеры вывода

### Sysfs Reader:
```
=== PTP OCP Devices Found ===

PCI Devices:
  - 0000:06:00.0 at /sys/bus/pci/devices/0000:06:00.0
    Vendor: 0x1d9b Device: 0x0400
    Serial Number: WW1234567
    Clock Source: GNSS
    GNSS Sync: 1
    SMA1: IN: 10MHz
    SMA2: IN: PPS1
    SMA3: OUT: 10MHz
    SMA4: OUT: PPS
```

### Function Tracer:
```
[14:32:15.123] chronyd          PID:  1234 TID:  1234 ptp_ocp_gettimex                 duration:    12.45 μs
[14:32:15.124] phc2sys          PID:  5678 TID:  5678 ptp_ocp_adjtime                  duration:    23.67 μs
```

## Доступ через /sys/class

Согласно статье TimeBeats, устройство PTP OCP доступно через следующие пути в sysfs:

1. **PCI устройство**: `/sys/bus/pci/devices/XXXX:XX:XX.X/`
2. **Timecard класс**: `/sys/class/timecard/ocpN/`
3. **PTP clock**: `/sys/class/ptp/ptpN/`

Где:
- `XXXX:XX:XX.X` - PCI адрес устройства
- `ocpN` - номер OCP устройства (ocp0, ocp1, ...)
- `ptpN` - номер PTP clock (ptp0, ptp1, ...)

## Отладка

### Проверка загрузки драйвера:
```bash
lsmod | grep ptp_ocp
```

### Просмотр сообщений драйвера:
```bash
dmesg | grep ptp_ocp
```

### Проверка PCI устройства:
```bash
lspci -v | grep -A 20 "Time Card"
```

## Лицензия

Этот проект распространяется под лицензией GPL-2.0, совместимой с драйвером ptp_ocp.

## Ссылки

- [Драйвер ptp_ocp в ядре Linux](https://github.com/torvalds/linux/blob/master/drivers/ptp/ptp_ocp.c)
- [Open Compute Project Time Card](https://www.opencompute.org/wiki/Time_Appliances_Project)
- [TimeBeats статья о доступе к устройству](https://support.timebeat.app/hc/en-gb/articles/13653309251090-Accessing-the-device-through-the-sys-class-directory)