"""
Главное окно GUI приложения для QUANTUM-PCI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Dict, Any

from ..core.device import QuantumPCIDevice
from ..core.config_manager import ConfigManager
from ..core.exceptions import QuantumPCIError, DeviceNotFoundError
from ..api.status_reader import StatusReader
from .components.device_panel import DevicePanel
from .components.clock_panel import ClockPanel
from .components.sma_panel import SMAPanel
from .components.status_panel import StatusPanel


class QuantumPCIGUI:
    """Главное окно GUI приложения"""
    
    def __init__(self, device_path: Optional[str] = None, headless_mode: bool = False):
        """
        Инициализация GUI
        
        Args:
            device_path: Путь к устройству (если не указан, происходит автопоиск)
            headless_mode: Режим без блокирующих диалогов
        """
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        self.headless_mode = headless_mode
        
        # Инициализация основных компонентов
        self.device = None
        self.config_manager = ConfigManager(logger=self.logger)
        self.status_reader = None
        
        # Создание главного окна
        self.root = tk.Tk()
        self.root.title("QUANTUM-PCI Configuration Tool v2.0")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # В headless режиме скрываем окно
        if self.headless_mode:
            self.root.withdraw()
        
        # Инициализация устройства
        self._init_device(device_path)
        
        # Создание интерфейса
        self._create_menu()
        self._create_main_interface()
        self._setup_status_monitoring()
        
        # Настройка событий закрытия
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _init_device(self, device_path: Optional[str] = None):
        """Инициализация устройства"""
        try:
            self.device = QuantumPCIDevice(device_path, logger=self.logger)
            self.status_reader = StatusReader(self.device, logger=self.logger)
            self.logger.info("Device initialized successfully")
        except DeviceNotFoundError as e:
            self.logger.error(f"Device not found: {e}")
            if not self.headless_mode:
                # В интерактивном режиме показываем диалог асинхронно
                self.root.after(100, lambda: self._show_device_error("Device Error", f"QUANTUM-PCI device not found:\n{e}"))
            else:
                print(f"Device not found (headless mode): {e}")
        except Exception as e:
            self.logger.error(f"Error initializing device: {e}")
            if not self.headless_mode:
                # В интерактивном режиме показываем диалог асинхронно
                self.root.after(100, lambda: self._show_device_error("Error", f"Error initializing device:\n{e}"))
            else:
                print(f"Device initialization error (headless mode): {e}")
    
    def _show_device_error(self, title: str, message: str):
        """Безопасный показ ошибки устройства"""
        try:
            messagebox.showerror(title, message)
        except Exception as e:
            self.logger.error(f"Error showing dialog: {e}")
            print(f"{title}: {message}")
    
    def _create_menu(self):
        """Создание главного меню"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Reconnect Device", command=self._reconnect_device)
        file_menu.add_separator()
        file_menu.add_command(label="Load Configuration", command=self._load_configuration)
        file_menu.add_command(label="Save Configuration", command=self._save_configuration)
        file_menu.add_command(label="Export Status", command=self._export_status)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)
        
        # Меню Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Device Health Check", command=self._health_check)
        tools_menu.add_command(label="Reset to Defaults", command=self._reset_to_defaults)
        tools_menu.add_command(label="View Logs", command=self._view_logs)
        
        # Меню Help
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Documentation", command=self._show_documentation)
    
    def _create_main_interface(self):
        """Создание основного интерфейса"""
        # Создание paned window для разделения интерфейса
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель с настройками
        settings_frame = ttk.Frame(main_paned)
        main_paned.add(settings_frame, weight=3)
        
        # Правая панель со статусом
        status_frame = ttk.Frame(main_paned)
        main_paned.add(status_frame, weight=1)
        
        # Создание notebook для настроек
        self.notebook = ttk.Notebook(settings_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Создание панелей
        self._create_panels()
        
        # Создание панели статуса
        self.status_panel = StatusPanel(status_frame, self.status_reader, self.logger)
    
    def _create_panels(self):
        """Создание панелей настроек"""
        if not self.device:
            # Если устройство не найдено, показываем только панель подключения
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="Device Connection")
            
            ttk.Label(error_frame, text="QUANTUM-PCI device not found", 
                     font=("Arial", 14, "bold")).pack(pady=20)
            ttk.Button(error_frame, text="Retry Connection", 
                      command=self._reconnect_device).pack(pady=10)
            return
        
        # Панель информации об устройстве
        self.device_panel = DevicePanel(
            self.notebook, self.device, self.config_manager, self.logger
        )
        self.notebook.add(self.device_panel.frame, text="Device Info")
        
        # Панель настроек часов
        self.clock_panel = ClockPanel(
            self.notebook, self.device, self.logger
        )
        self.notebook.add(self.clock_panel.frame, text="Clock Settings")
        
        # Панель настроек SMA
        self.sma_panel = SMAPanel(
            self.notebook, self.device, self.logger
        )
        self.notebook.add(self.sma_panel.frame, text="SMA Configuration")
    
    def _setup_status_monitoring(self):
        """Настройка мониторинга статуса"""
        if self.status_reader:
            callbacks = {
                "on_status_update": self._on_status_update,
                "on_clock_source_change": self._on_clock_source_change,
                "on_gnss_status_change": self._on_gnss_status_change,
                "on_health_change": self._on_health_change,
                "on_error": self._on_monitoring_error
            }
            self.status_reader.start_monitoring(interval=2.0, callbacks=callbacks)
    
    def _on_status_update(self, status: Dict[str, Any]):
        """Обработка обновления статуса"""
        if hasattr(self, 'status_panel'):
            self.root.after(0, lambda: self.status_panel.update_status(status))
    
    def _on_clock_source_change(self, old_source: str, new_source: str):
        """Обработка изменения источника синхронизации"""
        self.logger.info(f"Clock source changed: {old_source} -> {new_source}")
        if hasattr(self, 'clock_panel'):
            self.root.after(0, lambda: self.clock_panel.refresh())
    
    def _on_gnss_status_change(self, old_status: str, new_status: str):
        """Обработка изменения статуса GNSS"""
        self.logger.info(f"GNSS status changed: {old_status} -> {new_status}")
        # Можно добавить уведомления пользователю
    
    def _on_health_change(self, old_health: bool, new_health: bool):
        """Обработка изменения состояния здоровья устройства"""
        if not new_health:
            self.root.after(0, lambda: messagebox.showwarning(
                "Device Warning", 
                "Device health check failed. Please check the device status."
            ))
    
    def _on_monitoring_error(self, error: Exception):
        """Обработка ошибок мониторинга"""
        self.logger.error(f"Monitoring error: {error}")
    
    def _reconnect_device(self):
        """Переподключение к устройству"""
        try:
            # Остановка мониторинга
            if self.status_reader:
                self.status_reader.stop_monitoring()
            
            # Повторная инициализация устройства
            self._init_device()
            
            # Пересоздание интерфейса
            for widget in self.notebook.winfo_children():
                widget.destroy()
            
            self._create_panels()
            self._setup_status_monitoring()
            
            messagebox.showinfo("Success", "Device reconnected successfully")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reconnect device:\n{e}")
    
    def _load_configuration(self):
        """Загрузка конфигурации"""
        if not self.device:
            messagebox.showerror("Error", "No device connected")
            return
        
        from tkinter import simpledialog
        config_name = simpledialog.askstring("Load Configuration", "Enter configuration name:")
        if not config_name:
            return
        
        try:
            config = self.config_manager.load_config(config_name)
            if config:
                self._apply_configuration(config)
                messagebox.showinfo("Success", f"Configuration '{config_name}' loaded successfully")
            else:
                messagebox.showerror("Error", f"Configuration '{config_name}' not found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration:\n{e}")
    
    def _save_configuration(self):
        """Сохранение конфигурации"""
        if not self.device:
            messagebox.showerror("Error", "No device connected")
            return
        
        from tkinter import simpledialog
        config_name = simpledialog.askstring("Save Configuration", "Enter configuration name:")
        if not config_name:
            return
        
        try:
            config = self._get_current_configuration()
            if self.config_manager.save_config(config, config_name):
                messagebox.showinfo("Success", f"Configuration '{config_name}' saved successfully")
            else:
                messagebox.showerror("Error", "Failed to save configuration")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def _export_status(self):
        """Экспорт статуса устройства"""
        if not self.status_reader:
            messagebox.showerror("Error", "No device connected")
            return
        
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                format_type = "csv" if filename.endswith(".csv") else "json"
                if self.status_reader.export_status(filename, format_type):
                    messagebox.showinfo("Success", f"Status exported to {filename}")
                else:
                    messagebox.showerror("Error", "Failed to export status")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export status:\n{e}")
    
    def _health_check(self):
        """Проверка состояния устройства"""
        if not self.device:
            messagebox.showerror("Error", "No device connected")
            return
        
        try:
            health_status = self.status_reader._perform_health_checks()
            
            # Создание окна с результатами проверки
            health_window = tk.Toplevel(self.root)
            health_window.title("Device Health Check")
            health_window.geometry("400x300")
            
            text_widget = tk.Text(health_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget.insert(tk.END, "Device Health Check Results:\n\n")
            for check, result in health_status.items():
                status = "✓ PASS" if result else "✗ FAIL"
                text_widget.insert(tk.END, f"{check}: {status}\n")
                
        except Exception as e:
            messagebox.showerror("Error", f"Health check failed:\n{e}")
    
    def _reset_to_defaults(self):
        """Сброс к настройкам по умолчанию"""
        if not self.device:
            messagebox.showerror("Error", "No device connected")
            return
        
        if messagebox.askyesno("Confirm", "Reset device to default configuration?"):
            try:
                default_config = self.config_manager.create_default_config()
                self._apply_configuration(default_config)
                messagebox.showinfo("Success", "Device reset to default configuration")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset device:\n{e}")
    
    def _view_logs(self):
        """Просмотр логов"""
        log_window = tk.Toplevel(self.root)
        log_window.title("Application Logs")
        log_window.geometry("600x400")
        
        text_widget = tk.Text(log_window, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_window, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Здесь можно добавить реальные логи
        text_widget.insert(tk.END, "Application logs would be displayed here...\n")
    
    def _show_about(self):
        """Показ информации о приложении"""
        about_text = """QUANTUM-PCI Configuration Tool v2.0

A modern, refactored tool for configuring and monitoring QUANTUM-PCI devices.

Features:
- Device configuration management
- Real-time status monitoring
- Configuration save/load
- Health monitoring
- Export capabilities

© 2024 QUANTUM-PCI Development Team"""
        
        messagebox.showinfo("About", about_text)
    
    def _show_documentation(self):
        """Показ документации"""
        doc_window = tk.Toplevel(self.root)
        doc_window.title("Documentation")
        doc_window.geometry("800x600")
        
        text_widget = tk.Text(doc_window, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(doc_window, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Здесь можно загрузить реальную документацию
        text_widget.insert(tk.END, "Documentation would be displayed here...\n")
    
    def _get_current_configuration(self) -> Dict[str, Any]:
        """Получение текущей конфигурации устройства"""
        return {
            "device_info": self.device.get_device_info(),
            "clock_settings": {
                "source": self.device.get_current_clock_source(),
                "utc_tai_offset": self.device.read_device_file("utc_tai_offset")
            },
            "sma_settings": self.device.get_sma_configuration()
        }
    
    def _apply_configuration(self, config: Dict[str, Any]):
        """Применение конфигурации к устройству"""
        try:
            # Применение настроек часов
            if "clock_settings" in config:
                clock_settings = config["clock_settings"]
                if "source" in clock_settings:
                    self.device.set_clock_source(clock_settings["source"])
                if "utc_tai_offset" in clock_settings:
                    self.device.write_device_file("utc_tai_offset", str(clock_settings["utc_tai_offset"]))
            
            # Применение настроек SMA
            if "sma_settings" in config:
                sma_settings = config["sma_settings"]
                if "inputs" in sma_settings:
                    for port, signal in sma_settings["inputs"].items():
                        port_num = int(port[3:])  # Извлечение номера из "sma1"
                        self.device.set_sma_input(port_num, signal)
                if "outputs" in sma_settings:
                    for port, signal in sma_settings["outputs"].items():
                        port_num = int(port[3:])  # Извлечение номера из "sma1"
                        self.device.set_sma_output(port_num, signal)
            
            # Обновление интерфейса
            if hasattr(self, 'clock_panel'):
                self.clock_panel.refresh()
            if hasattr(self, 'sma_panel'):
                self.sma_panel.refresh()
                
        except Exception as e:
            raise Exception(f"Failed to apply configuration: {e}")
    
    def _on_closing(self):
        """Обработка закрытия приложения"""
        try:
            if self.status_reader:
                self.status_reader.stop_monitoring()
            self.root.destroy()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self.root.destroy()
    
    def run(self):
        """Запуск GUI приложения"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._on_closing()
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            messagebox.showerror("Critical Error", f"Application error:\n{e}")
            self._on_closing()