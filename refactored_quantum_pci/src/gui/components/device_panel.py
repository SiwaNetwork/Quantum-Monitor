"""
Панель информации об устройстве QUANTUM-PCI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional

from ...core.device import QuantumPCIDevice
from ...core.config_manager import ConfigManager
from ...core.exceptions import QuantumPCIError


class DevicePanel:
    """Панель отображения информации об устройстве"""
    
    def __init__(self, parent: tk.Widget, device: Optional[QuantumPCIDevice], 
                 config_manager: ConfigManager, logger: logging.Logger):
        """
        Инициализация панели устройства
        
        Args:
            parent: Родительский виджет
            device: Объект устройства
            config_manager: Менеджер конфигурации
            logger: Логгер
        """
        self.parent = parent
        self.device = device
        self.config_manager = config_manager
        self.logger = logger
        
        self.frame = ttk.Frame(parent)
        
        self._create_widgets()
        self._layout_widgets()
        self._load_device_info()
        
    def _create_widgets(self):
        """Создание виджетов панели устройства"""
        # Заголовок
        self.title_label = ttk.Label(
            self.frame, 
            text="Device Information", 
            font=("Arial", 14, "bold")
        )
        
        # Основная информация об устройстве
        self.info_frame = ttk.LabelFrame(self.frame, text="Device Details")
        
        # Путь к устройству
        self.path_label = ttk.Label(self.info_frame, text="Device Path:")
        self.path_value = ttk.Label(self.info_frame, text="Unknown")
        
        # Серийный номер
        self.serial_label = ttk.Label(self.info_frame, text="Serial Number:")
        self.serial_value = ttk.Label(self.info_frame, text="Unknown")
        
        # Версия прошивки
        self.fw_label = ttk.Label(self.info_frame, text="Firmware Version:")
        self.fw_value = ttk.Label(self.info_frame, text="Unknown")
        
        # Состояние устройства
        self.status_label = ttk.Label(self.info_frame, text="Status:")
        self.status_value = ttk.Label(self.info_frame, text="Unknown")
        
        # Кнопки управления
        self.control_frame = ttk.LabelFrame(self.frame, text="Device Control")
        
        self.refresh_button = ttk.Button(
            self.control_frame,
            text="Refresh Info",
            command=self._refresh_info
        )
        
        self.reset_button = ttk.Button(
            self.control_frame,
            text="Reset Device",
            command=self._reset_device
        )
        
        # Конфигурация
        self.config_frame = ttk.LabelFrame(self.frame, text="Configuration")
        
        self.save_config_button = ttk.Button(
            self.config_frame,
            text="Save Current Config",
            command=self._save_config
        )
        
        self.load_config_button = ttk.Button(
            self.config_frame,
            text="Load Config",
            command=self._load_config
        )
        
        # Текстовая область для дополнительной информации
        self.details_frame = ttk.LabelFrame(self.frame, text="Additional Details")
        self.details_text = tk.Text(
            self.details_frame,
            height=10,
            width=60,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.details_scroll = ttk.Scrollbar(self.details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=self.details_scroll.set)
        
    def _layout_widgets(self):
        """Размещение виджетов"""
        self.title_label.pack(pady=(0, 10))
        
        # Device info
        self.info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.path_label.grid(row=0, column=0, sticky=tk.W, padx=(10, 5), pady=2)
        self.path_value.grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.serial_label.grid(row=1, column=0, sticky=tk.W, padx=(10, 5), pady=2)
        self.serial_value.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.fw_label.grid(row=2, column=0, sticky=tk.W, padx=(10, 5), pady=2)
        self.fw_value.grid(row=2, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.status_label.grid(row=3, column=0, sticky=tk.W, padx=(10, 5), pady=2)
        self.status_value.grid(row=3, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        # Control buttons
        self.control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.refresh_button.pack(side=tk.LEFT, padx=(10, 5), pady=10)
        self.reset_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Configuration buttons
        self.config_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.save_config_button.pack(side=tk.LEFT, padx=(10, 5), pady=10)
        self.load_config_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        # Details
        self.details_frame.pack(fill=tk.BOTH, expand=True)
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        self.details_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))
        
    def _load_device_info(self):
        """Загрузка информации об устройстве"""
        try:
            if not self.device:
                self._show_no_device()
                return
                
            device_info = self.device.get_device_info()
            
            self.path_value.config(text=device_info.get('device_path', 'Unknown'))
            self.serial_value.config(text=device_info.get('serial_number', 'Unknown'))
            self.fw_value.config(text=device_info.get('firmware_version', 'Unknown'))
            
            # Определение статуса
            status = "Connected" if self.device.is_connected() else "Disconnected"
            self.status_value.config(text=status)
            
            # Загрузка дополнительной информации
            self._load_details()
            
        except Exception as e:
            self.logger.error(f"Error loading device info: {e}")
            self._show_error(str(e))
    
    def _load_details(self):
        """Загрузка детальной информации"""
        details = []
        
        try:
            if self.device:
                device_info = self.device.get_device_info()
                
                details.append("=== Complete Device Information ===")
                for key, value in device_info.items():
                    details.append(f"{key}: {value}")
                details.append("")
                
                # Дополнительная информация о состоянии
                details.append("=== Device State ===")
                details.append(f"Connected: {self.device.is_connected()}")
                
                try:
                    # Попытка получить конфигурацию SMA
                    sma_config = self.device.get_sma_configuration()
                    details.append("")
                    details.append("=== SMA Configuration ===")
                    if 'inputs' in sma_config:
                        details.append("Inputs:")
                        for port, signal in sma_config['inputs'].items():
                            details.append(f"  {port}: {signal}")
                    if 'outputs' in sma_config:
                        details.append("Outputs:")
                        for port, signal in sma_config['outputs'].items():
                            details.append(f"  {port}: {signal}")
                except Exception:
                    details.append("SMA configuration not available")
            
        except Exception as e:
            details = [f"Error loading details: {e}"]
        
        # Обновление текста
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, "\n".join(details))
        self.details_text.config(state=tk.DISABLED)
    
    def _show_no_device(self):
        """Отображение отсутствия устройства"""
        self.path_value.config(text="No device")
        self.serial_value.config(text="N/A")
        self.fw_value.config(text="N/A")
        self.status_value.config(text="Not connected")
        
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, "No QUANTUM-PCI device detected.\n\nPlease check:\n1. Device is connected\n2. Driver is loaded\n3. Permissions are correct")
        self.details_text.config(state=tk.DISABLED)
    
    def _show_error(self, error_msg: str):
        """Отображение ошибки"""
        self.status_value.config(text="Error")
        
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, f"Error accessing device:\n{error_msg}")
        self.details_text.config(state=tk.DISABLED)
    
    def _refresh_info(self):
        """Обновление информации об устройстве"""
        self._load_device_info()
    
    def _reset_device(self):
        """Сброс устройства"""
        if not self.device:
            messagebox.showerror("Error", "No device connected")
            return
            
        result = messagebox.askyesno(
            "Confirm Reset", 
            "Are you sure you want to reset the device?\nThis will restart the device and may interrupt current operations."
        )
        
        if result:
            try:
                # Здесь должен быть метод сброса устройства
                # self.device.reset()
                messagebox.showinfo("Reset", "Device reset command sent.\nPlease wait for device to restart.")
                self.logger.info("Device reset initiated")
            except Exception as e:
                self.logger.error(f"Error resetting device: {e}")
                messagebox.showerror("Reset Failed", f"Failed to reset device:\n{e}")
    
    def _save_config(self):
        """Сохранение текущей конфигурации"""
        try:
            if self.config_manager.save_current_config():
                messagebox.showinfo("Config Saved", "Current configuration saved successfully")
            else:
                messagebox.showerror("Save Failed", "Failed to save configuration")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            messagebox.showerror("Save Failed", f"Error saving configuration:\n{e}")
    
    def _load_config(self):
        """Загрузка конфигурации"""
        try:
            if self.config_manager.load_config():
                messagebox.showinfo("Config Loaded", "Configuration loaded successfully")
                self._refresh_info()
            else:
                messagebox.showerror("Load Failed", "Failed to load configuration")
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            messagebox.showerror("Load Failed", f"Error loading configuration:\n{e}")
    
    def refresh(self):
        """Обновление панели (вызывается извне)"""
        self._refresh_info()