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
        
        # Доступные сигналы согласно документации Linux kernel (/sys/class/timecard/ocpN/available_sma_*)
        self.available_input_signals = [
            "None",     # signal input is disabled
            "10Mhz",    # signal is used as the 10Mhz reference clock
            "PPS1",     # signal is sent to the PPS1 selector
            "PPS2",     # signal is sent to the PPS2 selector
            "TS1",      # signal is sent to timestamper 1
            "TS2",      # signal is sent to timestamper 2
            "TS3",      # signal is sent to timestamper 3
            "TS4",      # signal is sent to timestamper 4
            "IRIG",     # signal is sent to the IRIG-B module
            "DCF",      # signal is sent to the DCF module

        ]
        
        self.available_output_signals = [
            "10Mhz",    # output is from the 10Mhz reference clock
            "PHC",      # output PPS is from the PHC clock
            "MAC",      # output PPS is from the Miniature Atomic Clock
            "GNSS1",    # output PPS is from the first GNSS module
            "GNSS2",    # output PPS is from the second GNSS module
            "IRIG",     # output is from the PHC, in IRIG-B format
            "DCF",      # output is from the PHC, in DCF format

            "GND",      # output is GND
            "VCC"       # output is VCC
        ]
        
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
            # Используем стандартные сигналы согласно документации ядра Linux
            self.logger.info("Using standard SMA signals from kernel documentation")
            return
            
        try:
            # Попытка получить доступные сигналы от устройства
            device_inputs = self.device.get_available_sma_inputs()
            device_outputs = self.device.get_available_sma_outputs()
            
            # Если устройство предоставляет список сигналов, используем его
            if device_inputs:
                self.available_input_signals = device_inputs
                # Обеспечиваем наличие "None" в начале списка для отключения портов
                if "None" not in self.available_input_signals:
                    self.available_input_signals.insert(0, "None")
                    
            if device_outputs:
                self.available_output_signals = device_outputs
                
            self.logger.info(f"Loaded available SMA inputs: {self.available_input_signals}")
            self.logger.info(f"Loaded available SMA outputs: {self.available_output_signals}")
            
        except Exception as e:
            self.logger.warning(f"Error loading device SMA signals, using defaults: {e}")
            # Используем стандартные сигналы при ошибке
        
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
            combo.bind("<<ComboboxSelected>>", lambda e, p=port: self._on_input_changed(p))
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
            combo.bind("<<ComboboxSelected>>", lambda e, p=port: self._on_output_changed(p))
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
            values=["Standard", "GNSS Only", "External Clock", "IRIG-B", "DCF", "Custom"],
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
        
    def _on_input_changed(self, port: str):
        """Обработчик изменения входного сигнала"""
        value = self.input_vars[port].get()
        self.logger.info(f"Input {port} changed to: {value}")
        self._update_signal_description(f"Input {port}", value, True)
        
    def _on_output_changed(self, port: str):
        """Обработчик изменения выходного сигнала"""
        value = self.output_vars[port].get()
        self.logger.info(f"Output {port} changed to: {value}")
        self._update_signal_description(f"Output {port}", value, False)
        
    def _update_signal_description(self, port: str, signal: str, is_input: bool):
        """Обновление описания сигнала при выборе"""
        descriptions = {
            # Входные сигналы (destinations/sinks)
            "None": "Signal input is disabled",
            "10Mhz": "Signal is used as the 10MHz reference clock",
            "PPS1": "Signal is sent to the PPS1 selector",
            "PPS2": "Signal is sent to the PPS2 selector", 
            "TS1": "Signal is sent to timestamper 1",
            "TS2": "Signal is sent to timestamper 2",
            "TS3": "Signal is sent to timestamper 3",
            "TS4": "Signal is sent to timestamper 4",
            "IRIG": "Signal is sent to the IRIG-B module" if is_input else "Output is from the PHC, in IRIG-B format",
            "DCF": "Signal is sent to the DCF module" if is_input else "Output is from the PHC, in DCF format",

            # Выходные сигналы (sources)
            "PHC": "Output PPS is from the PHC clock",
            "MAC": "Output PPS is from the Miniature Atomic Clock",
            "GNSS1": "Output PPS is from the first GNSS module",
            "GNSS2": "Output PPS is from the second GNSS module",

            "GND": "Output is GND",
            "VCC": "Output is VCC"
        }
        
        # Для входных сигналов 10Mhz используется в качестве выхода
        if signal == "10Mhz" and not is_input:
            descriptions["10Mhz"] = "Output is from the 10MHz reference clock"
        
        description = descriptions.get(signal, "Unknown signal")
        
        # Показать уведомление с описанием
        if signal != "None":
            messagebox.showinfo(
                "Signal Description", 
                f"{port}: {signal}\n\n{description}"
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
            },
            "DCF": {
                'inputs': {'sma1': 'DCF', 'sma2': 'None', 'sma3': 'None', 'sma4': 'None'},
                'outputs': {'sma1_out': '10Mhz', 'sma2_out': 'DCF', 'sma3_out': 'None', 'sma4_out': 'None'}
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
            "=== SMA Signal Descriptions (Linux Kernel Documentation) ===",
            "",
            "INPUT SIGNALS (Destinations/Sinks):",
            "• None - Signal input is disabled",
            "• 10Mhz - Signal is used as the 10MHz reference clock",
            "• PPS1/PPS2 - Signal is sent to the PPS1/PPS2 selector",
            "• TS1-TS4 - Signal is sent to timestamper 1-4",
            "• IRIG - Signal is sent to the IRIG-B module",
            "• DCF - Signal is sent to the DCF module",

            "",
            "OUTPUT SIGNALS (Sources):",
            "• 10Mhz - Output is from the 10MHz reference clock",
            "• PHC - Output PPS is from the PHC clock",
            "• MAC - Output PPS is from the Miniature Atomic Clock",
            "• GNSS1/GNSS2 - Output PPS is from the first/second GNSS module",
            "• IRIG - Output is from the PHC, in IRIG-B format",
            "• DCF - Output is from the PHC, in DCF format",

            "• GND - Output is GND",
            "• VCC - Output is VCC",
            "",
            "CLOCK SOURCES (/sys/class/timecard/ocpN/available_clock_sources):",
            "• NONE - No adjustments",
            "• PPS - Adjustments come from the PPS1 selector (default)",
            "• TOD - Adjustments from the GNSS/TOD module",
            "• IRIG - Adjustments from external IRIG-B signal",
            "• DCF - Adjustments from external DCF signal",
            "",
            "ПРИМЕЧАНИЯ:",
            "• Сигналы соответствуют Linux kernel documentation",
            "• Выбор из выпадающего списка применяется сразу",
            "• Конфигурация сохраняется в устройстве",
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