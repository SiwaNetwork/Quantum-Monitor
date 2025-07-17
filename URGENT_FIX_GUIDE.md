# СРОЧНОЕ РУКОВОДСТВО: Устранение зависания системы QUANTUM-PCI

## 🚨 НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ

### 1. Проверка текущего состояния системы
```bash
# Проверить запущенные Python процессы
ps aux | grep python

# Если есть зависшие процессы:
sudo killall python3
sudo pkill -f quantum_pci
```

### 2. Проверка системных логов
```bash
# Проверить системные сообщения
sudo dmesg | tail -20

# Проверить загрузку CPU
top -b -n 1 | head -10
```

## 🔧 ОСНОВНЫЕ ПРИЧИНЫ ЗАВИСАНИЯ

### 1. **КРИТИЧНО: Бесконечный цикл в quantum_pci_status_reader.py**
- Строки 334-350: `while True:` без условий выхода
- Может работать бесконечно без duration

### 2. **Блокирующие файловые операции**
- Чтение файлов устройства без timeout
- Обращение к несуществующим `/sys/class/timecard/` файлам

### 3. **Системные команды без timeout**
- `subprocess.check_output()` может зависнуть
- `lspci` команды без ограничений времени

## ⚡ БЫСТРОЕ РЕШЕНИЕ

### Вариант 1: Использовать демо-режим
```bash
cd extracted_project
python3 demo.py
# Создаст mock-устройство для безопасного тестирования
```

### Вариант 2: Запуск с ограничениями
```bash
# Установить timeout для всего процесса
timeout 60 python3 quantum_pci_configurator.py
# Программа автоматически завершится через 60 секунд
```

### Вариант 3: Использовать исправленную версию
```bash
# Перейти в обновленную версию
cd refactored_quantum_pci
python3 main.py --cli
# Более безопасная реализация
```

## 🛠️ ДОЛГОСРОЧНОЕ ИСПРАВЛЕНИЕ

### 1. Примените исправления из safe_quantum_pci_fixes.py:

```python
# Добавить в начало quantum_pci_status_reader.py:
import signal
from contextlib import contextmanager

@contextmanager
def timeout(duration):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {duration} seconds")
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
```

### 2. Заменить опасный цикл:
```python
# ЗАМЕНИТЬ ЭТО:
while True:
    # ... код ...

# НА ЭТО:
max_iterations = 10000
iteration_count = 0
while iteration_count < max_iterations and not self._stop_monitoring:
    iteration_count += 1
    try:
        with timeout(10):
            # ... код с timeout ...
    except TimeoutError:
        print("Operation timed out")
        break
```

## 🔍 ДИАГНОСТИКА ПРОБЛЕМ

### Если программа уже запущена и зависла:
```bash
# Найти PID процесса
ps aux | grep quantum_pci

# Получить трассировку стека (заменить PID)
sudo gdb -p <PID> -batch -ex "thread apply all bt"

# Принудительно завершить
sudo kill -9 <PID>
```

### Мониторинг ресурсов во время работы:
```bash
# В другом терминале
watch -n 1 'ps aux | grep python; echo "---"; top -b -n 1 | head -5'
```

## ⚠️ ПРОФИЛАКТИКА

### 1. **Всегда используйте timeout:**
```python
# Для файловых операций
with timeout(5):
    data = file.read_text()

# Для subprocess
subprocess.run(cmd, timeout=30)
```

### 2. **Ограничивайте циклы:**
```python
max_iterations = 1000
for i in range(max_iterations):
    if stop_condition:
        break
```

### 3. **Используйте daemon threads:**
```python
thread = threading.Thread(target=func, daemon=True)
```

### 4. **Добавляйте обработку сигналов:**
```python
import signal
def signal_handler(signum, frame):
    global running
    running = False
signal.signal(signal.SIGINT, signal_handler)
```

## 🚀 РЕКОМЕНДУЕМЫЙ ПОРЯДОК ДЕЙСТВИЙ

1. **Сначала:** Остановить все запущенные процессы
2. **Проверить:** Состояние системы и логи
3. **Тестировать:** На demo.py перед реальным устройством
4. **Применить:** Исправления из safe_quantum_pci_fixes.py
5. **Запускать:** С ограничениями времени (timeout)

## 📞 В СЛУЧАЕ ПОВТОРНОГО ЗАВИСАНИЯ

1. Перезагрузить систему: `sudo reboot`
2. Не запускать программу до исправления
3. Использовать только demo-режим для разработки
4. Применить все исправления из анализа

**ВАЖНО:** Никогда не запускайте программу на продакшн системе без этих исправлений!