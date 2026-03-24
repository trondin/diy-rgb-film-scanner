#!/usr/bin/env python3
import sys
import signal
import json
import os
import socket
import threading
from pathlib import Path
import time
import re

from PyQt6.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QScrollArea, QMainWindow, QGroupBox, QSpinBox,
    QRadioButton, QFrame, QMessageBox, QButtonGroup, QCheckBox,
)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt
from http.server import HTTPServer, BaseHTTPRequestHandler
import gphoto2 as gp


# =============================================================================
# Constants
# =============================================================================
CONFIG_FILE = "film_scanner.json"
SERVER_PORT = 8080
LIVEVIEW_INTERVAL_MS = 50
BRIGHTNESS_MAX = 100
RGB_MAX = 255
COLOR_SCALE_FACTOR = 2.55  # RGB_MAX / BRIGHTNESS_MAX
SHUTTER_DELAY_SECONDS = 2  # Delay between setting backlight and shooting

DEFAULT_CONFIG = {
    "color_mode": "R",
    "brightness": {"R": 100, "G": 100, "B": 100, "W": 100},
    "custom_brightness": {"R": 100, "G": 100, "B": 100},
    "rect_width": 300,
    "rect_height": 200,
    "rect_x": 50,
    "rect_y": 50,
    "scan_sequence": "W",  # W, Custom, RGB, WRGB, CustomRGB
    "dark_frames": False
}


# =============================================================================
# Configuration Manager
# =============================================================================
class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cfg = DEFAULT_CONFIG.copy()
                    cfg.update(data)
                    return cfg
            except:
                pass
        return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(config):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except:
            pass


# =============================================================================
# Backlight Web Server
# =============================================================================
class RequestHandler(BaseHTTPRequestHandler):
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Backlight</title>
  <style>
    body{margin:0;height:100vh;background:#000;overflow:hidden}
    #rect{position:absolute;left:0;top:0;width:100px;height:100px;background:#f00}
    #info{position:fixed;bottom:8px;right:8px;color:#888;font:11px sans-serif;pointer-events:none}
  </style>
</head>
<body>
  <div id="rect"></div>
  <div id="info">Loading...</div>

<script>
const rect = document.getElementById('rect');
const info  = document.getElementById('info');

let last = {};

function updateRect(data) {
  if (last.x !== data.x) rect.style.left   = data.x + 'px';
  if (last.y !== data.y) rect.style.top    = data.y + 'px';
  if (last.w !== data.w) rect.style.width  = data.w + 'px';
  if (last.h !== data.h) rect.style.height = data.h + 'px';
  if (last.c !== data.c) rect.style.background = data.c;

  info.textContent = `${data.w}×${data.h}  •  (${data.x}, ${data.y})`;

  last = {x:data.x, y:data.y, w:data.w, h:data.h, c:data.c};
}

function poll() {
  fetch('/state', {cache:'no-store'})
    .then(r => r.json())
    .then(updateRect)
    .catch(() => setTimeout(poll, 2000))
    .finally(() => setTimeout(poll, 800));
}

poll();
</script>
</body>
</html>"""

    def do_GET(self):
        if self.path.rstrip('/') == '/state':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            color = self._get_current_color()
            payload = {
                "x": self.server.config["rect_x"],
                "y": self.server.config["rect_y"],
                "w": self.server.config["rect_width"],
                "h": self.server.config["rect_height"],
                "c": color
            }
            self.wfile.write(json.dumps(payload).encode('utf-8'))
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(self.html_template.encode('utf-8'))

    def _get_current_color(self):
        mode = self.server.config["color_mode"]
        br = self.server.config["brightness"]
        cb = self.server.config["custom_brightness"]

        def to_hex(v):
            return f"{int(v * COLOR_SCALE_FACTOR):02x}"

        if mode == "R":
            return "#" + to_hex(br["R"]) + "0000"
        if mode == "G":
            return "#" + "00" + to_hex(br["G"]) + "00"
        if mode == "B":
            return "#" + "0000" + to_hex(br["B"])
        if mode == "W":
            v = to_hex(br["W"])
            return "#" + v + v + v
        if mode == "Custom":
            return "#" + to_hex(cb["R"]) + to_hex(cb["G"]) + to_hex(cb["B"])
        if mode == "Off":
            return "#000000"

        return "#ff0000"  # fallback

    def log_message(self, *args, **kwargs):
        pass


class ConfigServer(HTTPServer):
    def __init__(self, server_address, handler_class, config):
        super().__init__(server_address, handler_class)
        self.config = config
        self.config_lock = threading.Lock()


class ServerThread(threading.Thread):
    def __init__(self, host, port, config):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.config = config
        self.server = None

    def run(self):
        self.server = ConfigServer((self.host, self.port), RequestHandler, self.config)
        self.server.serve_forever()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def update_config(self, new_values):
        if self.server:
            with self.server.config_lock:
                self.server.config.update(new_values)


# =============================================================================
# Main Application Window
# =============================================================================
class CombinedWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Film Scanner — Canon S5 IS + Backlight")
        self.resize(1100, 720)

        # Load config
        self.config = ConfigManager.load()
        self.server_thread = None
        self.server_running = False
        self.local_ip = self.get_local_ip()
        self.server_url = f"http://{self.local_ip}:{SERVER_PORT}"

        # Camera
        self.camera = None
        self.context = gp.Context()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read_frame)
        self.timer.setInterval(LIVEVIEW_INTERVAL_MS)

        self.images_folder = Path("images")
        self.images_folder.mkdir(exist_ok=True)

        # Variables for sequential scanning
        self.is_scanning = False
        self.scan_sequence = []
        self.current_scan_index = 0
        self.scan_folder = None
        self.original_color_mode = None
        self.captured_files_info = []  # List of tuples (folder, name) for each frame
        self.was_liveview_active = False

        # Pixmap for preview
        self.pixmap = QPixmap()

        # UI
        self.init_ui()
        self.sync_ui_from_config()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        # ===== Left panel =====
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        self.preview_label = QLabel("Camera not connected")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background: black; color: white; font: 16pt")
        self.preview_label.setMinimumSize(360, 240)
        left_layout.addWidget(self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_layout_cam = QHBoxLayout()
        btn_layout_cam.setSpacing(10)

        self.connect_btn = QPushButton("Connect camera")
        self.connect_btn.clicked.connect(self.toggle_connection)
        btn_layout_cam.addWidget(self.connect_btn)

        self.liveview_btn = QPushButton("Start Live View")
        self.liveview_btn.clicked.connect(self.toggle_liveview)
        self.liveview_btn.setEnabled(False)
        btn_layout_cam.addWidget(self.liveview_btn)

        self.capture_btn = QPushButton("Capture")
        self.capture_btn.clicked.connect(self.capture_photo)
        self.capture_btn.setEnabled(False)
        btn_layout_cam.addWidget(self.capture_btn)

        left_layout.addLayout(btn_layout_cam)

        # Instructions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(220)

        help_widget = QWidget()
        help_layout = QVBoxLayout(help_widget)
        help_layout.setSpacing(6)

        help_text = QLabel(
            "<b>Control Instructions:</b><br><br>"
            "• Switch the camera to <b>[M]</b> mode<br>"
            "• Enable Super Zoom: press and hold the <b>[⚘]</b> button on the lens for > 1 sec<br><br>"
            "• <b>[FUNC]</b> — white balance, size, compression, etc.<br>"
            "• <b>[ISO]</b> — switch ISO<br>"
            "• <b>[◀ ▶]</b> — shutter speed<br>"
            "• <b>[▲ ▼]</b> — aperture<br><br>"
            "Manual focus:<br>"
            "• Press and hold the <b>[MF]</b> button on the lens<br>"
            "• Then use <b>[▲ ▼]</b> to focus<br><br>"
            "Use <b>CHDK</b>!"
        )
        help_text.setStyleSheet("font-size: 11pt;")
        help_text.setWordWrap(True)
        help_text.setMinimumHeight(280)
        help_text.setMaximumHeight(360)
        help_layout.addWidget(help_text)
        help_layout.addStretch(1)

        scroll.setWidget(help_widget)
        left_layout.addWidget(scroll)
        left_layout.addStretch()

        main_layout.addWidget(left_widget, stretch=1)

        # ===== Right panel =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(12)

        # ---- Server group ----
        srv_group = QGroupBox("Backlight Server (phone control)")
        srv_layout = QVBoxLayout(srv_group)
        srv_layout.setContentsMargins(12, 10, 12, 10)

        self.status_label = QLabel("○ Stopped")
        self.status_label.setStyleSheet("color: gray; font-weight: bold; font-size: 11pt;")
        srv_layout.addWidget(self.status_label)

        self.address_label = QLabel(self.server_url)
        self.address_label.setStyleSheet("font-size: 10pt;")
        srv_layout.addWidget(self.address_label)

        btn_layout_srv = QHBoxLayout()
        btn_layout_srv.setSpacing(12)

        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_server)
        btn_layout_srv.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        btn_layout_srv.addWidget(self.stop_btn)

        srv_layout.addLayout(btn_layout_srv)
        right_layout.addWidget(srv_group)

        # ---- Rectangle group ----
        rect_group = QGroupBox("Rectangle Position && Size")
        rect_layout = QVBoxLayout(rect_group)
        rect_layout.setContentsMargins(12, 10, 12, 10)
        rect_layout.setSpacing(10)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(20, 1920)
        self.width_spin.setValue(self.config["rect_width"])
        self.width_spin.valueChanged.connect(self.apply_config)
        size_layout.addWidget(self.width_spin)

        size_layout.addSpacing(30)
        size_layout.addWidget(QLabel("Height:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(20, 1200)
        self.height_spin.setValue(self.config["rect_height"])
        self.height_spin.valueChanged.connect(self.apply_config)
        size_layout.addWidget(self.height_spin)
        rect_layout.addLayout(size_layout)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("X:"))
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 1920)
        self.x_spin.setValue(self.config["rect_x"])
        self.x_spin.valueChanged.connect(self.apply_config)
        pos_layout.addWidget(self.x_spin)

        pos_layout.addSpacing(30)
        pos_layout.addWidget(QLabel("Y:"))
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 1200)
        self.y_spin.setValue(self.config["rect_y"])
        self.y_spin.valueChanged.connect(self.apply_config)
        pos_layout.addWidget(self.y_spin)

        rect_layout.addLayout(pos_layout)
        right_layout.addWidget(rect_group)

        # ---- Color group ----
        color_group = QGroupBox("Color && Brightness")
        color_layout = QVBoxLayout(color_group)
        color_layout.setContentsMargins(12, 10, 12, 10)

        modes_layout = QHBoxLayout()
        modes_layout.setSpacing(20)
        modes_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.color_mode_group = QButtonGroup(self)

        modes = [
            ("Red",    "R",   True),
            ("Green",  "G",   True),
            ("Blue",   "B",   True),
            ("White",  "W",   True),
            ("Custom", "Custom", False),
            ("Off",    "Off",  False),
        ]

        self.brightness_spins = {}
        self.custom_spins = {}

        for text, value, has_brightness in modes:
            column = QVBoxLayout()
            column.setAlignment(Qt.AlignmentFlag.AlignTop)
            column.setSpacing(6)

            rb = QRadioButton(text)
            rb.setObjectName(value)
            rb.toggled.connect(self.on_mode_changed)
            self.color_mode_group.addButton(rb)
            column.addWidget(rb)

            controls_widget = QWidget()
            controls_layout = QVBoxLayout(controls_widget)
            controls_layout.setContentsMargins(0, 0, 0, 0)
            controls_layout.setSpacing(2)
            controls_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            if has_brightness:
                spin = QSpinBox()
                spin.setRange(0, BRIGHTNESS_MAX)
                spin.setFixedWidth(60)
                spin.setValue(self.config["brightness"].get(value, BRIGHTNESS_MAX))
                spin.valueChanged.connect(self.apply_config)
                controls_layout.addWidget(spin)
                self.brightness_spins[value] = spin
            elif value == "Custom":
                for ch in "RGB":
                    row = QHBoxLayout()
                    row.setContentsMargins(0, 0, 0, 0)
                    lbl = QLabel(f"{ch}:")
                    lbl.setFixedWidth(20)
                    row.addWidget(lbl)
                    spin = QSpinBox()
                    spin.setRange(0, BRIGHTNESS_MAX)
                    spin.setFixedWidth(60)
                    spin.setValue(self.config["custom_brightness"].get(ch, BRIGHTNESS_MAX))
                    spin.valueChanged.connect(self.apply_config)
                    row.addWidget(spin)
                    controls_layout.addLayout(row)
                    self.custom_spins[ch] = spin
            else:
                controls_layout.addStretch()

            column.addWidget(controls_widget)
            col_widget = QWidget()
            col_widget.setLayout(column)
            col_widget.setMinimumWidth(100)
            col_widget.setMaximumWidth(110)
            modes_layout.addWidget(col_widget)

        color_layout.addLayout(modes_layout)
        right_layout.addWidget(color_group)

        # ===== Scan Settings panel =====
        scan_group = QGroupBox("Scan Settings")
        scan_layout = QVBoxLayout(scan_group)
        scan_layout.setContentsMargins(12, 10, 12, 10)
        scan_layout.setSpacing(10)

        # Scan sequence
        seq_layout = QHBoxLayout()
        seq_layout.setSpacing(15)
        seq_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scan_sequence_group = QButtonGroup(self)
        
        sequences = [
            ("W only", "W"),
            ("Custom", "Custom"),
            ("RGB", "RGB"),
            ("WRGB", "WRGB"),
            ("Custom RGB", "CustomRGB")
        ]
        
        self.sequence_buttons = {}
        for text, value in sequences:
            rb = QRadioButton(text)
            rb.setObjectName(f"seq_{value}")
            rb.toggled.connect(self.on_scan_sequence_changed)
            self.scan_sequence_group.addButton(rb)
            seq_layout.addWidget(rb)
            self.sequence_buttons[value] = rb
        
        seq_layout.addStretch()
        scan_layout.addLayout(seq_layout)

        # Dark frames checkbox
        dark_layout = QHBoxLayout()
        self.dark_frames_check = QCheckBox("Capture dark frames (for sensor noise correction)")
        self.dark_frames_check.setChecked(self.config.get("dark_frames", False))
        self.dark_frames_check.stateChanged.connect(self.on_dark_frames_changed)
        dark_layout.addWidget(self.dark_frames_check)
        dark_layout.addStretch()
        scan_layout.addLayout(dark_layout)

        # Start scan button
        scan_btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton("Start Scan Sequence")
        self.scan_btn.clicked.connect(self.start_scan_sequence)
        self.scan_btn.setEnabled(False)
        self.scan_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        scan_btn_layout.addWidget(self.scan_btn)
        scan_layout.addLayout(scan_btn_layout)

        right_layout.addWidget(scan_group)
        right_layout.addStretch()

        main_layout.addWidget(right_widget, stretch=1)

    # -------------------------------------------------------------------------
    # UI state management
    # -------------------------------------------------------------------------
    def block_signals(self, block):
        """Block/unblock signals of all controls"""
        self.width_spin.blockSignals(block)
        self.height_spin.blockSignals(block)
        self.x_spin.blockSignals(block)
        self.y_spin.blockSignals(block)

        for spin in self.brightness_spins.values():
            spin.blockSignals(block)

        for spin in self.custom_spins.values():
            spin.blockSignals(block)

        for btn in self.color_mode_group.buttons():
            btn.blockSignals(block)
            
        for btn in self.scan_sequence_group.buttons():
            btn.blockSignals(block)
            
        self.dark_frames_check.blockSignals(block)

    def sync_ui_from_config(self):
        """Restore UI state from loaded config"""
        self.block_signals(True)

        # Select mode
        for btn in self.color_mode_group.buttons():
            if btn.objectName() == self.config.get("color_mode", "R"):
                btn.setChecked(True)
                break

        # Sync brightness spins
        for key, spin in self.brightness_spins.items():
            spin.setValue(self.config["brightness"].get(key, BRIGHTNESS_MAX))

        # Sync custom spins
        for key, spin in self.custom_spins.items():
            spin.setValue(self.config["custom_brightness"].get(key, BRIGHTNESS_MAX))

        # Rectangle position and size
        self.width_spin.setValue(self.config.get("rect_width", 300))
        self.height_spin.setValue(self.config.get("rect_height", 200))
        self.x_spin.setValue(self.config.get("rect_x", 50))
        self.y_spin.setValue(self.config.get("rect_y", 50))
        
        # Sync scan sequence
        seq = self.config.get("scan_sequence", "W")
        for value, btn in self.sequence_buttons.items():
            if value == seq:
                btn.setChecked(True)
                break
                
        # Sync dark frames checkbox
        self.dark_frames_check.setChecked(self.config.get("dark_frames", False))

        self.block_signals(False)
        self.apply_config()

    # -------------------------------------------------------------------------
    # Camera methods
    # -------------------------------------------------------------------------
    def toggle_connection(self):
        if self.camera:
            self.disconnect_camera()
        else:
            self.connect_camera()

    def connect_camera(self):
        self.preview_label.setText("Searching for camera...")

        try:
            self.camera = gp.Camera()
            self.camera.init(self.context)
            self.preview_label.setText("Camera connected")
            self.connect_btn.setText("Disconnect camera")
            self.liveview_btn.setEnabled(True)
            self.capture_btn.setEnabled(True)
            self.update_scan_button_state()
            print("Camera connected")
        except Exception as e:
            self.preview_label.setText(f"Connection error\n{e}")
            print(f"Connection error: {e}")
            self.camera = None

    def disconnect_camera(self):
        self.stop_liveview()

        if self.camera:
            try:
                self.camera.exit(self.context)
                print("Camera disconnected")
            except Exception as e:
                print(f"Disconnection error: {e}")
            self.camera = None

        self.connect_btn.setText("Connect camera")
        self.liveview_btn.setEnabled(False)
        self.capture_btn.setEnabled(False)
        self.update_scan_button_state()
        self.liveview_btn.setText("Start Live View")
        self.preview_label.setText("Camera not connected")

    def toggle_liveview(self):
        if self.timer.isActive():
            self.stop_liveview()
        else:
            self.start_liveview()

    def start_liveview(self):
        if not self.camera:
            return
        try:
            self.liveview_btn.setText("Stop Live View")
            self.preview_label.setText("Starting Live View...")
            self.timer.start()
            print("Live View started")
        except Exception as e:
            print(f"Live View start error: {e}")
            self.stop_liveview()

    def stop_liveview(self):
        self.timer.stop()
        self.preview_label.setText("Camera connected" if self.camera else "Camera not connected")
        self.liveview_btn.setText("Start Live View")
        print("Live View stopped")

    def read_frame(self):
        if not self.camera:
            return

        camera_file = None
        try:
            camera_file = self.camera.capture_preview(self.context)
            file_data = camera_file.get_data_and_size()

            img = QImage.fromData(file_data)
            if not img.isNull():
                self.pixmap.convertFromImage(img)
                self.preview_label.setPixmap(self.pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))

        except gp.GPhoto2Error as e:
            if e.code == gp.GP_ERROR_IO_USB_CLAIM:
                pass
            else:
                print(f"GPhoto2 frame error: {e}")
        except Exception as e:
            print(f"Frame read error: {e}")
        finally:
            if camera_file:
                del camera_file

    def capture_photo(self):
        if not self.camera:
            return

        was_running = self.timer.isActive()
        if was_running:
            self.timer.stop()

        self.preview_label.setText("Capturing...")
        self.capture_btn.setEnabled(False)

        captured_ok = False
        captured_files = []

        try:
            file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE, self.context)
            folder, name = file_path.folder, file_path.name
            print(f"Camera reports new file: {folder}/{name}")

            saved_file = self.save_file(folder, name, self.images_folder)
            if saved_file:
                captured_files.append(saved_file)

            jpg_name = None
            raw_name = None

            if name.startswith('IMG_') and name.endswith('.JPG'):
                jpg_name = name
                raw_name = f"CRW_{name[4:8]}.DNG"
            elif name.startswith('CRW_') and name.endswith('.DNG'):
                raw_name = name
                jpg_name = f"IMG_{name[4:8]}.JPG"

            if raw_name:
                saved_raw = self.save_file(folder, raw_name, self.images_folder)
                if saved_raw:
                    captured_files.append(saved_raw)
            if jpg_name and jpg_name != name:
                saved_jpg = self.save_file(folder, jpg_name, self.images_folder)
                if saved_jpg:
                    captured_files.append(saved_jpg)

            captured_ok = True

        except Exception as e:
            print(f"Capture / download error: {e}")
            self.preview_label.setText(f"Capture error\n{str(e)}")

        finally:
            self.disconnect_camera()
            time.sleep(1.2)

            if captured_ok:
                self.preview_label.setText("Photo saved")
            else:
                self.preview_label.setText("Photo taken, but download error")

            self.connect_camera()

            if was_running:
                self.start_liveview()

            self.capture_btn.setEnabled(True)
            
            return captured_files

    def save_file(self, folder, name, target_folder=None):
        if not self.camera:
            return None
        if target_folder is None:
            target_folder = self.images_folder
            
        try:
            print(f"Trying to save: {folder}/{name}")
            cam_file = self.camera.file_get(folder, name, gp.GP_FILE_TYPE_NORMAL, self.context)
            target = target_folder / name
            cam_file.save(str(target))
            print(f"Saved → {target}")
            del cam_file
            return target
        except gp.GPhoto2Error as e:
            print(f"Download error {name}: {e} (code {e.code})")
            return None
        except Exception as e:
            print(f"Unexpected error {name}: {e}")
            return None

    # -------------------------------------------------------------------------
    # Sequential scanning methods
    # -------------------------------------------------------------------------
    def get_next_frame_folder(self):
        existing_folders = []
        pattern = re.compile(r'^frame(\d{4})$')
        
        for item in self.images_folder.iterdir():
            if item.is_dir():
                match = pattern.match(item.name)
                if match:
                    existing_folders.append(int(match.group(1)))
        
        if not existing_folders:
            next_num = 0
        else:
            existing_folders.sort()
            next_num = 0
            for num in existing_folders:
                if num == next_num:
                    next_num += 1
                else:
                    break
        
        folder_name = f"frame{next_num:04d}"
        folder_path = self.images_folder / folder_name
        folder_path.mkdir(exist_ok=True)
        return folder_path

    def build_scan_sequence(self):
        sequence = []
        scan_seq = self.config.get("scan_sequence", "W")
        dark_frames = self.config.get("dark_frames", False)
        
        if dark_frames:
            sequence.append("Off")
        
        if scan_seq == "W":
            sequence.append("W")
        elif scan_seq == "Custom":
            sequence.append("Custom")
        elif scan_seq == "RGB":
            sequence.extend(["R", "G", "B"])
        elif scan_seq == "WRGB":
            sequence.append("W")
            sequence.extend(["R", "G", "B"])
        elif scan_seq == "CustomRGB":
            sequence.append("Custom")
            sequence.extend(["R", "G", "B"])
        
        return sequence

    def set_backlight_color(self, color_mode):
        if not self.server_running or not self.server_thread:
            return False
        
        self.config["color_mode"] = color_mode
        self.server_thread.update_config(self.config)
        
        self.block_signals(True)
        for btn in self.color_mode_group.buttons():
            if btn.objectName() == color_mode:
                btn.setChecked(True)
                break
        self.block_signals(False)
        
        return True

    def start_scan_sequence(self):
        if not self.camera or not self.server_running or self.is_scanning:
            return
        
        reply = QMessageBox.question(
            self, 
            "Start Scan Sequence", 
            "This will capture multiple photos with different backlight colors.\n"
            "Make sure the camera is in manual mode and ready.\n\n"
            f"Sequence: {', '.join(self.build_scan_sequence())}\n"
            f"Delay between shots: {SHUTTER_DELAY_SECONDS} seconds\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.scan_folder = self.get_next_frame_folder()
        print(f"Created scan folder: {self.scan_folder}")
        
        self.scan_sequence = self.build_scan_sequence()
        self.current_scan_index = 0
        self.captured_files_info = []
        self.original_color_mode = self.config["color_mode"]
        
        self.was_liveview_active = self.timer.isActive()
        if self.was_liveview_active:
            self.stop_liveview()
        
        self.is_scanning = True
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.capture_btn.setEnabled(False)
        
        QTimer.singleShot(100, self.capture_next_scan_frame)

    def capture_next_scan_frame(self):
        if not self.is_scanning or self.current_scan_index >= len(self.scan_sequence):
            self.download_all_frames()
            return
        
        color = self.scan_sequence[self.current_scan_index]
        print(f"Capturing frame {self.current_scan_index + 1}/{len(self.scan_sequence)}: {color}")
        
        self.preview_label.setText(f"Shooting: {color} ({self.current_scan_index + 1}/{len(self.scan_sequence)})")
        
        self.set_backlight_color(color)
        
        QTimer.singleShot(SHUTTER_DELAY_SECONDS * 1000, self.do_scan_capture)

    def do_scan_capture(self):
        if not self.is_scanning:
            return
        
        try:
            file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE, self.context)
            folder, name = file_path.folder, file_path.name
            print(f"Captured: {folder}/{name}")
            
            self.captured_files_info.append((folder, name))
            
            self.current_scan_index += 1
            
            if self.current_scan_index < len(self.scan_sequence):
                QTimer.singleShot(500, self.capture_next_scan_frame)
            else:
                QTimer.singleShot(500, self.download_all_frames)
                
        except Exception as e:
            print(f"Scan capture error: {e}")
            self.preview_label.setText(f"Scan error: {str(e)}")
            QTimer.singleShot(500, self.download_all_frames)

    def download_all_frames(self):
        print(f"Downloading {len(self.captured_files_info)} frames...")
        self.preview_label.setText(f"Downloading {len(self.captured_files_info)} frames...")
        
        if not self.captured_files_info:
            self.finish_scan_sequence(0)
            return
        
        first_folder, first_name = self.captured_files_info[0]
        base_name = Path(first_name).stem
        base_name = re.sub(r'[._][a-z]$', '', base_name, flags=re.IGNORECASE)
        
        downloaded_count = 0
        
        for i, (folder, name) in enumerate(self.captured_files_info):
            print(f"Downloading frame {i+1}/{len(self.captured_files_info)}: {folder}/{name}")
            
            color_suffix = self.get_color_suffix(self.scan_sequence[i])
            
            success = self.download_frame_files_with_rename(folder, name, i+1, base_name, color_suffix)
            
            if success:
                downloaded_count += 1
            else:
                print(f"Failed to download, reconnecting camera...")
                self.disconnect_camera()
                time.sleep(1.2)
                self.connect_camera()
                
                if self.camera:
                    success = self.download_frame_files_with_rename(folder, name, i+1, base_name, color_suffix)
                    if success:
                        downloaded_count += 1
        
        self.finish_scan_sequence(downloaded_count)

    def get_color_suffix(self, color_mode):
        suffixes = {
            "Off": "d",
            "W": "w",
            "Custom": "w",
            "R": "r",
            "G": "g",
            "B": "b"
        }
        return suffixes.get(color_mode, "x")

    def download_frame_files_with_rename(self, folder, name, frame_num, base_name, color_suffix):
        if not self.camera:
            return False
        
        try:
            saved_main = self.save_file_with_rename(folder, name, self.scan_folder, base_name, color_suffix)
            
            jpg_name = None
            raw_name = None
            
            if name.startswith('IMG_') and name.endswith('.JPG'):
                jpg_name = name
                raw_name = f"CRW_{name[4:8]}.DNG"
            elif name.startswith('CRW_') and name.endswith('.DNG'):
                raw_name = name
                jpg_name = f"IMG_{name[4:8]}.JPG"
            
            if raw_name and raw_name != name:
                self.save_file_with_rename(folder, raw_name, self.scan_folder, base_name, color_suffix)
            if jpg_name and jpg_name != name:
                self.save_file_with_rename(folder, jpg_name, self.scan_folder, base_name, color_suffix)
            
            return saved_main is not None
            
        except Exception as e:
            print(f"Error downloading frame {frame_num}: {e}")
            return False

    def save_file_with_rename(self, folder, name, target_folder, base_name, suffix):
        if not self.camera:
            return None
        
        try:
            print(f"Trying to save: {folder}/{name}")
            cam_file = self.camera.file_get(folder, name, gp.GP_FILE_TYPE_NORMAL, self.context)
            
            extension = Path(name).suffix
            new_name = f"{base_name}_{suffix}{extension}"
            target = target_folder / new_name
            
            cam_file.save(str(target))
            print(f"Saved → {target}")
            del cam_file
            return target
        except gp.GPhoto2Error as e:
            print(f"Download error {name}: {e} (code {e.code})")
            return None
        except Exception as e:
            print(f"Unexpected error {name}: {e}")
            return None

    def _save_scan_log_txt(self, base_name):
        """Creates a text file with backlight settings for each frame"""
        log_path = self.scan_folder / f"{base_name}.txt"
        
        lines = []
        for i, color_mode in enumerate(self.scan_sequence, 1):
            if color_mode == "Off":
                brightness_str = ""
            elif color_mode == "Custom":
                r = self.config["custom_brightness"]["R"]
                g = self.config["custom_brightness"]["G"]
                b = self.config["custom_brightness"]["B"]
                brightness_str = f"{r}% {g}% {b}%"
            else:
                # R, G, B, W
                brightness = self.config["brightness"].get(color_mode, 100)
                brightness_str = f"{brightness}%"
                
            lines.append(f"frame {i}: {color_mode} {brightness_str}".rstrip())
        
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print(f"Scan log saved: {log_path}")
        except Exception as e:
            print(f"Failed to save scan log {log_path}: {e}")

    def finish_scan_sequence(self, downloaded_count=0):
        print("Scan sequence finished")
        
        if self.original_color_mode:
            self.set_backlight_color(self.original_color_mode)
        
        if self.was_liveview_active and self.camera:
            self.start_liveview()
        
        self.is_scanning = False
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Start Scan Sequence")
        self.capture_btn.setEnabled(True)
        
        # If files were downloaded → create log
        if downloaded_count > 0 and self.captured_files_info:
            first_folder, first_name = self.captured_files_info[0]
            base_name = Path(first_name).stem
            base_name = re.sub(r'[._][a-z]$', '', base_name, flags=re.IGNORECASE)
            
            self._save_scan_log_txt(base_name)
        
        total_frames = len(self.captured_files_info)
        QMessageBox.information(
            self,
            "Scan Complete",
            f"Scan sequence finished.\n\n"
            f"Successfully downloaded: {downloaded_count}/{total_frames} frames\n"
            f"Images saved to:\n{self.scan_folder}"
        )
        
        self.preview_label.setText("Scan complete")

    def update_scan_button_state(self):
        self.scan_btn.setEnabled(
            self.camera is not None and 
            self.server_running and 
            not self.is_scanning
        )

    # -------------------------------------------------------------------------
    # Backlight methods
    # -------------------------------------------------------------------------
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def update_address_display(self):
        if self.server_running:
            self.status_label.setText("● Running")
            self.status_label.setStyleSheet("color: #0a0; font-weight: bold; font-size: 11pt;")
            self.address_label.setText(self.server_url)
            self.address_label.setStyleSheet("color: #0066cc; font-size: 10pt;")
        else:
            self.status_label.setText("○ Stopped")
            self.status_label.setStyleSheet("color: gray; font-weight: bold; font-size: 11pt;")
            self.address_label.setText(f"Will be: {self.server_url}")
            self.address_label.setStyleSheet("color: gray; font-size: 10pt;")

    def start_server(self):
        if self.server_running:
            return
        self.apply_config()
        try:
            self.server_thread = ServerThread("0.0.0.0", SERVER_PORT, self.config)
            self.server_thread.start()
            self.server_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.update_address_display()
            self.update_scan_button_state()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def stop_server(self):
        if not self.server_running:
            return
        self.server_thread.stop()
        self.server_thread = None
        self.server_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.update_address_display()
        self.update_scan_button_state()

    def on_mode_changed(self, checked):
        if checked:
            self.apply_config()
            
    def on_scan_sequence_changed(self, checked):
        if checked:
            self.apply_config()
            
    def on_dark_frames_changed(self, state):
        self.apply_config()

    def apply_config(self):
        btn = self.color_mode_group.checkedButton()
        if btn:
            self.config["color_mode"] = btn.objectName()

        self.config["rect_width"] = self.width_spin.value()
        self.config["rect_height"] = self.height_spin.value()
        self.config["rect_x"] = self.x_spin.value()
        self.config["rect_y"] = self.y_spin.value()

        self.config["brightness"] = {
            ch: self.brightness_spins[ch].value()
            for ch in "RGBW"
            if ch in self.brightness_spins
        }

        self.config["custom_brightness"] = {
            ch: spin.value() for ch, spin in self.custom_spins.items()
        }
        
        for value, btn in self.sequence_buttons.items():
            if btn.isChecked():
                self.config["scan_sequence"] = value
                break
                
        self.config["dark_frames"] = self.dark_frames_check.isChecked()

        if self.server_running and self.server_thread:
            self.server_thread.update_config(self.config)

    def closeEvent(self, event):
        print("Closing application...")
        self.disconnect_camera()

        self.apply_config()
        ConfigManager.save(self.config)
        if self.server_running:
            self.stop_server()

        super().closeEvent(event)


# =============================================================================
# Application launch
# =============================================================================
if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: QApplication.quit())
    app = QApplication(sys.argv)
    window = CombinedWindow()
    window.show()
    print("Film Scanner application started")
    sys.exit(app.exec())
