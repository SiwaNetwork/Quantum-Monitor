#!/usr/bin/env python3
"""
PTP OCP Sysfs Reader
Reads and displays sysfs attributes from PTP OCP devices
Based on the article: https://support.timebeat.app/hc/en-gb/articles/13653309251090-Accessing-the-device-through-the-sys-class-directory
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

class PTPOCPSysfsReader:
    """Read and analyze PTP OCP device attributes from sysfs"""
    
    def __init__(self):
        self.devices = []
        self.ptp_devices = []
        self.timecard_devices = []
        
    def find_ptp_ocp_devices(self):
        """Find all PTP OCP devices in the system"""
        # Check PCI devices
        pci_path = Path('/sys/bus/pci/devices')
        if pci_path.exists():
            for device in pci_path.iterdir():
                driver_link = device / 'driver'
                if driver_link.exists() and driver_link.is_symlink():
                    driver_name = driver_link.resolve().name
                    if driver_name == 'ptp_ocp':
                        self.devices.append({
                            'type': 'pci',
                            'path': device,
                            'name': device.name
                        })
                        
        # Check /sys/class/ptp for PTP devices
        ptp_path = Path('/sys/class/ptp')
        if ptp_path.exists():
            for device in ptp_path.iterdir():
                if device.is_symlink():
                    real_path = device.resolve()
                    # Check if this is a PTP OCP device
                    if 'ptp_ocp' in str(real_path):
                        self.ptp_devices.append({
                            'name': device.name,
                            'path': real_path,
                            'symlink': device
                        })
                        
        # Check /sys/class/timecard
        timecard_path = Path('/sys/class/timecard')
        if timecard_path.exists():
            for device in timecard_path.iterdir():
                if device.is_symlink():
                    real_path = device.resolve()
                    self.timecard_devices.append({
                        'name': device.name,
                        'path': real_path,
                        'symlink': device
                    })
                    
        return len(self.devices) + len(self.ptp_devices) + len(self.timecard_devices) > 0
        
    def read_attribute(self, path, attr_name):
        """Read a single attribute from sysfs"""
        attr_path = path / attr_name
        
        if not attr_path.exists():
            return None
            
        try:
            with open(attr_path, 'r') as f:
                value = f.read().strip()
                return value
        except Exception as e:
            return f"Error: {e}"
            
    def read_device_info(self, device_path):
        """Read all available attributes from a device"""
        info = {
            'path': str(device_path),
            'timestamp': datetime.now().isoformat(),
            'attributes': {}
        }
        
        # Common PCI attributes
        pci_attrs = [
            'vendor', 'device', 'subsystem_vendor', 'subsystem_device',
            'class', 'revision', 'irq', 'resource', 'config',
            'enable', 'local_cpus', 'numa_node'
        ]
        
        # PTP OCP specific attributes
        ptp_ocp_attrs = [
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
        
        # PTP clock attributes
        ptp_attrs = [
            'clock_name', 'dev', 'max_adj', 'n_alarm', 'n_ext_ts',
            'n_per_out', 'n_pins', 'pps_available'
        ]
        
        # Try to read all attributes
        all_attrs = pci_attrs + ptp_ocp_attrs + ptp_attrs
        
        for attr in all_attrs:
            value = self.read_attribute(device_path, attr)
            if value is not None:
                info['attributes'][attr] = value
                
        # Also list all files in the directory
        try:
            files = [f.name for f in device_path.iterdir() if f.is_file()]
            info['available_files'] = files
        except:
            pass
            
        return info
        
    def read_ptp_clock_info(self, ptp_path):
        """Read PTP clock specific information"""
        info = {
            'path': str(ptp_path),
            'timestamp': datetime.now().isoformat(),
            'attributes': {}
        }
        
        # PTP clock attributes
        attrs = [
            'clock_name', 'dev', 'max_adj', 'n_alarm', 'n_ext_ts',
            'n_per_out', 'n_pins', 'pps_available'
        ]
        
        for attr in attrs:
            value = self.read_attribute(ptp_path, attr)
            if value is not None:
                info['attributes'][attr] = value
                
        # Check for pins
        pins_dir = ptp_path / 'pins'
        if pins_dir.exists():
            info['pins'] = []
            for pin in pins_dir.iterdir():
                pin_info = {
                    'name': pin.name,
                    'attributes': {}
                }
                for attr in ['function', 'state']:
                    value = self.read_attribute(pin, attr)
                    if value is not None:
                        pin_info['attributes'][attr] = value
                info['pins'].append(pin_info)
                
        return info
        
    def display_results(self):
        """Display all found devices and their attributes"""
        print("\n=== PTP OCP Devices Found ===\n")
        
        # Display PCI devices
        if self.devices:
            print("PCI Devices:")
            for device in self.devices:
                print(f"  - {device['name']} at {device['path']}")
                info = self.read_device_info(device['path'])
                
                # Display key attributes
                attrs = info.get('attributes', {})
                if 'vendor' in attrs and 'device' in attrs:
                    print(f"    Vendor: 0x{attrs['vendor']} Device: 0x{attrs['device']}")
                if 'serialnum' in attrs:
                    print(f"    Serial Number: {attrs['serialnum']}")
                if 'clock_source' in attrs:
                    print(f"    Clock Source: {attrs['clock_source']}")
                if 'gnss_sync' in attrs:
                    print(f"    GNSS Sync: {attrs['gnss_sync']}")
                    
                # Show SMA configuration
                for i in range(1, 5):
                    sma_key = f'sma{i}'
                    if sma_key in attrs:
                        print(f"    SMA{i}: {attrs[sma_key]}")
                        
                print()
                
        # Display PTP devices
        if self.ptp_devices:
            print("\nPTP Devices:")
            for device in self.ptp_devices:
                print(f"  - {device['name']} -> {device['path']}")
                info = self.read_ptp_clock_info(device['symlink'])
                
                attrs = info.get('attributes', {})
                if 'clock_name' in attrs:
                    print(f"    Clock Name: {attrs['clock_name']}")
                if 'pps_available' in attrs:
                    print(f"    PPS Available: {attrs['pps_available']}")
                    
                if 'pins' in info:
                    print(f"    Pins: {len(info['pins'])}")
                    for pin in info['pins']:
                        print(f"      - {pin['name']}: {pin['attributes'].get('function', 'unknown')}")
                        
                print()
                
        # Display timecard devices
        if self.timecard_devices:
            print("\nTimecard Devices:")
            for device in self.timecard_devices:
                print(f"  - {device['name']} -> {device['path']}")
                info = self.read_device_info(device['path'])
                
                # Display available files
                if 'available_files' in info:
                    print(f"    Available attributes: {', '.join(sorted(info['available_files']))}")
                    
                print()
                
    def export_json(self, filename):
        """Export all device information to JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'pci_devices': [],
            'ptp_devices': [],
            'timecard_devices': []
        }
        
        for device in self.devices:
            info = self.read_device_info(device['path'])
            data['pci_devices'].append(info)
            
        for device in self.ptp_devices:
            info = self.read_ptp_clock_info(device['symlink'])
            data['ptp_devices'].append(info)
            
        for device in self.timecard_devices:
            info = self.read_device_info(device['path'])
            data['timecard_devices'].append(info)
            
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"Data exported to {filename}")
        
    def monitor_attribute(self, device_path, attr_name, interval=1):
        """Monitor a specific attribute for changes"""
        import time
        
        print(f"\nMonitoring {attr_name} on {device_path}")
        print("Press Ctrl+C to stop\n")
        
        last_value = None
        try:
            while True:
                value = self.read_attribute(Path(device_path), attr_name)
                if value != last_value:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    print(f"[{timestamp}] {attr_name}: {value}")
                    last_value = value
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")

def main():
    parser = argparse.ArgumentParser(description='PTP OCP Sysfs Reader')
    parser.add_argument('-e', '--export', help='Export data to JSON file')
    parser.add_argument('-m', '--monitor', nargs=2, metavar=('DEVICE', 'ATTR'),
                       help='Monitor a specific attribute (device_path attribute_name)')
    parser.add_argument('-i', '--interval', type=float, default=1.0,
                       help='Monitoring interval in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    reader = PTPOCPSysfsReader()
    
    if not reader.find_ptp_ocp_devices():
        print("No PTP OCP devices found in the system.")
        print("\nPlease check:")
        print("  1. The ptp_ocp driver is loaded (lsmod | grep ptp_ocp)")
        print("  2. A PTP OCP device is installed")
        print("  3. You have sufficient permissions to read sysfs")
        sys.exit(1)
        
    if args.monitor:
        reader.monitor_attribute(args.monitor[0], args.monitor[1], args.interval)
    else:
        reader.display_results()
        
        if args.export:
            reader.export_json(args.export)

if __name__ == '__main__':
    main()