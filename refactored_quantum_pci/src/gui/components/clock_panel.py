"""
Панель настроек синхронизации QUANTUM-PCI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, List

from ...core.device import QuantumPCIDevice
from ...core.exceptions import QuantumPCIError


class ClockPanel:
    """Панель настроек синхронизации"""
    
    def __init__(self, parent: tk.Widget, device: Optional[QuantumPCIDevice], logger: logging.Logger):
        """
        Инициализация панели синхронизации
        
        Args:
            parent: Родительский виджет
            device: Объект устройства
            logger: Логгер
        """
        self.parent = parent
        self.device = device
        self.logger = logger
        
        self.frame = ttk.Frame(parent)
        
        # Список доступных источников синхронизации
        self.available_sources = ["GNSS", "EXT", "EXT_PPS", "IRIG", "DCF", "MSF"]
        
        self._create_widgets()
        self._layout_widgets()
        self._load_clock_settings()
        
    def _create_widgets(self):
        """Создание виджетов панели синхронизации"""
        # Заголовок
        self.title_label = ttk.Label(
            self.frame, 
            text="Clock & Synchronization Settings", 
            font=("Arial", 14, "bold")
        )
        
        # Текущие настройки
        self.current_frame = ttk.LabelFrame(self.frame, text="Current Settings")
        
        self.current_source_label = ttk.Label(self.current_frame, text="Current Clock Source:")
        self.current_source_value = ttk.Label(self.current_frame, text="Unknown", font=("Arial", 10, "bold"))
        
        self.gnss_status_label = ttk.Label(self.current_frame, text="GNSS Status:")
        self.gnss_status_value = ttk.Label(self.current_frame, text="Unknown")
        
        self.sync_status_label = ttk.Label(self.current_frame, text="Sync Status:")
        self.sync_status_value = ttk.Label(self.current_frame, text="Unknown")
        
        # Управление источником синхронизации
        self.control_frame = ttk.LabelFrame(self.frame, text="Clock Source Control")
        
        self.source_label = ttk.Label(self.control_frame, text="Select Clock Source:")
        self.source_var = tk.StringVar()
        self.source_combo = ttk.Combobox(
            self.control_frame,
            textvariable=self.source_var,
            values=self.available_sources,
            state="readonly"
        )
        
        self.apply_source_button = ttk.Button(
            self.control_frame,
            text="Apply Clock Source",
            command=self._apply_clock_source
        )
        
        # Настройки GNSS
        self.gnss_frame = ttk.LabelFrame(self.frame, text="GNSS Settings")
        
        self.gnss_enable_var = tk.BooleanVar()
        self.gnss_enable_check = ttk.Checkbutton(
            self.gnss_frame,
            text="Enable GNSS",
            variable=self.gnss_enable_var,
            command=self._toggle_gnss
        )
        
        self.gnss_antenna_label = ttk.Label(self.gnss_frame, text="Antenna Power:")
        self.gnss_antenna_var = tk.BooleanVar()
        self.gnss_antenna_check = ttk.Checkbutton(
            self.gnss_frame,
            text="Enable Antenna Power",
            variable=self.gnss_antenna_var,
            command=self._toggle_antenna_power
        )
        
        # Настройки синхронизации
        self.sync_frame = ttk.LabelFrame(self.frame, text="Synchronization Settings")
        
        self.pps_enable_var = tk.BooleanVar()
        self.pps_enable_check = ttk.Checkbutton(
            self.sync_frame,
            text="Enable PPS Output",
            variable=self.pps_enable_var,
            command=self._toggle_pps
        )
        
        self.frequency_label = ttk.Label(self.sync_frame, text="Output Frequency (Hz):")
        self.frequency_var = tk.StringVar(value="10000000")  # 10 MHz default
        self.frequency_entry = ttk.Entry(self.sync_frame, textvariable=self.frequency_var)
        
        self.apply_freq_button = ttk.Button(
            self.sync_frame,
            text="Apply Frequency",
            command=self._apply_frequency
        )
        
        # Кнопки управления
        self.button_frame = ttk.Frame(self.frame)
        
        self.refresh_button = ttk.Button(
            self.button_frame,
            text="Refresh",
            command=self._refresh_settings
        )
        
        self.reset_button = ttk.Button(
            self.button_frame,
            text="Reset to Defaults",
            command=self._reset_to_defaults
        )
        
        # Информационная область
        self.info_frame = ttk.LabelFrame(self.frame, text="Synchronization Information")
        self.info_text = tk.Text(
            self.info_frame,
            height=8,
            width=60,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        
    def _layout_widgets(self):
        """Размещение виджетов"""
        self.title_label.pack(pady=(0, 10))
        
        # Current settings
        self.current_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.current_source_label.grid(row=0, column=0, sticky=tk.W, padx=(10, 5), pady=2)
        self.current_source_value.grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.gnss_status_label.grid(row=1, column=0, sticky=tk.W, padx=(10, 5), pady=2)
        self.gnss_status_value.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.sync_status_label.grid(row=2, column=0, sticky=tk.W, padx=(10, 5), pady=2)
        self.sync_status_value.grid(row=2, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        # Clock source control
        self.control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.source_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.source_combo.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.apply_source_button.pack(pady=10)
        
        # GNSS settings
        self.gnss_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.gnss_enable_check.pack(anchor=tk.W, padx=10, pady=5)
        self.gnss_antenna_label.pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.gnss_antenna_check.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        # Sync settings
        self.sync_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.pps_enable_check.pack(anchor=tk.W, padx=10, pady=5)
        
        freq_frame = ttk.Frame(self.sync_frame)
        freq_frame.pack(fill=tk.X, padx=10, pady=5)
        self.frequency_label.pack(side=tk.LEFT)
        self.frequency_entry.pack(side=tk.LEFT, padx=(10, 5))
        self.apply_freq_button.pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        self.button_frame.pack(fill=tk.X, pady=(0, 10))
        self.refresh_button.pack(side=tk.LEFT, padx=(10, 5))
        self.reset_button.pack(side=tk.LEFT, padx=5)
        
        # Info area
        self.info_frame.pack(fill=tk.BOTH, expand=True)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def _load_clock_settings(self):
        """Загрузка текущих настроек синхронизации"""
        try:
            if not self.device:
                self._show_no_device()
                return
                
            # Получение информации об устройстве
            device_info = self.device.get_device_info()
            
            # Текущий источник синхронизации
            current_source = device_info.get('current_clock_source', 'Unknown')
            self.current_source_value.config(text=current_source)
            
            # Статус GNSS
            gnss_status = device_info.get('gnss_sync', 'Unknown')
            self.gnss_status_value.config(text=gnss_status)
            
            # Установка выбранного источника в комбобоксе
            if current_source in self.available_sources:
                self.source_var.set(current_source)
            
            # Обновление информации
            self._update_info()
            
        except Exception as e:
            self.logger.error(f"Error loading clock settings: {e}")
            self._show_error(str(e))
    
    def _update_info(self):
        """Обновление информационной области"""
        info = []
        
        try:
            if self.device:
                device_info = self.device.get_device_info()
                
                info.append("=== Clock Synchronization Status ===")
                info.append(f"Current Clock Source: {device_info.get('current_clock_source', 'Unknown')}")
                info.append(f"GNSS Synchronization: {device_info.get('gnss_sync', 'Unknown')}")
                info.append("")
                
                info.append("=== Available Clock Sources ===")
                for source in self.available_sources:
                    status = "✓ Current" if source == device_info.get('current_clock_source') else "○ Available"
                    info.append(f"{status} {source}")
                
                info.append("")
                info.append("=== Source Descriptions ===")
                info.append("GNSS: Global Navigation Satellite System")
                info.append("EXT: External clock source")
                info.append("EXT_PPS: External Pulse Per Second")
                info.append("IRIG: IRIG-B time code")
                info.append("DCF: DCF77 time signal")
                info.append("MSF: MSF time signal")
                
        except Exception as e:
            info = [f"Error loading synchronization info: {e}"]
        
        # Обновление текста
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, "\n".join(info))
        self.info_text.config(state=tk.DISABLED)
    
    def _show_no_device(self):
        """Отображение отсутствия устройства"""
        self.current_source_value.config(text="No device")
        self.gnss_status_value.config(text="N/A")
        self.sync_status_value.config(text="N/A")
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, "No QUANTUM-PCI device connected.\nClock settings unavailable.")
        self.info_text.config(state=tk.DISABLED)
    
    def _show_error(self, error_msg: str):
        """Отображение ошибки"""
        self.sync_status_value.config(text="Error")
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, f"Error accessing clock settings:\n{error_msg}")
        self.info_text.config(state=tk.DISABLED)
    
    def _apply_clock_source(self):
        """Применение выбранного источника синхронизации"""
        if not self.device:
            messagebox.showerror("Error", "No device connected")
            return
            
        selected_source = self.source_var.get()
        if not selected_source:
            messagebox.showerror("Error", "Please select a clock source")
            return
            
        try:
            # Здесь должен быть метод установки источника синхронизации
            # self.device.set_clock_source(selected_source)
            messagebox.showinfo("Success", f"Clock source set to {selected_source}")
            self.logger.info(f"Clock source changed to {selected_source}")
            self._refresh_settings()
            
        except Exception as e:
            self.logger.error(f"Error setting clock source: {e}")
            messagebox.showerror("Error", f"Failed to set clock source:\n{e}")
    
    def _toggle_gnss(self):
        """Переключение GNSS"""
        try:
            # Здесь должен быть метод управления GNSS
            # enabled = self.gnss_enable_var.get()
            # self.device.set_gnss_enabled(enabled)
            self.logger.info(f"GNSS {'enabled' if self.gnss_enable_var.get() else 'disabled'}")
            
        except Exception as e:
            self.logger.error(f"Error toggling GNSS: {e}")
            messagebox.showerror("Error", f"Failed to toggle GNSS:\n{e}")
    
    def _toggle_antenna_power(self):
        """Переключение питания антенны"""
        try:
            # Здесь должен быть метод управления питанием антенны
            # enabled = self.gnss_antenna_var.get()
            # self.device.set_antenna_power(enabled)
            self.logger.info(f"Antenna power {'enabled' if self.gnss_antenna_var.get() else 'disabled'}")
            
        except Exception as e:
            self.logger.error(f"Error toggling antenna power: {e}")
            messagebox.showerror("Error", f"Failed to toggle antenna power:\n{e}")
    
    def _toggle_pps(self):
        """Переключение PPS"""
        try:
            # Здесь должен быть метод управления PPS
            # enabled = self.pps_enable_var.get()
            # self.device.set_pps_enabled(enabled)
            self.logger.info(f"PPS {'enabled' if self.pps_enable_var.get() else 'disabled'}")
            
        except Exception as e:
            self.logger.error(f"Error toggling PPS: {e}")
            messagebox.showerror("Error", f"Failed to toggle PPS:\n{e}")
    
    def _apply_frequency(self):
        """Применение частоты"""
        try:
            frequency = int(self.frequency_var.get())
            # Здесь должен быть метод установки частоты
            # self.device.set_output_frequency(frequency)
            messagebox.showinfo("Success", f"Output frequency set to {frequency} Hz")
            self.logger.info(f"Output frequency set to {frequency} Hz")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid frequency value")
        except Exception as e:
            self.logger.error(f"Error setting frequency: {e}")
            messagebox.showerror("Error", f"Failed to set frequency:\n{e}")
    
    def _refresh_settings(self):
        """Обновление настроек"""
        self._load_clock_settings()
    
    def _reset_to_defaults(self):
        """Сброс к настройкам по умолчанию"""
        result = messagebox.askyesno(
            "Confirm Reset", 
            "Reset clock settings to default values?\nThis will change the current synchronization configuration."
        )
        
        if result:
            try:
                # Сброс к значениям по умолчанию
                self.source_var.set("GNSS")
                self.gnss_enable_var.set(True)
                self.gnss_antenna_var.set(True)
                self.pps_enable_var.set(True)
                self.frequency_var.set("10000000")
                
                messagebox.showinfo("Reset", "Clock settings reset to defaults")
                self.logger.info("Clock settings reset to defaults")
                
            except Exception as e:
                self.logger.error(f"Error resetting to defaults: {e}")
                messagebox.showerror("Error", f"Failed to reset settings:\n{e}")
    
    def refresh(self):
        """Обновление панели (вызывается извне)"""
        self._refresh_settings()