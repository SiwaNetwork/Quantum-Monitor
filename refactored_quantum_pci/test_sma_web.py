#!/usr/bin/env python3
"""
Test script to verify SMA configuration through the web API
"""

import requests
import json
import time

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def test_api_health():
    """Test API health endpoint"""
    print("Testing API health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check response: {response.json()}")
        return response.json().get('device_available', False)
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_sma_options():
    """Test getting available SMA options"""
    print("\nTesting SMA options endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/device/sma-options")
        data = response.json()
        print(f"Available SMA inputs: {data['available_inputs']}")
        print(f"Available SMA outputs: {data['available_outputs']}")
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_sma_config():
    """Test getting current SMA configuration"""
    print("\nTesting SMA configuration endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/device/sma-config")
        data = response.json()
        print(f"Current SMA inputs: {data['inputs']}")
        print(f"Current SMA outputs: {data['outputs']}")
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_set_sma_input(port, signal):
    """Test setting SMA input"""
    print(f"\nTesting set SMA{port} input to {signal}...")
    try:
        payload = {"port": port, "signal": signal}
        response = requests.post(f"{BASE_URL}/device/sma-input", json=payload)
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_set_sma_output(port, signal):
    """Test setting SMA output"""
    print(f"\nTesting set SMA{port} output to {signal}...")
    try:
        payload = {"port": port, "signal": signal}
        response = requests.post(f"{BASE_URL}/device/sma-output", json=payload)
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("=" * 60)
    print("SMA Web API Test Script")
    print("=" * 60)
    
    # Test health
    if not test_api_health():
        print("\n❌ API is not healthy or device not available")
        print("Make sure to start the web server with test device:")
        print("  ./start_web_test.sh")
        return
    
    # Get available options
    options = test_sma_options()
    if not options:
        print("\n❌ Failed to get SMA options")
        return
    
    # Get current config
    config = test_sma_config()
    if not config:
        print("\n❌ Failed to get SMA configuration")
        return
    
    # Test setting inputs
    print("\n" + "="*40)
    print("Testing SMA input configuration...")
    print("="*40)
    
    # Test valid input
    if test_set_sma_input(1, "PPS1"):
        print("✅ Successfully set SMA1 input to PPS1")
    else:
        print("❌ Failed to set SMA1 input")
    
    # Test another input
    if test_set_sma_input(2, "10Mhz"):
        print("✅ Successfully set SMA2 input to 10Mhz")
    else:
        print("❌ Failed to set SMA2 input")
    
    # Test setting outputs
    print("\n" + "="*40)
    print("Testing SMA output configuration...")
    print("="*40)
    
    # Test valid output
    if test_set_sma_output(3, "PHC"):
        print("✅ Successfully set SMA3 output to PHC")
    else:
        print("❌ Failed to set SMA3 output")
    
    # Test another output
    if test_set_sma_output(4, "GEN1"):
        print("✅ Successfully set SMA4 output to GEN1")
    else:
        print("❌ Failed to set SMA4 output")
    
    # Verify changes
    print("\n" + "="*40)
    print("Verifying configuration changes...")
    print("="*40)
    
    time.sleep(1)  # Give it a moment
    final_config = test_sma_config()
    
    if final_config:
        print("\n✅ Configuration test completed!")
        print(f"Final inputs: {final_config['inputs']}")
        print(f"Final outputs: {final_config['outputs']}")
    
    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)

if __name__ == "__main__":
    main()