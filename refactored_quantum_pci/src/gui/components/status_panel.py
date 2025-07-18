"""
Панель статуса устройства QUANTUM-PCI
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Any, Optional

from ...api.status_reader import StatusReader


class StatusPanel:
    """Панель отображения статуса устройства"""
    
    def __init__(self, parent: tk.Widget, status_reader: Optional[StatusReader], logger: logging.Logger):
        """
        Инициализация панели статуса
        
        Args:
            parent: Родительский виджет
            status_reader: Объект для чтения статуса
            logger: Логгер
        """
        self.parent = parent
        self.status_reader = status_reader
        self.logger = logger
        
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_widgets()
        self._layout_widgets()
        
    def _create_widgets(self):
        """Создание виджетов панели статуса"""
        # Заголовок статуса
        self.status_label = ttk.Label(
            self.frame, 
            text="Device Status", 
            font=("Arial", 12, "bold")
        )
        
        # Основной фрейм для статуса
        self.status_content_frame = ttk.Frame(self.frame)
        
        # Индикатор здоровья устройства
        self.health_frame = ttk.LabelFrame(self.status_content_frame, text="Health Status")
        self.health_indicator = tk.Label(
            self.health_frame,
            text="●", 
            font=("Arial", 16, "bold"),
            fg="gray"
        )
        self.health_text = ttk.Label(self.health_frame, text="Unknown")
        
        # Информация о синхронизации
        self.sync_frame = ttk.LabelFrame(self.status_content_frame, text="Synchronization")
        self.clock_source_label = ttk.Label(self.sync_frame, text="Clock Source:")
        self.clock_source_value = ttk.Label(self.sync_frame, text="Unknown")
        self.gnss_status_label = ttk.Label(self.sync_frame, text="GNSS Status:")
        self.gnss_status_value = ttk.Label(self.sync_frame, text="Unknown")
        
        # Кнопка обновления
        self.refresh_button = ttk.Button(
            self.frame,
            text="Refresh Status",
            command=self._refresh_status
        )
        
        # Текстовая область для детальной информации
        self.detail_frame = ttk.LabelFrame(self.status_content_frame, text="Details")
        self.detail_text = tk.Text(
            self.detail_frame,
            height=8,
            width=50,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.detail_scroll = ttk.Scrollbar(self.detail_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=self.detail_scroll.set)
        
    def _layout_widgets(self):
        """Размещение виджетов"""
        self.status_label.pack(pady=(0, 10))
        self.status_content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Health status
        self.health_frame.pack(fill=tk.X, pady=(0, 5))
        self.health_indicator.pack(side=tk.LEFT, padx=(10, 5))
        self.health_text.pack(side=tk.LEFT)
        
        # Synchronization info
        self.sync_frame.pack(fill=tk.X, pady=(0, 5))
        self.clock_source_label.grid(row=0, column=0, sticky=tk.W, padx=(10, 5))
        self.clock_source_value.grid(row=0, column=1, sticky=tk.W)
        self.gnss_status_label.grid(row=1, column=0, sticky=tk.W, padx=(10, 5))
        self.gnss_status_value.grid(row=1, column=1, sticky=tk.W)
        
        # Details
        self.detail_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        self.detail_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))
        
        # Refresh button
        self.refresh_button.pack(pady=5)
        
    def update_status(self, status: Dict[str, Any]):
        """
        Обновление отображения статуса
        
        Args:
            status: Словарь с данными статуса
        """
        try:
            if not status:
                self._show_no_data()
                return
                
            # Обновление статуса здоровья
            health_status = status.get('health_status', {})
            if health_status:
                healthy = health_status.get('healthy', False)
                if healthy:
                    self.health_indicator.config(fg="green")
                    self.health_text.config(text="Healthy")
                else:
                    self.health_indicator.config(fg="red")
                    self.health_text.config(text="Unhealthy")
            
            # Обновление информации о синхронизации
            device_info = status.get('device_info', {})
            if device_info:
                clock_source = device_info.get('current_clock_source', 'Unknown')
                gnss_sync = device_info.get('gnss_sync', 'Unknown')
                
                self.clock_source_value.config(text=clock_source)
                
                # Улучшенное отображение GNSS статуса с цветовой индикацией
                if gnss_sync.upper() == "SYNC":
                    self.gnss_status_value.config(text="SYNCHRONIZED", foreground="green")
                elif gnss_sync.upper().startswith("LOST"):
                    self.gnss_status_value.config(text="LOST", foreground="red")
                else:
                    self.gnss_status_value.config(text=gnss_sync, foreground="black")
            
            # Обновление детальной информации
            self._update_details(status)
            
        except Exception as e:
            self.logger.error(f"Error updating status display: {e}")
            self._show_error(str(e))
    
    def _update_details(self, status: Dict[str, Any]):
        """Обновление детальной информации"""
        details = []
        
        # Информация об устройстве
        device_info = status.get('device_info', {})
        if device_info:
            details.append("=== Device Information ===")
            for key, value in device_info.items():
                details.append(f"{key}: {value}")
            details.append("")
        
        # Проверки здоровья
        health_status = status.get('health_status', {})
        if health_status and 'checks' in health_status:
            details.append("=== Health Checks ===")
            for check, result in health_status['checks'].items():
                status_text = "PASS" if result else "FAIL"
                details.append(f"{check}: {status_text}")
            details.append("")
        
        # Конфигурация SMA
        sma_config = status.get('sma_configuration', {})
        if sma_config:
            details.append("=== SMA Configuration ===")
            if 'inputs' in sma_config:
                details.append("Inputs:")
                for port, signal in sma_config['inputs'].items():
                    details.append(f"  {port}: {signal}")
            if 'outputs' in sma_config:
                details.append("Outputs:")
                for port, signal in sma_config['outputs'].items():
                    details.append(f"  {port}: {signal}")
        
        # Обновление текста
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, "\n".join(details))
        self.detail_text.config(state=tk.DISABLED)
    
    def _show_no_data(self):
        """Отображение отсутствия данных"""
        self.health_indicator.config(fg="gray")
        self.health_text.config(text="No Data")
        self.clock_source_value.config(text="Unknown")
        self.gnss_status_value.config(text="Unknown")
        
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, "No status data available")
        self.detail_text.config(state=tk.DISABLED)
    
    def _show_error(self, error_msg: str):
        """Отображение ошибки"""
        self.health_indicator.config(fg="red")
        self.health_text.config(text="Error")
        
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, f"Error: {error_msg}")
        self.detail_text.config(state=tk.DISABLED)
    
    def _refresh_status(self):
        """Принудительное обновление статуса"""
        if self.status_reader:
            try:
                status = self.status_reader.get_full_status()
                self.update_status(status)
            except Exception as e:
                self.logger.error(f"Error refreshing status: {e}")
                self._show_error(str(e))
        else:
            self._show_no_data()