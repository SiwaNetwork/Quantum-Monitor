#!/usr/bin/env python3
"""
QUANTUM-PCI Status Reader
Считыватель статусов для платы QUANTUM-PCI с поддержкой различных режимов работы
"""

import os
import sys
import time
import json
import signal
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager


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


class QuantumPCIStatusReader:
    """Класс для чтения статусов платы QUANTUM-PCI"""
    
    def __init__(self, device_path: Optional[str] = None):
        self.device_path = self._find_device_path(device_path)
        self.last_status = {}
        self._stop_monitoring = False
        
    def _find_device_path(self, device_path: Optional[str] = None) -> Optional[Path]:
        """Поиск пути к устройству"""
        if device_path:
            path = Path(device_path)
            if path.exists():
                return path
            else:
                print(f"Warning: Specified device path {device_path} does not exist")
        
        # Автоматический поиск в /sys/class/timecard/
        timecard_base = Path("/sys/class/timecard")
        if timecard_base.exists():
            for device_dir in timecard_base.iterdir():
                if device_dir.is_dir() and device_dir.name.startswith("ocp"):
                    return device_dir
        
        return None
    
    def is_device_available(self) -> bool:
        """Проверка доступности устройства"""
        return self.device_path is not None and self.device_path.exists()
    
    def read_file_safe(self, file_path: Path) -> Optional[str]:
        """Безопасное чтение файла"""
        try:
            if file_path.exists() and file_path.is_file():
                return file_path.read_text().strip()
        except (PermissionError, OSError, IOError) as e:
            print(f"Warning: Cannot read {file_path}: {e}")
        return None
    
    def get_basic_info(self) -> Dict[str, Any]:
        """Получение базовой информации об устройстве"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        info = {
            "device_path": str(self.device_path),
            "timestamp": datetime.now().isoformat(),
        }
        
        # Основные файлы информации
        basic_files = [
            "serialnum", "clock_source", "gnss_sync", 
            "clock_status_drift", "clock_status_offset"
        ]
        
        for file_name in basic_files:
            file_path = self.device_path / file_name
            value = self.read_file_safe(file_path)
            info[file_name] = value
        
        return info
    
    def get_clock_status(self) -> Dict[str, Any]:
        """Получение статуса синхронизации"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        clock_status = {
            "timestamp": datetime.now().isoformat(),
        }
        
        # Текущий источник синхронизации
        clock_source_file = self.device_path / "clock_source"
        clock_status["current_source"] = self.read_file_safe(clock_source_file)
        
        # Доступные источники
        available_sources_file = self.device_path / "available_clock_sources"
        available_sources = self.read_file_safe(available_sources_file)
        if available_sources:
            clock_status["available_sources"] = available_sources.split()
        
        # Статус дрейфа и смещения
        drift_file = self.device_path / "clock_status_drift"
        clock_status["drift"] = self.read_file_safe(drift_file)
        
        offset_file = self.device_path / "clock_status_offset"
        clock_status["offset"] = self.read_file_safe(offset_file)
        
        return clock_status
    
    def get_sma_status(self) -> Dict[str, Any]:
        """Получение статуса SMA портов"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        sma_status = {
            "timestamp": datetime.now().isoformat(),
            "inputs": {},
            "outputs": {},
        }
        
        # Доступные входы
        available_inputs_file = self.device_path / "available_sma_inputs"
        available_inputs = self.read_file_safe(available_inputs_file)
        if available_inputs:
            sma_status["available_inputs"] = available_inputs.split()
        
        # Доступные выходы
        available_outputs_file = self.device_path / "available_sma_outputs"
        available_outputs = self.read_file_safe(available_outputs_file)
        if available_outputs:
            sma_status["available_outputs"] = available_outputs.split()
        
        # Текущие настройки SMA портов
        for i in range(1, 5):
            # Входы
            sma_input_file = self.device_path / f"sma{i}"
            input_value = self.read_file_safe(sma_input_file)
            if input_value is not None:
                sma_status["inputs"][f"sma{i}"] = input_value
            
            # Выходы
            sma_output_file = self.device_path / f"sma{i}_out"
            output_value = self.read_file_safe(sma_output_file)
            if output_value is not None:
                sma_status["outputs"][f"sma{i}"] = output_value
        
        return sma_status
    
    def get_generator_status(self) -> Dict[str, Any]:
        """Получение статуса генераторов сигналов"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        generators = {
            "timestamp": datetime.now().isoformat(),
        }
        
        for i in range(1, 5):
            gen_dir = self.device_path / f"gen{i}"
            if gen_dir.exists() and gen_dir.is_dir():
                gen_info = {}
                
                # Параметры генератора
                gen_files = ["duty", "period", "phase", "polarity", "running", "start", "signal"]
                for file_name in gen_files:
                    file_path = gen_dir / file_name
                    value = self.read_file_safe(file_path)
                    if value is not None:
                        gen_info[file_name] = value
                
                generators[f"gen{i}"] = gen_info
        
        return generators
    
    def get_frequency_counter_status(self) -> Dict[str, Any]:
        """Получение статуса частотных счетчиков"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        freq_counters = {
            "timestamp": datetime.now().isoformat(),
        }
        
        for i in range(1, 5):
            freq_dir = self.device_path / f"freq{i}"
            if freq_dir.exists() and freq_dir.is_dir():
                freq_info = {}
                
                # Параметры частотного счетчика
                freq_files = ["frequency", "seconds"]
                for file_name in freq_files:
                    file_path = freq_dir / file_name
                    value = self.read_file_safe(file_path)
                    if value is not None:
                        freq_info[file_name] = value
                
                freq_counters[f"freq{i}"] = freq_info
        
        return freq_counters
    
    def get_gnss_status(self) -> Dict[str, Any]:
        """Получение статуса GNSS"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        gnss_status = {
            "timestamp": datetime.now().isoformat(),
        }
        
        # GNSS синхронизация
        gnss_sync_file = self.device_path / "gnss_sync"
        sync_value = self.read_file_safe(gnss_sync_file)
        if sync_value:
            gnss_status["sync"] = sync_value
            gnss_status["synchronized"] = "1" in sync_value or "sync" in sync_value.lower()
        
        return gnss_status
    
    def get_timestamper_status(self) -> Dict[str, Any]:
        """Получение статуса временных меток"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        timestampers = {
            "timestamp": datetime.now().isoformat(),
        }
        
        for i in range(1, 5):
            ts_dir = self.device_path / f"ts{i}"
            if ts_dir.exists() and ts_dir.is_dir():
                ts_info = {}
                
                # Чтение всех файлов в директории timestamper
                for ts_file in ts_dir.iterdir():
                    if ts_file.is_file():
                        value = self.read_file_safe(ts_file)
                        if value is not None:
                            ts_info[ts_file.name] = value
                
                timestampers[f"ts{i}"] = ts_info
        
        return timestampers
    
    def get_ptp_status(self) -> Dict[str, Any]:
        """Получение статуса PTP"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        ptp_status = {
            "timestamp": datetime.now().isoformat(),
        }
        
        # PTP устройство
        ptp_link = self.device_path / "ptp"
        if ptp_link.exists():
            try:
                ptp_device = ptp_link.resolve().name
                ptp_status["device"] = ptp_device
                
                # Дополнительная информация о PTP через ptp4l
                try:
                    ptp_info = subprocess.run(
                        ["pmc", "-u", "-b", "0", "GET CURRENT_DATA_SET"],
                        capture_output=True, text=True, timeout=5
                    )
                    if ptp_info.returncode == 0:
                        ptp_status["ptp_info"] = ptp_info.stdout.strip()
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass
                
            except Exception as e:
                ptp_status["error"] = f"Cannot read PTP link: {e}"
        
        return ptp_status
    
    def get_pps_status(self) -> Dict[str, Any]:
        """Получение статуса PPS"""
        if not self.is_device_available():
            return {"error": "Device not available"}
        
        pps_status = {
            "timestamp": datetime.now().isoformat(),
        }
        
        # PPS устройство
        pps_link = self.device_path / "pps"
        if pps_link.exists():
            try:
                pps_device = pps_link.resolve().name
                pps_status["device"] = pps_device
            except Exception as e:
                pps_status["error"] = f"Cannot read PPS link: {e}"
        
        return pps_status
    
    def get_full_status(self) -> Dict[str, Any]:
        """Получение полного статуса устройства"""
        full_status = {
            "timestamp": datetime.now().isoformat(),
            "device_available": self.is_device_available(),
        }
        
        if not self.is_device_available():
            full_status["error"] = "Device not available"
            return full_status
        
        # Сбор всех статусов
        full_status.update({
            "basic_info": self.get_basic_info(),
            "clock_status": self.get_clock_status(),
            "sma_status": self.get_sma_status(),
            "gnss_status": self.get_gnss_status(),
        })
        
        return full_status
    
    def monitor_status(self, interval: float = 1.0, duration: Optional[float] = None, 
                      output_file: Optional[str] = None, format_type: str = "json"):
        """Безопасная версия мониторинга статуса с защитой от зависания"""
        if not self.is_device_available():
            print("Error: Device not available")
            return
        
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
                        output = json.dumps(status, indent=2)
                    elif format_type == "compact":
                        output = self._format_compact_status(status)
                    else:
                        output = self._format_human_readable_status(status)
                    
                    # Вывод в файл или консоль
                    if output_file:
                        with open(output_file, 'a') as f:
                            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n")
                            f.write(output + "\n\n")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] Status updated")
                        print("-" * 50)
                        
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
    
    def _format_compact_status(self, status: Dict[str, Any]) -> str:
        """Форматирование компактного статуса"""
        if not status.get("device_available"):
            return f"[{status['timestamp']}] Device not available"
        
        basic = status.get("basic_info", {})
        clock = status.get("clock_status", {})
        gnss = status.get("gnss_status", {})
        
        return (f"[{status['timestamp']}] "
                f"Clock: {clock.get('current_source', 'N/A')} "
                f"GNSS: {'SYNC' if gnss.get('synchronized') else 'NO_SYNC'} "
                f"Drift: {clock.get('drift', 'N/A')} "
                f"Offset: {clock.get('offset', 'N/A')}")
    
    def _format_human_readable_status(self, status: Dict[str, Any]) -> str:
        """Форматирование человекочитаемого статуса"""
        if not status.get("device_available"):
            return f"Device not available at {status['timestamp']}"
        
        output = []
        output.append(f"QUANTUM-PCI Status Report - {status['timestamp']}")
        output.append("=" * 60)
        
        # Базовая информация
        basic = status.get("basic_info", {})
        if basic:
            output.append("Basic Information:")
            output.append(f"  Device Path: {basic.get('device_path', 'N/A')}")
            output.append(f"  Serial Number: {basic.get('serialnum', 'N/A')}")
            output.append("")
        
        # Статус синхронизации
        clock = status.get("clock_status", {})
        if clock:
            output.append("Clock Synchronization:")
            output.append(f"  Current Source: {clock.get('current_source', 'N/A')}")
            output.append(f"  Drift: {clock.get('drift', 'N/A')}")
            output.append(f"  Offset: {clock.get('offset', 'N/A')}")
            if clock.get('available_sources'):
                output.append(f"  Available Sources: {', '.join(clock['available_sources'])}")
            output.append("")
        
        # GNSS статус
        gnss = status.get("gnss_status", {})
        if gnss:
            output.append("GNSS Status:")
            sync_status = "SYNCHRONIZED" if gnss.get('synchronized') else "NOT SYNCHRONIZED"
            output.append(f"  Synchronization: {sync_status}")
            output.append(f"  Raw Value: {gnss.get('sync', 'N/A')}")
            output.append("")
        
        # Генераторы
        generators = status.get("generator_status", {})
        if generators and len(generators) > 1:  # Больше чем только timestamp
            output.append("Signal Generators:")
            for gen_name, gen_info in generators.items():
                if gen_name != "timestamp" and isinstance(gen_info, dict):
                    running = gen_info.get('running', '0')
                    status_text = "RUNNING" if running == '1' else "STOPPED"
                    output.append(f"  {gen_name.upper()}: {status_text}")
                    if running == '1':
                        output.append(f"    Period: {gen_info.get('period', 'N/A')} ns")
                        output.append(f"    Duty: {gen_info.get('duty', 'N/A')}%")
            output.append("")
        
        return "\\n".join(output)
    
    def save_status_to_file(self, filename: str, format_type: str = "json"):
        """Сохранение текущего статуса в файл"""
        status = self.get_full_status()
        
        if format_type == "json":
            with open(filename, 'w') as f:
                json.dump(status, f, indent=2)
        else:
            with open(filename, 'w') as f:
                f.write(self._format_human_readable_status(status))
        
        print(f"Status saved to {filename}")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="QUANTUM-PCI Status Reader")
    parser.add_argument("--device", "-d", help="Device path (auto-detect if not specified)")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--format", "-f", choices=["json", "human", "compact"], 
                       default="human", help="Output format")
    parser.add_argument("--monitor", "-m", action="store_true", 
                       help="Enable real-time monitoring")
    parser.add_argument("--interval", "-i", type=float, default=1.0, 
                       help="Monitoring interval in seconds")
    parser.add_argument("--duration", "-t", type=float, 
                       help="Monitoring duration in seconds")
    parser.add_argument("--basic", "-b", action="store_true", 
                       help="Show only basic information")
    parser.add_argument("--clock", "-c", action="store_true", 
                       help="Show only clock status")
    parser.add_argument("--gnss", "-g", action="store_true", 
                       help="Show only GNSS status")
    parser.add_argument("--sma", "-s", action="store_true", 
                       help="Show only SMA status")
    parser.add_argument("--generators", action="store_true", 
                       help="Show only generator status")
    
    args = parser.parse_args()
    
    # Создание экземпляра считывателя
    reader = QuantumPCIStatusReader(args.device)
    
    if not reader.is_device_available():
        print("Error: QUANTUM-PCI device not found")
        print("Please ensure:")
        print("1. The device is properly installed")
        print("2. The ptp_ocp driver is loaded")
        print("3. You have sufficient permissions to access /sys/class/timecard/")
        sys.exit(1)
    
    # Режим мониторинга
    if args.monitor:
        reader.monitor_status(
            interval=args.interval,
            duration=args.duration,
            output_file=args.output,
            format_type=args.format
        )
        return
    
    # Получение конкретного статуса
    if args.basic:
        status = reader.get_basic_info()
    elif args.clock:
        status = reader.get_clock_status()
    elif args.gnss:
        status = reader.get_gnss_status()
    elif args.sma:
        status = reader.get_sma_status()
    elif args.generators:
        status = reader.get_generator_status()
    else:
        status = reader.get_full_status()
    
    # Форматирование вывода
    if args.format == "json":
        output = json.dumps(status, indent=2)
    elif args.format == "compact":
        output = reader._format_compact_status(status)
    else:
        output = reader._format_human_readable_status(status)
    
    # Вывод результата
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Status saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()

