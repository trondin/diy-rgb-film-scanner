# tiff_crop.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import json
import numpy as np
import tifffile

CONFIG_FILE = "tiff_crop_config.json"

class TiffCropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TIFF Crop — Frame Cropping Tool (16-bit RGB Support)")

        self.config = self.load_config()
        self.folder = self.config.get("last_folder", os.getcwd())
        self.split_pos = self.config.get("split_pos", 720)
        self.last_ratio = self.config.get("last_ratio", "1:1")

        self.image_array = None    # Stores the original numpy array (preserves 16-bit!)
        self.current_path = None
        self.photo = None

        self.crop_ratio = tk.StringVar(value=self.last_ratio)

        # Crop rectangle coordinates
        self.crop_x1 = self.crop_y1 = 0
        self.crop_x2 = self.crop_y2 = 0
        self.drag_mode = None
        self.start_x = self.start_y = 0

        self.create_widgets()

        # Restore pane position
        self.root.after(100, self.restore_pane_position)

        self.root.geometry("1180x760+100+50")
        self.root.bind("<Configure>", self.on_resize)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        self.config["last_folder"] = self.folder
        self.config["split_pos"] = self.split_pos
        self.config["last_ratio"] = self.crop_ratio.get()
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except:
            pass

    def create_widgets(self):
        self.pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=8)
        self.pane.pack(fill=tk.BOTH, expand=True)

        self.left = tk.Frame(self.pane, bg="#111")
        self.pane.add(self.left, stretch="always")

        self.canvas = tk.Canvas(self.left, bg="#111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.right = tk.Frame(self.pane, bg="#2d2d2d")
        self.pane.add(self.right, stretch="never")

        self.create_right_panel()

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.pane.bind("<ButtonRelease-1>", self.on_sash_release)

    def create_right_panel(self):
        f = self.right
        tk.Label(f, text="TIFF Crop", font=("Arial", 16, "bold"), bg="#2d2d2d", fg="#00ccff").pack(pady=12)

        tk.Button(f, text="Open TIFF", command=self.open_file, height=2).pack(pady=6, fill="x", padx=15)
        tk.Button(f, text="Save As...", command=self.save_file, height=2).pack(pady=6, fill="x", padx=15)

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=15, padx=15)

        nav = tk.Frame(f, bg="#2d2d2d")
        nav.pack(pady=8)
        tk.Button(nav, text="← Previous", command=self.prev_file, width=14).pack(side="left", padx=8)
        tk.Button(nav, text="Next →", command=self.next_file, width=14).pack(side="left", padx=8)

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=15, padx=15)

        tk.Label(f, text="Rotate", bg="#2d2d2d", fg="white").pack(anchor="w", padx=20)
        rot = tk.Frame(f, bg="#2d2d2d")
        rot.pack(pady=6)
        tk.Button(rot, text="↺ 90° CCW", command=lambda: self.rotate(-90)).pack(side="left", padx=10)
        tk.Button(rot, text="↻ 90° CW", command=lambda: self.rotate(90)).pack(side="left", padx=10)

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=15, padx=15)

        tk.Label(f, text="Aspect Ratio", bg="#2d2d2d", fg="white").pack(anchor="w", padx=20)
        rframe = tk.Frame(f, bg="#2d2d2d")
        rframe.pack(pady=8)
        for r in ["1:1", "3:4", "4:3"]:
            tk.Radiobutton(rframe, text=r, variable=self.crop_ratio, value=r,
                           bg="#2d2d2d", fg="white", selectcolor="#555",
                           command=self.update_crop_ratio).pack(side="left", padx=12)

        tk.Button(f, text="Apply Crop", command=self.apply_crop,
                  bg="#0066cc", fg="white", height=2, font=("Arial", 10, "bold")).pack(pady=20, fill="x", padx=20)

        ttk.Separator(f, orient="horizontal").pack(fill="x", pady=10, padx=15)

        # File information
        self.info_label = tk.Label(f, text="No file opened", bg="#2d2d2d", fg="#aaaaaa",
                                   justify=tk.LEFT, anchor="w", font=("Arial", 9))
        self.info_label.pack(pady=15, fill="x", padx=20)

        tk.Button(f, text="Exit", command=self.on_close, bg="#aa0000", fg="white").pack(pady=10, fill="x", padx=20)

    def restore_pane_position(self):
        try:
            self.root.update_idletasks()
            current_width = self.pane.cget('width')
            if current_width and current_width > self.split_pos:
                self.pane.sash_place(0, self.split_pos, 0)
        except:
            pass

    def open_file(self):
        path = filedialog.askopenfilename(initialdir=self.folder,
                                          filetypes=[("TIFF", "*.tif *.tiff"), ("All files", "*.*")])
        if not path: return
        self.folder = os.path.dirname(path)
        self.load_image(path)

    def load_image(self, path):
        try:
            self.current_path = path
            # Read the matrix via tifffile (preserves 16-bit RGB and Grayscale)
            self.image_array = tifffile.imread(path)
            
            self.root.title(f"TIFF Crop — {os.path.basename(path)}")
            self.reset_crop_rect()
            self.show_image()
            self.update_file_info()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file:\n{str(e)}")

    def show_image(self):
        if self.image_array is None: return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            self.root.after(30, self.show_image)
            return

        # Prepare a copy ONLY for Tkinter display
        display_array = self.image_array.copy()
        
        # If the matrix is 16-bit (uint16), scale it down to 8-bit for the screen
        if display_array.dtype == np.uint16:
            display_array = (display_array / 256).astype(np.uint8)
        elif display_array.dtype == np.float32 or display_array.dtype == np.float64:
            # For HDR images if any
            display_array = np.clip(display_array * 255, 0, 255).astype(np.uint8)

        # Convert numpy array to Pillow Image for Canvas
        if len(display_array.shape) == 2:
            display_img = Image.fromarray(display_array).convert("RGB")
        else:
            # Trim alpha channel for display if present
            mode = "RGB" if display_array.shape[2] == 3 else "RGBA"
            display_img = Image.fromarray(display_array, mode=mode)
            if display_img.mode == "RGBA":
                display_img = display_img.convert("RGB")

        display_img.thumbnail((w, h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(display_img)
        self.canvas.delete("all")
        self.canvas.create_image(w//2, h//2, image=self.photo, anchor="center")
        self.draw_crop_rect()

    def reset_crop_rect(self):
        if self.image_array is None: return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 100 or h < 100: return

        # Get dimensions from numpy array: (height, width, channels)
        img_h, img_w = self.image_array.shape[:2]
        
        scale = min(w / img_w, h / img_h)
        disp_w = int(img_w * scale)
        disp_h = int(img_h * scale)

        self.crop_x1 = (w - disp_w) // 2
        self.crop_y1 = (h - disp_h) // 2
        self.crop_x2 = self.crop_x1 + disp_w
        self.crop_y2 = self.crop_y1 + disp_h

        self.enforce_ratio()

    def draw_crop_rect(self):
        self.canvas.delete("croprect")
        self.canvas.create_rectangle(self.crop_x1, self.crop_y1, self.crop_x2, self.crop_y2,
                                     outline="#00ff00", width=3, dash=(6, 4), tag="croprect")
        size = 8
        for x, y in [(self.crop_x1,self.crop_y1),(self.crop_x2,self.crop_y1),
                     (self.crop_x1,self.crop_y2),(self.crop_x2,self.crop_y2)]:
            self.canvas.create_rectangle(x-size, y-size, x+size, y+size,
                                         fill="#00ff00", outline="white", tag="croprect")

    def get_ratio(self):
        r = self.crop_ratio.get()
        if r == "1:1": return 1.0
        if r == "3:4": return 4/3
        return 3/4

    def update_crop_ratio(self):
        if self.image_array is None: return
        ratio = self.get_ratio()
        w = abs(self.crop_x2 - self.crop_x1)
        self.crop_y2 = self.crop_y1 + (w / ratio)
        self.draw_crop_rect()

    def update_file_info(self):
        if self.image_array is None:
            self.info_label.config(text="No file opened")
            return
            
        img_h, img_w = self.image_array.shape[:2]
        
        # Determine channels
        if len(self.image_array.shape) == 2:
            channels = 1
            mode = "Grayscale"
        else:
            channels = self.image_array.shape[2]
            mode = "RGB" if channels == 3 else "RGBA" if channels == 4 else f"{channels}-channel"
            
        # Determine bit depth from numpy dtype
        dtype = self.image_array.dtype
        depth = 8
        if dtype == np.uint16 or dtype == np.int16:
            depth = 16
        elif dtype == np.uint32 or dtype == np.int32 or dtype == np.float32:
            depth = 32
            
        text = f"Size: {img_w} × {img_h}\nMode: {mode} ({depth}-bit/channel)"
        self.info_label.config(text=text)

    def on_mouse_down(self, event):
        if self.image_array is None: return
        x, y = event.x, event.y
        self.start_x = x
        self.start_y = y
        size = 12
        if abs(x-self.crop_x1)<size and abs(y-self.crop_y1)<size: self.drag_mode = "nw"
        elif abs(x-self.crop_x2)<size and abs(y-self.crop_y1)<size: self.drag_mode = "ne"
        elif abs(x-self.crop_x1)<size and abs(y-self.crop_y2)<size: self.drag_mode = "sw"
        elif abs(x-self.crop_x2)<size and abs(y-self.crop_y2)<size: self.drag_mode = "se"
        elif abs(y-self.crop_y1)<8: self.drag_mode = "n"
        elif abs(y-self.crop_y2)<8: self.drag_mode = "s"
        elif abs(x-self.crop_x1)<8: self.drag_mode = "w"
        elif abs(x-self.crop_x2)<8: self.drag_mode = "e"
        elif self.crop_x1 < x < self.crop_x2 and self.crop_y1 < y < self.crop_y2:
            self.drag_mode = "move"

    def on_mouse_drag(self, event):
        if not self.drag_mode: return
        dx = event.x - self.start_x
        dy = event.y - self.start_y
        if self.drag_mode == "move":
            self.crop_x1 += dx; self.crop_y1 += dy
            self.crop_x2 += dx; self.crop_y2 += dy
        else:
            if "n" in self.drag_mode: self.crop_y1 += dy
            if "s" in self.drag_mode: self.crop_y2 += dy
            if "w" in self.drag_mode: self.crop_x1 += dx
            if "e" in self.drag_mode: self.crop_x2 += dx
            self.enforce_ratio()
        self.start_x, self.start_y = event.x, event.y
        self.draw_crop_rect()

    def enforce_ratio(self):
        ratio = self.get_ratio()
        w = abs(self.crop_x2 - self.crop_x1)
        h = w / ratio
        
        if self.crop_y2 < self.crop_y1:
            h = -h
            
        self.crop_y2 = self.crop_y1 + h
        
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.crop_x1 = max(0, min(self.crop_x1, cw))
        self.crop_x2 = max(0, min(self.crop_x2, cw))
        self.crop_y1 = max(0, min(self.crop_y1, ch))
        self.crop_y2 = max(0, min(self.crop_y2, ch))

    def on_mouse_up(self, event):
        self.drag_mode = None
        self.draw_crop_rect()

    def apply_crop(self):
        if self.image_array is None: return
        
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        img_h, img_w = self.image_array.shape[:2]
        
        scale = min(cw / img_w, ch / img_h)
        ox = (cw - img_w * scale) / 2
        oy = (ch - img_h * scale) / 2
        
        x1 = int((self.crop_x1 - ox) / scale)
        y1 = int((self.crop_y1 - oy) / scale)
        x2 = int((self.crop_x2 - ox) / scale)
        y2 = int((self.crop_y2 - oy) / scale)
        
        x1, x2 = sorted([max(0, min(x1, img_w)), max(0, min(x2, img_w))])
        y1, y2 = sorted([max(0, min(y1, img_h)), max(0, min(y2, img_h))])
        
        if x2 - x1 < 20 or y2 - y1 < 20:
            messagebox.showwarning("Area too small", "The selected area is too small.")
            return

        # Direct numpy array cropping
        self.image_array = self.image_array[y1:y2, x1:x2]
        
        self.reset_crop_rect()
        self.show_image()
        self.update_file_info()

    def rotate(self, degrees):
        if self.image_array is None: return
        
        # np.rot90 rotates the matrix counterclockwise when k=1
        if degrees == 90:
            self.image_array = np.rot90(self.image_array, k=-1) # clockwise
        else:
            self.image_array = np.rot90(self.image_array, k=1)  # counterclockwise
            
        self.reset_crop_rect()
        self.show_image()
        self.update_file_info()

    def save_file(self):
        if self.image_array is None: return
        
        default_name = "cropped.tiff"
        if self.current_path:
            base, ext = os.path.splitext(os.path.basename(self.current_path))
            default_name = f"{base}_cropped.tiff"
            
        path = filedialog.asksaveasfilename(
            initialdir=self.folder,
            initialfile=default_name,
            defaultextension=".tiff",
            filetypes=[("TIFF", "*.tif *.tiff")]
        )
        if not path: return
        
        try:
            # Save via tifffile with zlib compression
            tifffile.imwrite(path, self.image_array, compression='zlib')
            messagebox.showinfo("Saved", f"File saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error while saving:\n{str(e)}")

    def get_files_in_folder(self):
        if not self.folder: return []
        exts = {".tif", ".tiff"}
        return [os.path.join(self.folder, f) for f in sorted(os.listdir(self.folder))
                if os.path.splitext(f)[1].lower() in exts]

    def next_file(self):
        if not self.current_path: return
        files = self.get_files_in_folder()
        try:
            idx = files.index(self.current_path)
            if idx < len(files)-1: self.load_image(files[idx+1])
        except: pass

    def prev_file(self):
        if not self.current_path: return
        files = self.get_files_in_folder()
        try:
            idx = files.index(self.current_path)
            if idx > 0: self.load_image(files[idx-1])
        except: pass

    def on_resize(self, event):
        if event.widget == self.root:
            self.show_image()

    def on_sash_release(self, event):
        try:
            sash_pos = self.pane.sash_coord(0)
            if sash_pos:
                self.split_pos = sash_pos[0]
                self.save_config()
        except:
            pass

    def on_close(self):
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TiffCropApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
