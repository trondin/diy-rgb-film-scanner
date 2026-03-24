```
# RGB2W Processor

GUI tool for processing multi-channel RAW files (RGB + Dark + White) from specialized photography.

## Features
- Loads `IMG_XXXX_r.dng`, `IMG_XXXX_g.dng`, `IMG_XXXX_b.dng`, `IMG_XXXX_d.dng`, `IMG_XXXX_w.dng`
- Automatic dark frame subtraction
- Bad pixel correction (optional)
- Normalization, scaling and highlight roll-off
- Real-time histogram preview
- Saves: `_rgb.tiff` (16-bit), `_w.tiff` (16-bit) and `_rgb.jpg`

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/rgb2w-processor.git
cd rgb2w-processor
```

### 2. Create and activate virtual environment

**Linux / macOS:**

Bash

```
python3 -m venv venv
source venv/bin/activate
```

**Windows:**

Bash

```
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

Bash

```
pip install --upgrade pip
pip install numpy pillow tifffile rawpy matplotlib scipy opencv-python-headless
```

### 4. Run the program

Bash

```
python rgb2w_gui.py
```

## First launch

On the first run the program will ask you to select the folder containing your IMG_XXXX_?.DNG files.

## Optional: Create desktop shortcut (Linux)

Bash

```
chmod +x run.sh
./run.sh
```

(You can also create a .desktop file if needed)

## Requirements

- Python 3.10 or higher
- Supported OS: Linux, Windows, macOS

## Notes

- The venv/ folder is **not** included in the repository (it is in .gitignore).
- All settings are saved automatically in rgb2w_config.json.