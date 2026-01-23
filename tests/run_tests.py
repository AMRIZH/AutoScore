#!/usr/bin/env python
"""
Script untuk menjalankan semua unit tests.

Cara penggunaan:
    python run_tests.py           # Jalankan semua tests
    python run_tests.py -v        # Verbose mode
    python run_tests.py -k "test_login"  # Jalankan tests tertentu
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pytest


def main():
    """Run all tests."""
    # Get the unittest directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Default arguments
    args = [
        test_dir,
        '-v',  # Verbose
        '--tb=short',  # Short traceback
        '-x',  # Stop on first failure
    ]
    
    # Add any command line arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    # Run pytest
    exit_code = pytest.main(args)
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
