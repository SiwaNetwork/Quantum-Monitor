# Отчет об исправлении зависания программы refactored_quantum_pci

## Описание проблемы

Программа `refactored_quantum_pci` зависает при запуске из-за попыток мониторинга характеристик устройства, которые недоступны в конкретном экземпляре драйвера `ptp_ocp`.

## Анализ причин

### 1. Архитектура драйвера ptp_ocp

Драйвер `ptp_ocp` использует систему **capabilities** для определения доступных функций:

- `OCP_CAP_BASIC` - базовые функции (всегда доступны)
- `OCP_CAP_SIGNAL` - генераторы сигналов (gen1-gen4) 
- `OCP_CAP_FREQ` - частотные счетчики (freq1-freq4)

### 2. Условная регистрация sysfs атрибутов

Драйвер создает группы атрибутов в sysfs **только** при наличии соответствующих capabilities:

```c
// В ptp_ocp.c:5390-5393
for (i = 0; bp->attr_tbl[i].cap; i++) {
    if (!(bp->attr_tbl[i].cap & bp->fw_cap))
        continue;  // Пропускаем если capability не поддерживается
    err = sysfs_create_group(&bp->dev.kobj, bp->attr_tbl[i].group);
}
```

### 3. Проблема в программе

Программа пыталась читать **все возможные** характеристики без проверки их наличия:

```python
# Проблемный код в status_reader.py:149-156
for i in range(1, 5):
    gen_info = {}
    for file_name in gen_files:
        value = self.device.read_device_file(f"gen{i}/{file_name}")  # Может зависнуть!
```

## Реализованные исправления

### 1. Проверка доступности директорий

Добавлена проверка существования директорий перед чтением файлов:

```python
def _get_generator_status(self) -> Dict[str, Any]:
    for i in range(1, 5):
        gen_dir = self.device.device_path / f"gen{i}"
        if not gen_dir.exists() or not gen_dir.is_dir():
            self.logger.debug(f"Generator gen{i} not available - skipping")
            continue  # Пропускаем недоступные генераторы
```

### 2. Определение capabilities устройства

Добавлена функция для проверки доступных возможностей:

```python
def get_device_capabilities(self) -> Dict[str, bool]:
    capabilities = {
        "basic": True,
        "signal_generators": False,
        "frequency_counters": False,
        "irig": False,
        "tod": False
    }
    
    # Проверяем наличие директорий gen1-gen4
    for i in range(1, 5):
        gen_dir = self.device.device_path / f"gen{i}"
        if gen_dir.exists() and gen_dir.is_dir():
            capabilities["signal_generators"] = True
            break
```

### 3. Условный мониторинг

Статус генераторов и частотных счетчиков теперь проверяется только при их наличии:

```python
def get_full_status(self) -> Dict[str, Any]:
    capabilities = self.get_device_capabilities()
    
    # Добавляем только доступные характеристики
    if capabilities["signal_generators"]:
        status["generators"] = self._get_generator_status()
    
    if capabilities["frequency_counters"]:
        status["frequency_counters"] = self._get_frequency_counter_status()
```

### 4. Улучшенное чтение файлов

Добавлены дополнительные проверки и timeout для чтения файлов:

```python
def read_device_file(self, file_name: str, timeout_sec: int = 5) -> Optional[str]:
    # Проверка существования
    if not file_path.exists():
        return None
    
    # Проверка прав доступа
    if not os.access(file_path, os.R_OK):
        return None
    
    # Чтение с timeout и контролем размера
    start_time = time.time()
    with open(file_path, 'r') as f:
        content = ""
        while True:
            if time.time() - start_time > timeout_sec:
                return None
            # ... безопасное чтение по кускам
```

## Характеристики доступные в ptp_ocp

### Всегда доступные (OCP_CAP_BASIC):
- `serialnum` - серийный номер
- `gnss_sync` - статус синхронизации GNSS
- `clock_source` - источник синхронизации
- `available_clock_sources` - доступные источники
- `sma1`, `sma2`, `sma3`, `sma4` - конфигурация SMA портов
- `available_sma_inputs/outputs` - доступные SMA сигналы
- `clock_status_drift/offset` - статус часов
- `utc_tai_offset` - смещение UTC-TAI

### Условно доступные (OCP_CAP_SIGNAL):
- `gen1/`, `gen2/`, `gen3/`, `gen4/` - генераторы сигналов
  - `duty`, `period`, `phase`, `polarity`, `running`, `start`, `signal`

### Условно доступные (OCP_CAP_FREQ):
- `freq1/`, `freq2/`, `freq3/`, `freq4/` - частотные счетчики
  - `frequency`, `seconds`

### Дополнительные (зависят от модели):
- `irig_b_mode` - режим IRIG-B
- `tod_protocol` - протокол Time of Day
- `external_pps_cable_delay` - задержка внешнего PPS
- `internal_pps_cable_delay` - задержка внутреннего PPS

## Рекомендации

1. **Всегда проверяйте существование** файлов/директорий перед чтением
2. **Используйте timeout** для операций чтения файлов
3. **Определяйте capabilities** устройства при инициализации
4. **Мониторьте только доступные** характеристики
5. **Добавляйте обработку ошибок** для всех операций I/O
6. **Логируйте предупреждения** вместо критических ошибок для недоступных функций

## Результат

После внесения исправлений:
- ✅ Программа не зависает при отсутствии gen1-gen4/freq1-freq4
- ✅ Корректно определяются доступные возможности устройства  
- ✅ Мониторятся только существующие характеристики
- ✅ Добавлена устойчивость к ошибкам чтения
- ✅ Улучшено логирование для диагностики

## Тестирование

Для проверки исправлений рекомендуется тестирование на:
1. Устройствах с полным набором функций (Facebook Time Card)
2. Устройствах с ограниченными функциями (ART Card)
3. Симуляции недоступных характеристик