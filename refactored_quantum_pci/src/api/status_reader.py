"""
Рефакторированный модуль для чтения статусов QUANTUM-PCI устройства
"""

import time
import json
import signal
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import logging
import threading
from pathlib import Path
from contextlib import contextmanager

from ..core.device import QuantumPCIDevice
from ..core.exceptions import QuantumPCIError


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


class StatusReader:
    """Класс для чтения и мониторинга статусов QUANTUM-PCI устройства"""
    
    def __init__(self, device: Optional[QuantumPCIDevice] = None, logger: Optional[logging.Logger] = None):
        """
        Инициализация StatusReader
        
        Args:
            device: Экземпляр QuantumPCIDevice
            logger: Логгер для записи сообщений
        """
        self.logger = logger or logging.getLogger(__name__)
        self.device = device or QuantumPCIDevice(logger=self.logger)
        self._monitoring_active = False
        self._monitoring_thread = None
        self._callbacks = {}
        self._stop_flag = False
        self._stop_monitoring = False
        
    def get_full_status(self) -> Dict[str, Any]:
        """Получение полного статуса устройства"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "device_info": self.device.get_device_info(),
            "clock_status": self.device.get_clock_status(),
            "sma_configuration": self.device.get_sma_configuration(),
            "generators": self._get_generator_status(),
            "frequency_counters": self._get_frequency_counter_status(),
            "health_status": {
                "healthy": self.device.is_healthy(),
                "checks": self._perform_health_checks()
            }
        }
        return status
    
    def get_clock_status(self) -> Dict[str, Any]:
        """Получение расширенного статуса часов"""
        base_status = self.device.get_clock_status()
        
        # Добавление дополнительной информации
        extended_status = {
            **base_status,
            "source": self.device.get_current_clock_source(),
            "available_sources": self.device.get_available_clock_sources(),
            "utc_tai_offset": self.device.read_device_file("utc_tai_offset"),
            "internal_pps_delay": self.device.read_device_file("internal_pps_cable_delay"),
            "external_pps_delay": self.device.read_device_file("external_pps_cable_delay"),
            "irig_mode": self.device.read_device_file("irig_b_mode")
        }
        
        return extended_status
    
    def _get_generator_status(self) -> Dict[str, Any]:
        """Получение статуса генераторов сигналов"""
        generators = {
            "timestamp": datetime.now().isoformat(),
        }
        
        for i in range(1, 5):
            gen_info = {}
            gen_files = ["duty", "period", "phase", "polarity", "running", "start", "signal"]
            
            for file_name in gen_files:
                value = self.device.read_device_file(f"gen{i}/{file_name}")
                if value is not None:
                    gen_info[file_name] = value
            
            if gen_info:
                generators[f"gen{i}"] = gen_info
        
        return generators
    
    def _get_frequency_counter_status(self) -> Dict[str, Any]:
        """Получение статуса частотных счетчиков"""
        freq_counters = {
            "timestamp": datetime.now().isoformat(),
        }
        
        for i in range(1, 5):
            freq_info = {}
            freq_files = ["frequency", "seconds"]
            
            for file_name in freq_files:
                value = self.device.read_device_file(f"freq{i}/{file_name}")
                if value is not None:
                    freq_info[file_name] = value
            
            if freq_info:
                freq_counters[f"freq{i}"] = freq_info
        
        return freq_counters
    
    def _perform_health_checks(self) -> Dict[str, Any]:
        """Выполнение проверок состояния устройства"""
        checks = {}
        
        try:
            # Проверка базовых параметров
            checks["device_accessible"] = self.device.device_path.exists()
            checks["serial_readable"] = self.device.read_device_file("serialnum") is not None
            
            # Проверка синхронизации
            gnss_sync = self.device.read_device_file("gnss_sync")
            # Правильная проверка: SYNC означает синхронизацию, LOST означает потерю сигнала
            checks["gnss_synchronized"] = gnss_sync and gnss_sync.strip().upper() == "SYNC"
            
            # Проверка источника синхронизации
            clock_source = self.device.get_current_clock_source()
            checks["clock_source_set"] = clock_source is not None and clock_source != "NONE"
            
            # Проверка дрейфа часов
            drift = self.device.read_device_file("clock_status_drift")
            if drift:
                try:
                    drift_value = float(drift)
                    checks["clock_drift_acceptable"] = abs(drift_value) < 1000  # Пример порога
                except ValueError:
                    checks["clock_drift_acceptable"] = False
            else:
                checks["clock_drift_acceptable"] = None
            
        except Exception as e:
            self.logger.error(f"Error performing health checks: {e}")
            checks["error"] = str(e)
        
        return checks
    
    def start_monitoring(self, interval: float = 1.0, callbacks: Optional[Dict[str, Callable]] = None):
        """
        Запуск мониторинга в отдельном потоке
        
        Args:
            interval: Интервал обновления в секундах
            callbacks: Словарь callback функций для различных событий
        """
        if self._monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self._callbacks = callbacks or {}
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self._monitoring_thread.start()
        self.logger.info("Status monitoring started")
    
    def stop_monitoring(self):
        """Безопасная остановка всех процессов мониторинга"""
        
        self.logger.info("Stopping monitoring safely...")
        
        # Устанавливаем флаги остановки
        self._monitoring_active = False
        self._stop_flag = True
        self._stop_monitoring = True
        
        # Ждем завершения потока с timeout
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self.logger.info("Waiting for monitoring thread to stop...")
            self._monitoring_thread.join(timeout=5.0)
            
            if self._monitoring_thread.is_alive():
                self.logger.warning("Warning: Monitoring thread did not stop gracefully")
            else:
                self.logger.info("Monitoring thread stopped successfully")
        
        self.logger.info("Status monitoring stopped")
    
    def _monitoring_loop(self, interval: float):
        """Безопасная версия _monitoring_loop с защитой от зависания"""
        last_status = {}
        iteration_count = 0
        max_iterations = 86400  # Максимум 24 часа при интервале 1 сек
        
        self.logger.info("Starting safe status monitoring loop...")
        
        while (self._monitoring_active and 
               not self._stop_flag and 
               iteration_count < max_iterations):
            
            iteration_count += 1
            
            try:
                # Ограничиваем интервал
                if interval < 0.1:  # Минимум 100мс
                    interval = 0.1
                elif interval > 3600:  # Максимум 1 час
                    interval = 3600
                
                # Получение статуса с timeout
                try:
                    with timeout(10):  # 10 секунд timeout
                        current_status = self.get_full_status()
                    
                    # Вызов callback для полного статуса
                    if "on_status_update" in self._callbacks:
                        self._callbacks["on_status_update"](current_status)
                    
                    # Проверка изменений и вызов соответствующих callback
                    self._check_status_changes(last_status, current_status)
                    
                    last_status = current_status
                    
                except TimeoutError:
                    self.logger.warning(f"Status read timed out at iteration {iteration_count}")
                    if "on_error" in self._callbacks:
                        self._callbacks["on_error"](TimeoutError("Status read timeout"))
                
                # Безопасная пауза
                try:
                    time.sleep(interval)
                except KeyboardInterrupt:
                    self.logger.info("Monitoring interrupted by user")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error in monitoring loop iteration {iteration_count}: {e}")
                if "on_error" in self._callbacks:
                    self._callbacks["on_error"](e)
                time.sleep(1.0)  # Пауза при ошибке
                
        self.logger.info(f"Status monitoring loop completed after {iteration_count} iterations")
    
    def _check_status_changes(self, old_status: Dict[str, Any], new_status: Dict[str, Any]):
        """Проверка изменений статуса и вызов соответствующих callback"""
        try:
            # Проверка изменения источника синхронизации
            old_clock_source = old_status.get("clock_status", {}).get("source")
            new_clock_source = new_status.get("clock_status", {}).get("source")
            
            if old_clock_source != new_clock_source and "on_clock_source_change" in self._callbacks:
                self._callbacks["on_clock_source_change"](old_clock_source, new_clock_source)
            
            # Проверка изменения статуса GNSS
            old_gnss = old_status.get("clock_status", {}).get("gnss_sync")
            new_gnss = new_status.get("clock_status", {}).get("gnss_sync")
            
            if old_gnss != new_gnss and "on_gnss_status_change" in self._callbacks:
                self._callbacks["on_gnss_status_change"](old_gnss, new_gnss)
            
            # Проверка изменения состояния здоровья
            old_health = old_status.get("health_status", {}).get("healthy")
            new_health = new_status.get("health_status", {}).get("healthy")
            
            if old_health != new_health and "on_health_change" in self._callbacks:
                self._callbacks["on_health_change"](old_health, new_health)
                
        except Exception as e:
            self.logger.error(f"Error checking status changes: {e}")
    
    def export_status(self, output_file: str, format: str = "json") -> bool:
        """
        Экспорт текущего статуса в файл
        
        Args:
            output_file: Путь к выходному файлу
            format: Формат экспорта ("json" или "csv")
            
        Returns:
            True при успехе
        """
        try:
            status = self.get_full_status()
            output_path = Path(output_file)
            
            if format.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(status, f, indent=4, ensure_ascii=False)
                    
            elif format.lower() == "csv":
                import csv
                # Упрощенный экспорт основных параметров в CSV
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Parameter", "Value"])
                    
                    # Основная информация
                    device_info = status.get("device_info", {})
                    writer.writerow(["Serial Number", device_info.get("serial_number")])
                    writer.writerow(["Clock Source", device_info.get("current_clock_source")])
                    writer.writerow(["GNSS Sync", device_info.get("gnss_sync")])
                    
                    # Статус часов
                    clock_status = status.get("clock_status", {})
                    writer.writerow(["Clock Drift", clock_status.get("drift")])
                    writer.writerow(["Clock Offset", clock_status.get("offset")])
                    
                    # SMA конфигурация
                    sma_config = status.get("sma_configuration", {})
                    for port, value in sma_config.get("inputs", {}).items():
                        writer.writerow([f"SMA {port} Input", value])
                    for port, value in sma_config.get("outputs", {}).items():
                        writer.writerow([f"SMA {port} Output", value])
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Status exported to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting status: {e}")
            return False
    
    def safe_continuous_monitoring(self, duration=None, interval=1, format_type="json", output_file=None):
        """Безопасная версия continuous_monitoring с защитой от зависания"""
        
        # Флаг остановки
        self._stop_monitoring = False
        
        # Максимальное количество итераций для безопасности  
        max_iterations = 10000 if duration is None else int(duration / interval) + 100
        iteration_count = 0
        
        start_time = time.time()
        
        self.logger.info("Starting safe monitoring...")
        self.logger.info(f"Duration: {duration}, Interval: {interval}, Max iterations: {max_iterations}")
        
        if output_file:
            self.logger.info(f"Output file: {output_file}")
        
        try:
            while (iteration_count < max_iterations and 
                   not self._stop_monitoring):
                
                current_time = time.time()
                iteration_count += 1
                
                # Проверка времени выполнения
                if duration and (current_time - start_time) >= duration:
                    self.logger.info(f"Duration limit reached: {duration} seconds")
                    break
                
                # Проверка каждые 100 итераций
                if iteration_count % 100 == 0:
                    self.logger.info(f"Iteration {iteration_count}/{max_iterations}")
                
                try:
                    # Получение статуса с timeout
                    with timeout(10):  # 10 секунд timeout
                        status = self.get_full_status()
                    
                    # Вывод статуса
                    if format_type == "json":
                        output = json.dumps(status, indent=2)
                    elif format_type == "compact":
                        output = self._format_compact_status(status) if hasattr(self, '_format_compact_status') else str(status)
                    else:
                        output = str(status)
                    
                    if output_file:
                        with open(output_file, 'a') as f:
                            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                            f.write(output + "\n\n")
                    else:
                        self.logger.info(f"[{time.strftime('%H:%M:%S')}] Status updated")
                        
                except TimeoutError:
                    self.logger.warning(f"Warning: Status read timed out at iteration {iteration_count}")
                    
                except Exception as e:
                    self.logger.error(f"Error getting status at iteration {iteration_count}: {e}")
                    
                # Безопасная пауза
                try:
                    time.sleep(interval)
                except KeyboardInterrupt:
                    self.logger.info("Monitoring interrupted by user")
                    break
                    
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user (Ctrl+C)")
        except Exception as e:
            self.logger.error(f"Critical error in monitoring: {e}")
        finally:
            self.logger.info(f"Monitoring completed. Total iterations: {iteration_count}")
            self._stop_monitoring = True