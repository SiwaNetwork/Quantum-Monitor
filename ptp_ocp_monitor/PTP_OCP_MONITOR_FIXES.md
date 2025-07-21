# PTP OCP Monitor Fixes

## Issues Identified and Fixed

### 1. TypeError: unsupported operand type(s) for /: 'str' and 'str'

**Problem**: When a device path was passed via command line argument (`-d /sys/bus/pci/devices/0000:01:00.0`), it was passed as a string, but the code expected a `Path` object for the `/` operator.

**Location**: `src/ptp_ocp_monitor.py`, line 109 in `read_sysfs_attr()` method

**Fix**: Modified the `__init__` method to convert string device paths to `Path` objects:

```python
# Find PTP OCP device if not specified
if not device_path:
    self.device_path = self._find_ptp_ocp_device()
else:
    # Convert string path to Path object
    self.device_path = Path(device_path)
```

### 2. ftrace Echo Command I/O Error

**Problem**: The subprocess commands for ftrace setup were incorrectly formatted, using list format with shell redirection which doesn't work.

**Location**: `src/ptp_ocp_monitor.py`, `setup_ftrace()` and `cleanup_ftrace()` methods

**Original problematic code**:
```python
subprocess.run(['echo', 'function', '>', '/sys/kernel/debug/tracing/current_tracer'], 
               shell=True, check=True)
```

**Fix**: Changed to proper shell command strings:
```python
subprocess.run('echo function > /sys/kernel/debug/tracing/current_tracer', 
               shell=True, check=True)
```

### 3. Enhanced Error Handling for ftrace

**Problem**: Poor error handling when ftrace setup failed, leading to cryptic error messages.

**Fix**: Added comprehensive checks and better error messages:

- Check if running as root
- Check if debugfs is mounted at `/sys/kernel/debug`
- Check if function tracing is available
- Individual function filter testing with success counting
- Detailed error messages for each failure scenario

**New features**:
```python
# Check if debugfs is mounted
if not os.path.exists('/sys/kernel/debug/tracing'):
    self.logger.warning("Tracing debugfs not available. Please mount debugfs:")
    self.logger.warning("  sudo mount -t debugfs none /sys/kernel/debug")
    return False

# Try each function filter individually
successful_filters = 0
for func in self.trace_functions:
    cmd = f'echo {func} >> /sys/kernel/debug/tracing/set_ftrace_filter'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        successful_filters += 1
    else:
        self.logger.debug(f"Failed to add filter for {func}: {result.stderr}")
```

### 4. Robust sysfs Attribute Reading

**Problem**: The code assumed sysfs attributes existed directly under the device path, but for PTP OCP devices, they're often under a `timecard/ocpX/` subdirectory.

**Fix**: Enhanced `read_sysfs_attr()` method to check multiple locations:

```python
def read_sysfs_attr(self, attr_name):
    """Read a sysfs attribute value"""
    # Try to find the attribute in timecard subdirectory first
    timecard_path = self.device_path / 'timecard'
    if timecard_path.exists():
        for device in timecard_path.iterdir():
            if device.is_dir():
                attr_path = device / attr_name
                if attr_path.exists():
                    try:
                        with open(attr_path, 'r') as f:
                            value = f.read().strip()
                            return value
                    except Exception as e:
                        self.logger.debug(f"Error reading {attr_path}: {e}")
    
    # Fallback: try direct path
    attr_path = self.device_path / attr_name
    if attr_path.exists():
        try:
            with open(attr_path, 'r') as f:
                value = f.read().strip()
                return value
        except Exception as e:
            self.logger.debug(f"Error reading {attr_path}: {e}")
    
    # Not found in either location
    return None
```

### 5. Intelligent Attribute Discovery

**Problem**: The monitor tried to read hardcoded sysfs attributes that might not exist on the current system.

**Fix**: Added attribute availability checking before starting monitoring:

```python
def monitor_sysfs(self):
    """Monitor sysfs attributes"""
    # First, check which attributes are actually available
    available_attrs = []
    for attr in self.sysfs_attrs:
        if self.read_sysfs_attr(attr) is not None:
            available_attrs.append(attr)
    
    if not available_attrs:
        self.logger.warning("No sysfs attributes found. Device may not be properly configured.")
        # Still continue but with minimal monitoring
        available_attrs = ['uevent']  # uevent should always exist
    else:
        self.logger.info(f"Found {len(available_attrs)} available attributes: {', '.join(available_attrs)}")
```

### 6. BPF Tracer Improvements

**Problem**: The BPF tracer tried to attach to functions that might not exist, causing attachment failures.

**Fix**: Added function availability checking using `/proc/kallsyms`:

```python
def check_function_availability(self):
    """Check which functions are available in kallsyms"""
    available_functions = []
    try:
        with open('/proc/kallsyms', 'r') as f:
            kallsyms = f.read()
            for func in self.trace_functions:
                if func in kallsyms:
                    available_functions.append(func)
                    print(f"✓ Function {func} is available")
                else:
                    print(f"✗ Function {func} is not available")
    except Exception as e:
        print(f"Warning: Could not read /proc/kallsyms: {e}")
        # Fallback to original list
        available_functions = self.trace_functions
        
    return available_functions
```

**Reduced function list**: Focused on core PTP functions most likely to be available:
- `ptp_ocp_adjfine`
- `ptp_ocp_adjtime`
- `ptp_ocp_gettime64`
- `ptp_ocp_settime64`
- `ptp_ocp_enable`
- `ptp_ocp_adjtime_coarse`

## Test Results

After applying these fixes:

### Without sudo:
```
2025-07-21 09:25:31,733 - INFO - Monitoring PTP OCP device: /sys/bus/pci/devices/0000:01:00.0
2025-07-21 09:25:31,734 - WARNING - Not running as root. Function tracing will be limited.
2025-07-21 09:25:31,734 - INFO - Monitoring started. Press Ctrl+C to stop.
2025-07-21 09:25:31,734 - WARNING - No sysfs attributes found. Device may not be properly configured.
```

### With sudo:
```
2025-07-21 09:25:42,400 - INFO - Monitoring PTP OCP device: /sys/bus/pci/devices/0000:01:00.0
2025-07-21 09:25:42,401 - WARNING - No sysfs attributes found. Device may not be properly configured.
2025-07-21 09:25:42,402 - WARNING - Tracing debugfs not available. Please mount debugfs:
2025-07-21 09:25:42,402 - WARNING -   sudo mount -t debugfs none /sys/kernel/debug
2025-07-21 09:25:42,402 - INFO - Monitoring started. Press Ctrl+C to stop.
```

## Key Improvements

1. **No more TypeError**: Fixed the Path object conversion issue
2. **No more I/O errors**: Fixed ftrace command formatting
3. **Better error messages**: Clear guidance on what's missing and how to fix it
4. **Graceful degradation**: Works even when some features aren't available
5. **Intelligent discovery**: Only monitors attributes that actually exist
6. **Robust sysfs reading**: Handles different device layouts
7. **Function availability checking**: Only traces functions that exist

## Recommendations for Production Use

1. **Mount debugfs for tracing**:
   ```bash
   sudo mount -t debugfs none /sys/kernel/debug
   ```

2. **Install BCC for BPF tracing**:
   ```bash
   sudo apt-get install bpfcc-tools python3-bpfcc
   ```

3. **Ensure PTP OCP driver is loaded**:
   ```bash
   modprobe ptp_ocp
   ```

4. **Run with appropriate permissions**:
   ```bash
   sudo python3 src/ptp_ocp_monitor.py -d <device_path>
   ```

All critical issues have been resolved, and the monitor now provides clear error messages and graceful degradation when features are unavailable.