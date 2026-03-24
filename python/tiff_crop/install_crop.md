**TIFF Crop** — a tiny Tkinter desktop tool for quick cropping and 90° rotation of 16-bit TIFF images (RGB or Grayscale) while preserving full bit depth.

Finding a compact, ready-to-use program that only rotates an image and crops it while reliably keeping the original 16-bit data in TIFF turned out to be almost impossible. That is exactly why this simple script was written.

**Features**

- Opens and displays 16-bit TIFF files correctly
- Interactive crop rectangle with fixed aspect ratios (1:1, 3:4, 4:3)
- 90° clockwise / counterclockwise rotation
- Preserves original numpy data (no quality loss)
- Saves with zlib compression via tifffile

**Installation & Run**

Bash

```
pip install pillow numpy tifffile
python tiff_crop.py
```

It contains some bugs and rough edges, but it does its main job well enough for everyday use.

Just save the code above as tiff_crop.py and run it. Enjoy!