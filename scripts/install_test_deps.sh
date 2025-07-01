#!/usr/bin/env bash
set -e

# Install required Python packages for running tests
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Ensure pytest itself is installed
pip install pytest
