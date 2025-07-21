#!/usr/bin/env python3
"""
Pure CLI версия QUANTUM-PCI Monitor без GUI зависимостей
Мониторинг всех параметров драйвера ptp_ocp
"""

import os
import sys
import time
import json
import signal
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


@contextmanager
def timeout(duration):
    """Контекстный менеджер для операций с timeout"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {duration} seconds")
    
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
            if show_error:
                print(f"Command failed: {command}\nError: {result.stderr.strip()}")
            return None
            
    except subprocess.TimeoutExpired:
        if show_error:
            print(f"Command timeout after {timeout_sec}s: {command}")
        return None
        
    except Exception as e:
        if show_error:
            print(f"Command error: {command}\nException: {str(e)}")
        return None


class QuantumPCIMonitor:
    """Pure CLI монитор QUANTUM-PCI без GUI зависимостей"""
    
    # Полный список атрибутов драйвера ptp_ocp
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
        'signal_generators': [
            'duty', 'period', 'phase', 'polarity', 'running', 'start', 'signal'
        ],
        # Частотные счетчики (динамически проверяются)
        'frequency_counters': [
            'frequency', 'seconds'
        ]
    }
    
    def __init__(self, device_path: Optional[str] = None):
        self.device_path = self._find_device_path(device_path)
        self._stop_monitoring = False
        
    def _find_device_path(self, device_path: Optional[str] = None) -> Optional[Path]:
        """Безопасный поиск пути к устройству"""
        print("Starting safe device detection...")
        
        if device_path:
            path = Path(device_path)
            if path.exists():
                print(f"Using specified device path: {path}")
                return path
            else:
                print(f"Specified device path {device_path} does not exist")
        
        # Автоматический поиск в /sys/class/timecard/
        timecard_path = Path("/sys/class/timecard")
        if timecard_path.exists() and timecard_path.is_dir():
            print(f"Checking timecard directory: {timecard_path}")
            
            for device_dir in timecard_path.iterdir():
                if device_dir.is_dir() and device_dir.name.startswith("ocp"):
                    print(f"Checking device: {device_dir}")
                    
                    # Проверяем основные файлы устройства
                    essential_files = ["serialnum", "available_clock_sources"]
                    if all((device_dir / f).exists() for f in essential_files):
                        print(f"Device found and verified: {device_dir}")
                        return device_dir
                    else:
                        print(f"Device {device_dir} failed verification")
        else:
            print("Timecard directory not found or not accessible")
        
        return None
    
    def is_device_available(self) -> bool:
        """Проверка доступности устройства"""
        return self.device_path is not None and self.device_path.exists()
    
    def read_device_file(self, file_name: str) -> Optional[str]:
        """Безопасное чтение файла устройства"""
        if not self.device_path:
            return None
            
        file_path = self.device_path / file_name
        try:
            with timeout(5):
                if file_path.exists() and file_path.is_file():
                    return file_path.read_text().strip()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return None
    
    def scan_available_attributes(self) -> Dict[str, List[str]]:
        """Сканирование всех доступных атрибутов устройства"""
        available = {
            'basic': [],
            'sma': [],
            'tod': [],
            'signal_generators': {},
            'frequency_counters': {}
        }
        
        if not self.is_device_available():
            print("Device not available for attribute scanning")
            return available
        
        print("Scanning device attributes...")
        
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
            for attr in self.ALL_DEVICE_ATTRIBUTES['signal_generators']:
                if self._check_attribute_exists(f"signal{i}_{attr}"):
                    gen_attrs.append(attr)
            if gen_attrs:
                available['signal_generators'][f'signal{i}'] = gen_attrs
        
        # Сканирование частотных счетчиков
        for i in range(1, 5):
            freq_attrs = []
            for attr in self.ALL_DEVICE_ATTRIBUTES['frequency_counters']:
                if self._check_attribute_exists(f"freq{i}_{attr}"):
                    freq_attrs.append(attr)
            if freq_attrs:
                available['frequency_counters'][f'freq{i}'] = freq_attrs
        
        return available
    
    def _check_attribute_exists(self, attr_name: str) -> bool:
        """Проверка существования атрибута на устройстве"""
        try:
            attr_path = self.device_path / attr_name
            return attr_path.exists() and attr_path.is_file()
        except Exception:
            return False
    
    def get_full_status(self) -> Dict[str, Any]:
        """Получение полного статуса устройства"""
        if not self.is_device_available():
            return {"error": "Device not available", "timestamp": datetime.now().isoformat()}
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "device_path": str(self.device_path),
            "available_attributes": self.scan_available_attributes(),
            "basic_attributes": {},
            "sma_attributes": {},
            "tod_attributes": {},
            "signal_generators": {},
            "frequency_counters": {}
        }
        
        # Чтение всех доступных атрибутов
        available = status["available_attributes"]
        
        # Основные атрибуты
        for attr in available.get('basic', []):
            value = self.read_device_file(attr)
            if value is not None:
                status["basic_attributes"][attr] = value
        
        # SMA атрибуты
        for attr in available.get('sma', []):
            value = self.read_device_file(attr)
            if value is not None:
                status["sma_attributes"][attr] = value
        
        # TOD атрибуты
        for attr in available.get('tod', []):
            value = self.read_device_file(attr)
            if value is not None:
                status["tod_attributes"][attr] = value
        
        # Генераторы сигналов
        for gen_name, attrs in available.get('signal_generators', {}).items():
            gen_status = {}
            for attr in attrs:
                value = self.read_device_file(f"{gen_name}_{attr}")
                if value is not None:
                    gen_status[attr] = value
            if gen_status:
                status["signal_generators"][gen_name] = gen_status
        
        # Частотные счетчики
        for freq_name, attrs in available.get('frequency_counters', {}).items():
            freq_status = {}
            for attr in attrs:
                value = self.read_device_file(f"{freq_name}_{attr}")
                if value is not None:
                    freq_status[attr] = value
            if freq_status:
                status["frequency_counters"][freq_name] = freq_status
        
        return status
    
    def print_status_report(self):
        """Печать подробного отчета о состоянии устройства"""
        print("=" * 80)
        print("QUANTUM-PCI Pure CLI Monitor - Full Device Status Report")
        print("=" * 80)
        
        status = self.get_full_status()
        
        if "error" in status:
            print(f"ERROR: {status['error']}")
            return
        
        print(f"Timestamp: {status['timestamp']}")
        print(f"Device Path: {status['device_path']}")
        print()
        
        # Статистика атрибутов
        available = status['available_attributes']
        total_basic = len(available.get('basic', []))
        total_sma = len(available.get('sma', []))
        total_tod = len(available.get('tod', []))
        total_signal_gen = len(available.get('signal_generators', {}))
        total_freq_count = len(available.get('frequency_counters', {}))
        
        print("ATTRIBUTE SUMMARY:")
        print(f"  Basic attributes: {total_basic}")
        print(f"  SMA attributes: {total_sma}")
        print(f"  TOD attributes: {total_tod}")
        print(f"  Signal generators: {total_signal_gen}")
        print(f"  Frequency counters: {total_freq_count}")
        print()
        
        # Основные атрибуты
        if status.get('basic_attributes'):
            print("BASIC ATTRIBUTES:")
            for attr, value in status['basic_attributes'].items():
                print(f"  {attr}: {value}")
            print()
        
        # SMA атрибуты
        if status.get('sma_attributes'):
            print("SMA ATTRIBUTES:")
            for attr, value in status['sma_attributes'].items():
                print(f"  {attr}: {value}")
            print()
        
        # TOD атрибуты
        if status.get('tod_attributes'):
            print("TOD ATTRIBUTES:")
            for attr, value in status['tod_attributes'].items():
                print(f"  {attr}: {value}")
            print()
        
        # Генераторы сигналов
        if status.get('signal_generators'):
            print("SIGNAL GENERATORS:")
            for gen_name, gen_data in status['signal_generators'].items():
                print(f"  {gen_name}:")
                for attr, value in gen_data.items():
                    print(f"    {attr}: {value}")
            print()
        
        # Частотные счетчики
        if status.get('frequency_counters'):
            print("FREQUENCY COUNTERS:")
            for freq_name, freq_data in status['frequency_counters'].items():
                print(f"  {freq_name}:")
                for attr, value in freq_data.items():
                    print(f"    {attr}: {value}")
            print()
    
    def monitor_continuous(self, interval: int = 5, duration: int = 60):
        """Непрерывный мониторинг"""
        print(f"Starting continuous monitoring (interval: {interval}s, duration: {duration}s)")
        print("Press Ctrl+C to stop...")
        
        start_time = time.time()
        iteration = 0
        
        try:
            while not self._stop_monitoring:
                current_time = time.time()
                if current_time - start_time > duration:
                    break
                
                iteration += 1
                print(f"\n--- Iteration {iteration} ({datetime.now().strftime('%H:%M:%S')}) ---")
                
                # Быстрая проверка основных параметров
                if self.is_device_available():
                    clock_source = self.read_device_file("clock_source")
                    gnss_sync = self.read_device_file("gnss_sync")
                    print(f"Clock Source: {clock_source}, GNSS Sync: {gnss_sync}")
                else:
                    print("Device not available")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        
        print(f"Monitoring completed after {iteration} iterations")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="QUANTUM-PCI Pure CLI Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--device", 
        type=str,
        help="Path to QUANTUM-PCI device (auto-detected if not specified)"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show full device status report"
    )
    
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Start continuous monitoring"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Monitoring interval in seconds (default: 5)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Monitoring duration in seconds (default: 60)"
    )
    
    parser.add_argument(
        "--export",
        type=str,
        help="Export full status to JSON file"
    )
    
    args = parser.parse_args()
    
    # Создание монитора
    monitor = QuantumPCIMonitor(args.device)
    
    if not monitor.is_device_available():
        print("ERROR: QUANTUM-PCI device not found")
        print("Please check that:")
        print("1. The device is properly connected")
        print("2. The driver is loaded (modprobe ptp_ocp)")
        print("3. You have sufficient permissions")
        sys.exit(1)
    
    if args.status:
        monitor.print_status_report()
    
    if args.monitor:
        monitor.monitor_continuous(args.interval, args.duration)
    
    if args.export:
        try:
            status = monitor.get_full_status()
            with open(args.export, 'w') as f:
                json.dump(status, f, indent=2)
            print(f"Status exported to: {args.export}")
        except Exception as e:
            print(f"Error exporting status: {e}")
    
    if not (args.status or args.monitor or args.export):
        # По умолчанию показываем краткий статус
        print("QUANTUM-PCI Pure CLI Monitor")
        print(f"Device: {monitor.device_path}")
        
        if monitor.is_device_available():
            # Показываем основную информацию
            serial = monitor.read_device_file("serialnum")
            clock_source = monitor.read_device_file("clock_source")
            gnss_sync = monitor.read_device_file("gnss_sync")
            
            print(f"Serial Number: {serial}")
            print(f"Clock Source: {clock_source}")
            print(f"GNSS Sync: {gnss_sync}")
            
            print("\nUse --status for full report or --monitor for continuous monitoring")
        else:
            print("Device not accessible")


if __name__ == "__main__":
    main()