"""
Рефакторированный модуль для чтения статусов QUANTUM-PCI устройства
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import logging
import threading
from pathlib import Path

from ..core.device import QuantumPCIDevice
from ..core.exceptions import QuantumPCIError


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
            checks["gnss_synchronized"] = gnss_sync == "1" if gnss_sync else False
            
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
        """Остановка мониторинга"""
        if self._monitoring_active:
            self._monitoring_active = False
            if self._monitoring_thread:
                self._monitoring_thread.join(timeout=5.0)
            self.logger.info("Status monitoring stopped")
    
    def _monitoring_loop(self, interval: float):
        """Основной цикл мониторинга"""
        last_status = {}
        
        while self._monitoring_active:
            try:
                current_status = self.get_full_status()
                
                # Вызов callback для полного статуса
                if "on_status_update" in self._callbacks:
                    self._callbacks["on_status_update"](current_status)
                
                # Проверка изменений и вызов соответствующих callback
                self._check_status_changes(last_status, current_status)
                
                last_status = current_status
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                if "on_error" in self._callbacks:
                    self._callbacks["on_error"](e)
                time.sleep(interval)
    
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