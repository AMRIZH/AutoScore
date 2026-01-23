#!/usr/bin/env python
"""
Simple test runner for AutoScoring.

Usage:
    python test.py           # Run all tests
    python test.py -v        # Verbose mode
    python test.py -k name   # Run tests matching 'name'
"""

import os
import sys

# Set testing environment
os.environ['FLASK_TESTING'] = '1'

# Run pytest
if __name__ == '__main__':
    import pytest
    
    args = ['tests/', '-v', '--tb=short']
    
    # Add any command line arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    sys.exit(pytest.main(args))
