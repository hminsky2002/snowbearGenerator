#!/bin/bash

# Go to the project directory (replace with your absolute path)
cd ~/src/snowbearGenerator

# Activate virtual environment
source venv/bin/activate
set -a source .hqmenv

# Run the script
python icebear.py

# Deactivate virtual environment
deactivate
