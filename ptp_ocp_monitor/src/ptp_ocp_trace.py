#!/usr/bin/env python3
"""
PTP OCP Function Tracer using eBPF
Traces function calls in the ptp_ocp driver
"""

import os
import sys
import argparse
import signal
from datetime import datetime

# Check if BCC is available
try:
    from bcc import BPF
except ImportError:
    print("Error: BCC (BPF Compiler Collection) is not installed.")
    print("Please install it using:")
    print("  Ubuntu/Debian: sudo apt-get install bpfcc-tools python3-bpfcc")
    print("  RHEL/CentOS: sudo yum install bcc-tools python-bcc")
    sys.exit(1)

# eBPF program
BPF_PROGRAM = """
#include <linux/ptrace.h>
#include <linux/sched.h>

struct data_t {
    u64 timestamp;
    u32 pid;
    u32 tid;
    char comm[16];
    char func_name[32];
    u64 duration_ns;
};

BPF_HASH(start_times, u64);
BPF_PERF_OUTPUT(events);

// Function entry probe
int trace_func_entry(struct pt_regs *ctx) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u64 ts = bpf_ktime_get_ns();
    
    start_times.update(&pid_tgid, &ts);
    return 0;
}

// Function return probe
int trace_func_return(struct pt_regs *ctx) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u64 *start_ts = start_times.lookup(&pid_tgid);
    
    if (start_ts == 0) {
        return 0;  // Entry not found
    }
    
    u64 duration = bpf_ktime_get_ns() - *start_ts;
    start_times.delete(&pid_tgid);
    
    struct data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    data.pid = pid_tgid >> 32;
    data.tid = pid_tgid;
    data.duration_ns = duration;
    
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    
    // Copy function name
    const char *func_name = "FUNC_NAME_PLACEHOLDER";
    bpf_probe_read_kernel_str(&data.func_name, sizeof(data.func_name), func_name);
    
    events.perf_submit(ctx, &data, sizeof(data));
    
    return 0;
}
"""

class PTPOCPTracer:
    """Trace PTP OCP driver functions using eBPF"""
    
    def __init__(self, duration_filter=0):
        self.duration_filter = duration_filter * 1000  # Convert to nanoseconds
        self.running = True
        self.bpf_programs = [{}]
        
        # Core functions that are most likely to be available
        self.trace_functions = [
            'ptp_ocp_adjfine',
            'ptp_ocp_adjtime', 
            'ptp_ocp_gettime64',
            'ptp_ocp_settime64',
            'ptp_ocp_enable',
            'ptp_ocp_adjtime_coarse'
        ]
        
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

    def create_bpf_program(self, func_name):
        """Create BPF program for a specific function"""
        # Replace placeholder with actual function name
        program = BPF_PROGRAM.replace("FUNC_NAME_PLACEHOLDER", func_name)
        
        try:
            b = BPF(text=program)
            
            # Attach kprobe and kretprobe
            b.attach_kprobe(event=func_name, fn_name="trace_func_entry")
            b.attach_kretprobe(event=func_name, fn_name="trace_func_return")
            
            return b
        except Exception as e:
            print(f"Warning: Failed to attach to {func_name}: {e}")
            return None
            
    def print_event(self, cpu, data, size):
        """Print traced event"""
        event = self.bpf_programs[0]["events"].event(data)
        
        # Apply duration filter
        if self.duration_filter > 0 and event.duration_ns < self.duration_filter:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        duration_us = event.duration_ns / 1000.0
        
        print(f"[{timestamp}] {event.comm.decode('utf-8', 'replace'):16} "
              f"PID:{event.pid:6} TID:{event.tid:6} "
              f"{event.func_name.decode('utf-8', 'replace'):32} "
              f"duration: {duration_us:8.2f} μs")
              
    def start_tracing(self):
        """Start tracing PTP OCP functions"""
        print("Starting PTP OCP function tracing...")
        
        # Check which functions are available
        available_functions = self.check_function_availability()
        
        if not available_functions:
            print("Error: No PTP OCP functions are available for tracing.")
            print("This might be because:")
            print("  1. The ptp_ocp driver is not loaded")
            print("  2. The functions are inlined by the compiler")
            print("  3. You don't have sufficient permissions")
            return
            
        print(f"Found {len(available_functions)} available functions")
        print("Press Ctrl+C to stop\n")
        
        # Create BPF programs for available functions only
        active_bpf = None
        successful_attachments = 0
        
        for func in available_functions:
            b = self.create_bpf_program(func)
            if b:
                if not active_bpf:
                    active_bpf = b
                    # Set up perf buffer callback
                    b["events"].open_perf_buffer(self.print_event)
                    self.bpf_programs[0] = b
                successful_attachments += 1
                    
        if not active_bpf or successful_attachments == 0:
            print("Error: No functions could be traced successfully.")
            print("The functions might be inlined or not currently loaded.")
            return
            
        print(f"Successfully attached to {successful_attachments} functions...")
        print("Function                         Duration (μs)")
        print("-" * 60)
        
        # Main loop
        while self.running:
            try:
                active_bpf.perf_buffer_poll()
            except KeyboardInterrupt:
                self.running = False
                
        print("\nTracing stopped.")
        
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C"""
        self.running = False

def check_requirements():
    """Check if all requirements are met"""
    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This script must be run as root for eBPF tracing.")
        sys.exit(1)
        
    # Check if kernel supports BPF
    if not os.path.exists("/sys/kernel/debug/tracing"):
        print("Error: Kernel tracing is not available.")
        print("Make sure debugfs is mounted and CONFIG_FTRACE is enabled.")
        sys.exit(1)
        
    # Check if ptp_ocp module is loaded
    try:
        with open('/proc/modules', 'r') as f:
            modules = f.read()
            if 'ptp_ocp' not in modules:
                print("Warning: ptp_ocp module is not loaded.")
                print("Load it with: sudo modprobe ptp_ocp")
    except:
        pass

def main():
    parser = argparse.ArgumentParser(description='PTP OCP Function Tracer using eBPF')
    parser.add_argument('-d', '--duration', type=int, default=0,
                       help='Only show functions that take longer than N microseconds')
    parser.add_argument('-f', '--function', action='append',
                       help='Specific function to trace (can be used multiple times)')
    
    args = parser.parse_args()
    
    # Check requirements
    check_requirements()
    
    # Create tracer
    tracer = PTPOCPTracer(duration_filter=args.duration)  # Convert to nanoseconds
    
    # Override function list if specific functions are requested
    if args.function:
        tracer.trace_functions = args.function
        
    # Set up signal handler
    signal.signal(signal.SIGINT, tracer.signal_handler)
    
    # Start tracing
    try:
        tracer.start_tracing()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()