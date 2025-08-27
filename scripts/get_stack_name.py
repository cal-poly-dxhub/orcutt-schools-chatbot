#!/usr/bin/env python3
"""
Simple script to get the stack name from config
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config

if __name__ == "__main__":
    config = get_config()
    print(config.get_stack_name())