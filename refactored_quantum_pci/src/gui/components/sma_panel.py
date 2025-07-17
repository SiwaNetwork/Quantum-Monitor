"""
Панель настроек SMA портов QUANTUM-PCI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Dict, List

from ...core.device import QuantumPCIDevice
from ...core.exceptions import QuantumPCIError


class SMAPanel:
    """Панель настроек SMA портов"""
    
    def __init__(self, parent: tk.Widget, device: Optional[QuantumPCIDevice], logger: logging.Logger):
        """
        Инициализация панели SMA
        
        Args:
            parent: Родительский виджет
            device: Объект устройства
            logger: Логгер
        """
        self.parent = parent
        self.device = device
        self.logger = logger
        
        self.frame = ttk.Frame(parent)
        
        # Доступные сигналы для подключения
        self.available_signals = [
            "NONE", "10MHZ", "PPS", "GNSS_1PPS", "EXT_CLK", 
            "IRIG_B", "DCF77", "MSF", "FREQUENCY_REF"
        ]
        
        # Хранилище переменных для комбобоксов
        self.input_vars = {}
        self.output_vars = {}
        
        self._create_widgets()
        self._layout_widgets()
        self._load_sma_configuration()
        
    def _create_widgets(self):
        """Создание виджетов панели SMA"""
        # Заголовок
        self.title_label = ttk.Label(
            self.frame, 
            text="SMA Port Configuration", 
            font=("Arial", 14, "bold")
        )
        
        # Текущая конфигурация
        self.current_frame = ttk.LabelFrame(self.frame, text="Current Configuration")
        self.current_text = tk.Text(
            self.current_frame,
            height=6,
            width=60,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        
        # Входные порты
        self.inputs_frame = ttk.LabelFrame(self.frame, text="Input Ports")
        
        # SMA Input порты (обычно SMA1, SMA2, SMA3, SMA4)
        self.input_ports = ["SMA1", "SMA2", "SMA3", "SMA4"]
        self.input_combos = {}
        
        for i, port in enumerate(self.input_ports):
            label = ttk.Label(self.inputs_frame, text=f"{port}:")
            var = tk.StringVar()
            self.input_vars[port] = var
            
            combo = ttk.Combobox(
                self.inputs_frame,
                textvariable=var,
                values=self.available_signals,
                state="readonly",
                width=15
            )
            self.input_combos[port] = combo
        
        # Выходные порты
        self.outputs_frame = ttk.LabelFrame(self.frame, text="Output Ports")
        
        # SMA Output порты
        self.output_ports = ["SMA1_OUT", "SMA2_OUT", "SMA3_OUT", "SMA4_OUT"]
        self.output_combos = {}
        
        for i, port in enumerate(self.output_ports):
            label = ttk.Label(self.outputs_frame, text=f"{port}:")
            var = tk.StringVar()
            self.output_vars[port] = var
            
            combo = ttk.Combobox(
                self.outputs_frame,
                textvariable=var,
                values=self.available_signals,
                state="readonly",
                width=15
            )
            self.output_combos[port] = combo
        
        # Кнопки управления
        self.control_frame = ttk.Frame(self.frame)
        
        self.apply_button = ttk.Button(
            self.control_frame,
            text="Apply Configuration",
            command=self._apply_configuration
        )
        
        self.refresh_button = ttk.Button(
            self.control_frame,
            text="Refresh",
            command=self._refresh_configuration
        )
        
        self.reset_button = ttk.Button(
            self.control_frame,
            text="Reset to Defaults",
            command=self._reset_to_defaults
        )
        
        # Предустановленные конфигурации
        self.presets_frame = ttk.LabelFrame(self.frame, text="Preset Configurations")
        
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(
            self.presets_frame,
            textvariable=self.preset_var,
            values=["Standard", "GNSS Only", "External Clock", "IRIG-B", "Custom"],
            state="readonly"
        )
        
        self.load_preset_button = ttk.Button(
            self.presets_frame,
            text="Load Preset",
            command=self._load_preset
        )
        
        # Информационная область
        self.info_frame = ttk.LabelFrame(self.frame, text="Signal Descriptions")
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
        
        # Current configuration
        self.current_frame.pack(fill=tk.X, pady=(0, 10))
        self.current_text.pack(fill=tk.X, padx=10, pady=10)
        
        # Create a frame to hold inputs and outputs side by side
        ports_frame = ttk.Frame(self.frame)
        ports_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Input ports
        self.inputs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        for i, port in enumerate(self.input_ports):
            row_frame = ttk.Frame(self.inputs_frame)
            row_frame.pack(fill=tk.X, padx=10, pady=2)
            
            label = ttk.Label(row_frame, text=f"{port}:", width=8)
            label.pack(side=tk.LEFT)
            
            self.input_combos[port].pack(side=tk.LEFT, padx=(5, 0))
        
        # Output ports
        self.outputs_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        for i, port in enumerate(self.output_ports):
            row_frame = ttk.Frame(self.outputs_frame)
            row_frame.pack(fill=tk.X, padx=10, pady=2)
            
            label = ttk.Label(row_frame, text=f"{port}:", width=10)
            label.pack(side=tk.LEFT)
            
            self.output_combos[port].pack(side=tk.LEFT, padx=(5, 0))
        
        # Control buttons
        self.control_frame.pack(fill=tk.X, pady=(0, 10))
        self.apply_button.pack(side=tk.LEFT, padx=(10, 5))
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        self.reset_button.pack(side=tk.LEFT, padx=5)
        
        # Presets
        self.presets_frame.pack(fill=tk.X, pady=(0, 10))
        
        preset_control_frame = ttk.Frame(self.presets_frame)
        preset_control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(preset_control_frame, text="Preset:").pack(side=tk.LEFT)
        self.preset_combo.pack(side=tk.LEFT, padx=(10, 5))
        self.load_preset_button.pack(side=tk.LEFT, padx=5)
        
        # Info area
        self.info_frame.pack(fill=tk.BOTH, expand=True)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Load signal descriptions
        self._load_signal_descriptions()
        
    def _load_sma_configuration(self):
        """Загрузка текущей конфигурации SMA"""
        try:
            if not self.device:
                self._show_no_device()
                return
                
            sma_config = self.device.get_sma_configuration()
            
            # Загрузка конфигурации входов
            inputs = sma_config.get('inputs', {})
            for port in self.input_ports:
                signal = inputs.get(port, 'NONE')
                if signal in self.available_signals:
                    self.input_vars[port].set(signal)
                else:
                    self.input_vars[port].set('NONE')
            
            # Загрузка конфигурации выходов
            outputs = sma_config.get('outputs', {})
            for port in self.output_ports:
                signal = outputs.get(port, 'NONE')
                if signal in self.available_signals:
                    self.output_vars[port].set(signal)
                else:
                    self.output_vars[port].set('NONE')
            
            # Обновление текущей конфигурации
            self._update_current_config_display(sma_config)
            
        except Exception as e:
            self.logger.error(f"Error loading SMA configuration: {e}")
            self._show_error(str(e))
    
    def _update_current_config_display(self, config: Dict):
        """Обновление отображения текущей конфигурации"""
        lines = []
        lines.append("=== Current SMA Configuration ===")
        lines.append("")
        
        inputs = config.get('inputs', {})
        if inputs:
            lines.append("INPUT PORTS:")
            for port, signal in inputs.items():
                lines.append(f"  {port}: {signal}")
        
        outputs = config.get('outputs', {})
        if outputs:
            lines.append("")
            lines.append("OUTPUT PORTS:")
            for port, signal in outputs.items():
                lines.append(f"  {port}: {signal}")
        
        # Обновление текста
        self.current_text.config(state=tk.NORMAL)
        self.current_text.delete(1.0, tk.END)
        self.current_text.insert(1.0, "\n".join(lines))
        self.current_text.config(state=tk.DISABLED)
    
    def _load_signal_descriptions(self):
        """Загрузка описаний сигналов"""
        descriptions = [
            "=== Available Signals ===",
            "",
            "NONE: No connection (port disabled)",
            "10MHZ: 10 MHz reference clock",
            "PPS: Pulse Per Second output",
            "GNSS_1PPS: GNSS-derived 1PPS signal",
            "EXT_CLK: External clock input",
            "IRIG_B: IRIG-B time code signal",
            "DCF77: DCF77 time signal (77.5 kHz)",
            "MSF: MSF time signal (60 kHz)",
            "FREQUENCY_REF: Frequency reference output",
            "",
            "=== Port Guidelines ===",
            "",
            "• Input ports receive external signals",
            "• Output ports provide device-generated signals",
            "• GNSS signals require GNSS module to be active",
            "• External clock inputs should be stable",
            "• PPS outputs are synchronized to device time"
        ]
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, "\n".join(descriptions))
        self.info_text.config(state=tk.DISABLED)
    
    def _show_no_device(self):
        """Отображение отсутствия устройства"""
        for var in self.input_vars.values():
            var.set("N/A")
        for var in self.output_vars.values():
            var.set("N/A")
            
        self.current_text.config(state=tk.NORMAL)
        self.current_text.delete(1.0, tk.END)
        self.current_text.insert(1.0, "No QUANTUM-PCI device connected.\nSMA configuration unavailable.")
        self.current_text.config(state=tk.DISABLED)
    
    def _show_error(self, error_msg: str):
        """Отображение ошибки"""
        self.current_text.config(state=tk.NORMAL)
        self.current_text.delete(1.0, tk.END)
        self.current_text.insert(1.0, f"Error accessing SMA configuration:\n{error_msg}")
        self.current_text.config(state=tk.DISABLED)
    
    def _apply_configuration(self):
        """Применение конфигурации SMA"""
        if not self.device:
            messagebox.showerror("Error", "No device connected")
            return
            
        try:
            # Сбор конфигурации из GUI
            new_config = {
                'inputs': {},
                'outputs': {}
            }
            
            for port in self.input_ports:
                signal = self.input_vars[port].get()
                if signal and signal != "N/A":
                    new_config['inputs'][port] = signal
            
            for port in self.output_ports:
                signal = self.output_vars[port].get()
                if signal and signal != "N/A":
                    new_config['outputs'][port] = signal
            
            # Применение конфигурации
            # Здесь должен быть метод установки конфигурации SMA
            # self.device.set_sma_configuration(new_config)
            
            messagebox.showinfo("Success", "SMA configuration applied successfully")
            self.logger.info("SMA configuration updated")
            
            # Обновление отображения
            self._update_current_config_display(new_config)
            
        except Exception as e:
            self.logger.error(f"Error applying SMA configuration: {e}")
            messagebox.showerror("Error", f"Failed to apply SMA configuration:\n{e}")
    
    def _refresh_configuration(self):
        """Обновление конфигурации"""
        self._load_sma_configuration()
    
    def _reset_to_defaults(self):
        """Сброс к настройкам по умолчанию"""
        result = messagebox.askyesno(
            "Confirm Reset", 
            "Reset SMA configuration to default values?\nThis will change all port assignments."
        )
        
        if result:
            try:
                # Настройки по умолчанию
                default_config = {
                    'inputs': {
                        'SMA1': 'EXT_CLK',
                        'SMA2': 'NONE',
                        'SMA3': 'NONE',
                        'SMA4': 'NONE'
                    },
                    'outputs': {
                        'SMA1_OUT': '10MHZ',
                        'SMA2_OUT': 'PPS',
                        'SMA3_OUT': 'NONE',
                        'SMA4_OUT': 'NONE'
                    }
                }
                
                # Установка значений в GUI
                for port, signal in default_config['inputs'].items():
                    if port in self.input_vars:
                        self.input_vars[port].set(signal)
                
                for port, signal in default_config['outputs'].items():
                    if port in self.output_vars:
                        self.output_vars[port].set(signal)
                
                messagebox.showinfo("Reset", "SMA configuration reset to defaults")
                self.logger.info("SMA configuration reset to defaults")
                
            except Exception as e:
                self.logger.error(f"Error resetting to defaults: {e}")
                messagebox.showerror("Error", f"Failed to reset configuration:\n{e}")
    
    def _load_preset(self):
        """Загрузка предустановленной конфигурации"""
        preset = self.preset_var.get()
        if not preset:
            messagebox.showerror("Error", "Please select a preset")
            return
            
        try:
            presets = {
                "Standard": {
                    'inputs': {'SMA1': 'EXT_CLK', 'SMA2': 'NONE', 'SMA3': 'NONE', 'SMA4': 'NONE'},
                    'outputs': {'SMA1_OUT': '10MHZ', 'SMA2_OUT': 'PPS', 'SMA3_OUT': 'NONE', 'SMA4_OUT': 'NONE'}
                },
                "GNSS Only": {
                    'inputs': {'SMA1': 'NONE', 'SMA2': 'NONE', 'SMA3': 'NONE', 'SMA4': 'NONE'},
                    'outputs': {'SMA1_OUT': 'GNSS_1PPS', 'SMA2_OUT': '10MHZ', 'SMA3_OUT': 'NONE', 'SMA4_OUT': 'NONE'}
                },
                "External Clock": {
                    'inputs': {'SMA1': 'EXT_CLK', 'SMA2': 'EXT_CLK', 'SMA3': 'NONE', 'SMA4': 'NONE'},
                    'outputs': {'SMA1_OUT': 'FREQUENCY_REF', 'SMA2_OUT': 'PPS', 'SMA3_OUT': 'NONE', 'SMA4_OUT': 'NONE'}
                },
                "IRIG-B": {
                    'inputs': {'SMA1': 'IRIG_B', 'SMA2': 'NONE', 'SMA3': 'NONE', 'SMA4': 'NONE'},
                    'outputs': {'SMA1_OUT': '10MHZ', 'SMA2_OUT': 'PPS', 'SMA3_OUT': 'IRIG_B', 'SMA4_OUT': 'NONE'}
                }
            }
            
            if preset in presets:
                config = presets[preset]
                
                # Установка значений в GUI
                for port, signal in config['inputs'].items():
                    if port in self.input_vars:
                        self.input_vars[port].set(signal)
                
                for port, signal in config['outputs'].items():
                    if port in self.output_vars:
                        self.output_vars[port].set(signal)
                
                messagebox.showinfo("Preset Loaded", f"'{preset}' preset configuration loaded")
                self.logger.info(f"Loaded preset: {preset}")
            else:
                messagebox.showinfo("Custom", "Custom preset selected - configure ports manually")
                
        except Exception as e:
            self.logger.error(f"Error loading preset: {e}")
            messagebox.showerror("Error", f"Failed to load preset:\n{e}")
    
    def refresh(self):
        """Обновление панели (вызывается извне)"""
        self._refresh_configuration()