# StimJimGUI
GUI for the [StimJim](https://bitbucket.org/natecermak/stimjim) Open Source electrophysiology stimulator

The GUI offers two modes:

## Simple Mode
![Screenshot 2024-02-06 230855](https://github.com/MarinManuel/StimJimGUI/assets/65401298/632121ee-0278-4650-b66f-8415ec79f997)

In "Simple Mode", a rising pulse on TRIG0 triggers the output of a train of stimuli on OUT0, while a rising pulse on 
TRIG1 triggers OUT1. You can adjust the number and frequency of the output, as well as its intensity and duration of the 
pulses.

### Bipolar mode
Checking the "bipolar checkbox" creates a bipolar pulse such as each stimulus is immediately followed by a 
stimulus of opposite amplitude. Both pulses have equal duration and their combined duration is equal to the pulse
duration shown in the corresponding box.

### Threshold
Amplitudes can be expressed in V or A (depending on the chosen output mode), or can be expressed relative to a "threshold"
value. When the threshold amplitude as been measured, click on the `threshold` button, the value of the threshold amplitude
now appear next to the button, and the pulse amplitude is expressed as a multiple of the threshold value (e.g. If the 
threshold were 200mV, 1.5 xT would correspond to a pulse 300 mV in amplitude)

## "Full Mode"
![Screenshot 2024-02-06 233854](https://github.com/MarinManuel/StimJimGUI/assets/65401298/c4542f50-e629-4f3e-b9e8-0a9db881e065)


In "Full Mode", all the settings can be freely adjusted as described in the [StimJim Documentation](https://bitbucket.org/natecermak/stimjim/src/master/)

![Screenshot 2024-02-06 230539](https://github.com/MarinManuel/StimJimGUI/assets/65401298/812a0715-ebcb-4424-ac76-b02525fad89f)

# Usage
## 🚀 Installation and Running

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)]()
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)]()

---

<details>
<summary><strong>📥 Quick Setup (One Command)</strong></summary>

### Windows (Command Prompt or PowerShell)

```bash
setup.bat
```

### macOS / Linux (Terminal)

```bash
bash setup.sh
```

> 🛠️ These scripts:
> - Create and activate a virtual environment called **StimJimGUI**
> - Install all dependencies from `requirements.txt`
> - Optionally launch the application after installation

</details>

---

## 🛠 Manual Setup (Step-by-Step)

<details>
<summary><strong>1. Install Python</strong></summary>

- **Windows/macOS**: Download from [python.org](https://www.python.org/downloads/).
- **Linux**: Install via:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

Verify installation:

```bash
python --version
```
or
```bash
python3 --version
```

</details>

<details>
<summary><strong>2. Clone the Repository</strong></summary>

```bash
git clone https://github.com/MarinManuel/StimJimGUI.git
cd StimJimGUI
```

</details>

<details>
<summary><strong>3. Create and Activate the Virtual Environment</strong></summary>

### Windows:

```bash
python -m venv StimJimGUI
.\StimJimGUI\Scripts\activate
```

### macOS/Linux:

```bash
python3 -m venv StimJimGUI
source StimJimGUI/bin/activate
```

</details>

<details>
<summary><strong>4. Install Dependencies</strong></summary>

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

</details>

<details>
<summary><strong>5. Run the Application</strong></summary>

```bash
python main.py
```

</details>

---

## ⚙️ Common Problems

- **`pip` not recognized**: Make sure Python and pip are added to your PATH.
- **Linux/macOS permissions**: Try adding `sudo` if needed.
- **Alternative (conda environment)**: Supported if you prefer.

---

## Running
2. Activate the environment
3. Launch the GUI: `python StimJimGUI.py`
The software attempts to detect the serial port automatically, but you can also specify the port to use using the 
`--port` command line argument

Other command line arguments:
```txt
usage: StimJimGUI [-h] [-p PORT] [-l LOG] [-v]

This software provides a graphical user interface for controlling a StimJim, an open source electrophysiology stimulator for physiology and behavior

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  the serial port used to communicate with the StimJim. If not provided, then the software will try to find the port automatically, and/or offer a choice of possible ports
  -l LOG, --log LOG     save the log file to file FILENAME
  -v, --verbose         increase verbosity of output (can be repeated to increase verbosity further)
```

# Acknowledgments
This work was supported in part by NIH-NINDS R01NS132487.

`scientific_spinbox.py` is from [pyqt-labutils](https://github.com/OE-FET/pyqt-labutils/tree/master)

Icons by [Icons8](https://icons8.com)
 - [Bolt](https://icons8.com/icon/QIoqXePo167Z/lightning-bolt)
 - [Plus](https://icons8.com/icon/3XO4Ci6_-HuH/plus)
 - [Minus](https://icons8.com/icon/o83WC4-i7INr/minus)
 - [Cancel](https://icons8.com/icon/MmVr5QVBaT-5/cancel)
 - [Outgoing Data](https://icons8.com/icon/UHovfkMCzm95/outgoing-data)
 - [Open](https://icons8.com/icon/cc92oA88hLvF/external-link)
 - [Open Document](https://icons8.com/icon/EpclQMdUhtqh/open-document)
 - [Save](https://icons8.com/icon/R6CZNG0w5CQP/save)
 - [Download](https://icons8.com/icon/eyOW-vh0lq9E/downloading-updates)
 - [Logout](https://icons8.com/icon/_Ee4K9lYArVo/logout)
