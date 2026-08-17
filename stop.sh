#!/bin/bash
pkill -f "uvicorn main:app"
pkill -f "uvicorn gateway:app"
pkill -f "uvicorn app:app"
pkill -f "live_demo.py"
echo "APIShield AI services stopped. (Database still running.)"
