# 🚀 Installation and Running

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

# 🛠 Manual Setup (Step-by-Step)

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

#### Windows:

```bash
python -m venv StimJimGUI
.\StimJimGUI\Scripts\activate
```

#### macOS/Linux:

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

# ⚙️ Common Problems

- **`pip` not recognized**: Make sure Python and pip are added to your PATH.
- **Linux/macOS permissions**: Try adding `sudo` if needed.
- **Alternative (conda environment)**: Supported if you prefer.

---

# 📋 Notes

- Tested on **Windows 10/11**, **macOS Monterey/Ventura**, and **Ubuntu 22.04**.
- Contributions welcome — feel free to fork and open a PR!
