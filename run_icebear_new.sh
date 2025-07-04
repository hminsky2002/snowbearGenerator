#!/bin/bash

# Go to the project directory (replace with your absolute path)
cd ~/src/snowbearGenerator

# Activate virtual environment
source venv/bin/activate
set -a source .env

# Run the script
python icebear-gen-image-assisted.py

# Deactivate virtual environment
deactivate
