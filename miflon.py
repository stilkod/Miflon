import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np
import os
import json
import re
from pathlib import Path
from datetime import datetime

# Opsiyonel: Drag&Drop
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

# -------------------------------------------------------------
# Yapılandırma (JSON) yardımcıları
# -------------------------------------------------------------
CONFIG_FILE = str(Path.home() / ".miflon_config.json")

def _read_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _deep_update(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v

def _write_config(patch):
    data = _read_config()
    _deep_update(data, patch)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

# -------------------------------------------------------------
# Güvenli kırpma oranı parse (eval yerine)
# -------------------------------------------------------------
def parse_ratio(value: str):
    if value == "original":
        return None
    try:
        a, b = value.split(":")
        a = float(a.strip())
        b = float(b.strip())
        if b == 0:
            return None
        return a / b
    except Exception:
        return None

# -------------------------------------------------------------
# Drag&Drop dosya listesi ayrıştırma
# -------------------------------------------------------------
def parse_dnd_paths(data: str):
    # event.data örnekleri:
    # - Windows: "{C:\path with spaces\file 1.jpg} {C:\other\file2.png}"
    # - *nix: "/home/user/file1.jpg /home/user/file2.png"
    tokens = re.findall(r'\{([^}]*)\}|([^\s]+)', data)
    paths = [t[0] or t[1] for t in tokens]
    # yalnızca resim dosyalarını filtrele
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    return [p for p in paths if os.path.splitext(p)[1].lower() in exts]

# ==============================================================================
# KIRPMA DİYALOĞU (Uygula → Görseli günceller)
# ==============================================================================
class CropDialog:
    def __init__(self, parent, cv_image):
        self.top = tk.Toplevel(parent)
        self.top.title("Kırp")
        self.top.transient(parent)
        self.top.grab_set()

        self.cv_image = cv_image
        self.h, self.w = self.cv_image.shape[:2]

        cfg = _read_config().get("crop", {})
        self.crop_var = tk.StringVar(value=cfg.get("ratio", "16:9"))

        self.crop_x_offset_preview = 0
        self.crop_y_offset_preview = 0
        self.dragging = False
        self.last_drag_x = 0
        self.last_drag_y = 0

        main = tk.Frame(self.top, padx=12, pady=12)
        main.pack(expand=True, fill="both")

        left = tk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 12))
        right = tk.Frame(main)
        right.pack(side="left", expand=True, fill="both")

        lf = tk.LabelFrame(left, text="Kırpma Oranı", padx=8, pady=8)
        lf.pack(fill="x", pady=(0,8))
        crop_ratios = {
            "Kırpma Yok (Orjinal)": "original", "Manşet (21:9)": "21:9",
            "Galeri (16:9)": "16:9", "Klasik (4:3)": "4:3", "Kare (1:1)": "1:1"
        }
        for text, val in crop_ratios.items():
            tk.Radiobutton(lf, text=text, variable=self.crop_var, value=val,
                           command=self.update_preview).pack(anchor="w")

        btns = tk.Frame(left)
        btns.pack(fill="x", pady=(8,0))
        tk.Button(btns, text="Uygula", bg="#4CAF50", fg="white",
                  command=self.apply).pack(fill="x", pady=(0,6))
        tk.Button(btns, text="İptal", command=self.top.destroy).pack(fill="x")

        self.canvas = tk.Canvas(right, bg="gray20", cursor="fleur")
        self.canvas.pack(expand=True, fill="both")
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)

        self.result_image = None

        self._prepare_preview_image()
        self.update_preview()

    def _prepare_preview_image(self):
        preview = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB)
        preview = Image.fromarray(preview)
        preview.thumbnail((800, 550))
        self.preview_img = preview
        self.scale_w = self.w / self.preview_img.width if self.preview_img.width > 0 else 1
        self.scale_h = self.h / self.preview_img.height if self.preview_img.height > 0 else 1

    def start_drag(self, e):
        self.dragging = True
        self.last_drag_x, self.last_drag_y = e.x, e.y

    def on_drag(self, e):
        if not self.dragging:
            return
        ratio = parse_ratio(self.crop_var.get())
        if ratio is None:
            return
        dx, dy = e.x - self.last_drag_x, e.y - self.last_drag_y
        pw, ph = self.preview_img.size

        if pw / ph > ratio:
            crop_h = ph
            crop_w = int(crop_h * ratio)
            max_offset_x = pw - crop_w
            self.crop_x_offset_preview = max(0, min(self.crop_x_offset_preview + dx, max_offset_x))
        else:
            crop_w = pw
            crop_h = int(crop_w / ratio)
            max_offset_y = ph - crop_h
            self.crop_y_offset_preview = max(0, min(self.crop_y_offset_preview + dy, max_offset_y))

        self.last_drag_x, self.last_drag_y = e.x, e.y
        self.update_preview()

    def stop_drag(self, e):
        self.dragging = False

    def update_preview(self):
        base = self.preview_img.copy()
        pw, ph = base.size
        ratio = parse_ratio(self.crop_var.get())

        draw_img = base.convert("RGBA")
        if ratio is not None:
            overlay = Image.new("RGBA", (pw, ph), (0, 0, 0, 140))
            if pw / ph > ratio:
                crop_h = ph
                crop_w = int(crop_h * ratio)
                self.crop_x_offset_preview = max(0, min(self.crop_x_offset_preview, pw - crop_w))
                x0 = int(self.crop_x_offset_preview)
                overlay.paste((0,0,0,0), (x0, 0, x0 + crop_w, crop_h))
            else:
                crop_w = pw
                crop_h = int(crop_w / ratio)
                self.crop_y_offset_preview = max(0, min(self.crop_y_offset_preview, ph - crop_h))
                y0 = int(self.crop_y_offset_preview)
                overlay.paste((0,0,0,0), (0, y0, crop_w, y0 + crop_h))
            draw_img = Image.alpha_composite(draw_img, overlay)

        self.tk_prev = ImageTk.PhotoImage(draw_img.convert("RGB"))
        self.canvas.delete("all")
        self.canvas.config(width=pw, height=ph)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_prev)

    def apply(self):
        ratio = parse_ratio(self.crop_var.get())
        final = self.cv_image.copy()
        if ratio is not None:
            H, W = final.shape[:2]
            if W / H > ratio:
                new_h, new_w = H, int(H * ratio)
            else:
                new_w, new_h = W, int(W / ratio)
            crop_x = int(self.crop_x_offset_preview * self.scale_w)
            crop_y = int(self.crop_y_offset_preview * self.scale_h)
            crop_x = max(0, min(crop_x, W - new_w))
            crop_y = max(0, min(crop_y, H - new_h))
            final = final[crop_y:crop_y+new_h, crop_x:crop_x+new_w]

        _write_config({"crop": {"ratio": self.crop_var.get()}})
        self.result_image = final
        self.top.destroy()

# ==============================================================================
# FİLİGRAN/LOGO AYARLARI DİYALOĞU (Ayarları JSON'a yazar)
# ==============================================================================
class WatermarkSettingsDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Filigran/Logo Ayarları")
        self.top.transient(parent)
        self.top.grab_set()

        cfg = _read_config()
        wm = cfg.get("watermark", {})
        self.enable_text = tk.BooleanVar(value=wm.get("enable_text", True))
        self.enable_logo = tk.BooleanVar(value=wm.get("enable_logo", True))
        self.text = tk.StringVar(value=wm.get("text", "* KVKK gereği bazı yüzler bulanıklaştırılmıştır."))
        self.text_size_percent = tk.IntVar(value=int(wm.get("text_size_percent", 2)))  # %2 varsayılan
        self.opacity = tk.IntVar(value=int(wm.get("opacity", 40)))
        color = wm.get("color", [255, 255, 255])
        self.text_color = (int(color[0]), int(color[1]), int(color[2]))
        self.logo_path = tk.StringVar(value=wm.get("logo_path", ""))
        self.logo_size_percent = tk.IntVar(value=int(wm.get("logo_size_percent", 15)))

        main = tk.Frame(self.top, padx=12, pady=12)
        main.pack(expand=True, fill="both")

        # Metin
        tf = tk.LabelFrame(main, text="Metin (sağ alt)", padx=8, pady=8)
        tf.pack(fill="x", pady=(0,8))
        tk.Checkbutton(tf, text="Metin ekle", variable=self.enable_text).grid(row=0, column=0, sticky="w", pady=2, columnspan=2)
        tk.Label(tf, text="İçerik:").grid(row=1, column=0, sticky="w")
        tk.Entry(tf, textvariable=self.text, width=40).grid(row=1, column=1, sticky="ew", padx=(6,0))
        tk.Label(tf, text="Boyut (% yükseklik):").grid(row=2, column=0, sticky="w", pady=4)
        tk.Scale(tf, from_=1, to=15, orient="horizontal", variable=self.text_size_percent, length=220).grid(row=2, column=1, sticky="w")
        tk.Label(tf, text="Renk:").grid(row=3, column=0, sticky="w")
        tk.Button(tf, text="Renk Seç", command=self.choose_color).grid(row=3, column=1, sticky="w", padx=(6,0))

        # Logo
        lf = tk.LabelFrame(main, text="Logo (merkez)", padx=8, pady=8)
        lf.pack(fill="x", pady=(0,8))
        tk.Checkbutton(lf, text="Logo ekle", variable=self.enable_logo).grid(row=0, column=0, sticky="w", pady=2, columnspan=3)
        tk.Label(lf, text="Dosya:").grid(row=1, column=0, sticky="w")
        tk.Entry(lf, textvariable=self.logo_path, state="readonly", width=35).grid(row=1, column=1, sticky="ew")
        tk.Button(lf, text="...", command=self.browse_logo).grid(row=1, column=2, padx=5)
        tk.Label(lf, text="Boyut (% genişlik):").grid(row=2, column=0, sticky="w", pady=4)
        tk.Scale(lf, from_=1, to=100, orient="horizontal", variable=self.logo_size_percent, length=220).grid(row=2, column=1, sticky="w", columnspan=2)

        # Ortak
        cf = tk.LabelFrame(main, text="Ortak", padx=8, pady=8)
        cf.pack(fill="x", pady=(0,8))
        tk.Label(cf, text="Şeffaflık (%):").grid(row=0, column=0, sticky="w")
        tk.Scale(cf, from_=0, to=100, orient="horizontal", variable=self.opacity, length=220).grid(row=0, column=1, sticky="w")

        # Alt butonlar
        bf = tk.Frame(main)
        bf.pack(fill="x", pady=(8,0))
        tk.Button(bf, text="Kaydet", bg="#4CAF50", fg="white", command=self.save).pack(side="right", padx=5)
        tk.Button(bf, text="İptal", command=self.top.destroy).pack(side="right")

    def choose_color(self):
        c = colorchooser.askcolor(title="Metin Rengi Seçin")
        if c and c[0]:
            self.text_color = tuple(int(v) for v in c[0])

    def browse_logo(self):
        p = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if p:
            self.logo_path.set(p)
            _write_config({"watermark": {"logo_path": p}})  # hemen kaydet

    def save(self):
        patch = {
            "watermark": {
                "enable_text": bool(self.enable_text.get()),
                "enable_logo": bool(self.enable_logo.get()),
                "text": self.text.get().strip(),
                "text_size_percent": int(self.text_size_percent.get()),
                "color": [int(self.text_color[0]), int(self.text_color[1]), int(self.text_color[2])],
                "opacity": int(self.opacity.get()),
                "logo_path": self.logo_path.get(),
                "logo_size_percent": int(self.logo_size_percent.get()),
            }
        }
        _write_config(patch)
        self.top.destroy()

# ==============================================================================
# KAYDET DİYALOĞU (şablon + klasör + format + kalite + önizleme)
# ==============================================================================
class SaveDialog:
    DEFAULT_TEMPLATES = [
        "{name}_miflon",
        "{name}_{date}",
        "{name}_{index:03d}",
        "{name}_{date}_{index:03d}",
        "{name}_{w}x{h}",
        "{name}_wm_{index:02d}",
    ]

    def __init__(self, parent, cv_image, original_path, batch_pos=None, batch_total=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Kaydet")
        self.top.transient(parent)
        self.top.grab_set()

        self.cv_image = cv_image
        self.original_path = original_path
        self.h, self.w = self.cv_image.shape[:2]

        cfg = _read_config().get("save", {})
        self.out_folder = tk.StringVar(value=cfg.get("folder", os.path.dirname(original_path) if original_path else str(Path.home())))
        self.format_var = tk.StringVar(value=cfg.get("format", "JPG"))
        self.jpg_quality = tk.IntVar(value=int(cfg.get("jpg_quality", 95)))
        self.template_var = tk.StringVar(value=cfg.get("template", "{name}_{index:03d}"))
        self.index_var = tk.IntVar(value=int(cfg.get("index", 1)))

        main = tk.Frame(self.top, padx=12, pady=12)
        main.pack(expand=True, fill="both")

        # Üst: klasör + format + kalite
        f1 = tk.Frame(main)
        f1.pack(fill="x", pady=(0,8))
        tk.Label(f1, text="Kayıt Klasörü:").grid(row=0, column=0, sticky="w")
        tk.Entry(f1, textvariable=self.out_folder, width=40).grid(row=0, column=1, sticky="ew", padx=(6,6))
        tk.Button(f1, text="Seç...", command=self.choose_folder).grid(row=0, column=2)
        f1.grid_columnconfigure(1, weight=1)

        f2 = tk.Frame(main)
        f2.pack(fill="x", pady=(0,8))
        tk.Label(f2, text="Format:").pack(side="left")
        ttk.Combobox(f2, textvariable=self.format_var, values=["JPG", "PNG", "BMP"], width=6, state="readonly").pack(side="left", padx=(6,12))
        self.qlab = tk.Label(f2, text="JPG Kalitesi:")
        self.qlab.pack(side="left")
        self.qscale = tk.Scale(f2, from_=50, to=100, orient="horizontal", variable=self.jpg_quality, length=200)
        self.qscale.pack(side="left", padx=(6,0))
        self.format_var.trace_add("write", lambda *a: self.toggle_quality())

        # Şablon
        f3 = tk.LabelFrame(main, text="İsim Şablonu", padx=8, pady=8)
        f3.pack(fill="x", pady=(0,8))
        ttk.Combobox(f3, values=self.DEFAULT_TEMPLATES, textvariable=self.template_var, width=40).grid(row=0, column=0, sticky="ew", columnspan=2)
        tk.Label(f3, text="Index başlangıcı:").grid(row=1, column=0, sticky="w", pady=(6,0))
        tk.Spinbox(f3, from_=1, to=999999, textvariable=self.index_var, width=8).grid(row=1, column=1, sticky="w", pady=(6,0))
        tk.Label(f3, text="Değişkenler: {name}, {index[:0Nd]}, {date}, {time}, {w}, {h}").grid(row=2, column=0, columnspan=2, sticky="w", pady=(6,0))

        # Önizleme
        self.preview_lbl = tk.Label(main, text="", fg="#00AA55")
        self.preview_lbl.pack(fill="x", pady=(4,8))

        # Butonlar
        bf = tk.Frame(main)
        bf.pack(fill="x")
        if batch_pos and batch_total:
            tk.Label(bf, text=f"Fotoğraf: {batch_pos}/{batch_total}").pack(side="left", padx=(0,8))
        tk.Button(bf, text="Kaydet", bg="#4CAF50", fg="white", command=self.save).pack(side="right", padx=5)
        tk.Button(bf, text="İptal", command=self.top.destroy).pack(side="right")

        self.saved = False
        self.toggle_quality()
        self.update_preview()
        self.template_var.trace_add("write", lambda *a: self.update_preview())
        self.index_var.trace_add("write", lambda *a: self.update_preview())
        self.format_var.trace_add("write", lambda *a: self.update_preview())
        self.out_folder.trace_add("write", lambda *a: self.update_preview())

    def toggle_quality(self):
        if self.format_var.get().upper() == "JPG":
            self.qlab.configure(state="normal")
            self.qscale.configure(state="normal")
        else:
            self.qlab.configure(state="disabled")
            self.qscale.configure(state="disabled")

    def choose_folder(self):
        d = filedialog.askdirectory(initialdir=self.out_folder.get() or str(Path.home()))
        if d:
            self.out_folder.set(d)

    def _sanitize(self, name: str):
        # Windows yasak karakterleri temizle
        return re.sub(r'[\\/:*?"<>|]', '_', name)

    def _render_template(self, tpl, name, index, w, h, ext):
        # {index} veya {index:03d} gibi
        def repl(match):
            token = match.group(1)
            fmt = match.group(2)
            if token == "name":
                return name
            elif token == "date":
                return datetime.now().strftime("%Y%m%d")
            elif token == "time":
                return datetime.now().strftime("%H%M%S")
            elif token == "w":
                return str(w)
            elif token == "h":
                return str(h)
            elif token == "ext":
                return ext
            elif token == "index":
                pad = 0
                if fmt:
                    m = re.match(r":0(\d+)d", fmt)
                    if m:
                        pad = int(m.group(1))
                return str(index).zfill(pad) if pad > 0 else str(index)
            return ""
        return re.sub(r"\{(name|date|time|w|h|ext|index)(:[^}]*)?\}", repl, tpl)

    def update_preview(self):
        folder = self.out_folder.get().strip() or str(Path.home())
        ext = self.format_var.get().lower()
        name = "image"
        if self.original_path:
            name = os.path.splitext(os.path.basename(self.original_path))[0]
        try:
            idx = int(self.index_var.get())
        except Exception:
            idx = 1
        filename = self._render_template(self.template_var.get(), name, idx, self.w, self.h, ext)
        filename = self._sanitize(filename) + f".{ext}"
        self.preview_path = os.path.join(folder, filename)
        self.preview_lbl.config(text=f"Örnek: {self.preview_path}")

    def save(self):
        # Ayarları kalıcı yap
        _write_config({
            "save": {
                "folder": self.out_folder.get().strip(),
                "format": self.format_var.get(),
                "jpg_quality": int(self.jpg_quality.get()),
                "template": self.template_var.get(),
                "index": int(self.index_var.get())
            }
        })
        # Kaydet
        out_path = self.preview_path
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        try:
            ext = os.path.splitext(out_path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                cv2.imwrite(out_path, self.cv_image, [cv2.IMWRITE_JPEG_QUALITY, int(self.jpg_quality.get())])
            else:
                cv2.imwrite(out_path, self.cv_image)
            # index +1 ve kalıcı
            new_idx = int(self.index_var.get()) + 1
            _write_config({"save": {"index": new_idx}})
            self.saved = True
            messagebox.showinfo("Kaydedildi", f"Fotoğraf kaydedildi:\n{os.path.normpath(out_path)}", parent=self.top)
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydetme hatası: {e}", parent=self.top)

# ==============================================================================
# ANA UYGULAMA (ID Photos Pro benzeri adım mantığı + DnD + şablonlu kaydet)
# ==============================================================================
class ImageToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Miflon - Görsel Araç Seti")

        screen_width = int(root.winfo_screenwidth() * 0.9)
        screen_height = int(root.winfo_screenheight() * 0.9)
        x_pos = (root.winfo_screenwidth() - screen_width) // 2
        y_pos = (root.winfo_screenheight() - screen_height) // 2
        self.root.geometry(f"{screen_width}x{screen_height}+{x_pos}+{y_pos}")
        self.root.minsize(900, 620)

        # Durum
        self.cv_image, self.tk_image, self.selection_rect = None, None, None
        self.start_x, self.start_y = 0, 0
        self.image_offset_x, self.image_offset_y = 0, 0
        self.display_image_w, self.display_image_h = 1, 1
        self.current_path = None

        # Batch (çoklu dosya)
        self.batch_files = []
        self.batch_index = -1

        # Tuval
        self.canvas = tk.Canvas(root, cursor="cross", bg='gray20')
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)

        # DnD
        if DND_AVAILABLE:
            try:
                self.canvas.drop_target_register(DND_FILES)
                self.canvas.dnd_bind('<<Drop>>', self.on_drop_files)
            except Exception:
                pass

        # Step bar
        step = tk.Frame(root)
        step.pack(fill="x", side="bottom", pady=6)

        self.btn_open = tk.Button(step, text="1) Fotoğraf Aç", command=self.open_images)
        self.btn_open.pack(side="left", padx=8)

        # Efekt/Seçim (2. adım)
        fx_cfg = _read_config().get("app", {})
        self.effect_type = tk.StringVar(value=fx_cfg.get("effect_type", "blur"))
        self.selection_type = tk.StringVar(value=fx_cfg.get("selection_type", "oval"))
        self.blur_value = tk.IntVar(value=int(fx_cfg.get("blur_value", 19)))
        self.pixel_value = tk.IntVar(value=int(fx_cfg.get("pixel_value", 7)))
        self.feather_value = tk.IntVar(value=int(fx_cfg.get("feather_value", 8)))

        fx = tk.LabelFrame(step, text="2) Bulanıklaştırma/Piksel", padx=6, pady=4)
        fx.pack(side="left", padx=6)
        tk.Radiobutton(fx, text="Blur", variable=self.effect_type, value="blur").pack(side="left")
        tk.Radiobutton(fx, text="Pixel", variable=self.effect_type, value="pixel").pack(side="left")
        tk.Scale(fx, from_=3, to=99, orient="horizontal", label="Blur", resolution=2, length=120, variable=self.blur_value).pack(side="left", padx=4)
        tk.Scale(fx, from_=2, to=50, orient="horizontal", label="Pixel", length=120, variable=self.pixel_value).pack(side="left", padx=4)
        tk.Label(fx, text="Seçim:").pack(side="left", padx=(6,0))
        tk.Radiobutton(fx, text="Kare", variable=self.selection_type, value="rectangle").pack(side="left")
        tk.Radiobutton(fx, text="Oval", variable=self.selection_type, value="oval").pack(side="left")
        tk.Scale(fx, from_=0, to=50, orient="horizontal", label="Kenar Yumuşatma", length=140, variable=self.feather_value).pack(side="left", padx=4)

        # 3) Kırp
        self.btn_crop = tk.Button(step, text="3) Kırp...", command=self.open_crop, state="disabled")
        self.btn_crop.pack(side="left", padx=8)

        # 4) Filigran
        self.btn_wm_settings = tk.Button(step, text="4) Filigran Ayarları...", command=self.open_wm_settings, state="disabled")
        self.btn_wm_settings.pack(side="left", padx=4)
        self.btn_apply_wm = tk.Button(step, text="Filigran ve Logo Ekle", command=self.apply_wm_logo_now, state="disabled")
        self.btn_apply_wm.pack(side="left", padx=4)

        # 5) Kaydet
        self.btn_save = tk.Button(step, text="5) Kaydet...", command=self.save_current, state="disabled")
        self.btn_save.pack(side="left", padx=8)

        # Sağ: geri al
        right = tk.Frame(step)
        right.pack(side="right", padx=8)
        self.btn_undo = tk.Button(right, text="Geri Al (Ctrl+Z)", command=self.undo, state="disabled")
        self.btn_undo.pack()

        # Undo
        self.history, self.current_step = [], -1
        self.max_history = 20

        # Olaylar
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind('<Configure>', self.on_window_resize)
        self.root.bind('<Control-z>', self.undo)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ----- Genel ayarlar kaydet -----
    def save_app_settings(self):
        _write_config({
            "app": {
                "effect_type": self.effect_type.get(),
                "selection_type": self.selection_type.get(),
                "blur_value": int(self.blur_value.get()),
                "pixel_value": int(self.pixel_value.get()),
                "feather_value": int(self.feather_value.get()),
            }
        })

    def on_closing(self):
        self.save_app_settings()
        self.root.destroy()

    # ----- Drag & Drop -----
    def on_drop_files(self, event):
        paths = parse_dnd_paths(event.data)
        if not paths:
            return
        self.batch_files = paths
        self.batch_index = 0
        self.load_image_from_path(self.batch_files[self.batch_index])

    # ----- Batch/Fotoğraf yükleme -----
    def open_images(self):
        files = filedialog.askopenfilenames(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")])
        if not files:
            return
        self.batch_files = list(files)
        self.batch_index = 0
        self.load_image_from_path(self.batch_files[self.batch_index])

    def load_image_from_path(self, filepath):
        try:
            pil_image = Image.open(filepath)
            if pil_image.mode == 'RGBA':
                self.cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGR)
            else:
                self.cv_image = cv2.cvtColor(np.array(pil_image.convert('RGB')), cv2.COLOR_RGB2BGR)
            self.current_path = filepath

            self.update_window_title(filepath)
            self.history = []
            self.current_step = -1
            self.add_to_history(self.cv_image)
            self.update_display_image()

            # Adım butonlarını aktif et
            self.btn_crop.config(state="normal")
            self.btn_wm_settings.config(state="normal")
            self.btn_apply_wm.config(state="normal")
            self.btn_save.config(state="normal")
            self.btn_undo.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Hata", f"Resim açılırken hata oluştu: {str(e)}")

    def after_save_flow(self):
        if self.batch_files and 0 <= self.batch_index < len(self.batch_files) - 1:
            self.batch_index += 1
            self.load_image_from_path(self.batch_files[self.batch_index])
            messagebox.showinfo("Sıradaki Fotoğraf", f"Kaydedildi. ({self.batch_index + 1}/{len(self.batch_files)}) sıradaki fotoğraf yüklendi.")
        else:
            self.reset_to_initial_state()
            messagebox.showinfo("Bitti", "Kaydetme tamamlandı. Yeni bir fotoğraf açabilirsiniz.")

    def reset_to_initial_state(self):
        self.cv_image = None
        self.current_path = None
        self.history, self.current_step = [], -1
        self.canvas.delete("all")
        self.update_window_title(None)
        self.btn_crop.config(state="disabled")
        self.btn_wm_settings.config(state="disabled")
        self.btn_apply_wm.config(state="disabled")
        self.btn_save.config(state="disabled")
        self.btn_undo.config(state="disabled")
        self.batch_files = []
        self.batch_index = -1

    # ----- Undo -----
    def add_to_history(self, image_state):
        if self.current_step < len(self.history) - 1:
            self.history = self.history[:self.current_step + 1]
        self.history.append(image_state.copy())
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.current_step = len(self.history) - 1
        self.btn_undo.config(state="normal")

    def undo(self, event=None):
        if self.current_step > 0:
            self.current_step -= 1
            self.cv_image = self.history[self.current_step].copy()
            self.update_display_image()
            if self.current_step == 0:
                self.btn_undo.config(state="disabled")

    # ----- UI yardımcıları -----
    def update_window_title(self, filepath=None):
        base_title = "Miflon - Görsel Araç Seti"
        if filepath:
            self.root.title(f"{os.path.basename(filepath)} - {base_title}")
        else:
            self.root.title(base_title)

    def on_window_resize(self, event=None):
        if self.cv_image is not None:
            self.update_display_image()

    def update_display_image(self):
        if self.cv_image is None:
            return
        image_rgb = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        canvas_width, canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_width < 10 or canvas_height < 10:
            return

        img_ratio = pil_image.width / pil_image.height if pil_image.height > 0 else 1
        canvas_ratio = canvas_width / canvas_height if canvas_height > 0 else 1

        if img_ratio > canvas_ratio:
            new_width = max(1, canvas_width - 10)
            new_height = max(1, int(new_width / img_ratio))
        else:
            new_height = max(1, canvas_height - 10)
            new_width = max(1, int(new_height * img_ratio))

        resized_pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        self.display_image_w, self.display_image_h = resized_pil_image.size
        self.tk_image = ImageTk.PhotoImage(resized_pil_image)

        self.canvas.delete("all")
        self.image_offset_x = (canvas_width - self.display_image_w) // 2
        self.image_offset_y = (canvas_height - self.display_image_h) // 2
        self.canvas.create_image(self.image_offset_x, self.image_offset_y, anchor="nw", image=self.tk_image)

    # ----- Seçim ve efekt (2. adım) -----
    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)

    def on_mouse_drag(self, event):
        if self.cv_image is None:
            return
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        shape_method = self.canvas.create_oval if self.selection_type.get() == "oval" else self.canvas.create_rectangle
        self.selection_rect = shape_method(self.start_x, self.start_y, cur_x, cur_y, outline='red', width=2)

    def on_button_release(self, event):
        if self.cv_image is not None and self.start_x is not None:
            end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
                self.selection_rect = None
            self.apply_effect_to_selection(self.start_x, self.start_y, end_x, end_y)
            self.start_x, self.start_y = None, None
            self.save_app_settings()

    def apply_pixelate(self, img, pixel_size):
        h, w = img.shape[:2]
        if w < pixel_size or h < pixel_size or pixel_size <= 0:
            return img
        small = cv2.resize(img, (max(1, w // pixel_size), max(1, h // pixel_size)), interpolation=cv2.INTER_AREA)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    def apply_effect_to_selection(self, start_x, start_y, end_x, end_y):
        x1, y1 = min(start_x, end_x) - self.image_offset_x, min(start_y, end_y) - self.image_offset_y
        x2, y2 = max(start_x, end_x) - self.image_offset_x, max(start_y, end_y) - self.image_offset_y
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(self.display_image_w, int(x2)), min(self.display_image_h, int(y2))
        if (x2 - x1) < 3 or (y2 - y1) < 3:
            return

        h_orig, w_orig = self.cv_image.shape[:2]
        w_ratio = w_orig / self.display_image_w if self.display_image_w > 0 else 1
        h_ratio = h_orig / self.display_image_h if self.display_image_h > 0 else 1

        x1_orig, x2_orig = int(x1 * w_ratio), int(x2 * w_ratio)
        y1_orig, y2_orig = int(y1 * h_ratio), int(y2 * h_ratio)

        image_copy = self.cv_image.copy()
        roi_original = image_copy[y1_orig:y2_orig, x1_orig:x2_orig]
        if roi_original.size == 0:
            return

        if self.effect_type.get() == "blur":
            k = int(self.blur_value.get()); k = k if k % 2 == 1 else k + 1
            processed_roi = cv2.GaussianBlur(roi_original, (k, k), 0)
        else:
            processed_roi = self.apply_pixelate(roi_original, int(self.pixel_value.get()))

        mask = np.zeros(roi_original.shape[:2], dtype=np.uint8)
        if self.selection_type.get() == "oval":
            center = (roi_original.shape[1] // 2, roi_original.shape[0] // 2)
            axes = (roi_original.shape[1] // 2, roi_original.shape[0] // 2)
            cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
        else:
            mask[:] = 255

        feather = int(self.feather_value.get())
        if feather > 0:
            mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=feather, sigmaY=feather)

        mask_f = (mask.astype(np.float32) / 255.0)[..., None]
        final_roi = (processed_roi.astype(np.float32) * mask_f + roi_original.astype(np.float32) * (1 - mask_f)).astype(np.uint8)

        image_copy[y1_orig:y2_orig, x1_orig:x2_orig] = final_roi
        self.cv_image = image_copy
        self.add_to_history(self.cv_image)
        self.update_display_image()

    # ----- 3) Kırp -----
    def open_crop(self):
        if self.cv_image is None:
            return
        dlg = CropDialog(self.root, self.cv_image)
        self.root.wait_window(dlg.top)
        if dlg.result_image is not None:
            self.cv_image = dlg.result_image
            self.add_to_history(self.cv_image)
            self.update_display_image()
            messagebox.showinfo("Kırpma", "Kırpma uygulandı.")

    # ----- 4) Filigran -----
    def open_wm_settings(self):
        WatermarkSettingsDialog(self.root)

    def _load_font(self, size):
        for fp in ["arial.ttf", "DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"]:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _measure_text(self, draw, text, font):
        try:
            l, t, r, b = draw.textbbox((0, 0), text, font=font)
            return r - l, b - t
        except Exception:
            try:
                return draw.textsize(text, font=font)
            except Exception:
                return len(text) * font.size, font.size

    def apply_wm_logo_now(self):
        if self.cv_image is None:
            return
        cfg = _read_config()
        wm = cfg.get("watermark", {})
        enable_text = wm.get("enable_text", True)
        enable_logo = wm.get("enable_logo", True)
        text = wm.get("text", "* KVKK gereği bazı yüzler bulanıklaştırılmıştır.").strip()
        text_size_pct = int(wm.get("text_size_percent", 2))
        opacity = int(wm.get("opacity", 40))
        color = wm.get("color", [255, 255, 255])
        text_color = (int(color[0]), int(color[1]), int(color[2]))
        logo_path = wm.get("logo_path", "")
        logo_size_pct = int(wm.get("logo_size_percent", 15))

        base = Image.fromarray(cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB)).convert("RGBA")
        w, h = base.size
        layer = Image.new("RGBA", (w, h), (0,0,0,0))

        # Logo merkez
        if enable_logo and logo_path and os.path.isfile(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                target_w = max(1, int(w * (logo_size_pct / 100.0)))
                ratio = target_w / logo.width
                target_h = max(1, int(logo.height * ratio))
                logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
                if opacity < 100:
                    data = np.array(logo)
                    data[..., 3] = (data[..., 3].astype(np.float32) * (opacity/100.0)).astype(np.uint8)
                    logo = Image.fromarray(data, mode="RGBA")
                lw, lh = logo.size
                pos = ((w - lw)//2, (h - lh)//2)
                layer.paste(logo, pos, mask=logo)
            except Exception as e:
                messagebox.showwarning("Logo", f"Logo uygulanamadı: {e}")

        # Metin sağ alt
        if enable_text and text:
            draw = ImageDraw.Draw(layer)
            desired_h = max(8, int(h * (text_size_pct / 100.0)))
            font_size = max(8, desired_h)
            font = self._load_font(font_size)
            tw, th = self._measure_text(draw, text, font)
            max_w = int(w * 0.94)
            if tw > max_w and tw > 0:
                scale = max_w / tw
                font_size = max(8, int(font_size * scale))
                font = self._load_font(font_size)
                tw, th = self._measure_text(draw, text, font)
            col = (text_color[0], text_color[1], text_color[2], int(255 * (opacity/100.0)))
            margin = 12
            pos = (w - tw - margin, h - th - margin)
            draw.text(pos, text, font=font, fill=col)

        final_pil = Image.alpha_composite(base, layer).convert("RGB")
        self.cv_image = cv2.cvtColor(np.array(final_pil), cv2.COLOR_RGB2BGR)
        self.add_to_history(self.cv_image)
        self.update_display_image()
        messagebox.showinfo("Filigran", "Filigran ve logo uygulandı.")

    # ----- 5) Kaydet -----
    def save_current(self):
        if self.cv_image is None:
            return
        dlg = SaveDialog(self.root, self.cv_image, self.current_path,
                         batch_pos=(self.batch_index + 1) if self.batch_index >= 0 else None,
                         batch_total=len(self.batch_files) if self.batch_files else None)
        self.root.wait_window(dlg.top)
        if dlg.saved:
            self.after_save_flow()

# ==============================================================================
# Uygulamayı başlat
# ==============================================================================
if __name__ == "__main__":
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = ImageToolApp(root)
    root.mainloop()