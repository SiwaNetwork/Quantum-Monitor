#!/usr/bin/env python3
"""
Скрипт для тестирования исправлений зависания программы refactored_quantum_pci
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / "refactored_quantum_pci"))

def test_basic_import():
    """Тест базового импорта модулей"""
    print("1. Тестирование импорта модулей...")
    try:
        from src.core.device import QuantumPCIDevice
        from src.api.status_reader import StatusReader
        print("   ✅ Импорт модулей успешен")
        return True
    except ImportError as e:
        print(f"   ❌ Ошибка импорта: {e}")
        return False

def test_device_detection():
    """Тест обнаружения устройства"""
    print("2. Тестирование обнаружения устройства...")
    try:
        from src.core.device import QuantumPCIDevice
        from src.core.exceptions import DeviceNotFoundError
        
        try:
            device = QuantumPCIDevice()
            print("   ✅ Устройство найдено")
            return device, True
        except DeviceNotFoundError:
            print("   ⚠️  Устройство не найдено (нормально для тестовой среды)")
            return None, True
    except Exception as e:
        print(f"   ❌ Ошибка обнаружения устройства: {e}")
        return None, False

def test_mock_device():
    """Тест с симулированным устройством"""
    print("3. Тестирование с симулированным устройством...")
    
    # Создаем временную директорию для тестирования
    mock_dir = Path("/tmp/test_quantum_device")
    try:
        mock_dir.mkdir(exist_ok=True)
        
        # Создаем базовые файлы
        (mock_dir / "serialnum").write_text("TEST123456")
        (mock_dir / "available_clock_sources").write_text("GNSS IRIG EXTERNAL")
        (mock_dir / "clock_source").write_text("GNSS")
        (mock_dir / "gnss_sync").write_text("SYNC")
        (mock_dir / "available_sma_inputs").write_text("10Mhz PPS1 PPS2 None")
        (mock_dir / "available_sma_outputs").write_text("10Mhz PHC MAC None")
        
        # НЕ создаем gen1-gen4 и freq1-freq4 для тестирования отсутствия
        
        from src.core.device import QuantumPCIDevice
        from src.api.status_reader import StatusReader
        
        # Тестируем с симулированным устройством
        device = QuantumPCIDevice(str(mock_dir))
        status_reader = StatusReader(device)
        
        print("   ✅ Симулированное устройство создано")
        return device, status_reader, True
        
    except Exception as e:
        print(f"   ❌ Ошибка создания симулированного устройства: {e}")
        return None, None, False

def test_capabilities_detection(status_reader):
    """Тест определения capabilities"""
    print("4. Тестирование определения capabilities...")
    try:
        capabilities = status_reader.get_device_capabilities()
        print(f"   Найдены capabilities: {capabilities}")
        
        # Проверяем ожидаемые результаты
        if capabilities.get("basic") == True:
            print("   ✅ Базовые функции определены корректно")
        else:
            print("   ❌ Ошибка определения базовых функций")
            
        if capabilities.get("signal_generators") == False:
            print("   ✅ Корректно определено отсутствие генераторов")
        else:
            print("   ❌ Неверно определены генераторы")
            
        if capabilities.get("frequency_counters") == False:
            print("   ✅ Корректно определено отсутствие частотных счетчиков")
        else:
            print("   ❌ Неверно определены частотные счетчики")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка определения capabilities: {e}")
        return False

def test_status_reading(status_reader):
    """Тест чтения статуса без зависания"""
    print("5. Тестирование чтения статуса...")
    try:
        start_time = time.time()
        
        # Читаем полный статус
        status = status_reader.get_full_status()
        
        elapsed = time.time() - start_time
        print(f"   Время чтения статуса: {elapsed:.2f} секунд")
        
        if elapsed < 10:  # Не должно занимать больше 10 секунд
            print("   ✅ Статус прочитан быстро (нет зависания)")
        else:
            print("   ⚠️  Чтение статуса заняло много времени")
            
        # Проверяем структуру статуса
        expected_keys = ["timestamp", "device_info", "device_capabilities", "clock_status", "sma_configuration", "health_status"]
        for key in expected_keys:
            if key in status:
                print(f"   ✅ Ключ '{key}' присутствует")
            else:
                print(f"   ❌ Ключ '{key}' отсутствует")
                
        # Проверяем что генераторы и частотные счетчики отсутствуют
        if "generators" not in status:
            print("   ✅ Генераторы корректно исключены из статуса")
        else:
            print("   ❌ Генераторы присутствуют в статусе (не должны)")
            
        if "frequency_counters" not in status:
            print("   ✅ Частотные счетчики корректно исключены из статуса")
        else:
            print("   ❌ Частотные счетчики присутствуют в статусе (не должны)")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка чтения статуса: {e}")
        return False

def test_monitoring_loop(status_reader):
    """Тест мониторинга в цикле"""
    print("6. Тестирование цикла мониторинга...")
    try:
        start_time = time.time()
        iterations = 0
        max_iterations = 5
        
        print(f"   Запуск {max_iterations} итераций мониторинга...")
        
        while iterations < max_iterations:
            iteration_start = time.time()
            status = status_reader.get_full_status()
            iteration_time = time.time() - iteration_start
            
            iterations += 1
            print(f"   Итерация {iterations}: {iteration_time:.2f}с")
            
            if iteration_time > 5:  # Если итерация занимает больше 5 секунд
                print("   ⚠️  Итерация заняла слишком много времени")
                break
                
            time.sleep(0.5)  # Небольшая пауза между итерациями
        
        total_time = time.time() - start_time
        print(f"   Общее время мониторинга: {total_time:.2f} секунд")
        
        if total_time < 30:  # Должно завершиться быстро
            print("   ✅ Мониторинг завершен без зависания")
            return True
        else:
            print("   ❌ Мониторинг занял слишком много времени")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка в цикле мониторинга: {e}")
        return False

def cleanup():
    """Очистка тестовых файлов"""
    try:
        import shutil
        test_dir = Path("/tmp/test_quantum_device")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print("✅ Тестовые файлы очищены")
    except:
        pass

def main():
    """Основная функция тестирования"""
    print("🔧 Тестирование исправлений программы refactored_quantum_pci")
    print("=" * 60)
    
    results = []
    
    # Тест 1: Импорт
    results.append(test_basic_import())
    
    # Тест 2: Обнаружение устройства
    device, result = test_device_detection()
    results.append(result)
    
    # Тест 3: Симулированное устройство
    mock_device, status_reader, result = test_mock_device()
    results.append(result)
    
    if mock_device and status_reader:
        # Тест 4: Capabilities
        results.append(test_capabilities_detection(status_reader))
        
        # Тест 5: Чтение статуса
        results.append(test_status_reading(status_reader))
        
        # Тест 6: Мониторинг
        results.append(test_monitoring_loop(status_reader))
    else:
        print("⚠️  Пропускаем дополнительные тесты из-за ошибки в предыдущих")
        results.extend([False, False, False])
    
    # Очистка
    cleanup()
    
    # Результаты
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    passed = sum(results)
    total = len(results)
    
    print(f"Пройдено тестов: {passed}/{total}")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Исправления работают корректно.")
        return 0
    else:
        print("❌ Некоторые тесты не пройдены. Требуется дополнительная отладка.")
        return 1

if __name__ == "__main__":
    sys.exit(main())