# SMA Configuration Fix Report

## Overview
Fixed SMA configuration settings according to Linux kernel documentation for `/sys/class/timecard/ocpN/available_sma_*` interfaces. Updated both SMA and clock source selection to use dropdown menus with accurate signal descriptions.

## Changes Made

### 1. Updated SMA Panel (`refactored_quantum_pci/src/gui/components/sma_panel.py`)

#### Fixed Signal Definitions
Updated signal lists to match exact kernel documentation:

**Available SMA Inputs (Destinations/Sinks):**
- `None` - Signal input is disabled
- `10Mhz` - Signal is used as the 10MHz reference clock
- `PPS1` - Signal is sent to the PPS1 selector
- `PPS2` - Signal is sent to the PPS2 selector
- `TS1` - Signal is sent to timestamper 1
- `TS2` - Signal is sent to timestamper 2
- `TS3` - Signal is sent to timestamper 3
- `TS4` - Signal is sent to timestamper 4
- `IRIG` - Signal is sent to the IRIG-B module
- `DCF` - Signal is sent to the DCF module
- `FREQ1` - Signal is sent to frequency counter 1
- `FREQ2` - Signal is sent to frequency counter 2
- `FREQ3` - Signal is sent to frequency counter 3
- `FREQ4` - Signal is sent to frequency counter 4

**Available SMA Outputs (Sources):**
- `10Mhz` - Output is from the 10MHz reference clock
- `PHC` - Output PPS is from the PHC clock
- `MAC` - Output PPS is from the Miniature Atomic Clock
- `GNSS1` - Output PPS is from the first GNSS module
- `GNSS2` - Output PPS is from the second GNSS module
- `IRIG` - Output is from the PHC, in IRIG-B format
- `DCF` - Output is from the PHC, in DCF format
- `GEN1` - Output is from frequency generator 1
- `GEN2` - Output is from frequency generator 2
- `GEN3` - Output is from frequency generator 3
- `GEN4` - Output is from frequency generator 4
- `GND` - Output is GND
- `VCC` - Output is VCC

#### Enhanced Dropdown Functionality
- Added event handlers for dropdown selection changes
- Added real-time signal descriptions when users select options
- Improved user experience with instant feedback
- Updated preset configurations to include DCF option

#### Added Interactive Features
- `_on_input_changed()` - Handler for input signal selection
- `_on_output_changed()` - Handler for output signal selection
- `_update_signal_description()` - Shows detailed descriptions on selection
- Context-aware descriptions based on input vs output signal types

### 2. Updated Clock Panel (`refactored_quantum_pci/src/gui/components/clock_panel.py`)

#### Fixed Clock Source Definitions
Updated clock sources according to kernel documentation:

**Available Clock Sources:**
- `NONE` - No adjustments
- `PPS` - Adjustments come from the PPS1 selector (default)
- `TOD` - Adjustments from the GNSS/TOD module
- `IRIG` - Adjustments from external IRIG-B signal
- `DCF` - Adjustments from external DCF signal

#### Enhanced Functionality
- Added `_load_available_clock_sources()` to read from device
- Added dropdown change handler with descriptions
- Added `update_device()` method for proper device updates
- Improved signal descriptions with technical details

### 3. Updated Information Display
- Updated help text to reference Linux kernel documentation
- Added comprehensive signal descriptions
- Included clock source information
- Updated notes to reflect dropdown-based configuration

## Technical Improvements

### Device Integration
- Proper loading of available signals from sysfs files
- Fallback to standard signals when device unavailable
- Better error handling and logging

### User Interface
- Immediate feedback on signal selection
- Descriptive tooltips and popup information
- Improved layout and organization
- Better visual feedback for configuration changes

### Signal Validation
- Only allows selection of available signals
- Proper validation against device capabilities
- Clear error messages for invalid selections

## Files Modified

1. `refactored_quantum_pci/src/gui/components/sma_panel.py`
   - Updated signal definitions
   - Added dropdown event handlers
   - Enhanced user feedback
   - Updated information display

2. `refactored_quantum_pci/src/gui/components/clock_panel.py`
   - Updated clock source definitions
   - Added device integration
   - Enhanced dropdown functionality
   - Added signal descriptions

## Compatibility Notes

- All changes are backward compatible with existing device drivers
- Uses standard sysfs interfaces as documented in Linux kernel
- Fallback mechanisms ensure operation even when device files unavailable
- Maintains existing API for programmatic configuration

## Testing Recommendations

1. **Device Connection Testing**
   - Test with actual QUANTUM-PCI hardware
   - Verify sysfs file reading works correctly
   - Check fallback behavior without hardware

2. **UI Functionality Testing**
   - Test all dropdown selections
   - Verify popup descriptions appear
   - Check preset configurations work
   - Test refresh and reset functionality

3. **Signal Configuration Testing**
   - Test input signal routing
   - Test output signal generation
   - Verify clock source switching
   - Check configuration persistence

## Usage Instructions

### For SMA Configuration:
1. Open the SMA Port Configuration tab
2. Select desired input signals from dropdown menus for SMA1-4
3. Select desired output signals from dropdown menus for SMA1_OUT-4_OUT
4. Click "Apply Configuration" to save changes
5. Use presets for common configurations

### For Clock Source Configuration:
1. Open the Clock & Synchronization Settings tab
2. Select desired clock source from dropdown menu
3. Review description popup for selected source
4. Click "Apply Clock Source" to save changes

## Future Enhancements

- Add real-time status monitoring for signal lock
- Implement signal quality indicators
- Add advanced IRIG-B and DCF configuration options
- Include signal routing visualization
- Add automated signal testing capabilities