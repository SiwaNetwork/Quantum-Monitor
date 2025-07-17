#!/usr/bin/env python3
"""
QUANTUM-PCI Web Status Monitor
Веб-интерфейс для мониторинга статуса платы QUANTUM-PCI
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import threading
import time
from quantum_pci_status_reader import QuantumPCIStatusReader


app = Flask(__name__)
CORS(app)  # Разрешение CORS для всех доменов

# Глобальные переменные
status_reader = None
current_status = {}
monitoring_active = False
monitoring_thread = None


def initialize_reader():
    """Инициализация считывателя статуса"""
    global status_reader
    status_reader = QuantumPCIStatusReader()
    return status_reader.is_device_available()


def update_status_loop():
    """Цикл обновления статуса"""
    global current_status, monitoring_active
    
    while monitoring_active:
        if status_reader and status_reader.is_device_available():
            try:
                current_status = status_reader.get_full_status()
            except Exception as e:
                current_status = {
                    "error": f"Failed to read status: {str(e)}",
                    "timestamp": time.time()
                }
        else:
            current_status = {
                "error": "Device not available",
                "timestamp": time.time()
            }
        
        time.sleep(1)  # Обновление каждую секунду


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """API для получения текущего статуса"""
    return jsonify(current_status)


@app.route('/api/status/basic')
def get_basic_status():
    """API для получения базового статуса"""
    if status_reader and status_reader.is_device_available():
        return jsonify(status_reader.get_basic_info())
    else:
        return jsonify({"error": "Device not available"})


@app.route('/api/status/clock')
def get_clock_status():
    """API для получения статуса синхронизации"""
    if status_reader and status_reader.is_device_available():
        return jsonify(status_reader.get_clock_status())
    else:
        return jsonify({"error": "Device not available"})


@app.route('/api/status/gnss')
def get_gnss_status():
    """API для получения статуса GNSS"""
    if status_reader and status_reader.is_device_available():
        return jsonify(status_reader.get_gnss_status())
    else:
        return jsonify({"error": "Device not available"})


@app.route('/api/status/sma')
def get_sma_status():
    """API для получения статуса SMA"""
    if status_reader and status_reader.is_device_available():
        return jsonify(status_reader.get_sma_status())
    else:
        return jsonify({"error": "Device not available"})


@app.route('/api/status/generators')
def get_generators_status():
    """API для получения статуса генераторов"""
    if status_reader and status_reader.is_device_available():
        return jsonify(status_reader.get_generator_status())
    else:
        return jsonify({"error": "Device not available"})


@app.route('/api/device/available')
def check_device():
    """API для проверки доступности устройства"""
    available = status_reader and status_reader.is_device_available()
    return jsonify({
        "available": available,
        "device_path": str(status_reader.device_path) if available else None
    })


@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring():
    """API для запуска мониторинга"""
    global monitoring_active, monitoring_thread
    
    if not monitoring_active:
        monitoring_active = True
        monitoring_thread = threading.Thread(target=update_status_loop, daemon=True)
        monitoring_thread.start()
        return jsonify({"status": "started"})
    else:
        return jsonify({"status": "already_running"})


@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring():
    """API для остановки мониторинга"""
    global monitoring_active
    
    monitoring_active = False
    return jsonify({"status": "stopped"})


@app.route('/api/monitoring/status')
def get_monitoring_status():
    """API для получения статуса мониторинга"""
    return jsonify({
        "active": monitoring_active,
        "device_available": status_reader and status_reader.is_device_available()
    })


if __name__ == '__main__':
    # Инициализация
    device_available = initialize_reader()
    
    if device_available:
        print("QUANTUM-PCI device detected")
        # Автоматический запуск мониторинга
        monitoring_active = True
        monitoring_thread = threading.Thread(target=update_status_loop, daemon=True)
        monitoring_thread.start()
    else:
        print("Warning: QUANTUM-PCI device not detected")
    
    # Запуск веб-сервера
    print("Starting QUANTUM-PCI Web Status Monitor...")
    print("Access the web interface at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

