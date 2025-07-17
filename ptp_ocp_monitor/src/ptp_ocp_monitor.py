#!/usr/bin/env python3
"""
PTP OCP Driver Monitor
Monitors functions and sysfs attributes of the ptp_ocp driver
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import threading
import queue

class PTPOCPMonitor:
    """Monitor for PTP OCP driver functions and sysfs attributes"""
    
    def __init__(self, device_path=None, log_file=None):
        self.device_path = device_path
        self.log_file = log_file or f"ptp_ocp_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.running = False
        self.data_queue = queue.Queue()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Find PTP OCP device if not specified
        if not self.device_path:
            self.device_path = self._find_ptp_ocp_device()
            
        if not self.device_path:
            raise ValueError("No PTP OCP device found. Please specify device path.")
            
        self.logger.info(f"Monitoring PTP OCP device: {self.device_path}")
        
        # Define sysfs attributes to monitor
        self.sysfs_attrs = [
            'sma1', 'sma2', 'sma3', 'sma4',
            'available_sma_inputs', 'available_sma_outputs',
            'serialnum', 'gnss_sync', 'utc_tai_offset',
            'external_pps_cable_delay', 'internal_pps_cable_delay',
            'holdover', 'mac_i2c', 'ts_window_adjust',
            'irig_b_mode', 'clock_source', 'available_clock_sources',
            'clock_status_drift', 'clock_status_offset',
            'tod_protocol', 'available_tod_protocols',
            'tod_baud_rate', 'available_tod_baud_rates',
            'tod_correction'
        ]
        
        # Functions to trace using ftrace
        self.trace_functions = [
            'ptp_ocp_gettimex',
            'ptp_ocp_settime',
            'ptp_ocp_adjtime',
            'ptp_ocp_adjfine',
            'ptp_ocp_enable',
            'ptp_ocp_ts_enable',
            'ptp_ocp_signal_enable',
            'ptp_ocp_sma_store',
            'ptp_ocp_sma_show',
            'ptp_ocp_read_eeprom',
            'ptp_ocp_probe',
            'ptp_ocp_remove',
            'ptp_ocp_watchdog',
            'ptp_ocp_tod_info',
            'ptp_ocp_get_irq',
            'ptp_ocp_register_ext',
            'ptp_ocp_register_mem',
            'ptp_ocp_register_i2c',
            'ptp_ocp_register_spi',
            'ptp_ocp_register_serial'
        ]
        
    def _find_ptp_ocp_device(self):
        """Find PTP OCP device in sysfs"""
        pci_devices = Path('/sys/bus/pci/devices')
        
        for device in pci_devices.iterdir():
            driver_link = device / 'driver'
            if driver_link.exists() and driver_link.is_symlink():
                driver_name = driver_link.resolve().name
                if driver_name == 'ptp_ocp':
                    self.logger.info(f"Found PTP OCP device: {device}")
                    return device
                    
        # Also check /sys/class/timecard
        timecard_path = Path('/sys/class/timecard')
        if timecard_path.exists():
            for device in timecard_path.iterdir():
                if device.is_symlink():
                    return device.resolve()
                    
        return None
        
    def read_sysfs_attr(self, attr_name):
        """Read a sysfs attribute value"""
        attr_path = self.device_path / attr_name
        
        if not attr_path.exists():
            return None
            
        try:
            with open(attr_path, 'r') as f:
                value = f.read().strip()
                return value
        except Exception as e:
            self.logger.error(f"Error reading {attr_name}: {e}")
            return None
            
    def monitor_sysfs(self):
        """Monitor sysfs attributes"""
        while self.running:
            timestamp = datetime.now().isoformat()
            data = {'timestamp': timestamp, 'type': 'sysfs', 'attributes': {}}
            
            for attr in self.sysfs_attrs:
                value = self.read_sysfs_attr(attr)
                if value is not None:
                    data['attributes'][attr] = value
                    
            self.data_queue.put(data)
            self.logger.debug(f"Sysfs data: {json.dumps(data, indent=2)}")
            
            time.sleep(1)  # Read every second
            
    def setup_ftrace(self):
        """Setup ftrace for monitoring driver functions"""
        try:
            # Check if running as root
            if os.geteuid() != 0:
                self.logger.warning("Not running as root. Function tracing will be limited.")
                return False
                
            # Enable function tracer
            subprocess.run(['echo', 'function', '>', '/sys/kernel/debug/tracing/current_tracer'], 
                         shell=True, check=True)
            
            # Clear existing filters
            subprocess.run(['echo', '>', '/sys/kernel/debug/tracing/set_ftrace_filter'], 
                         shell=True, check=True)
            
            # Add our functions to filter
            for func in self.trace_functions:
                cmd = f'echo {func} >> /sys/kernel/debug/tracing/set_ftrace_filter'
                subprocess.run(cmd, shell=True, check=True)
                
            # Enable tracing
            subprocess.run(['echo', '1', '>', '/sys/kernel/debug/tracing/tracing_on'], 
                         shell=True, check=True)
            
            self.logger.info("Function tracing enabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup ftrace: {e}")
            return False
            
    def cleanup_ftrace(self):
        """Cleanup ftrace settings"""
        try:
            if os.geteuid() == 0:
                subprocess.run(['echo', '0', '>', '/sys/kernel/debug/tracing/tracing_on'], 
                             shell=True, check=True)
                subprocess.run(['echo', '>', '/sys/kernel/debug/tracing/set_ftrace_filter'], 
                             shell=True, check=True)
                self.logger.info("Function tracing disabled")
        except Exception as e:
            self.logger.error(f"Failed to cleanup ftrace: {e}")
            
    def read_ftrace_buffer(self):
        """Read ftrace buffer"""
        try:
            with open('/sys/kernel/debug/tracing/trace_pipe', 'r') as f:
                while self.running:
                    line = f.readline()
                    if line:
                        # Parse ftrace output
                        if any(func in line for func in self.trace_functions):
                            timestamp = datetime.now().isoformat()
                            data = {
                                'timestamp': timestamp,
                                'type': 'ftrace',
                                'trace': line.strip()
                            }
                            self.data_queue.put(data)
                            self.logger.debug(f"Ftrace: {line.strip()}")
        except Exception as e:
            self.logger.error(f"Error reading ftrace: {e}")
            
    def save_data(self):
        """Save collected data to file"""
        output_file = f"ptp_ocp_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        data_list = []
        
        while not self.data_queue.empty():
            data_list.append(self.data_queue.get())
            
        with open(output_file, 'w') as f:
            json.dump(data_list, f, indent=2)
            
        self.logger.info(f"Data saved to {output_file}")
        
    def start(self):
        """Start monitoring"""
        self.running = True
        
        # Start sysfs monitoring thread
        sysfs_thread = threading.Thread(target=self.monitor_sysfs)
        sysfs_thread.start()
        
        # Start ftrace monitoring if available
        ftrace_thread = None
        if self.setup_ftrace():
            ftrace_thread = threading.Thread(target=self.read_ftrace_buffer)
            ftrace_thread.start()
            
        self.logger.info("Monitoring started. Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Stopping monitor...")
            self.running = False
            
            # Wait for threads to finish
            sysfs_thread.join()
            if ftrace_thread:
                ftrace_thread.join()
                
            # Cleanup
            self.cleanup_ftrace()
            self.save_data()
            
            self.logger.info("Monitor stopped.")

def main():
    parser = argparse.ArgumentParser(description='PTP OCP Driver Monitor')
    parser.add_argument('-d', '--device', help='Device path (e.g., /sys/bus/pci/devices/0000:01:00.0)')
    parser.add_argument('-l', '--log', help='Log file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    try:
        monitor = PTPOCPMonitor(device_path=args.device, log_file=args.log)
        monitor.start()
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()