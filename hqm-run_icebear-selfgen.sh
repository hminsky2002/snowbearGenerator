#!/bin/bash

# Go to the project directory (replace with your absolute path)
cd ~/src/snowbearGenerator

# Activate virtual environment
source venv/bin/activate
set -a source .hqmenv

set
# Run the script
python icebear-selfgen.py

# Deactivate virtual environment
deactivate
