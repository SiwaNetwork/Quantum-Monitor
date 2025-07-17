# Анализ проблем зависания системы в QUANTUM-PCI программе

## Выявленные проблемы

### 1. Бесконечный цикл в status_reader.py (КРИТИЧНО)

**Файл:** `extracted_project/quantum_pci_status_reader.py`, строки 334-350

**Проблема:** Бесконечный цикл `while True:` без правильной обработки условий выхода:

```python
while True:
    current_time = time.time()
    
    # Проверка времени выполнения
    if duration and (current_time - start_time) >= duration:
        break
    
    # Получение статуса
    status = self.get_full_status()
    # ... обработка статуса ...
```

**Причина зависания:** Если `duration` не задан (None), цикл выполняется бесконечно без возможности выхода.

### 2. Потоки мониторинга без правильной синхронизации

**Файлы:** 
- `extracted_project/quantum_pci_configurator.py` (строки 771-802)
- `refactored_quantum_pci/src/api/status_reader.py` (строки 170-200)

**Проблема:** Циклы мониторинга могут блокироваться при обращении к файлам устройства:

```python
def status_update_loop(self):
    while self.status_running:
        # Чтение файлов устройства без timeout
        clock_file = self.device_path / "clock_source"
        if clock_file.exists():
            clock_source = clock_file.read_text().strip()  # Может зависнуть
```

### 3. Системные команды без timeout

**Файл:** `extracted_project/configurator.py`, строки 5-15

**Проблема:** Использование `subprocess.check_output` без timeout:

```python
def run_command(command):
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        return output.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"
```

### 4. Блокирующее обнаружение устройства

**Файл:** `extracted_project/quantum_pci_configurator.py`, строки 378-420

**Проблема:** Метод `detect_device()` может блокироваться при попытке обращения к несуществующим файлам устройства.

### 5. Отсутствие устройства вызывает зависание GUI

**Проблема:** При отсутствии реального устройства QUANTUM-PCI, программа пытается многократно обращаться к файлам в `/sys/class/timecard/`, что может вызвать зависание системы.

## Рекомендации по исправлению

### 1. Исправление бесконечного цикла

```python
# В quantum_pci_status_reader.py
def continuous_monitoring(self, duration=None, interval=1, format_type="json", output_file=None):
    start_time = time.time()
    max_iterations = 10000  # Максимум итераций для безопасности
    iteration_count = 0
    
    try:
        while iteration_count < max_iterations:
            current_time = time.time()
            iteration_count += 1
            
            # Проверка времени выполнения
            if duration and (current_time - start_time) >= duration:
                break
                
            # Проверка сигнала прерывания
            if hasattr(self, '_stop_monitoring') and self._stop_monitoring:
                break
            
            # Получение статуса с timeout
            try:
                status = self.get_full_status()
                # ... обработка ...
            except Exception as e:
                print(f"Error getting status: {e}")
                time.sleep(interval)
                continue
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Monitoring stopped by user")
```

### 2. Добавление timeout для файловых операций

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout(duration):
    def timeout_handler(signum, frame):
        raise TimeoutError("Operation timed out")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    try:
        yield
    finally:
        signal.alarm(0)

# Использование:
try:
    with timeout(5):  # 5 секунд timeout
        clock_source = clock_file.read_text().strip()
except TimeoutError:
    print("File read timed out")
    clock_source = "UNKNOWN"
```

### 3. Исправление системных команд

```python
def run_command(command, timeout_sec=30):
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout_sec
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout_sec} seconds"
    except Exception as e:
        return f"Error: {str(e)}"
```

### 4. Безопасное обнаружение устройства

```python
def detect_device(self):
    """Безопасное обнаружение устройства с timeout"""
    self.status_label.config(text="Detecting device...")
    
    try:
        # Поиск с timeout
        with timeout(10):
            timecard_path = Path("/sys/class/timecard")
            device_found = False
            
            if timecard_path.exists():
                for device_dir in timecard_path.iterdir():
                    if device_dir.is_dir() and device_dir.name.startswith("ocp"):
                        # Проверка доступности файлов устройства
                        essential_files = ["clock_source", "serialnum"]
                        all_files_exist = all(
                            (device_dir / f).exists() for f in essential_files
                        )
                        
                        if all_files_exist:
                            self.device_path = device_dir
                            device_found = True
                            break
                            
    except TimeoutError:
        print("Device detection timed out")
        device_found = False
    except Exception as e:
        print(f"Error during device detection: {e}")
        device_found = False
    
    # Остальная логика...
```

### 5. Добавление флага прерывания мониторинга

```python
class QuantumPCIConfigurator:
    def __init__(self):
        # ...
        self._stop_flag = False
        
    def stop_monitoring(self):
        """Безопасная остановка мониторинга"""
        self.status_running = False
        self._stop_flag = True
        
        if self.status_update_thread and self.status_update_thread.is_alive():
            self.status_update_thread.join(timeout=5.0)
            
    def status_update_loop(self):
        """Улучшенный цикл обновления статуса"""
        while self.status_running and not self._stop_flag:
            try:
                # ... логика мониторинга с проверками timeout ...
                time.sleep(interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval)
```

## Быстрое решение проблемы

1. **Немедленное действие:** Перезагрузить систему и больше не запускать программу до исправления
2. **Временное решение:** Использовать demo-режим:
   ```bash
   cd extracted_project
   python3 demo.py  # Создает mock-устройство
   ```
3. **Проверка системы:** 
   ```bash
   sudo dmesg | tail -50  # Проверить системные сообщения
   ps aux | grep python   # Найти зависшие процессы Python
   sudo killall python3   # Завершить все процессы Python при необходимости
   ```

## Профилактические меры

1. Всегда использовать timeout для файловых операций
2. Добавлять максимальное количество итераций в циклы
3. Использовать daemon threads для фоновых задач
4. Добавлять обработку сигналов прерывания (Ctrl+C)
5. Тестировать программу без реального устройства на mock-данных