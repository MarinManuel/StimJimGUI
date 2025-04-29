#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "📦 Creating virtual environment 'StimJimGUI'..."
python3 -m venv StimJimGUI

echo "✅ Activating virtual environment..."
source StimJimGUI/bin/activate

echo "📦 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "⚡ To run the application, activate the environment and provide a serial port:"
echo ""
echo "source StimJimGUI/bin/activate"
echo "python3 StimJimGUI.py -p /dev/ttyUSB0    # <-- Replace with your actual serial port"
echo ""
