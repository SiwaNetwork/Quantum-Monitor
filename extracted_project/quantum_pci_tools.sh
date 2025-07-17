#!/bin/bash

# QUANTUM-PCI Configuration and Monitoring Tools
# Installation and usage script

echo "QUANTUM-PCI Configuration and Monitoring Tools"
echo "=============================================="
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Warning: Running as root. Some GUI applications may not work properly."
   echo "Consider running as a regular user with sudo privileges."
   echo
fi

# Function to check dependencies
check_dependencies() {
    echo "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 is required but not installed."
        exit 1
    fi
    
    # Check required Python modules
    python3 -c "import tkinter" 2>/dev/null || {
        echo "Error: tkinter module is required. Install with: sudo apt-get install python3-tk"
        exit 1
    }
    
    python3 -c "import flask" 2>/dev/null || {
        echo "Warning: Flask is not installed. Web monitor will not work."
        echo "Install with: pip3 install flask flask-cors"
    }
    
    echo "Dependencies check completed."
    echo
}

# Function to check device
check_device() {
    echo "Checking for QUANTUM-PCI device..."
    
    if [ -d "/sys/class/timecard" ]; then
        device_count=$(ls -1 /sys/class/timecard/ 2>/dev/null | wc -l)
        if [ $device_count -gt 0 ]; then
            echo "Found QUANTUM-PCI device(s):"
            ls -la /sys/class/timecard/
            echo
            return 0
        fi
    fi
    
    echo "No QUANTUM-PCI device found in /sys/class/timecard/"
    echo "Checking PCI devices..."
    
    if lspci | grep -i quantum &> /dev/null; then
        echo "QUANTUM device found in PCI, but driver may not be loaded."
    elif lspci | grep 0x0400 &> /dev/null; then
        echo "Device with ID 0x0400 found in PCI, but driver may not be loaded."
    else
        echo "No QUANTUM-PCI device found."
    fi
    
    echo
    echo "If you have a QUANTUM-PCI device, ensure:"
    echo "1. The device is properly installed"
    echo "2. The ptp_ocp driver is loaded (modprobe ptp_ocp)"
    echo "3. You have sufficient permissions"
    echo
    return 1
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  gui           Launch GUI configurator"
    echo "  status        Show device status"
    echo "  monitor       Start real-time monitoring"
    echo "  web           Start web-based monitor"
    echo "  install       Install dependencies"
    echo "  check         Check system and device"
    echo "  help          Show this help"
    echo
    echo "Examples:"
    echo "  $0 gui                    # Launch GUI configurator"
    echo "  $0 status --format json   # Show status in JSON format"
    echo "  $0 monitor --interval 2   # Monitor with 2-second interval"
    echo "  $0 web                    # Start web interface on port 5000"
    echo
}

# Function to install dependencies
install_dependencies() {
    echo "Installing dependencies..."
    
    # Update package list
    sudo apt-get update
    
    # Install Python and tkinter
    sudo apt-get install -y python3 python3-pip python3-tk
    
    # Install Python packages
    pip3 install flask flask-cors
    
    echo "Dependencies installed."
}

# Function to launch GUI
launch_gui() {
    echo "Launching GUI configurator..."
    if [ -f "quantum_pci_configurator.py" ]; then
        python3 quantum_pci_configurator.py
    else
        echo "Error: quantum_pci_configurator.py not found"
        exit 1
    fi
}

# Function to show status
show_status() {
    echo "Reading device status..."
    if [ -f "quantum_pci_status_reader.py" ]; then
        python3 quantum_pci_status_reader.py "$@"
    else
        echo "Error: quantum_pci_status_reader.py not found"
        exit 1
    fi
}

# Function to start monitoring
start_monitoring() {
    echo "Starting real-time monitoring..."
    if [ -f "quantum_pci_status_reader.py" ]; then
        python3 quantum_pci_status_reader.py --monitor "$@"
    else
        echo "Error: quantum_pci_status_reader.py not found"
        exit 1
    fi
}

# Function to start web monitor
start_web_monitor() {
    echo "Starting web-based monitor..."
    if [ -f "quantum_pci_web_monitor.py" ]; then
        echo "Web interface will be available at: http://localhost:5000"
        python3 quantum_pci_web_monitor.py
    else
        echo "Error: quantum_pci_web_monitor.py not found"
        exit 1
    fi
}

# Main script logic
case "${1:-help}" in
    gui)
        check_dependencies
        launch_gui
        ;;
    status)
        check_dependencies
        shift
        show_status "$@"
        ;;
    monitor)
        check_dependencies
        shift
        start_monitoring "$@"
        ;;
    web)
        check_dependencies
        start_web_monitor
        ;;
    install)
        install_dependencies
        ;;
    check)
        check_dependencies
        check_device
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo "Unknown option: $1"
        echo
        show_usage
        exit 1
        ;;
esac

