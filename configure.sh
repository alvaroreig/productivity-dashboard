#!/bin/bash

# Set up env
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
python3 -m pip install -r requirements.txt
