#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования QUANTUM-PCI инструментов
без реального устройства
"""

import os
import tempfile
import shutil
from pathlib import Path
import json


class MockQuantumDevice:
    """Создание mock устройства для демонстрации"""
    
    def __init__(self, base_path="/tmp/mock_timecard"):
        self.base_path = Path(base_path)
        self.device_path = self.base_path / "ocp0"
        
    def create_mock_device(self):
        """Создание структуры mock устройства"""
        print(f"Creating mock QUANTUM-PCI device at {self.device_path}")
        
        # Создание базовой структуры
        self.device_path.mkdir(parents=True, exist_ok=True)
        
        # Основные файлы устройства
        device_files = {
            "serialnum": "MOCK-QUANTUM-001",
            "clock_source": "PPS",
            "available_clock_sources": "NONE PPS TOD IRIG DCF",
            "gnss_sync": "1",
            "clock_status_drift": "123.456",
            "clock_status_offset": "-0.789",
            "available_sma_inputs": "10Mhz PPS1 PPS2 TS1 TS2 TS3 TS4 IRIG DCF FREQ1 FREQ2 FREQ3 FREQ4 None",
            "available_sma_outputs": "10Mhz PHC MAC GNSS1 GNSS2 IRIG DCF GEN1 GEN2 GEN3 GEN4 GND VCC",
            "sma1": "PPS1",
            "sma2": "TS1",
            "sma3": "None",
            "sma4": "None",
            "sma1_out": "PHC",
            "sma2_out": "GEN1",
            "sma3_out": "GND",
            "sma4_out": "GND",
            "irig_b_mode": "3"
        }
        
        # Создание файлов устройства
        for filename, content in device_files.items():
            file_path = self.device_path / filename
            file_path.write_text(content)
        
        # Создание генераторов
        for i in range(1, 5):
            gen_dir = self.device_path / f"gen{i}"
            gen_dir.mkdir(exist_ok=True)
            
            gen_files = {
                "duty": "50",
                "period": "1000000000",  # 1 секунда в наносекундах
                "phase": "0",
                "polarity": "1",
                "running": "0",
                "start": "0.0",
                "signal": "0"
            }
            
            for gen_file, gen_content in gen_files.items():
                (gen_dir / gen_file).write_text(gen_content)
        
        # Создание частотных счетчиков
        for i in range(1, 5):
            freq_dir = self.device_path / f"freq{i}"
            freq_dir.mkdir(exist_ok=True)
            
            freq_files = {
                "frequency": "10000000.0",  # 10 MHz
                "seconds": "1"
            }
            
            for freq_file, freq_content in freq_files.items():
                (freq_dir / freq_file).write_text(freq_content)
        
        # Создание timestampers
        for i in range(1, 5):
            ts_dir = self.device_path / f"ts{i}"
            ts_dir.mkdir(exist_ok=True)
            
            ts_files = {
                "enable": "0",
                "mode": "rising",
                "count": "0"
            }
            
            for ts_file, ts_content in ts_files.items():
                (ts_dir / ts_file).write_text(ts_content)
        
        # Создание символических ссылок для PTP и PPS
        try:
            ptp_link = self.device_path / "ptp"
            if not ptp_link.exists():
                ptp_link.symlink_to("/dev/ptp0")
        except OSError:
            pass  # Игнорируем ошибки создания ссылок
        
        try:
            pps_link = self.device_path / "pps"
            if not pps_link.exists():
                pps_link.symlink_to("/dev/pps0")
        except OSError:
            pass
        
        print("Mock device created successfully!")
        return str(self.device_path)
    
    def cleanup(self):
        """Удаление mock устройства"""
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
            print("Mock device cleaned up")


def test_status_reader(device_path):
    """Тестирование считывателя статусов"""
    print("\\n=== Testing Status Reader ===")
    
    import subprocess
    
    # Тест базовой информации
    print("\\n1. Basic information:")
    result = subprocess.run([
        "python3", "quantum_pci_status_reader.py", 
        "--device", device_path, "--basic"
    ], capture_output=True, text=True)
    print(result.stdout)
    
    # Тест статуса синхронизации
    print("\\n2. Clock status:")
    result = subprocess.run([
        "python3", "quantum_pci_status_reader.py", 
        "--device", device_path, "--clock"
    ], capture_output=True, text=True)
    print(result.stdout)
    
    # Тест GNSS статуса
    print("\\n3. GNSS status:")
    result = subprocess.run([
        "python3", "quantum_pci_status_reader.py", 
        "--device", device_path, "--gnss"
    ], capture_output=True, text=True)
    print(result.stdout)
    
    # Тест JSON формата
    print("\\n4. JSON format:")
    result = subprocess.run([
        "python3", "quantum_pci_status_reader.py", 
        "--device", device_path, "--basic", "--format", "json"
    ], capture_output=True, text=True)
    
    try:
        json_data = json.loads(result.stdout)
        print(json.dumps(json_data, indent=2))
    except json.JSONDecodeError:
        print("Error parsing JSON output")
        print(result.stdout)


def test_gui_import():
    """Тестирование импорта GUI модулей"""
    print("\\n=== Testing GUI Import ===")
    
    try:
        import tkinter as tk
        print("✓ tkinter import successful")
        
        # Тест создания окна (без отображения)
        root = tk.Tk()
        root.withdraw()  # Скрыть окно
        root.destroy()
        print("✓ tkinter window creation successful")
        
    except ImportError as e:
        print(f"✗ tkinter import failed: {e}")
        return False
    
    try:
        # Тест импорта конфигуратора
        import sys
        sys.path.insert(0, '.')
        
        # Импорт без запуска GUI
        spec = __import__('quantum_pci_configurator')
        print("✓ GUI configurator import successful")
        
    except Exception as e:
        print(f"✗ GUI configurator import failed: {e}")
        return False
    
    return True


def test_web_monitor():
    """Тестирование веб-монитора"""
    print("\\n=== Testing Web Monitor ===")
    
    try:
        import flask
        from flask_cors import CORS
        print("✓ Flask modules available")
        
        # Тест импорта веб-монитора
        import sys
        sys.path.insert(0, '.')
        
        spec = __import__('quantum_pci_web_monitor')
        print("✓ Web monitor import successful")
        
        return True
        
    except ImportError as e:
        print(f"✗ Flask modules not available: {e}")
        print("Install with: pip3 install flask flask-cors")
        return False
    except Exception as e:
        print(f"✗ Web monitor import failed: {e}")
        return False


def run_demo():
    """Запуск полной демонстрации"""
    print("QUANTUM-PCI Tools Demo")
    print("=" * 50)
    
    # Создание mock устройства
    mock_device = MockQuantumDevice()
    
    try:
        device_path = mock_device.create_mock_device()
        
        # Тестирование компонентов
        test_status_reader(device_path)
        gui_ok = test_gui_import()
        web_ok = test_web_monitor()
        
        print("\\n=== Demo Summary ===")
        print(f"✓ Mock device created at: {device_path}")
        print(f"✓ Status reader: Working")
        print(f"{'✓' if gui_ok else '✗'} GUI configurator: {'Working' if gui_ok else 'Failed'}")
        print(f"{'✓' if web_ok else '✗'} Web monitor: {'Working' if web_ok else 'Failed'}")
        
        print("\\n=== Usage Examples ===")
        print(f"# Test with mock device:")
        print(f"python3 quantum_pci_status_reader.py --device {device_path}")
        print(f"python3 quantum_pci_configurator.py  # Will auto-detect mock device")
        print(f"python3 quantum_pci_web_monitor.py   # Web interface at http://localhost:5000")
        
        print("\\n=== Manual Testing ===")
        print("You can now manually test the tools with the mock device.")
        print("The mock device will persist until you run cleanup.")
        print(f"Mock device location: {device_path}")
        
        # Предложение интерактивного тестирования
        response = input("\\nWould you like to keep the mock device for manual testing? (y/n): ")
        if response.lower() != 'y':
            mock_device.cleanup()
        else:
            print(f"Mock device kept at: {device_path}")
            print("Run 'python3 demo.py cleanup' to remove it later.")
            
    except Exception as e:
        print(f"Demo failed: {e}")
        mock_device.cleanup()


def cleanup_demo():
    """Очистка демонстрационных данных"""
    mock_device = MockQuantumDevice()
    mock_device.cleanup()
    print("Demo cleanup completed.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_demo()
    else:
        run_demo()

