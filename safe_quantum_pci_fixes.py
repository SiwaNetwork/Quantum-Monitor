#!/usr/bin/env python3
"""
Критические исправления для предотвращения зависания системы в QUANTUM-PCI программе
Применить эти изменения к соответствующим файлам
"""

import signal
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
import threading
from typing import Optional


# 1. ИСПРАВЛЕНИЕ БЕСКОНЕЧНОГО ЦИКЛА в quantum_pci_status_reader.py
def safe_continuous_monitoring(self, duration=None, interval=1, format_type="json", output_file=None):
    """Безопасная версия continuous_monitoring с защитой от зависания"""
    
    # Флаг остановки
    self._stop_monitoring = False
    
    # Максимальное количество итераций для безопасности  
    max_iterations = 10000 if duration is None else int(duration / interval) + 100
    iteration_count = 0
    
    start_time = time.time()
    
    print("Starting safe monitoring...")
    print(f"Duration: {duration}, Interval: {interval}, Max iterations: {max_iterations}")
    
    if output_file:
        print(f"Output file: {output_file}")
    
    try:
        while (iteration_count < max_iterations and 
               not self._stop_monitoring):
            
            current_time = time.time()
            iteration_count += 1
            
            # Проверка времени выполнения
            if duration and (current_time - start_time) >= duration:
                print(f"Duration limit reached: {duration} seconds")
                break
            
            # Проверка каждые 100 итераций
            if iteration_count % 100 == 0:
                print(f"Iteration {iteration_count}/{max_iterations}")
            
            try:
                # Получение статуса с timeout
                with timeout(10):  # 10 секунд timeout
                    status = self.get_full_status()
                
                # Вывод статуса
                if format_type == "json":
                    import json
                    output = json.dumps(status, indent=2)
                elif format_type == "compact":
                    output = self._format_compact_status(status)
                else:
                    output = str(status)
                
                if output_file:
                    with open(output_file, 'a') as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                        f.write(output + "\n\n")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Status updated")
                    
            except TimeoutError:
                print(f"Warning: Status read timed out at iteration {iteration_count}")
                
            except Exception as e:
                print(f"Error getting status at iteration {iteration_count}: {e}")
                
            # Безопасная пауза
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                print("Monitoring interrupted by user")
                break
                
    except KeyboardInterrupt:
        print("Monitoring stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"Critical error in monitoring: {e}")
    finally:
        print(f"Monitoring completed. Total iterations: {iteration_count}")
        self._stop_monitoring = True


# 2. КОНТЕКСТНЫЙ МЕНЕДЖЕР ДЛЯ TIMEOUT
@contextmanager
def timeout(duration):
    """Контекстный менеджер для операций с timeout"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {duration} seconds")
    
    # Сохраняем старый обработчик
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


# 3. БЕЗОПАСНАЯ ФУНКЦИЯ ВЫПОЛНЕНИЯ КОМАНД
def safe_run_command(command, timeout_sec=30, show_error=True):
    """Безопасная версия run_command с timeout"""
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
            error_msg = f"Command failed: {command}\nError: {result.stderr.strip()}"
            if show_error:
                print(error_msg)
            return None
            
    except subprocess.TimeoutExpired:
        error_msg = f"Command timeout after {timeout_sec}s: {command}"
        if show_error:
            print(error_msg)
        return None
        
    except Exception as e:
        error_msg = f"Command error: {command}\nException: {str(e)}"
        if show_error:
            print(error_msg)
        return None


# 4. БЕЗОПАСНОЕ ОБНАРУЖЕНИЕ УСТРОЙСТВА
def safe_detect_device(self):
    """Безопасная версия detect_device с timeout и проверками"""
    
    print("Starting safe device detection...")
    
    # Флаг обнаружения
    device_found = False
    
    try:
        # Ограничиваем время поиска
        with timeout(15):
            # Поиск устройства через lspci с timeout
            pci_result = safe_run_command("lspci | grep -i quantum", timeout_sec=10, show_error=False)
            if not pci_result:
                pci_result = safe_run_command("lspci | grep 0x0400", timeout_sec=10, show_error=False)
            
            # Поиск в /sys/class/timecard/ с безопасными проверками
            timecard_path = Path("/sys/class/timecard")
            
            if timecard_path.exists() and timecard_path.is_dir():
                print(f"Checking timecard directory: {timecard_path}")
                
                try:
                    # Получаем список директорий с timeout
                    device_dirs = [d for d in timecard_path.iterdir() 
                                 if d.is_dir() and d.name.startswith("ocp")]
                    
                    for device_dir in device_dirs:
                        print(f"Checking device: {device_dir}")
                        
                        # Проверяем основные файлы устройства
                        essential_files = ["clock_source", "serialnum"]
                        files_exist = []
                        
                        for file_name in essential_files:
                            file_path = device_dir / file_name
                            try:
                                with timeout(2):  # 2 секунды на файл
                                    exists = file_path.exists() and file_path.is_file()
                                    files_exist.append(exists)
                                    if exists:
                                        # Проверяем возможность чтения
                                        with timeout(2):
                                            file_path.read_text()
                                            
                            except (TimeoutError, PermissionError, OSError) as e:
                                print(f"Cannot access {file_path}: {e}")
                                files_exist.append(False)
                        
                        # Если все основные файлы доступны
                        if all(files_exist):
                            self.device_path = device_dir
                            device_found = True
                            print(f"Device found and verified: {device_dir}")
                            break
                        else:
                            print(f"Device {device_dir} failed verification")
                            
                except PermissionError as e:
                    print(f"Permission denied accessing timecard directory: {e}")
                except OSError as e:
                    print(f"OS error accessing timecard directory: {e}")
            else:
                print("Timecard directory not found or not accessible")
                
    except TimeoutError:
        print("Device detection timed out (15 seconds)")
        device_found = False
        
    except Exception as e:
        print(f"Unexpected error during device detection: {e}")
        device_found = False
    
    # Обновляем интерфейс
    if hasattr(self, 'device_status_label'):
        if device_found:
            self.device_status_label.config(text=f"Device: {self.device_path.name}")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Device detected")
            print("Device detection successful")
        else:
            self.device_status_label.config(text="Device: Not detected")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="No device found")
            print("No device detected")
    
    return device_found


# 5. БЕЗОПАСНЫЙ ЦИКЛ МОНИТОРИНГА ДЛЯ GUI
def safe_status_update_loop(self):
    """Безопасная версия status_update_loop с защитой от зависания"""
    
    print("Starting safe status monitoring loop...")
    iteration_count = 0
    max_iterations = 86400  # Максимум 24 часа при интервале 1 сек
    
    while (self.status_running and 
           not getattr(self, '_stop_flag', False) and 
           iteration_count < max_iterations):
        
        iteration_count += 1
        
        try:
            # Получаем интервал обновления
            try:
                interval = float(self.update_interval_var.get())
                if interval < 0.1:  # Минимум 100мс
                    interval = 0.1
                elif interval > 3600:  # Максимум 1 час
                    interval = 3600
            except (ValueError, AttributeError):
                interval = 1.0
            
            if self.device_path and self.device_path.exists():
                timestamp = time.strftime("%H:%M:%S")
                
                # Обновление параметров с timeout
                for param_name, file_name in [
                    ("Clock source", "clock_source"),
                    ("GNSS sync", "gnss_sync"),
                    ("Serial number", "serialnum")
                ]:
                    try:
                        with timeout(3):  # 3 секунды на операцию
                            param_file = self.device_path / file_name
                            if param_file.exists():
                                value = param_file.read_text().strip()
                                if hasattr(self, 'log_status'):
                                    self.log_status(f"[{timestamp}] {param_name}: {value}")
                                    
                    except TimeoutError:
                        if hasattr(self, 'log_status'):
                            self.log_status(f"[{timestamp}] {param_name}: TIMEOUT")
                    except Exception as e:
                        if hasattr(self, 'log_status'):
                            self.log_status(f"[{timestamp}] {param_name}: ERROR - {e}")
            
            # Безопасная пауза
            time.sleep(interval)
            
        except Exception as e:
            print(f"Error in monitoring loop iteration {iteration_count}: {e}")
            time.sleep(1.0)  # Пауза при ошибке
            
    print(f"Status monitoring loop completed after {iteration_count} iterations")


# 6. БЕЗОПАСНАЯ ОСТАНОВКА МОНИТОРИНГА
def safe_stop_monitoring(self):
    """Безопасная остановка всех процессов мониторинга"""
    
    print("Stopping monitoring safely...")
    
    # Устанавливаем флаги остановки
    self.status_running = False
    self._stop_flag = True
    
    if hasattr(self, '_stop_monitoring'):
        self._stop_monitoring = True
    
    # Ждем завершения потока с timeout
    if hasattr(self, 'status_update_thread') and self.status_update_thread:
        if self.status_update_thread.is_alive():
            print("Waiting for monitoring thread to stop...")
            self.status_update_thread.join(timeout=5.0)
            
            if self.status_update_thread.is_alive():
                print("Warning: Monitoring thread did not stop gracefully")
            else:
                print("Monitoring thread stopped successfully")
    
    print("Monitoring stopped")


# 7. ИСПОЛЬЗОВАНИЕ В КОДЕ
"""
Чтобы применить эти исправления:

1. В quantum_pci_status_reader.py:
   - Заменить метод continuous_monitoring на safe_continuous_monitoring

2. В quantum_pci_configurator.py:
   - Заменить метод run_command на safe_run_command
   - Заменить метод detect_device на safe_detect_device  
   - Заменить метод status_update_loop на safe_status_update_loop
   - Заменить метод stop_monitoring на safe_stop_monitoring

3. Добавить в начало файлов:
   - Импорт signal
   - Контекстный менеджер timeout

4. В конструкторе класса добавить:
   - self._stop_flag = False
   - self._stop_monitoring = False
"""

if __name__ == "__main__":
    print("Этот файл содержит исправления для предотвращения зависания системы")
    print("Примените функции к соответствующим файлам проекта")