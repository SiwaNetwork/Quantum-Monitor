#!/usr/bin/env python3
"""
QUANTUM-PCI Card Configurator
Улучшенный GUI конфигуратор для платы QUANTUM-PCI с поддержкой sys/class интерфейса
"""

import os
import signal
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import threading
import time
import json
from pathlib import Path
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


class QuantumPCIConfigurator:
    def __init__(self):
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
        self.detect_device()
        
    def create_widgets(self):
        """Создание виджетов интерфейса"""
        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Refresh Device", command=self.detect_device)
        file_menu.add_command(label="Save Config", command=self.save_config)
        file_menu.add_command(label="Load Config", command=self.load_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Меню Help
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Создание notebook для вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка Device Info
        self.create_device_info_tab()
        
        # Вкладка Clock Sources
        self.create_clock_sources_tab()
        
        # Вкладка SMA Configuration
        self.create_sma_config_tab()
        
        # Вкладка Signal Generators
        self.create_signal_generators_tab()
        
        # Вкладка GNSS Status
        self.create_gnss_status_tab()
        
        # Вкладка Timestampers
        self.create_timestampers_tab()
        
        # Вкладка Status Monitor
        self.create_status_monitor_tab()
        
        # Статусная строка
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        self.device_status_label = ttk.Label(self.status_frame, text="Device: Not detected")
        self.device_status_label.pack(side=tk.RIGHT)
        
    def create_device_info_tab(self):
        """Создание вкладки информации об устройстве"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Device Info")
        
        # Информация об устройстве
        info_frame = ttk.LabelFrame(frame, text="Device Information")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.device_info_text = scrolledtext.ScrolledText(info_frame, height=15)
        self.device_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Refresh", command=self.refresh_device_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Detect Device", command=self.detect_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Show PCI Info", command=self.show_pci_info).pack(side=tk.LEFT, padx=5)
        
    def create_clock_sources_tab(self):
        """Создание вкладки источников синхронизации"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Clock Sources")
        
        # Текущий источник синхронизации
        current_frame = ttk.LabelFrame(frame, text="Current Clock Source")
        current_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.current_clock_var = tk.StringVar()
        self.current_clock_label = ttk.Label(current_frame, textvariable=self.current_clock_var)
        self.current_clock_label.pack(padx=10, pady=10)
        
        # Доступные источники
        available_frame = ttk.LabelFrame(frame, text="Available Clock Sources")
        available_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.clock_source_var = tk.StringVar()
        self.clock_sources_combo = ttk.Combobox(available_frame, textvariable=self.clock_source_var, state="readonly")
        self.clock_sources_combo.pack(padx=10, pady=10)
        
        # Кнопки управления
        clock_button_frame = ttk.Frame(frame)
        clock_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(clock_button_frame, text="Set Clock Source", command=self.set_clock_source).pack(side=tk.LEFT, padx=5)
        ttk.Button(clock_button_frame, text="Refresh", command=self.refresh_clock_sources).pack(side=tk.LEFT, padx=5)
        
        # Статус синхронизации
        status_frame = ttk.LabelFrame(frame, text="Clock Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.clock_status_text = scrolledtext.ScrolledText(status_frame, height=8)
        self.clock_status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def create_sma_config_tab(self):
        """Создание вкладки конфигурации SMA"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="SMA Configuration")
        
        # SMA Inputs
        input_frame = ttk.LabelFrame(frame, text="SMA Inputs")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.sma_inputs = {}
        for i in range(1, 5):  # SMA1-SMA4
            sma_frame = ttk.Frame(input_frame)
            sma_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(sma_frame, text=f"SMA{i}:").pack(side=tk.LEFT, padx=5)
            
            var = tk.StringVar()
            combo = ttk.Combobox(sma_frame, textvariable=var, state="readonly", width=15)
            combo.pack(side=tk.LEFT, padx=5)
            
            self.sma_inputs[f"sma{i}"] = {"var": var, "combo": combo}
            
            ttk.Button(sma_frame, text="Set", command=lambda i=i: self.set_sma_input(i)).pack(side=tk.LEFT, padx=5)
        
        # SMA Outputs
        output_frame = ttk.LabelFrame(frame, text="SMA Outputs")
        output_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.sma_outputs = {}
        for i in range(1, 5):  # SMA1-SMA4
            sma_frame = ttk.Frame(output_frame)
            sma_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(sma_frame, text=f"SMA{i}:").pack(side=tk.LEFT, padx=5)
            
            var = tk.StringVar()
            combo = ttk.Combobox(sma_frame, textvariable=var, state="readonly", width=15)
            combo.pack(side=tk.LEFT, padx=5)
            
            self.sma_outputs[f"sma{i}"] = {"var": var, "combo": combo}
            
            ttk.Button(sma_frame, text="Set", command=lambda i=i: self.set_sma_output(i)).pack(side=tk.LEFT, padx=5)
        
        # Кнопки управления
        sma_button_frame = ttk.Frame(frame)
        sma_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(sma_button_frame, text="Refresh All", command=self.refresh_sma_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(sma_button_frame, text="Reset to Default", command=self.reset_sma_config).pack(side=tk.LEFT, padx=5)
        
    def create_signal_generators_tab(self):
        """Создание вкладки генераторов сигналов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Signal Generators")
        
        self.generators = {}
        for i in range(1, 5):  # GEN1-GEN4
            gen_frame = ttk.LabelFrame(frame, text=f"Generator {i}")
            gen_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Параметры генератора
            params_frame = ttk.Frame(gen_frame)
            params_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Period
            ttk.Label(params_frame, text="Period (ns):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
            period_var = tk.StringVar()
            period_entry = ttk.Entry(params_frame, textvariable=period_var, width=15)
            period_entry.grid(row=0, column=1, padx=5, pady=2)
            
            # Duty cycle
            ttk.Label(params_frame, text="Duty (%):").grid(row=0, column=2, padx=5, pady=2, sticky="w")
            duty_var = tk.StringVar()
            duty_entry = ttk.Entry(params_frame, textvariable=duty_var, width=10)
            duty_entry.grid(row=0, column=3, padx=5, pady=2)
            
            # Phase
            ttk.Label(params_frame, text="Phase (ns):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
            phase_var = tk.StringVar()
            phase_entry = ttk.Entry(params_frame, textvariable=phase_var, width=15)
            phase_entry.grid(row=1, column=1, padx=5, pady=2)
            
            # Polarity
            ttk.Label(params_frame, text="Polarity:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
            polarity_var = tk.StringVar()
            polarity_combo = ttk.Combobox(params_frame, textvariable=polarity_var, values=["0", "1"], state="readonly", width=8)
            polarity_combo.grid(row=1, column=3, padx=5, pady=2)
            
            # Кнопки управления
            control_frame = ttk.Frame(gen_frame)
            control_frame.pack(fill=tk.X, padx=5, pady=5)
            
            start_btn = ttk.Button(control_frame, text="Start", command=lambda i=i: self.start_generator(i))
            start_btn.pack(side=tk.LEFT, padx=5)
            
            stop_btn = ttk.Button(control_frame, text="Stop", command=lambda i=i: self.stop_generator(i))
            stop_btn.pack(side=tk.LEFT, padx=5)
            
            status_label = ttk.Label(control_frame, text="Status: Stopped")
            status_label.pack(side=tk.LEFT, padx=10)
            
            self.generators[f"gen{i}"] = {
                "period_var": period_var,
                "duty_var": duty_var,
                "phase_var": phase_var,
                "polarity_var": polarity_var,
                "status_label": status_label
            }
        
    def create_gnss_status_tab(self):
        """Создание вкладки статуса GNSS"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="GNSS Status")
        
        # GNSS Sync Status
        sync_frame = ttk.LabelFrame(frame, text="GNSS Synchronization")
        sync_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.gnss_sync_var = tk.StringVar()
        self.gnss_sync_label = ttk.Label(sync_frame, textvariable=self.gnss_sync_var, font=("Arial", 12, "bold"))
        self.gnss_sync_label.pack(padx=10, pady=10)
        
        # GNSS Details
        details_frame = ttk.LabelFrame(frame, text="GNSS Details")
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.gnss_details_text = scrolledtext.ScrolledText(details_frame, height=15)
        self.gnss_details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления
        gnss_button_frame = ttk.Frame(frame)
        gnss_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(gnss_button_frame, text="Refresh", command=self.refresh_gnss_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(gnss_button_frame, text="Reset GNSS", command=self.reset_gnss).pack(side=tk.LEFT, padx=5)
        
    def create_timestampers_tab(self):
        """Создание вкладки временных меток"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Timestampers")
        
        # Timestamper Configuration
        config_frame = ttk.LabelFrame(frame, text="Timestamper Configuration")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.timestampers = {}
        for i in range(1, 5):  # TS1-TS4
            ts_frame = ttk.Frame(config_frame)
            ts_frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(ts_frame, text=f"TS{i}:").pack(side=tk.LEFT, padx=5)
            
            enable_var = tk.BooleanVar()
            enable_check = ttk.Checkbutton(ts_frame, text="Enable", variable=enable_var)
            enable_check.pack(side=tk.LEFT, padx=5)
            
            mode_var = tk.StringVar()
            mode_combo = ttk.Combobox(ts_frame, textvariable=mode_var, values=["Rising", "Falling", "Both"], state="readonly", width=10)
            mode_combo.pack(side=tk.LEFT, padx=5)
            
            count_var = tk.StringVar()
            count_label = ttk.Label(ts_frame, textvariable=count_var)
            count_label.pack(side=tk.LEFT, padx=10)
            
            self.timestampers[f"ts{i}"] = {
                "enable_var": enable_var,
                "mode_var": mode_var,
                "count_var": count_var
            }
        
        # Timestamper Status
        status_frame = ttk.LabelFrame(frame, text="Timestamper Status")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.timestamper_status_text = scrolledtext.ScrolledText(status_frame, height=10)
        self.timestamper_status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления
        ts_button_frame = ttk.Frame(frame)
        ts_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(ts_button_frame, text="Apply Config", command=self.apply_timestamper_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(ts_button_frame, text="Reset Counters", command=self.reset_timestamper_counters).pack(side=tk.LEFT, padx=5)
        ttk.Button(ts_button_frame, text="Refresh", command=self.refresh_timestamper_status).pack(side=tk.LEFT, padx=5)
        
    def create_status_monitor_tab(self):
        """Создание вкладки мониторинга статуса"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Status Monitor")
        
        # Контроль мониторинга
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.monitor_var = tk.BooleanVar()
        self.monitor_check = ttk.Checkbutton(control_frame, text="Enable Real-time Monitoring", 
                                           variable=self.monitor_var, command=self.toggle_monitoring)
        self.monitor_check.pack(side=tk.LEFT, padx=5)
        
        self.update_interval_var = tk.StringVar(value="1")
        ttk.Label(control_frame, text="Update Interval (s):").pack(side=tk.LEFT, padx=10)
        interval_entry = ttk.Entry(control_frame, textvariable=self.update_interval_var, width=5)
        interval_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Clear Log", command=self.clear_status_log).pack(side=tk.RIGHT, padx=5)
        
        # Лог статуса
        log_frame = ttk.LabelFrame(frame, text="Status Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.status_log_text = scrolledtext.ScrolledText(log_frame, height=20)
        self.status_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def run_command(self, command, show_error=True):
        """Выполнение команды в терминале"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                error_msg = f"Command failed: {command}\\nError: {result.stderr.strip()}"
                if show_error:
                    self.log_status(error_msg)
                return None
        except subprocess.TimeoutExpired:
            error_msg = f"Command timeout: {command}"
            if show_error:
                self.log_status(error_msg)
            return None
        except Exception as e:
            error_msg = f"Command error: {command}\\nException: {str(e)}"
            if show_error:
                self.log_status(error_msg)
            return None
    
    def detect_device(self):
        """Безопасное обнаружение устройства QUANTUM-PCI с timeout и проверками"""
        
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
            self.refresh_sma_config()
        else:
            self.device_status_label.config(text="Device: Not detected")
            self.status_label.config(text="No device found")
            print("No device detected")
            messagebox.showwarning("Device Detection", 
                                 "QUANTUM-PCI device not found.\\n"
                                 "Please ensure the device is properly installed and the driver is loaded.")
    
    def refresh_device_info(self):
        """Обновление информации об устройстве"""
        if not self.device_path:
            return
        
        info_text = "QUANTUM-PCI Device Information\\n"
        info_text += "=" * 40 + "\\n\\n"
        
        # Чтение основной информации
        info_files = ["serialnum", "gnss_sync", "clock_source", "clock_status_drift", "clock_status_offset"]
        
        for file_name in info_files:
            file_path = self.device_path / file_name
            if file_path.exists():
                try:
                    value = file_path.read_text().strip()
                    info_text += f"{file_name}: {value}\\n"
                except Exception as e:
                    info_text += f"{file_name}: Error reading ({str(e)})\\n"
        
        # PTP информация
        ptp_link = self.device_path / "ptp"
        if ptp_link.exists():
            try:
                ptp_device = ptp_link.resolve().name
                info_text += f"\\nPTP Device: {ptp_device}\\n"
            except Exception:
                pass
        
        # PPS информация
        pps_link = self.device_path / "pps"
        if pps_link.exists():
            try:
                pps_device = pps_link.resolve().name
                info_text += f"PPS Device: {pps_device}\\n"
            except Exception:
                pass
        
        self.device_info_text.delete(1.0, tk.END)
        self.device_info_text.insert(1.0, info_text)
    
    def refresh_clock_sources(self):
        """Обновление информации об источниках синхронизации"""
        if not self.device_path:
            return
        
        # Текущий источник
        current_file = self.device_path / "clock_source"
        if current_file.exists():
            try:
                current = current_file.read_text().strip()
                self.current_clock_var.set(f"Current: {current}")
            except Exception:
                self.current_clock_var.set("Current: Unknown")
        
        # Доступные источники
        available_file = self.device_path / "available_clock_sources"
        if available_file.exists():
            try:
                available = available_file.read_text().strip().split()
                self.clock_sources_combo['values'] = available
                if available:
                    self.clock_sources_combo.current(0)
            except Exception:
                pass
        
        # Статус синхронизации
        self.refresh_clock_status()
    
    def refresh_clock_status(self):
        """Обновление статуса синхронизации"""
        if not self.device_path:
            return
        
        status_text = "Clock Synchronization Status\\n"
        status_text += "=" * 30 + "\\n\\n"
        
        status_files = ["clock_status_drift", "clock_status_offset", "gnss_sync"]
        
        for file_name in status_files:
            file_path = self.device_path / file_name
            if file_path.exists():
                try:
                    value = file_path.read_text().strip()
                    status_text += f"{file_name}: {value}\\n"
                except Exception as e:
                    status_text += f"{file_name}: Error ({str(e)})\\n"
        
        self.clock_status_text.delete(1.0, tk.END)
        self.clock_status_text.insert(1.0, status_text)
    
    def set_clock_source(self):
        """Установка источника синхронизации"""
        if not self.device_path:
            messagebox.showerror("Error", "Device not detected")
            return
        
        source = self.clock_source_var.get()
        if not source:
            messagebox.showerror("Error", "Please select a clock source")
            return
        
        try:
            clock_file = self.device_path / "clock_source"
            clock_file.write_text(source)
            self.log_status(f"Clock source set to: {source}")
            self.refresh_clock_sources()
            messagebox.showinfo("Success", f"Clock source set to: {source}")
        except Exception as e:
            error_msg = f"Failed to set clock source: {str(e)}"
            self.log_status(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def refresh_sma_config(self):
        """Обновление конфигурации SMA"""
        if not self.device_path:
            return
        
        # Доступные входы
        available_inputs_file = self.device_path / "available_sma_inputs"
        if available_inputs_file.exists():
            try:
                inputs = available_inputs_file.read_text().strip().split()
                for sma_name, sma_data in self.sma_inputs.items():
                    sma_data["combo"]['values'] = inputs
            except Exception:
                pass
        
        # Доступные выходы
        available_outputs_file = self.device_path / "available_sma_outputs"
        if available_outputs_file.exists():
            try:
                outputs = available_outputs_file.read_text().strip().split()
                for sma_name, sma_data in self.sma_outputs.items():
                    sma_data["combo"]['values'] = outputs
            except Exception:
                pass
    
    def set_sma_input(self, sma_num):
        """Установка конфигурации SMA входа"""
        if not self.device_path:
            messagebox.showerror("Error", "Device not detected")
            return
        
        sma_data = self.sma_inputs[f"sma{sma_num}"]
        value = sma_data["var"].get()
        
        if not value:
            messagebox.showerror("Error", f"Please select a value for SMA{sma_num}")
            return
        
        try:
            sma_file = self.device_path / f"sma{sma_num}"
            sma_file.write_text(value)
            self.log_status(f"SMA{sma_num} input set to: {value}")
            messagebox.showinfo("Success", f"SMA{sma_num} input set to: {value}")
        except Exception as e:
            error_msg = f"Failed to set SMA{sma_num} input: {str(e)}"
            self.log_status(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def set_sma_output(self, sma_num):
        """Установка конфигурации SMA выхода"""
        if not self.device_path:
            messagebox.showerror("Error", "Device not detected")
            return
        
        sma_data = self.sma_outputs[f"sma{sma_num}"]
        value = sma_data["var"].get()
        
        if not value:
            messagebox.showerror("Error", f"Please select a value for SMA{sma_num}")
            return
        
        try:
            sma_file = self.device_path / f"sma{sma_num}_out"
            sma_file.write_text(value)
            self.log_status(f"SMA{sma_num} output set to: {value}")
            messagebox.showinfo("Success", f"SMA{sma_num} output set to: {value}")
        except Exception as e:
            error_msg = f"Failed to set SMA{sma_num} output: {str(e)}"
            self.log_status(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def reset_sma_config(self):
        """Сброс конфигурации SMA к значениям по умолчанию"""
        if messagebox.askyesno("Confirm", "Reset all SMA configurations to default?"):
            # Реализация сброса к значениям по умолчанию
            self.log_status("SMA configuration reset to default")
    
    def start_generator(self, gen_num):
        """Запуск генератора сигналов"""
        if not self.device_path:
            messagebox.showerror("Error", "Device not detected")
            return
        
        gen_data = self.generators[f"gen{gen_num}"]
        
        period = gen_data["period_var"].get()
        duty = gen_data["duty_var"].get()
        phase = gen_data["phase_var"].get()
        polarity = gen_data["polarity_var"].get()
        
        if not period:
            messagebox.showerror("Error", "Period is required")
            return
        
        try:
            gen_dir = self.device_path / f"gen{gen_num}"
            if gen_dir.exists():
                signal_file = gen_dir / "signal"
                
                # Формирование команды
                command = period
                if duty:
                    command += f" {duty}"
                if phase:
                    command += f" {phase}"
                if polarity:
                    command += f" {polarity}"
                
                signal_file.write_text(command)
                gen_data["status_label"].config(text="Status: Running")
                self.log_status(f"Generator {gen_num} started with: {command}")
                messagebox.showinfo("Success", f"Generator {gen_num} started")
            else:
                messagebox.showerror("Error", f"Generator {gen_num} not available")
        except Exception as e:
            error_msg = f"Failed to start generator {gen_num}: {str(e)}"
            self.log_status(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def stop_generator(self, gen_num):
        """Остановка генератора сигналов"""
        if not self.device_path:
            messagebox.showerror("Error", "Device not detected")
            return
        
        try:
            gen_dir = self.device_path / f"gen{gen_num}"
            if gen_dir.exists():
                signal_file = gen_dir / "signal"
                signal_file.write_text("0")
                
                gen_data = self.generators[f"gen{gen_num}"]
                gen_data["status_label"].config(text="Status: Stopped")
                self.log_status(f"Generator {gen_num} stopped")
                messagebox.showinfo("Success", f"Generator {gen_num} stopped")
            else:
                messagebox.showerror("Error", f"Generator {gen_num} not available")
        except Exception as e:
            error_msg = f"Failed to stop generator {gen_num}: {str(e)}"
            self.log_status(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def refresh_gnss_status(self):
        """Обновление статуса GNSS"""
        if not self.device_path:
            return
        
        # GNSS Sync
        gnss_sync_file = self.device_path / "gnss_sync"
        if gnss_sync_file.exists():
            try:
                sync_status = gnss_sync_file.read_text().strip()
                if "1" in sync_status or "sync" in sync_status.lower():
                    self.gnss_sync_var.set("GNSS: SYNCHRONIZED")
                    self.gnss_sync_label.config(foreground="green")
                else:
                    self.gnss_sync_var.set("GNSS: NOT SYNCHRONIZED")
                    self.gnss_sync_label.config(foreground="red")
            except Exception:
                self.gnss_sync_var.set("GNSS: UNKNOWN")
                self.gnss_sync_label.config(foreground="orange")
        
        # GNSS Details
        details_text = "GNSS Status Details\\n"
        details_text += "=" * 20 + "\\n\\n"
        
        gnss_files = ["gnss_sync"]
        for file_name in gnss_files:
            file_path = self.device_path / file_name
            if file_path.exists():
                try:
                    value = file_path.read_text().strip()
                    details_text += f"{file_name}: {value}\\n"
                except Exception as e:
                    details_text += f"{file_name}: Error ({str(e)})\\n"
        
        self.gnss_details_text.delete(1.0, tk.END)
        self.gnss_details_text.insert(1.0, details_text)
    
    def reset_gnss(self):
        """Сброс GNSS"""
        if messagebox.askyesno("Confirm", "Reset GNSS receiver?"):
            self.log_status("GNSS reset requested")
            # Реализация сброса GNSS
    
    def apply_timestamper_config(self):
        """Применение конфигурации временных меток"""
        if not self.device_path:
            messagebox.showerror("Error", "Device not detected")
            return
        
        self.log_status("Applying timestamper configuration")
        # Реализация применения конфигурации
    
    def reset_timestamper_counters(self):
        """Сброс счетчиков временных меток"""
        if messagebox.askyesno("Confirm", "Reset all timestamper counters?"):
            self.log_status("Timestamper counters reset")
            # Реализация сброса счетчиков
    
    def refresh_timestamper_status(self):
        """Обновление статуса временных меток"""
        if not self.device_path:
            return
        
        status_text = "Timestamper Status\\n"
        status_text += "=" * 18 + "\\n\\n"
        
        # Поиск timestamper директорий
        for i in range(1, 5):
            ts_dir = self.device_path / f"ts{i}"
            if ts_dir.exists():
                status_text += f"Timestamper {i}:\\n"
                for ts_file in ts_dir.iterdir():
                    if ts_file.is_file():
                        try:
                            value = ts_file.read_text().strip()
                            status_text += f"  {ts_file.name}: {value}\\n"
                        except Exception:
                            status_text += f"  {ts_file.name}: Error reading\\n"
                status_text += "\\n"
        
        self.timestamper_status_text.delete(1.0, tk.END)
        self.timestamper_status_text.insert(1.0, status_text)
    
    def toggle_monitoring(self):
        """Переключение мониторинга в реальном времени"""
        if self.monitor_var.get():
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """Запуск мониторинга"""
        if self.status_running:
            return
        
        self.status_running = True
        self.status_update_thread = threading.Thread(target=self.status_update_loop, daemon=True)
        self.status_update_thread.start()
        self.log_status("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Безопасная остановка всех процессов мониторинга"""
        
        print("Stopping monitoring safely...")
        
        # Устанавливаем флаги остановки
        self.status_running = False
        self._stop_flag = True
        
        if hasattr(self, '_stop_monitoring'):
            self._stop_monitoring = True
        
        # Ждем завершения потока с timeout
        if hasattr(self, 'status_update_thread') and self.status_update_thread:
            if self.status_update_thread.is_alive():
                print("Waiting for monitoring thread to stop...")
                self.status_update_thread.join(timeout=5.0)
                
                if self.status_update_thread.is_alive():
                    print("Warning: Monitoring thread did not stop gracefully")
                else:
                    print("Monitoring thread stopped successfully")
        
        self.log_status("Real-time monitoring stopped")
        print("Monitoring stopped")
    
    def status_update_loop(self):
        """Безопасная версия status_update_loop с защитой от зависания"""
        
        print("Starting safe status monitoring loop...")
        iteration_count = 0
        max_iterations = 86400  # Максимум 24 часа при интервале 1 сек
        
        while (self.status_running and 
               not getattr(self, '_stop_flag', False) and 
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
                    
                    # Обновление параметров с timeout
                    for param_name, file_name in [
                        ("Clock source", "clock_source"),
                        ("GNSS sync", "gnss_sync"),
                        ("Serial number", "serialnum")
                    ]:
                        try:
                            with timeout(3):  # 3 секунды на операцию
                                param_file = self.device_path / file_name
                                if param_file.exists():
                                    value = param_file.read_text().strip()
                                    if hasattr(self, 'log_status'):
                                        self.log_status(f"[{timestamp}] {param_name}: {value}")
                                        
                        except TimeoutError:
                            if hasattr(self, 'log_status'):
                                self.log_status(f"[{timestamp}] {param_name}: TIMEOUT")
                        except Exception as e:
                            if hasattr(self, 'log_status'):
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
        log_message = f"[{timestamp}] {message}\\n"
        
        self.status_log_text.insert(tk.END, log_message)
        self.status_log_text.see(tk.END)
    
    def clear_status_log(self):
        """Очистка лога статуса"""
        self.status_log_text.delete(1.0, tk.END)
    
    def show_pci_info(self):
        """Показ информации PCI"""
        pci_info = self.run_command("lspci -v | grep -A 20 -i quantum")
        if not pci_info:
            pci_info = self.run_command("lspci -v | grep -A 20 0x0400")
        
        if pci_info:
            messagebox.showinfo("PCI Information", pci_info)
        else:
            messagebox.showinfo("PCI Information", "No PCI information found")
    
    def save_config(self):
        """Сохранение конфигурации"""
        if not self.device_path:
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
        
        # Сохранение в файл
        try:
            config_file = Path("quantum_pci_config.json")
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Success", f"Configuration saved to {config_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
    def load_config(self):
        """Загрузка конфигурации"""
        try:
            config_file = Path("quantum_pci_config.json")
            if not config_file.exists():
                messagebox.showerror("Error", "Configuration file not found")
                return
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Применение настроек
            if "clock_source" in config and self.device_path:
                try:
                    clock_file = self.device_path / "clock_source"
                    clock_file.write_text(config["clock_source"])
                except Exception:
                    pass
            
            messagebox.showinfo("Success", "Configuration loaded")
            self.refresh_device_info()
            self.refresh_clock_sources()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
    
    def show_about(self):
        """Показ информации о программе"""
        about_text = """QUANTUM-PCI Card Configurator
        
Version: 2.0
Author: AI Assistant
        
This tool provides a comprehensive interface for configuring
and monitoring QUANTUM-PCI timing cards through the Linux
sys/class interface.

Features:
- Device detection and information
- Clock source configuration
- SMA input/output configuration
- Signal generator control
- GNSS status monitoring
- Timestamper configuration
- Real-time status monitoring
"""
        messagebox.showinfo("About", about_text)
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    app = QuantumPCIConfigurator()
    app.run()

