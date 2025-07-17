#!/usr/bin/env python3
"""
Главный файл для запуска QUANTUM-PCI Configuration Tool v2.0
"""

import sys
import argparse
import logging
from pathlib import Path

# Добавление текущей директории в путь Python
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.status_reader import StatusReader
from src.core.device import QuantumPCIDevice
from src.core.exceptions import QuantumPCIError, DeviceNotFoundError


def setup_logging(level: str = "INFO"):
    """Настройка логирования"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('quantum_pci.log')
        ]
    )


def run_cli_mode(device_path: str = None):
    """Запуск в режиме командной строки"""
    try:
        print("QUANTUM-PCI Configuration Tool v2.0 - CLI Mode")
        print("=" * 50)
        
        device = QuantumPCIDevice(device_path)
        status_reader = StatusReader(device)
        
        # Получение и вывод основной информации
        device_info = device.get_device_info()
        print(f"Device Path: {device_info['device_path']}")
        print(f"Serial Number: {device_info['serial_number']}")
        print(f"Current Clock Source: {device_info['current_clock_source']}")
        print(f"GNSS Sync: {device_info['gnss_sync']}")
        
        # Получение статуса
        full_status = status_reader.get_full_status()
        health_status = full_status['health_status']
        
        print(f"\nHealth Status: {'✓ HEALTHY' if health_status['healthy'] else '✗ UNHEALTHY'}")
        
        print("\nHealth Checks:")
        for check, result in health_status['checks'].items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  {check}: {status}")
        
        # SMA Configuration
        sma_config = device.get_sma_configuration()
        print("\nSMA Configuration:")
        print("  Inputs:")
        for port, signal in sma_config['inputs'].items():
            print(f"    {port}: {signal}")
        print("  Outputs:")
        for port, signal in sma_config['outputs'].items():
            print(f"    {port}: {signal}")
            
    except DeviceNotFoundError:
        print("ERROR: QUANTUM-PCI device not found")
        print("Please check that:")
        print("1. The device is properly connected")
        print("2. The driver is loaded (modprobe ptp_ocp)")
        print("3. You have sufficient permissions")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def run_gui_mode(device_path: str = None):
    """Запуск в режиме GUI"""
    try:
        # Импортируем GUI только при необходимости
        from src.gui.main_window import QuantumPCIGUI
        app = QuantumPCIGUI(device_path)
        app.run()
    except ImportError as e:
        print(f"Error: GUI dependencies not available: {e}")
        print("Please install tkinter: sudo apt-get install python3-tk")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting GUI: {e}")
        sys.exit(1)


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="QUANTUM-PCI Configuration Tool v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run GUI mode
  %(prog)s --cli                     # Run CLI mode
  %(prog)s --device /sys/class/timecard/ocp0  # Specify device path
  %(prog)s --cli --export status.json  # Export status to file
        """
    )
    
    parser.add_argument(
        "--device", 
        type=str,
        help="Path to QUANTUM-PCI device (auto-detected if not specified)"
    )
    
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode instead of GUI"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--export",
        type=str,
        help="Export device status to file (CLI mode only)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="QUANTUM-PCI Configuration Tool v2.0"
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    setup_logging(args.log_level)
    
    if args.cli:
        run_cli_mode(args.device)
        
        # Экспорт статуса если указан
        if args.export:
            try:
                device = QuantumPCIDevice(args.device)
                status_reader = StatusReader(device)
                format_type = "csv" if args.export.endswith(".csv") else "json"
                
                if status_reader.export_status(args.export, format_type):
                    print(f"\nStatus exported to: {args.export}")
                else:
                    print(f"\nERROR: Failed to export status to {args.export}")
                    
            except Exception as e:
                print(f"\nERROR: Export failed: {e}")
    else:
        run_gui_mode(args.device)


if __name__ == "__main__":
    main()