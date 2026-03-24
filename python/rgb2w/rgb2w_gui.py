import sys
import os
import numpy as np
from PIL import Image, ImageTk
import tifffile
import rawpy
import json
import warnings
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import scipy.ndimage as ndimage
import cv2

warnings.filterwarnings('ignore')

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rgb2w_config.json')


def load_config():
    default = {
        'last_path': os.getcwd(),
        'log_hist': False,
        'pane_horizontal': 800,
        'pane_vertical': 600,
        'fix_bad_pixels': False,
        'bad_pixel_strength': 1,
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                default.update({k: v for k, v in config.items() if k in default})
    except:
        pass
    return default


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except:
        pass


# ────────────────────────────────────────────────
# RAW Processing
# ────────────────────────────────────────────────

def fix_bad_pixels_custom(img, strength=1):
    if img.ndim == 3:
        # Process RGB channels separately
        out = np.empty_like(img, dtype=np.uint16)
        for c in range(3):
            ch = img[:, :, c].astype(np.uint16)
            filtered = cv2.medianBlur(ch, ksize=5)
            out[:, :, c] = filtered
        return out.astype(np.float32)

    # Single channel case (dark frame)
    img_uint16 = img.astype(np.uint16)
    filtered = cv2.medianBlur(img_uint16, ksize=5)

    if strength == 1:
        return filtered.astype(np.float32)

    # Second pass only when strength >= 2
    filtered2 = cv2.medianBlur(filtered, ksize=5)
    return filtered2.astype(np.float32)


def load_raw_channel(path, fix_bad_pixels=False, bad_pixel_strength=1):
    try:
        with rawpy.imread(path) as raw:
            params = {
                'demosaic_algorithm': rawpy.DemosaicAlgorithm.AHD,
                'half_size': False,
                'four_color_rgb': False,
                'use_camera_wb': False,
                'use_auto_wb': False,
                'output_color': rawpy.ColorSpace.raw,
                'output_bps': 16,
                'gamma': (1, 1),
                'no_auto_bright': True,
                'bright': 1.0,
                'highlight_mode': rawpy.HighlightMode.Clip,
                'exp_shift': None,
                'exp_preserve_highlights': 0.0,
                'fbdd_noise_reduction': rawpy.FBDDNoiseReductionMode.Off,
                'median_filter_passes': 0,
            }
            
            rgb = raw.postprocess(**params)
            return rgb.astype(np.float32)
    except Exception as e:
        print(f"Error reading {os.path.basename(path)}: {e}")
        return None


def highlight_rolloff(channel, limit=65535, knee_factor=0.75):
    p99 = np.percentile(channel, 99.5)
    if p99 < limit * 0.9:
        return np.clip(channel, 0, limit)
    knee = limit * knee_factor
    result = channel.copy()
    mask = result > knee
    if np.any(mask):
        x = result[mask]
        result[mask] = knee + (limit - knee) * (1 - np.exp(-(x - knee) / (limit - knee)))
    return np.clip(result, 0, limit)


def save_compressed_tiff(data, output_path, photometric='rgb'):
    try:
        data_uint16 = data.astype(np.uint16)
        tifffile.imwrite(
            output_path,
            data_uint16,
            compression='zlib',
            compressionargs={'level': 9},
            photometric=photometric
        )
        print(f"Saved: {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"Save error {os.path.basename(output_path)}: {e}")
        return False


# ────────────────────────────────────────────────
# GUI Application
# ────────────────────────────────────────────────

class RGB2WApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RGB2W Processor")
        self.root.geometry("1200x800")

        self.config = load_config()
        self.current_folder = self.config['last_path']
        self.base = None
        self.channels = None
        self.proc_channels = None
        self.out_rgb = None
        self.out_w = None
        self.tk_image = None
        self.modified = False
        self.resize_timer = None

        self.norm_percentile = tk.DoubleVar(value=99.95)
        self.scale_target    = tk.DoubleVar(value=62000.0)
        self.knee_factor     = tk.DoubleVar(value=0.82)
        self.log_hist        = tk.BooleanVar(value=self.config['log_hist'])
        self.fix_bad_pixels  = tk.BooleanVar(value=self.config.get('fix_bad_pixels', False))
        self.bad_pixel_strength = tk.StringVar(value=str(self.config.get('bad_pixel_strength', 1)))

        self.setup_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Configure>", self.on_configure)
        self.root.bind("<Map>", self.on_window_mapped)
        self.root.after(100, self.initial_load)

    def update_image(self):
        if self.out_rgb is None:
            return

        gamma = 1 / 2.2
        norm = self.out_rgb / 65535.0
        corrected = np.power(norm, gamma)
        display = (corrected * 255).clip(0, 255).astype(np.uint8)

        img = Image.fromarray(display)

        w = self.image_label.winfo_width()
        h = self.image_label.winfo_height()
        if w < 20 or h < 20:
            return

        ratio = min(w / img.width, h / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))

        resized = img.resize(new_size, Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.image_label.config(image=self.tk_image, text="")

    def update_histograms(self):
        if self.proc_channels is None or self.out_rgb is None:
            return

        log = self.log_hist.get()
        self.config['log_hist'] = log
        save_config(self.config)

        sources = [self.proc_channels['r'], self.proc_channels['g'], self.proc_channels['b'], self.out_rgb]
        titles = ['Red channel (_r)', 'Green channel (_g)', 'Blue channel (_b)', 'Merged RGB']

        for ax, src, title in zip(self.hist_axes, sources, titles):
            ax.clear()
            ax.set_title(title)

            for i, color in enumerate(['r', 'g', 'b']):
                data = src[..., i].ravel()
                ax.hist(data, bins=256, range=(0, 65535),
                        log=log, color=color, alpha=0.5, histtype='stepfilled',
                        label=color.upper())

            ax.legend(fontsize='small')
            ax.set_xlim(0, 65535)

        for canvas in self.hist_canvases:
            canvas.draw()

        self.hist_canvas.configure(scrollregion=self.hist_canvas.bbox("all"))

    def setup_gui(self):
        self.vert_pane = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.vert_pane.pack(fill=tk.BOTH, expand=True)

        top_frame = tk.Frame(self.vert_pane)
        self.vert_pane.add(top_frame, weight=1)

        self.horiz_pane = ttk.PanedWindow(top_frame, orient=tk.HORIZONTAL)
        self.horiz_pane.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(self.horiz_pane)
        self.horiz_pane.add(left_frame, weight=3)

        self.image_label = tk.Label(left_frame, text="Select folder")
        self.image_label.pack(fill=tk.BOTH, expand=True)

        right_frame = tk.Frame(self.horiz_pane)
        self.horiz_pane.add(right_frame, weight=2)

        tk.Checkbutton(right_frame, text="Log scale", variable=self.log_hist,
                       command=self.update_histograms).pack(anchor="w", padx=5, pady=4)

        canvas_frame = tk.Frame(right_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.hist_canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0)
        self.hist_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.hist_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.hist_canvas.configure(yscrollcommand=scrollbar.set)

        self.hist_inner_frame = tk.Frame(self.hist_canvas)
        self.hist_canvas.create_window((0,0), window=self.hist_inner_frame, anchor="nw")

        self.hist_canvases = []
        self.hist_axes = []
        titles = ['Red channel (_r)', 'Green channel (_g)', 'Blue channel (_b)', 'Merged RGB']

        for title in titles:
            fig = Figure(figsize=(4.8, 2.2))
            ax = fig.add_subplot(111)
            ax.set_title(title)
            canvas = FigureCanvasTkAgg(fig, master=self.hist_inner_frame)
            canvas.get_tk_widget().pack(fill=tk.X, expand=False, pady=3, padx=5)
            self.hist_canvases.append(canvas)
            self.hist_axes.append(ax)

        self.hist_inner_frame.bind("<Configure>", lambda e: self.hist_canvas.configure(
            scrollregion=self.hist_canvas.bbox("all")))

        bottom_frame = tk.Frame(self.vert_pane)
        self.vert_pane.add(bottom_frame, weight=0)

        row = 0
        check_frame = tk.Frame(bottom_frame)
        check_frame.grid(row=row, column=0, columnspan=4, sticky="w", padx=8, pady=4)
        
        tk.Checkbutton(
            check_frame, 
            text="Fix bad pixels", 
            variable=self.fix_bad_pixels,
            command=self.on_fix_bad_pixels_changed
        ).pack(side=tk.LEFT)
        
        tk.Label(check_frame, text="Strength:", font=('TkDefaultFont', 9)).pack(side=tk.LEFT, padx=(15, 5))
        
        strength_options = [
            "1 - Weak (minimal effect)",
            "2 - Medium",
            "3 - Strong (maximum cleanup)"
        ]
        
        strength_combo = ttk.Combobox(
            check_frame,
            textvariable=self.bad_pixel_strength,
            values=strength_options,
            state="readonly",
            width=35
        )
        strength_combo.pack(side=tk.LEFT)
        strength_combo.bind('<<ComboboxSelected>>', self.on_fix_bad_pixels_changed)
        
        current_strength = int(self.config.get('bad_pixel_strength', 1))
        strength_combo.set(strength_options[current_strength - 1])
        
        tk.Label(
            check_frame,
            text="(new correction barely affects sharpness)",
            font=('TkDefaultFont', 8),
            fg='gray'
        ).pack(side=tk.LEFT, padx=(10, 0))

        row = 1
        widgets = [
            ("Norm percentile:", self.norm_percentile),
            ("Scale target:",    self.scale_target),
            ("Knee factor:",     self.knee_factor),
        ]

        for label_text, var in widgets:
            tk.Label(bottom_frame, text=label_text).grid(row=row, column=0, sticky="e", padx=8, pady=4)
            tk.Entry(bottom_frame, textvariable=var, width=12).grid(row=row, column=1, sticky="w", padx=8, pady=4)
            row += 1

        btn_frame = tk.Frame(bottom_frame)
        btn_frame.grid(row=row, column=0, columnspan=4, pady=12, sticky="w")

        tk.Button(btn_frame, text="Apply", command=self.apply_changes, width=10).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Save",  command=self.save_files,   width=10).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_frame, text="Change Folder", command=self.change_folder, width=14).pack(side=tk.LEFT, padx=6)

    def get_strength_value(self):
        selected = self.bad_pixel_strength.get()
        if selected.startswith("1"): return 1
        elif selected.startswith("2"): return 2
        elif selected.startswith("3"): return 3
        return 1

    def on_fix_bad_pixels_changed(self, event=None):
        strength = self.get_strength_value()
        self.config['fix_bad_pixels'] = self.fix_bad_pixels.get()
        self.config['bad_pixel_strength'] = strength
        save_config(self.config)
        if self.channels is not None:
            self.load_files()

    def on_window_mapped(self, event):
        self.root.unbind("<Map>")
        self.root.after(300, self.restore_panes)

    def restore_panes(self):
        try:
            if hasattr(self, 'horiz_pane') and hasattr(self, 'vert_pane'):
                h_pos = self.config.get('pane_horizontal', 800)
                v_pos = self.config.get('pane_vertical', 600)
                if h_pos > 0 and v_pos > 0:
                    self.root.after(500, lambda: self._apply_pane_positions(h_pos, v_pos))
        except Exception as e:
            print(f"Pane restore error: {e}")

    def _apply_pane_positions(self, h_pos, v_pos):
        try:
            if hasattr(self, 'horiz_pane') and self.horiz_pane.winfo_exists():
                max_h = self.horiz_pane.winfo_width()
                if max_h > 100:
                    h_pos = min(h_pos, max_h - 100)
                    if h_pos > 50:
                        self.horiz_pane.sashpos(0, h_pos)
            
            if hasattr(self, 'vert_pane') and self.vert_pane.winfo_exists():
                max_v = self.vert_pane.winfo_height()
                if max_v > 100:
                    v_pos = min(v_pos, max_v - 100)
                    if v_pos > 50:
                        self.vert_pane.sashpos(0, v_pos)
        except Exception as e:
            print(f"Pane apply error: {e}")

    def save_panes(self):
        try:
            if hasattr(self, 'horiz_pane') and self.horiz_pane.winfo_exists():
                h_pos = self.horiz_pane.sashpos(0)
                if h_pos and h_pos > 0:
                    self.config['pane_horizontal'] = h_pos
            
            if hasattr(self, 'vert_pane') and self.vert_pane.winfo_exists():
                v_pos = self.vert_pane.sashpos(0)
                if v_pos and v_pos > 0:
                    self.config['pane_vertical'] = v_pos
            
            save_config(self.config)
        except Exception as e:
            print(f"Pane save error: {e}")

    def on_configure(self, event):
        if self.resize_timer:
            self.root.after_cancel(self.resize_timer)
        self.resize_timer = self.root.after(300, self.update_image)

    def set_wait_cursor(self):
        self.root.config(cursor="watch")
        self.root.update()

    def set_normal_cursor(self):
        self.root.config(cursor="")

    def change_folder(self):
        if self.modified and not messagebox.askyesno("Unsaved changes", "Changes will be lost. Continue?"):
            return

        folder = filedialog.askdirectory(title="Folder with IMG_*_?.DNG files", initialdir=self.current_folder)
        if folder:
            self.current_folder = folder
            self.config['last_path'] = folder
            save_config(self.config)
            self.load_files()

    def load_files(self):
        self.set_wait_cursor()
        try:
            self.base = self.find_smallest_base_number(self.current_folder)
            if not self.base:
                messagebox.showerror("Error", "No files found matching IMG_XXXX_[rgbdw].DNG")
                return

            suffixes = ['r','g','b','d','w']
            paths = {s: os.path.join(self.current_folder, f"{self.base}_{s}.DNG") for s in suffixes}

            missing = [s for s in suffixes if not os.path.exists(paths[s])]
            if missing:
                messagebox.showerror("Error", f"Missing files: {', '.join(missing)}")
                return

            self.channels = {}
            fix_bad = self.fix_bad_pixels.get()
            strength = self.get_strength_value()
            
            strength_names = ["off", "weak", "medium", "strong"]
            print(f"Loading files with correction: {strength_names[strength if fix_bad else 0]}")
            
            for s in suffixes:
                print(f"  → {s.upper()}...")
                ch = load_raw_channel(paths[s], fix_bad_pixels=fix_bad, bad_pixel_strength=strength)
                if ch is None:
                    messagebox.showerror("Error", f"Failed to load {s.upper()}")
                    return
                self.channels[s] = ch

            self.process_images(auto=True)
            self.modified = False
        finally:
            self.set_normal_cursor()

    def find_smallest_base_number(self, folder):
        files = [f.lower() for f in os.listdir(folder) if f.lower().endswith('.dng') and f.lower().startswith('img_')]
        bases = set()
        for f in files:
            parts = f.split('_')
            if len(parts) >= 3 and parts[1].isdigit():
                bases.add(int(parts[1]))
        return f"IMG_{min(bases):04d}" if bases else None

    def process_images(self, auto=False):
        if not self.channels:
            return

        self.set_wait_cursor()
        try:
            # Filter dark frame BEFORE subtraction
            dark = self.channels['d']
            if self.fix_bad_pixels.get():
                strength = self.get_strength_value()
                dark = fix_bad_pixels_custom(dark, strength)

            r = np.clip(self.channels['r'] - dark, 0, None)
            g = np.clip(self.channels['g'] - dark, 0, None)
            b = np.clip(self.channels['b'] - dark, 0, None)

            # RGB channel filtering
            if self.fix_bad_pixels.get():
                strength = self.get_strength_value()
                r = fix_bad_pixels_custom(r, strength)
                g = fix_bad_pixels_custom(g, strength)
                b = fix_bad_pixels_custom(b, strength)

            self.proc_channels = {'r': r, 'g': g, 'b': b}

            red_ch   = self.proc_channels['r'].mean(axis=2)
            green_ch = self.proc_channels['g'].mean(axis=2)
            blue_ch  = self.proc_channels['b'].mean(axis=2)

            compensation = 3.8
            red_ch   *= compensation
            green_ch *= compensation
            blue_ch  *= compensation

            p = self.norm_percentile.get()
            mx = max(np.percentile(ch, p) for ch in (red_ch, green_ch, blue_ch))
            mx = max(mx, 1e-6)

            desired_max = self.scale_target.get()
            scale = desired_max / mx

            red_ch   *= scale
            green_ch *= scale
            blue_ch  *= scale

            self.out_rgb = np.stack([
                highlight_rolloff(red_ch,   knee_factor=self.knee_factor.get()),
                highlight_rolloff(green_ch, knee_factor=self.knee_factor.get()),
                highlight_rolloff(blue_ch,  knee_factor=self.knee_factor.get())
            ], axis=-1)

            self.out_w = self.channels['w']          # w-channel is left untouched as requested

            self.update_image()
            self.update_histograms()
            if not auto:
                self.modified = True
        finally:
            self.set_normal_cursor()

    def apply_changes(self):
        self.process_images(auto=False)

    def save_files(self):
        if self.out_rgb is None:
            messagebox.showwarning("No data", "Process image first")
            return

        self.set_wait_cursor()
        try:
            p = self.current_folder
            rgb_path = os.path.join(p, f"{self.base}_rgb.tiff")
            w_path   = os.path.join(p, f"{self.base}_w.tiff")
            jpg_path = os.path.join(p, f"{self.base}_rgb.jpg")

            save_compressed_tiff(self.out_rgb, rgb_path)
            save_compressed_tiff(self.out_w,   w_path)

            gamma = 1 / 2.2
            norm = self.out_rgb / 65535.0
            jpg = (np.power(norm, gamma) * 255).clip(0,255).astype(np.uint8)
            Image.fromarray(jpg).save(jpg_path, quality=92)

            messagebox.showinfo("Saved", 
                f"RGB → {self.base}_rgb.tiff\n"
                f"W   → {self.base}_w.tiff\n"
                f"JPG → {self.base}_rgb.jpg")
            self.modified = False
        finally:
            self.set_normal_cursor()

    def initial_load(self):
        if os.path.exists(self.current_folder):
            self.load_files()
        else:
            self.change_folder()

    def on_closing(self):
        self.save_panes()
        self.config['fix_bad_pixels'] = self.fix_bad_pixels.get()
        self.config['bad_pixel_strength'] = self.get_strength_value()
        save_config(self.config)
        
        if self.modified and not messagebox.askokcancel("Exit", "There are unsaved changes.\nExit anyway?"):
            return
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RGB2WApp(root)
    root.mainloop()
