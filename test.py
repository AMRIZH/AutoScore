#!/usr/bin/env python
"""
AutoScoring Test Runner.

This script runs the pytest suite for the AutoScoring application.
It automatically sets the FLASK_TESTING environment variable.

Usage:
    python test.py           # Run all tests with verbose output
    python test.py -k name   # Run tests matching 'name'
    python test.py -q        # Run in quiet mode
"""

import os
import sys

# Set testing environment
os.environ['FLASK_TESTING'] = '1'

# Run pytest
if __name__ == '__main__':
    try:
        import pytest  # type: ignore
    except ImportError:
        print("Error: pytest is not installed. Please run 'pip install -r requirements.txt'")
        sys.exit(1)
    
    # Default arguments: run all tests in 'tests/' directory, verbose, short traceback
    args = ['tests/', '-v', '--tb=short']
    
    # Add any command line arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    sys.exit(pytest.main(args))
