#!/usr/bin/env python3
"""
Веб-сервер для QUANTUM-PCI Configuration Tool v2.0
Запуск: python web_server.py
"""

import sys
import argparse
import logging
import signal
import asyncio
from pathlib import Path

# Добавление текущей директории в путь Python
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.web_api import QuantumPCIWebAPI


def setup_logging(level: str = "INFO"):
    """Настройка логирования"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('quantum_pci_web.log')
        ]
    )


def signal_handler(web_api):
    """Обработчик сигналов для graceful shutdown"""
    def handler(signum, frame):
        print(f"\nReceived signal {signum}. Shutting down...")
        if web_api.monitoring_task:
            web_api.monitoring_task.cancel()
        sys.exit(0)
    return handler


def main():
    """Главная функция запуска веб-сервера"""
    parser = argparse.ArgumentParser(
        description="QUANTUM-PCI Web Interface Server v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Start web server on port 8000
  %(prog)s --port 8080                  # Start on custom port
  %(prog)s --device /sys/class/timecard/ocp0  # Specify device path
  %(prog)s --debug                      # Enable debug mode
  %(prog)s --host 127.0.0.1            # Bind to localhost only
        """
    )
    
    parser.add_argument(
        "--device", 
        type=str,
        help="Path to QUANTUM-PCI device (auto-detected if not specified)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with auto-reload"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="QUANTUM-PCI Web Interface v2.0"
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting QUANTUM-PCI Web Interface v2.0")
    logger.info(f"Device: {args.device or 'auto-detect'}")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Debug mode: {args.debug}")
    
    try:
        # Создание веб API
        web_api = QuantumPCIWebAPI(
            device_path=args.device,
            host=args.host,
            port=args.port
        )
        
        # Настройка обработчика сигналов
        signal.signal(signal.SIGINT, signal_handler(web_api))
        signal.signal(signal.SIGTERM, signal_handler(web_api))
        
        # Проверка доступности устройства
        if web_api.device is None:
            logger.warning("QUANTUM-PCI device not found or not accessible")
            logger.warning("Web interface will run in limited mode")
        else:
            logger.info(f"QUANTUM-PCI device found: {web_api.device.device_path}")
        
        # Запуск сервера
        logger.info(f"Starting web server at http://{args.host}:{args.port}")
        logger.info("Press Ctrl+C to stop the server")
        
        if args.debug:
            logger.info("Debug mode enabled - server will auto-reload on code changes")
        
        # Информация о доступных URL
        print("\n" + "="*60)
        print(f"🚀 QUANTUM-PCI Web Interface v2.0")
        print("="*60)
        print(f"📡 Web Interface: http://{args.host}:{args.port}/")
        print(f"📚 API Docs:      http://{args.host}:{args.port}/docs")
        print(f"🔍 API Explorer:  http://{args.host}:{args.port}/redoc")
        print(f"💓 Health Check:  http://{args.host}:{args.port}/api/health")
        print("="*60)
        
        if web_api.device:
            print("✅ Device Status: Connected")
        else:
            print("⚠️  Device Status: Not found (limited mode)")
        
        print(f"📝 Log Level:     {args.log_level}")
        print(f"🔧 Debug Mode:    {'Enabled' if args.debug else 'Disabled'}")
        print("="*60)
        print("Press Ctrl+C to stop the server")
        print()
        
        # Запуск сервера
        web_api.run(debug=args.debug)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")
        logger.exception("Detailed error:")
        sys.exit(1)
    finally:
        logger.info("Web server stopped")


if __name__ == "__main__":
    main()