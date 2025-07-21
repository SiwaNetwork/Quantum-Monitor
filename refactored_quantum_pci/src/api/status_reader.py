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


@contextmanager
def thread_safe_timeout(duration):
    """Потокобезопасный контекстный менеджер для операций с timeout"""
    start_time = time.time()
    
    class TimeoutChecker:
        def __init__(self, timeout_duration):
            self.timeout_duration = timeout_duration
            self.start_time = time.time()
        
        def check(self):
            if time.time() - self.start_time > self.timeout_duration:
                raise TimeoutError(f"Operation timed out after {self.timeout_duration} seconds")
    
    checker = TimeoutChecker(duration)
    try:
        yield checker
    finally:
        pass


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
    
    # Полный список атрибутов драйвера на основе анализа ptp_ocp.c
    ALL_DEVICE_ATTRIBUTES = {
        # Основные атрибуты устройства
        'basic': [
            'serialnum', 'gnss_sync', 'clock_source', 'available_clock_sources',
            'external_pps_cable_delay', 'internal_pps_cable_delay', 'holdover',
            'mac_i2c', 'utc_tai_offset', 'ts_window_adjust', 'irig_b_mode',
            'clock_status_drift', 'clock_status_offset'
        ],
        # SMA интерфейсы
        'sma': [
            'sma1', 'sma2', 'sma3', 'sma4',
            'available_sma_inputs', 'available_sma_outputs'
        ],
        # TOD (Time of Day) протокол
        'tod': [
            'tod_protocol', 'available_tod_protocols',
            'tod_baud_rate', 'available_tod_baud_rates',
            'tod_correction'
        ],
        # Генераторы сигналов (динамически проверяются)
        'signal_generators': {
            'signal': ['duty', 'period', 'phase', 'polarity', 'running', 'start', 'signal']
        },
        # Частотные счетчики (динамически проверяются)
        'frequency_counters': {
            'freq': ['frequency', 'seconds']
        }
    }
    
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
        
        # Кэш для доступных атрибутов
        self._available_attributes = None
        self._last_scan_time = None
        
    def scan_available_attributes(self, force_rescan: bool = False) -> Dict[str, List[str]]:
        """
        Сканирование всех доступных атрибутов устройства
        
        Args:
            force_rescan: Принудительное повторное сканирование
            
        Returns:
            Словарь с доступными атрибутами по категориям
        """
        # Проверяем кэш (обновляем каждые 60 секунд)
        current_time = time.time()
        if (not force_rescan and self._available_attributes is not None and 
            self._last_scan_time is not None and 
            current_time - self._last_scan_time < 60):
            return self._available_attributes
        
        available = {
            'basic': [],
            'sma': [],
            'tod': [],
            'signal_generators': {},
            'frequency_counters': {}
        }
        
        if not self.device or not self.device.device_path:
            self.logger.warning("Device not available for attribute scanning")
            return available
        
        # Сканирование основных атрибутов
        for attr in self.ALL_DEVICE_ATTRIBUTES['basic']:
            if self._check_attribute_exists(attr):
                available['basic'].append(attr)
        
        # Сканирование SMA атрибутов
        for attr in self.ALL_DEVICE_ATTRIBUTES['sma']:
            if self._check_attribute_exists(attr):
                available['sma'].append(attr)
        
        # Сканирование TOD атрибутов
        for attr in self.ALL_DEVICE_ATTRIBUTES['tod']:
            if self._check_attribute_exists(attr):
                available['tod'].append(attr)
        
        # Сканирование генераторов сигналов
        for i in range(1, 5):
            gen_attrs = []
            for attr in self.ALL_DEVICE_ATTRIBUTES['signal_generators']['signal']:
                if self._check_attribute_exists(f"signal{i}_{attr}"):
                    gen_attrs.append(attr)
            if gen_attrs:
                available['signal_generators'][f'signal{i}'] = gen_attrs
        
        # Сканирование частотных счетчиков
        for i in range(1, 5):
            freq_attrs = []
            for attr in self.ALL_DEVICE_ATTRIBUTES['frequency_counters']['freq']:
                if self._check_attribute_exists(f"freq{i}_{attr}"):
                    freq_attrs.append(attr)
            if freq_attrs:
                available['frequency_counters'][f'freq{i}'] = freq_attrs
        
        # Сохранение в кэш
        self._available_attributes = available
        self._last_scan_time = current_time
        
        # Логирование результатов
        total_attrs = (len(available['basic']) + len(available['sma']) + 
                      len(available['tod']) + len(available['signal_generators']) + 
                      len(available['frequency_counters']))
        self.logger.info(f"Device attribute scan complete: {total_attrs} categories found")
        
        return available
    
    def _check_attribute_exists(self, attr_name: str) -> bool:
        """Проверка существования атрибута на устройстве"""
        try:
            attr_path = self.device.device_path / attr_name
            return attr_path.exists() and attr_path.is_file()
        except Exception as e:
            self.logger.debug(f"Error checking attribute {attr_name}: {e}")
            return False
    
    def get_device_capabilities(self) -> Dict[str, bool]:
        """
        Определение доступных возможностей устройства
        на основе наличия соответствующих директорий/файлов
        """
        capabilities = {
            "basic": True,  # Базовые функции всегда доступны
            "signal_generators": False,
            "frequency_counters": False,
            "irig": False,
            "tod": False
        }
        
        try:
            # Проверка генераторов сигналов (gen1-gen4)
            for i in range(1, 5):
                gen_dir = self.device.device_path / f"gen{i}"
                if gen_dir.exists() and gen_dir.is_dir():
                    capabilities["signal_generators"] = True
                    break
            
            # Проверка частотных счетчиков (freq1-freq4)
            for i in range(1, 5):
                freq_dir = self.device.device_path / f"freq{i}"
                if freq_dir.exists() and freq_dir.is_dir():
                    capabilities["frequency_counters"] = True
                    break
            
            # Проверка IRIG-B
            irig_file = self.device.device_path / "irig_b_mode"
            if irig_file.exists():
                capabilities["irig"] = True
            
            # Проверка TOD (Time of Day)
            tod_file = self.device.device_path / "tod_protocol"
            if tod_file.exists():
                capabilities["tod"] = True
                
        except Exception as e:
            self.logger.error(f"Error checking device capabilities: {e}")
        
        return capabilities

    def get_full_status(self) -> Dict[str, Any]:
        """Получение полного статуса устройства со всеми доступными параметрами"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "device_info": self.device.get_device_info(),
            "device_capabilities": self.get_device_capabilities(),
            "available_attributes": self.scan_available_attributes(),
            "clock_status": self.device.get_clock_status(),
            "sma_configuration": self.device.get_sma_configuration(),
            "health_status": {
                "healthy": self.device.is_healthy(),
                "checks": self._perform_health_checks()
            }
        }
        
        # Добавляем все доступные основные атрибуты
        basic_attributes = self._get_all_basic_attributes()
        if basic_attributes:
            status["basic_attributes"] = basic_attributes
        
        # Добавляем TOD атрибуты если доступны
        tod_attributes = self._get_tod_attributes()
        if tod_attributes:
            status["tod_attributes"] = tod_attributes
        
        # Добавляем статус генераторов только если они поддерживаются
        capabilities = status["device_capabilities"]
        if capabilities["signal_generators"]:
            status["generators"] = self._get_generator_status()
        
        # Добавляем статус частотных счетчиков только если они поддерживаются
        if capabilities["frequency_counters"]:
            status["frequency_counters"] = self._get_frequency_counter_status()
        
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
    
    def _get_all_basic_attributes(self) -> Dict[str, Any]:
        """Получение всех доступных основных атрибутов"""
        attributes = {}
        available = self.scan_available_attributes()
        
        for attr in available.get('basic', []):
            try:
                value = self.device.read_device_file(attr)
                if value is not None:
                    attributes[attr] = value
            except Exception as e:
                self.logger.warning(f"Error reading basic attribute {attr}: {e}")
                attributes[attr] = f"ERROR: {e}"
        
        return attributes
    
    def _get_tod_attributes(self) -> Dict[str, Any]:
        """Получение атрибутов TOD (Time of Day) протокола"""
        attributes = {}
        available = self.scan_available_attributes()
        
        for attr in available.get('tod', []):
            try:
                value = self.device.read_device_file(attr)
                if value is not None:
                    attributes[attr] = value
            except Exception as e:
                self.logger.warning(f"Error reading TOD attribute {attr}: {e}")
                attributes[attr] = f"ERROR: {e}"
        
        return attributes
    
    def _get_generator_status(self) -> Dict[str, Any]:
        """Получение статуса генераторов сигналов (только доступных)"""
        generators = {
            "timestamp": datetime.now().isoformat(),
        }
        
        # Сначала проверяем, какие генераторы реально доступны
        for i in range(1, 5):
            gen_dir = self.device.device_path / f"gen{i}"
            if not gen_dir.exists() or not gen_dir.is_dir():
                self.logger.debug(f"Generator gen{i} not available - skipping")
                continue
                
            gen_info = {}
            gen_files = ["duty", "period", "phase", "polarity", "running", "start", "signal"]
            
            for file_name in gen_files:
                # Проверяем существование файла перед чтением
                file_path = gen_dir / file_name
                if file_path.exists() and file_path.is_file():
                    try:
                        value = self.device.read_device_file(f"gen{i}/{file_name}")
                        if value is not None:
                            gen_info[file_name] = value
                    except Exception as e:
                        self.logger.warning(f"Error reading gen{i}/{file_name}: {e}")
            
            if gen_info:
                generators[f"gen{i}"] = gen_info
        
        return generators
    
    def _get_frequency_counter_status(self) -> Dict[str, Any]:
        """Получение статуса частотных счетчиков (только доступных)"""
        freq_counters = {
            "timestamp": datetime.now().isoformat(),
        }
        
        # Сначала проверяем, какие частотные счетчики реально доступны
        for i in range(1, 5):
            freq_dir = self.device.device_path / f"freq{i}"
            if not freq_dir.exists() or not freq_dir.is_dir():
                self.logger.debug(f"Frequency counter freq{i} not available - skipping")
                continue
                
            freq_info = {}
            freq_files = ["frequency", "seconds"]
            
            for file_name in freq_files:
                # Проверяем существование файла перед чтением
                file_path = freq_dir / file_name
                if file_path.exists() and file_path.is_file():
                    try:
                        value = self.device.read_device_file(f"freq{i}/{file_name}")
                        if value is not None:
                            freq_info[file_name] = value
                    except Exception as e:
                        self.logger.warning(f"Error reading freq{i}/{file_name}: {e}")
            
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
                    # Используем простой timeout без сигналов для потокобезопасности
                    start_time = time.time()
                    current_status = self.get_full_status()
                    elapsed = time.time() - start_time
                    
                    if elapsed > 10:  # Если операция заняла больше 10 секунд
                        self.logger.warning(f"Status read took {elapsed:.2f} seconds")
                    
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