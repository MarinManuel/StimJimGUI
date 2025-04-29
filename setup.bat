@echo off
setlocal

echo 📦 Creating virtual environment 'StimJimGUI'...
python -m venv StimJimGUI

echo ✅ Activating virtual environment...
call StimJimGUI\Scripts\activate

echo 📦 Installing requirements...
pip install --upgrade pip
pip install -r requirements.txt

echo ✅ Setup complete!
echo.
echo ⚡ To run the application, activate the environment and provide a serial port:
echo.
echo StimJimGUI\Scripts\activate
echo python StimJimGUI.py -p COM3    REM <-- Replace COM3 with your actual serial port
echo.

endlocal
