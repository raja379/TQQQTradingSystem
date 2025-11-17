#!/usr/bin/env python3
"""
Test runner script for the trading system.
"""

import sys
import subprocess
import os


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔧 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner."""
    print("🧪 Trading System Test Suite")
    print("=" * 50)
    
    # Change to the script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Install test dependencies
    print("\n📦 Installing test dependencies...")
    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                       "Installing dependencies"):
        return 1
    
    # Run different test suites
    test_commands = [
        # Unit tests only
        ([sys.executable, "-m", "pytest", "tests/unit/", "-v", "--tb=short"], 
         "Running unit tests"),
        
        # Integration tests
        ([sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"], 
         "Running integration tests"),
        
        # All tests with coverage
        ([sys.executable, "-m", "pytest", "tests/", "--cov=src", "--cov-report=term-missing", 
          "--cov-report=html:htmlcov", "-v"], 
         "Running all tests with coverage"),
    ]
    
    failed_tests = []
    
    for cmd, description in test_commands:
        if not run_command(cmd, description):
            failed_tests.append(description)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    if not failed_tests:
        print("🎉 All tests passed!")
        print("\n📈 Coverage report generated in 'htmlcov/' directory")
        return 0
    else:
        print(f"❌ {len(failed_tests)} test suite(s) failed:")
        for test in failed_tests:
            print(f"  - {test}")
        return 1


if __name__ == "__main__":
    sys.exit(main())