#!/usr/bin/env python3
"""
Исправленная версия QUANTUM-PCI Card Configurator с защитой от зависания
"""

import os
import sys
import time
import json
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

import tkinter as tk
from tkinter import ttk, messagebox, filedialog


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


class QuantumPCIConfigurator:
    def __init__(self, headless_mode=False):
        """Инициализация с поддержкой headless режима"""
        self.headless_mode = headless_mode
        
        # Создание главного окна
        self.root = tk.Tk()
        self.root.title("QUANTUM-PCI Card Configurator")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Переменные для хранения состояния
        self.device_path = None
        self.device_info = {}
        self.status_update_thread = None
        self.status_running = False
        self._stop_flag = False
        self._stop_monitoring = False
        
        # Создание интерфейса
        self.create_widgets()
        
        # Безопасное обнаружение устройства без блокирующих диалогов
        self.detect_device_safe()
        
        # Обработчик закрытия
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Refresh Device", command=self.detect_device_safe)
        file_menu.add_command(label="Save Config", command=self.save_config)
        file_menu.add_command(label="Load Config", command=self.load_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Меню Help
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Создание notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка Device Info
        self.create_device_info_tab()
        
        # Вкладка Clock Configuration
        self.create_clock_config_tab()
        
        # Вкладка SMA Configuration
        self.create_sma_config_tab()
        
        # Вкладка Status Monitor
        self.create_status_monitor_tab()
        
        # Статусная строка
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.device_status_label = ttk.Label(self.status_frame, text="Device: Not detected")
        self.device_status_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.RIGHT, padx=5, pady=2)
        
    def create_device_info_tab(self):
        """Создание вкладки с информацией об устройстве"""
        self.device_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.device_frame, text="Device Info")
        
        # Кнопки управления
        button_frame = ttk.Frame(self.device_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Detect Device", command=self.detect_device_safe).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh Info", command=self.refresh_device_info).pack(side=tk.LEFT, padx=5)
        
        # Информация об устройстве
        info_frame = ttk.LabelFrame(self.device_frame, text="Device Information")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.device_info_text = tk.Text(info_frame, height=20, width=80)
        scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.device_info_text.yview)
        self.device_info_text.configure(yscrollcommand=scrollbar.set)
        
        self.device_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_clock_config_tab(self):
        """Создание вкладки конфигурации часов"""
        self.clock_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.clock_frame, text="Clock Config")
        
        # Источник синхронизации
        clock_source_frame = ttk.LabelFrame(self.clock_frame, text="Clock Source Configuration")
        clock_source_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.clock_source_var = tk.StringVar()
        self.clock_source_combo = ttk.Combobox(clock_source_frame, textvariable=self.clock_source_var, 
                                              values=["internal", "external", "gnss"])
        self.clock_source_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(clock_source_frame, text="Apply", command=self.apply_clock_source).pack(side=tk.LEFT, padx=5)
        ttk.Button(clock_source_frame, text="Refresh", command=self.refresh_clock_sources).pack(side=tk.LEFT, padx=5)
        
    def create_sma_config_tab(self):
        """Создание вкладки конфигурации SMA"""
        self.sma_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sma_frame, text="SMA Config")
        
        # Заглушка для SMA конфигурации
        sma_label = ttk.Label(self.sma_frame, text="SMA Configuration (placeholder)")
        sma_label.pack(pady=20)
        
    def create_status_monitor_tab(self):
        """Создание вкладки мониторинга статуса"""
        self.monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.monitor_frame, text="Status Monitor")
        
        # Элементы управления мониторингом
        control_frame = ttk.Frame(self.monitor_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.monitor_var = tk.BooleanVar()
        ttk.Checkbutton(control_frame, text="Enable Real-time Monitoring", 
                       variable=self.monitor_var, command=self.toggle_monitoring).pack(side=tk.LEFT, padx=5)
        
        # Интервал обновления
        ttk.Label(control_frame, text="Update Interval (s):").pack(side=tk.LEFT, padx=5)
        self.update_interval_var = tk.StringVar(value="1.0")
        ttk.Entry(control_frame, textvariable=self.update_interval_var, width=8).pack(side=tk.LEFT, padx=5)
        
        # Лог статуса
        log_frame = ttk.LabelFrame(self.monitor_frame, text="Status Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.status_log_text = tk.Text(log_frame, height=15, width=80)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.status_log_text.yview)
        self.status_log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.status_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопка очистки лога
        ttk.Button(self.monitor_frame, text="Clear Log", command=self.clear_status_log).pack(pady=5)
        
    def run_command(self, command, show_error=True, timeout_sec=30):
        """Безопасное выполнение команд с timeout"""
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
                if show_error and not self.headless_mode:
                    print(error_msg)
                return None
                
        except subprocess.TimeoutExpired:
            error_msg = f"Command timeout after {timeout_sec}s: {command}"
            if show_error and not self.headless_mode:
                print(error_msg)
            return None
            
        except Exception as e:
            error_msg = f"Command error: {command}\nException: {str(e)}"
            if show_error and not self.headless_mode:
                print(error_msg)
            return None
    
    def detect_device_safe(self):
        """Безопасное обнаружение устройства без блокирующих диалогов"""
        print("Starting safe device detection...")
        self.status_label.config(text="Detecting device...")
        
        # Флаг обнаружения
        device_found = False
        
        try:
            # Ограничиваем время поиска
            with timeout(15):
                # Поиск устройства через lspci с timeout
                pci_result = self.run_command("lspci | grep -i quantum", show_error=False)
                if not pci_result:
                    pci_result = self.run_command("lspci | grep 0x0400", show_error=False)
                
                # Поиск в /sys/class/timecard/ с безопасными проверками
                timecard_path = Path("/sys/class/timecard")
                
                if timecard_path.exists() and timecard_path.is_dir():
                    print(f"Checking timecard directory: {timecard_path}")
                    
                    try:
                        # Получаем список директорий с timeout
                        device_dirs = [d for d in timecard_path.iterdir() 
                                     if d.is_dir() and d.name.startswith("ocp")]
                        
                        for device_dir in device_dirs:
                            print(f"Checking device: {device_dir}")
                            
                            # Проверяем основные файлы устройства
                            essential_files = ["serialnum", "available_clock_sources"]
                            files_exist = []
                            
                            for file_name in essential_files:
                                file_path = device_dir / file_name
                                try:
                                    with timeout(2):  # 2 секунды на файл
                                        exists = file_path.exists() and file_path.is_file()
                                        files_exist.append(exists)
                                        if exists:
                                            # Проверяем возможность чтения
                                            with timeout(2):
                                                file_path.read_text()
                                                
                                except (TimeoutError, PermissionError, OSError) as e:
                                    print(f"Cannot access {file_path}: {e}")
                                    files_exist.append(False)
                            
                            # Если все основные файлы доступны
                            if all(files_exist):
                                self.device_path = device_dir
                                device_found = True
                                print(f"Device found and verified: {device_dir}")
                                break
                            else:
                                print(f"Device {device_dir} failed verification")
                                
                    except PermissionError as e:
                        print(f"Permission denied accessing timecard directory: {e}")
                    except OSError as e:
                        print(f"OS error accessing timecard directory: {e}")
                else:
                    print("Timecard directory not found or not accessible")
                    
        except TimeoutError:
            print("Device detection timed out (15 seconds)")
            device_found = False
            
        except Exception as e:
            print(f"Unexpected error during device detection: {e}")
            device_found = False
        
        # Обновляем интерфейс
        if device_found:
            self.device_status_label.config(text=f"Device: {self.device_path.name}")
            self.status_label.config(text="Device detected")
            print("Device detection successful")
            self.refresh_device_info()
            self.refresh_clock_sources()
        else:
            self.device_status_label.config(text="Device: Not detected")
            self.status_label.config(text="No device found")
            print("No device detected")
            
            # ИСПРАВЛЕНИЕ: Не показываем блокирующий messagebox в headless режиме
            if not self.headless_mode:
                # Показываем предупреждение только в интерактивном режиме
                # И делаем это через after, чтобы не блокировать
                self.root.after(100, self.show_device_warning)
            else:
                print("Running in headless mode - skipping dialog")
                
    def show_device_warning(self):
        """Показ предупреждения о том, что устройство не найдено"""
        try:
            messagebox.showwarning("Device Detection", 
                                 "QUANTUM-PCI device not found.\n"
                                 "Please ensure the device is properly installed and the driver is loaded.")
        except Exception as e:
            print(f"Error showing warning dialog: {e}")
    
    def refresh_device_info(self):
        """Обновление информации об устройстве"""
        if not self.device_path:
            self.device_info_text.delete(1.0, tk.END)
            self.device_info_text.insert(1.0, "No device detected")
            return
        
        info_text = "QUANTUM-PCI Device Information\n"
        info_text += "=" * 40 + "\n\n"
        
        # Чтение основной информации
        info_files = ["serialnum", "gnss_sync", "clock_source", "clock_status_drift", "clock_status_offset"]
        
        for file_name in info_files:
            file_path = self.device_path / file_name
            if file_path.exists():
                try:
                    with timeout(5):
                        value = file_path.read_text().strip()
                        info_text += f"{file_name}: {value}\n"
                except (TimeoutError, Exception) as e:
                    info_text += f"{file_name}: Error ({str(e)})\n"
            else:
                info_text += f"{file_name}: Not available\n"
        
        self.device_info_text.delete(1.0, tk.END)
        self.device_info_text.insert(1.0, info_text)
    
    def refresh_clock_sources(self):
        """Обновление доступных источников синхронизации"""
        if not self.device_path:
            return
        
        sources_file = self.device_path / "available_clock_sources"
        if sources_file.exists():
            try:
                with timeout(5):
                    sources = sources_file.read_text().strip().split()
                    self.clock_source_combo['values'] = sources
                    
                    # Установка текущего источника
                    current_file = self.device_path / "clock_source"
                    if current_file.exists():
                        with timeout(5):
                            current = current_file.read_text().strip()
                            self.clock_source_var.set(current)
            except (TimeoutError, Exception) as e:
                print(f"Error reading clock sources: {e}")
    
    def apply_clock_source(self):
        """Применение выбранного источника синхронизации"""
        if not self.device_path:
            if not self.headless_mode:
                messagebox.showerror("Error", "Device not detected")
            return
        
        selected_source = self.clock_source_var.get()
        if not selected_source:
            if not self.headless_mode:
                messagebox.showerror("Error", "Please select a clock source")
            return
        
        clock_file = self.device_path / "clock_source"
        try:
            with open(clock_file, 'w') as f:
                f.write(selected_source)
            
            self.log_status(f"Clock source changed to: {selected_source}")
            if not self.headless_mode:
                messagebox.showinfo("Success", f"Clock source set to: {selected_source}")
                
        except Exception as e:
            error_msg = f"Error setting clock source: {e}"
            self.log_status(error_msg)
            if not self.headless_mode:
                messagebox.showerror("Error", error_msg)
    
    def toggle_monitoring(self):
        """Переключение мониторинга статуса"""
        if self.monitor_var.get():
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """Запуск мониторинга статуса"""
        if self.status_running:
            return
        
        self.status_running = True
        self._stop_flag = False
        
        self.status_update_thread = threading.Thread(target=self.status_update_loop, daemon=True)
        self.status_update_thread.start()
        
        self.log_status("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Остановка мониторинга статуса"""
        if not self.status_running:
            return
        
        self.status_running = False
        self._stop_flag = True
        
        # Ожидание завершения потока с timeout
        if self.status_update_thread and self.status_update_thread.is_alive():
            self.status_update_thread.join(timeout=5.0)
            if self.status_update_thread.is_alive():
                print("Warning: Monitoring thread did not stop gracefully")
            else:
                print("Monitoring thread stopped successfully")
        
        self.log_status("Real-time monitoring stopped")
    
    def status_update_loop(self):
        """Безопасная версия status_update_loop с защитой от зависания"""
        print("Starting safe status monitoring loop...")
        iteration_count = 0
        max_iterations = 86400  # Максимум 24 часа при интервале 1 сек
        
        while (self.status_running and 
               not self._stop_flag and 
               iteration_count < max_iterations):
            
            iteration_count += 1
            
            try:
                # Получаем интервал обновления
                try:
                    interval = float(self.update_interval_var.get())
                    if interval < 0.1:  # Минимум 100мс
                        interval = 0.1
                    elif interval > 3600:  # Максимум 1 час
                        interval = 3600
                except (ValueError, AttributeError):
                    interval = 1.0
                
                if self.device_path and self.device_path.exists():
                    timestamp = time.strftime("%H:%M:%S")
                    
                    # Обновление параметров БЕЗ timeout для быстрых операций файловой системы
                    for param_name, file_name in [
                        ("Clock source", "clock_source"),
                        ("GNSS sync", "gnss_sync"),
                        ("Serial number", "serialnum")
                    ]:
                        try:
                            param_file = self.device_path / file_name
                            if param_file.exists() and param_file.is_file():
                                # Быстрая проверка доступности без timeout
                                try:
                                    value = param_file.read_text().strip()
                                    self.log_status(f"[{timestamp}] {param_name}: {value}")
                                except (OSError, PermissionError, UnicodeDecodeError) as e:
                                    self.log_status(f"[{timestamp}] {param_name}: READ ERROR - {e}")
                            else:
                                self.log_status(f"[{timestamp}] {param_name}: FILE NOT FOUND")
                                        
                        except Exception as e:
                            self.log_status(f"[{timestamp}] {param_name}: ERROR - {e}")
                
                # Безопасная пауза
                time.sleep(interval)
                
            except Exception as e:
                print(f"Error in monitoring loop iteration {iteration_count}: {e}")
                time.sleep(1.0)  # Пауза при ошибке
                
        print(f"Status monitoring loop completed after {iteration_count} iterations")
    
    def log_status(self, message):
        """Добавление сообщения в лог статуса"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        try:
            self.status_log_text.insert(tk.END, log_message)
            self.status_log_text.see(tk.END)
        except Exception as e:
            print(f"Error logging message: {e}")
    
    def clear_status_log(self):
        """Очистка лога статуса"""
        try:
            self.status_log_text.delete(1.0, tk.END)
        except Exception as e:
            print(f"Error clearing log: {e}")
    
    def save_config(self):
        """Сохранение конфигурации"""
        if not self.device_path:
            if not self.headless_mode:
                messagebox.showerror("Error", "Device not detected")
            return
        
        config = {}
        
        # Сохранение текущих настроек
        try:
            clock_file = self.device_path / "clock_source"
            if clock_file.exists():
                config["clock_source"] = clock_file.read_text().strip()
        except Exception:
            pass
        
        # Выбор файла для сохранения
        if not self.headless_mode:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                try:
                    with open(filename, 'w') as f:
                        json.dump(config, f, indent=2)
                    messagebox.showinfo("Success", f"Configuration saved to: {filename}")
                except Exception as e:
                    messagebox.showerror("Error", f"Error saving configuration: {e}")
        else:
            # В headless режиме сохраняем в default файл
            filename = "quantum_pci_config.json"
            try:
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                print(f"Configuration saved to: {filename}")
            except Exception as e:
                print(f"Error saving configuration: {e}")
    
    def load_config(self):
        """Загрузка конфигурации"""
        if not self.headless_mode:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
        else:
            filename = "quantum_pci_config.json"
            
        if filename and os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    config = json.load(f)
                
                # Применение настроек
                if "clock_source" in config:
                    self.clock_source_var.set(config["clock_source"])
                    self.apply_clock_source()
                
                if not self.headless_mode:
                    messagebox.showinfo("Success", f"Configuration loaded from: {filename}")
                else:
                    print(f"Configuration loaded from: {filename}")
                    
            except Exception as e:
                error_msg = f"Error loading configuration: {e}"
                if not self.headless_mode:
                    messagebox.showerror("Error", error_msg)
                else:
                    print(error_msg)
    
    def show_about(self):
        """Показ информации о программе"""
        if not self.headless_mode:
            messagebox.showinfo("About", 
                              "QUANTUM-PCI Card Configurator\n"
                              "Version 1.0 (Fixed)\n"
                              "Fixed hanging issues in headless environments")
        else:
            print("QUANTUM-PCI Card Configurator v1.0 (Fixed)")
    
    def on_closing(self):
        """Обработчик закрытия программы"""
        print("Shutting down...")
        
        # Остановка мониторинга
        if self.status_running:
            self.stop_monitoring()
        
        # Закрытие главного окна
        try:
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
        
        print("Shutdown complete")
    
    def run(self, auto_close_after=None):
        """Запуск приложения"""
        try:
            if auto_close_after:
                # Автоматическое закрытие через заданное время (для тестирования)
                self.root.after(auto_close_after * 1000, self.on_closing)
            
            self.root.mainloop()
        except KeyboardInterrupt:
            print("Interrupted by user")
            self.on_closing()
        except Exception as e:
            print(f"Error running application: {e}")
            self.on_closing()


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="QUANTUM-PCI Card Configurator (Fixed)")
    parser.add_argument("--headless", action="store_true", 
                       help="Run in headless mode (no blocking dialogs)")
    parser.add_argument("--test", type=int, metavar="SECONDS", 
                       help="Auto-close after specified seconds (for testing)")
    
    args = parser.parse_args()
    
    print("Starting QUANTUM-PCI Configurator (Fixed Version)...")
    
    try:
        # Проверка доступности GUI
        root_test = tk.Tk()
        root_test.withdraw()  # Скрываем тестовое окно
        root_test.destroy()
        
        app = QuantumPCIConfigurator(headless_mode=args.headless)
        app.run(auto_close_after=args.test)
        
    except Exception as e:
        print(f"Error: Cannot initialize GUI: {e}")
        print("Running in headless mode...")
        
        app = QuantumPCIConfigurator(headless_mode=True)
        app.run(auto_close_after=args.test)


if __name__ == "__main__":
    main()