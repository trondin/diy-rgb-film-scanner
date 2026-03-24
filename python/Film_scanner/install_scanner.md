**Film Scanner — Canon PowerShot S5 IS + RGB Backlight Controller**

Desktop application (PyQt6) for digitizing film negatives using a Canon PowerShot S5 IS camera controlled via gPhoto2 and a DIY RGB backlight panel controlled from a phone.

**Features:**

- Live view from the camera
- Manual and automatic multi-color scanning (W / RGB / WRGB / Custom)
- Web server for real-time backlight control from any device on the local network
- Automatic saving of RAW + JPEG with proper naming
- Dark frame support for noise subtraction
- Configurable backlight rectangle position and size

**Installation:**

Bash

```
# 1. Install system dependencies
sudo apt install python3-pip libgphoto2-dev

# 2. Install Python packages
pip install PyQt6 gphoto2

# 3. Run
python3 film_scanner.py
```

Connect your Canon S5 IS via USB, start the backlight server, open the address shown in the app on your phone, and start scanning.

Ready for batch digitization of 35mm format film.