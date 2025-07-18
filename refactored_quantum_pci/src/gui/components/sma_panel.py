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
        
        # Доступные сигналы будут загружены от устройства
        self.available_input_signals = []
        self.available_output_signals = []
        
        # Хранилище переменных для комбобоксов
        self.input_vars = {}
        self.output_vars = {}
        
        self._load_available_signals()
        self._create_widgets()
        self._layout_widgets()
        self._load_sma_configuration()
        
    def _load_available_signals(self):
        """Загрузка доступных сигналов от устройства"""
        if not self.device:
            # Fallback сигналы точно соответствующие драйверу ptp_ocp.c
            self.available_input_signals = ["None", "10Mhz", "PPS1", "PPS2", "TS1", "TS2", "TS3", "TS4", "IRIG", "DCF", "FREQ1", "FREQ2", "FREQ3", "FREQ4"]
            self.available_output_signals = ["None", "10Mhz", "PHC", "MAC", "GNSS1", "GNSS2", "IRIG", "DCF", "GEN1", "GEN2", "GEN3", "GEN4", "GND", "VCC"]
            return
            
        try:
            # Получаем доступные сигналы от устройства
            self.available_input_signals = self.device.get_available_sma_inputs()
            self.available_output_signals = self.device.get_available_sma_outputs()
            
            # Добавляем "None" если его нет в списке
            if "None" not in self.available_input_signals:
                self.available_input_signals.insert(0, "None")
            if "None" not in self.available_output_signals:
                self.available_output_signals.insert(0, "None")
                
            self.logger.info(f"Loaded available SMA inputs: {self.available_input_signals}")
            self.logger.info(f"Loaded available SMA outputs: {self.available_output_signals}")
            
        except Exception as e:
            self.logger.error(f"Error loading available SMA signals: {e}")
            # Используем fallback сигналы при ошибке (полный набор из ptp_ocp.c)
            self.available_input_signals = ["None", "10Mhz", "PPS1", "PPS2", "TS1", "TS2", "TS3", "TS4", "IRIG", "DCF", "FREQ1", "FREQ2", "FREQ3", "FREQ4"]
            self.available_output_signals = ["None", "10Mhz", "PHC", "MAC", "GNSS1", "GNSS2", "IRIG", "DCF", "GEN1", "GEN2", "GEN3", "GEN4", "GND", "VCC"]
        
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
        
        # SMA Input порты (sma1, sma2, sma3, sma4)
        self.input_ports = ["sma1", "sma2", "sma3", "sma4"]
        self.input_combos = {}
        
        for i, port in enumerate(self.input_ports):
            label = ttk.Label(self.inputs_frame, text=f"{port.upper()}:")
            var = tk.StringVar()
            self.input_vars[port] = var
            
            combo = ttk.Combobox(
                self.inputs_frame,
                textvariable=var,
                values=self.available_input_signals,
                state="readonly",
                width=15
            )
            self.input_combos[port] = combo
        
        # Выходные порты
        self.outputs_frame = ttk.LabelFrame(self.frame, text="Output Ports")
        
        # SMA Output порты (sma1_out, sma2_out, sma3_out, sma4_out)
        self.output_ports = ["sma1_out", "sma2_out", "sma3_out", "sma4_out"]
        self.output_combos = {}
        
        for i, port in enumerate(self.output_ports):
            label = ttk.Label(self.outputs_frame, text=f"{port.upper()}:")
            var = tk.StringVar()
            self.output_vars[port] = var
            
            combo = ttk.Combobox(
                self.outputs_frame,
                textvariable=var,
                values=self.available_output_signals,
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
            
            label = ttk.Label(row_frame, text=f"{port.upper()}:", width=8)
            label.pack(side=tk.LEFT)
            
            self.input_combos[port].pack(side=tk.LEFT, padx=(5, 0))
        
        # Output ports
        self.outputs_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        for i, port in enumerate(self.output_ports):
            row_frame = ttk.Frame(self.outputs_frame)
            row_frame.pack(fill=tk.X, padx=10, pady=2)
            
            label = ttk.Label(row_frame, text=f"{port.upper()}:", width=12)
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
        preset_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.preset_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.load_preset_button.pack(side=tk.LEFT)
        
        # Information area
        self.info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Заполнение информационной области
        self._update_info_display()
    
    def _load_sma_configuration(self):
        """Загрузка текущей конфигурации SMA"""
        if not self.device:
            self._show_no_device()
            return
        
        try:
            sma_config = self.device.get_sma_configuration()
            
            # Обновление входов
            inputs = sma_config.get('inputs', {})
            for port in self.input_ports:
                if port in inputs:
                    value = inputs[port]
                    # Проверяем что значение доступно в комбобоксе
                    if value in self.available_input_signals:
                        self.input_vars[port].set(value)
                    else:
                        self.input_vars[port].set("None")
                else:
                    self.input_vars[port].set("None")
            
            # Обновление выходов  
            outputs = sma_config.get('outputs', {})
            for port in self.output_ports:
                # Ключ в конфигурации может быть без "_out" суффикса
                port_key = port.replace("_out", "")
                if port in outputs:
                    value = outputs[port]
                elif port_key in outputs:
                    value = outputs[port_key]
                else:
                    value = "None"
                    
                # Проверяем что значение доступно в комбобоксе
                if value in self.available_output_signals:
                    self.output_vars[port].set(value)
                else:
                    self.output_vars[port].set("None")
            
            # Обновление отображения текущей конфигурации
            self._update_current_config_display(sma_config)
            
        except Exception as e:
            self.logger.error(f"Error loading SMA configuration: {e}")
            self._show_error(str(e))
    
    def _update_current_config_display(self, sma_config: Dict):
        """Обновление отображения текущей конфигурации"""
        lines = []
        lines.append("=== Current SMA Configuration ===")
        lines.append("")
        
        # Входы
        if 'inputs' in sma_config:
            lines.append("INPUT PORTS:")
            for port, signal in sma_config['inputs'].items():
                lines.append(f"  {port.upper()}: {signal}")
        
        lines.append("")
        
        # Выходы
        if 'outputs' in sma_config:
            lines.append("OUTPUT PORTS:")
            for port, signal in sma_config['outputs'].items():
                lines.append(f"  {port.upper()}: {signal}")
        
        lines.append("")
        lines.append(f"Last updated: {sma_config.get('timestamp', 'Unknown')}")
        
        # Информация о портах
        lines.append("")
        lines.append("=== Port Guidelines ===")
        lines.append("• SMA1-4: Physical SMA connectors")
        lines.append("• Input signals: External signals to device")
        lines.append("• Output signals: Device signals to external")
        lines.append("• None: Disconnected/unused port")
        lines.append("• 10Mhz: 10MHz reference clock")
        lines.append("• PPS1/PPS2: Pulse Per Second signals")
        lines.append("• PHC: PTP Hardware Clock output")
        lines.append("• GNSS1/GNSS2: GNSS receiver outputs")
        lines.append("• IRIG/DCF: Time code signals")
        
        self.current_text.config(state=tk.NORMAL)
        self.current_text.delete(1.0, tk.END)
        self.current_text.insert(1.0, "\n".join(lines))
        self.current_text.config(state=tk.DISABLED)
    
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
            # Применяем каждый порт по отдельности для лучшего контроля ошибок
            errors = []
            success_count = 0
            
            # Применение входов
            for port in self.input_ports:
                signal = self.input_vars[port].get()
                if signal and signal != "N/A" and signal != "None":
                    try:
                        port_num = int(port[-1])  # извлекаем номер из sma1, sma2, etc.
                        self.device.set_sma_input(port_num, signal)
                        self.logger.info(f"Set {port} input to {signal}")
                        success_count += 1
                    except Exception as e:
                        error_msg = f"Failed to set {port} input to {signal}: {e}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
            
            # Применение выходов
            for port in self.output_ports:
                signal = self.output_vars[port].get()
                if signal and signal != "N/A" and signal != "None":
                    try:
                        port_num = int(port[3])  # извлекаем номер из sma1_out, sma2_out, etc.
                        self.device.set_sma_output(port_num, signal)
                        self.logger.info(f"Set {port} output to {signal}")
                        success_count += 1
                    except Exception as e:
                        error_msg = f"Failed to set {port} output to {signal}: {e}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
            
            # Показываем результат
            if errors:
                error_text = "\n".join(errors)
                if success_count > 0:
                    messagebox.showwarning("Partial Success", 
                        f"Applied {success_count} configurations successfully.\n\nErrors:\n{error_text}")
                else:
                    messagebox.showerror("Error", f"Failed to apply SMA configuration:\n{error_text}")
            else:
                messagebox.showinfo("Success", f"SMA configuration applied successfully! ({success_count} changes)")
                self.logger.info("SMA configuration updated successfully")
            
            # Обновление отображения
            self._refresh_configuration()
            
        except Exception as e:
            self.logger.error(f"Error applying SMA configuration: {e}")
            messagebox.showerror("Error", f"Failed to apply SMA configuration:\n{e}")
    
    def _refresh_configuration(self):
        """Обновление конфигурации"""
        self._load_available_signals()  # Обновляем доступные сигналы
        self._load_sma_configuration()  # Загружаем текущую конфигурацию
    
    def _reset_to_defaults(self):
        """Сброс к настройкам по умолчанию"""
        result = messagebox.askyesno(
            "Confirm Reset", 
            "Reset SMA configuration to default values?\nThis will change all port assignments."
        )
        
        if result:
            try:
                # Настройки по умолчанию для ptp_ocp согласно документации
                default_config = {
                    'inputs': {
                        'sma1': 'None',     # Обычно используется для внешнего опорного сигнала
                        'sma2': 'None',     # Зарезервирован
                        'sma3': 'None',     # Зарезервирован  
                        'sma4': 'None'      # Зарезервирован
                    },
                    'outputs': {
                        'sma1_out': '10Mhz',  # Обычно 10MHz опорная частота
                        'sma2_out': 'PPS1',   # Pulse Per Second
                        'sma3_out': 'None',   # Зарезервирован
                        'sma4_out': 'None'    # Зарезервирован
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
                messagebox.showerror("Error", f"Failed to reset configuration: {e}")
    
    def _load_preset(self):
        """Загрузка предустановленной конфигурации"""
        preset = self.preset_var.get()
        
        if not preset:
            messagebox.showwarning("Warning", "Please select a preset configuration")
            return
        
        presets = {
            "Standard": {
                'inputs': {'sma1': 'None', 'sma2': 'None', 'sma3': 'None', 'sma4': 'None'},
                'outputs': {'sma1_out': '10Mhz', 'sma2_out': 'PPS1', 'sma3_out': 'None', 'sma4_out': 'None'}
            },
            "GNSS Only": {
                'inputs': {'sma1': 'None', 'sma2': 'None', 'sma3': 'None', 'sma4': 'None'},
                'outputs': {'sma1_out': 'GNSS1', 'sma2_out': 'PPS1', 'sma3_out': 'None', 'sma4_out': 'None'}
            },
            "External Clock": {
                'inputs': {'sma1': '10Mhz', 'sma2': 'PPS1', 'sma3': 'None', 'sma4': 'None'},
                'outputs': {'sma1_out': 'PHC', 'sma2_out': 'PPS1', 'sma3_out': 'None', 'sma4_out': 'None'}
            },
            "IRIG-B": {
                'inputs': {'sma1': 'IRIG', 'sma2': 'None', 'sma3': 'None', 'sma4': 'None'},
                'outputs': {'sma1_out': '10Mhz', 'sma2_out': 'IRIG', 'sma3_out': 'None', 'sma4_out': 'None'}
            }
        }
        
        if preset == "Custom":
            messagebox.showinfo("Custom", "Custom configuration allows manual setup of all ports")
            return
        
        config = presets.get(preset)
        if config:
            # Установка значений в GUI
            for port, signal in config['inputs'].items():
                if port in self.input_vars and signal in self.available_input_signals:
                    self.input_vars[port].set(signal)
            
            for port, signal in config['outputs'].items():
                if port in self.output_vars and signal in self.available_output_signals:
                    self.output_vars[port].set(signal)
            
            messagebox.showinfo("Preset Loaded", f"'{preset}' configuration loaded")
            self.logger.info(f"Loaded preset configuration: {preset}")
    
    def _update_info_display(self):
        """Обновление информационного дисплея"""
        info_lines = [
            "=== SMA Signal Descriptions ===",
            "",
            "INPUT SIGNALS:",
            "• None - Порт отключен",
            "• 10Mhz - Внешний опорный сигнал 10 МГц",
            "• PPS1/PPS2 - Внешние импульсы секунды",
            "• TS1-TS4 - Внешние временные метки",
            "• IRIG - IRIG-B временной код",
            "• DCF - DCF77 временной код",
            "• FREQ1-FREQ4 - Частотные входы",
            "",
            "OUTPUT SIGNALS:",
            "• None - Порт отключен",
            "• 10Mhz - Опорная частота 10 МГц",
            "• PHC - PTP Hardware Clock выход",
            "• MAC - MAC часы",
            "• GNSS1/GNSS2 - GNSS приемник",
            "• IRIG - IRIG-B временной код",
            "• DCF - DCF77 временной код",
            "• GEN1-GEN4 - Программируемые генераторы",
            "• GND - Земля",
            "• VCC - Питание",
            "",
            "ПРИМЕЧАНИЯ:",
            "• Конфигурация сохраняется в устройстве",
            "• Изменения применяются немедленно",
            "• Некорректные сигналы могут вызвать ошибки",
            "• Используйте 'Refresh' для обновления статуса"
        ]
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, "\n".join(info_lines))
        self.info_text.config(state=tk.DISABLED)
    
    def update_device(self, device: Optional[QuantumPCIDevice]):
        """Обновление ссылки на устройство"""
        self.device = device
        self._load_available_signals()
        
        # Обновление значений комбобоксов
        for combo in self.input_combos.values():
            combo['values'] = self.available_input_signals
        for combo in self.output_combos.values():
            combo['values'] = self.available_output_signals
            
        self._load_sma_configuration()
    
    def get_widget(self) -> tk.Widget:
        """Получение основного виджета панели"""
        return self.frame