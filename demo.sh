#!/bin/bash
cd "$(dirname "$0")"
echo "Starting live attack simulation... (Ctrl+C to stop). Watch the dashboard!"
traffic-generator/venv/bin/python traffic-generator/live_demo.py
