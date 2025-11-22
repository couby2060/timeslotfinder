#!/usr/bin/env python3
"""
Convenience entry point for running timeslotfinder directly.

Usage: python timeslotfinder.py [command] [options]
"""

from src.cli.app import app

if __name__ == "__main__":
    app()

