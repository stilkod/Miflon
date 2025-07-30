import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFont
import cv2
import numpy as np
import os
import json # YENİ: Ayarları kaydetmek/yüklemek için eklendi

# YENİ: Yapılandırma dosyasının adı
CONFIG_FILE = "miflon_config.json"


# ==============================================================================
# BÖLÜM 1: KAYDETME, KIRPMA VE YENİDEN BOYUTLANDIRMA DİYALOG PENCERESİ
# ==============================================================================
class SaveOptionsDialog:
    def __init__(self, parent, image_to_save):
        self.top = tk.Toplevel(parent)
        self.top.title("Kaydet, Kırp ve Yeniden Boyutlandır")
        self.top.transient(parent)
        self.top.grab_set()

        self.image_to_save = image_to_save
        self.original_h, self.original_w = self.image_to_save.shape[:2]

        # --- Değişkenler ---
        self.crop_x_offset_preview = 0
        self.crop_y_offset_preview = 0
        self.dragging = False
        self.last_drag_x = 0
        self.last_drag_y = 0

        # --- Arayüz Elemanları ---
        main_frame = tk.Frame(self.top, padx=15, pady=15)
        main_frame.pack(expand=True, fill="both")

        left_panel = tk.Frame(main_frame)
        left_panel.pack(side="left", fill="y", padx=(0, 15))
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side="left", fill="both", expand=True)

        # --- Sol Panel (Ayarlar) ---
        self.crop_frame = tk.LabelFrame(left_panel, text="1. Kırpma Oranı Seç", padx=10, pady=10)
        self.crop_frame.pack(fill="x", pady=(0, 10))
        self.crop_var = tk.StringVar(value="16:9")
        crop_ratios = {
            "Kırpma Yok (Orjinal)": "original", "Manşet (21:9)": "21:9",
            "Galeri (16:9)": "16:9", "Klasik (4:3)": "4:3", "Kare (1:1)": "1:1"
        }
        for text, value in crop_ratios.items():
            tk.Radiobutton(self.crop_frame, text=text, variable=self.crop_var,
                          value=value, command=self.on_crop_change).pack(anchor="w")

        self.size_frame = tk.LabelFrame(left_panel, text="2. Yeniden Boyutlandır", padx=10, pady=10)
        self.size_frame.pack(fill="x", pady=10)
        self.size_var = tk.StringVar(value="original")
        self.size_buttons_frame = tk.Frame(self.size_frame)
        self.size_buttons_frame.pack(fill="x")

        tk.Radiobutton(self.size_buttons_frame, text="Özel Boyut:", variable=self.size_var,
                      value="custom", command=self.toggle_custom_size_entries).pack(anchor="w")
        self.custom_frame = tk.Frame(self.size_frame)
        self.custom_frame.pack(fill="x", padx=20)
        tk.Label(self.custom_frame, text="Genişlik:").grid(row=0, column=0)
        self.width_entry = tk.Entry(self.custom_frame, width=7)
        self.width_entry.grid(row=0, column=1, padx=2)
        tk.Label(self.custom_frame, text="Yükseklik:").grid(row=0, column=2, padx=(5,0))
        self.height_entry = tk.Entry(self.custom_frame, width=7)
        self.height_entry.grid(row=0, column=3, padx=2)

        self.quality_frame = tk.LabelFrame(left_panel, text="3. JPG Kalitesi", padx=10, pady=10)
        self.quality_frame.pack(fill="x", pady=10)
        self.quality_scale = tk.Scale(self.quality_frame, from_=0, to=100, orient="horizontal", label="Kalite", length=200)
        self.quality_scale.set(95)
        self.quality_scale.pack(fill="x")
        
        tk.Button(left_panel, text="Kaydet", command=self.apply_and_save, bg="#4CAF50", fg="white", height=2).pack(fill="x", side="bottom", pady=5)
        tk.Button(left_panel, text="İptal", command=self.top.destroy).pack(fill="x", side="bottom")

        # --- Sağ Panel (Önizleme) ---
        self.preview_canvas = tk.Canvas(right_panel, bg='gray20', cursor="fleur")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<ButtonPress-1>", self.start_drag)
        self.preview_canvas.bind("<B1-Motion>", self.on_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self.stop_drag)

        self.prepare_preview_image()
        self.on_crop_change()

    def prepare_preview_image(self):
        preview = cv2.cvtColor(self.image_to_save, cv2.COLOR_BGR2RGB)
        preview = Image.fromarray(preview)
        preview.thumbnail((500, 400))
        self.original_preview_img = preview
        self.scale_w = self.original_w / self.original_preview_img.width if self.original_preview_img.width > 0 else 1
        self.scale_h = self.original_h / self.original_preview_img.height if self.original_preview_img.height > 0 else 1

    def on_crop_change(self):
        self.crop_x_offset_preview = 0
        self.crop_y_offset_preview = 0
        self.update_preview()
        self.update_size_options()
        self.toggle_custom_size_entries()

    def update_preview(self):
        preview_copy = self.original_preview_img.copy()
        pw, ph = preview_copy.size
        
        overlay = Image.new('RGBA', (pw, ph), (0, 0, 0, 128))

        if self.crop_var.get() != "original":
            target_ratio = eval(self.crop_var.get().replace(':', '/'))
            if pw / ph > target_ratio:
                crop_h = ph
                crop_w = int(crop_h * target_ratio)
                max_offset = pw - crop_w
                self.crop_x_offset_preview = max(0, min(self.crop_x_offset_preview, max_offset))
                overlay.paste((0, 0, 0, 0), (int(self.crop_x_offset_preview), 0, int(self.crop_x_offset_preview + crop_w), crop_h))
            else:
                crop_w = pw
                crop_h = int(crop_w / target_ratio)
                max_offset = ph - crop_h
                self.crop_y_offset_preview = max(0, min(self.crop_y_offset_preview, max_offset))
                overlay.paste((0, 0, 0, 0), (0, int(self.crop_y_offset_preview), crop_w, int(self.crop_y_offset_preview + crop_h)))
        
        preview_copy.paste(overlay, (0, 0), overlay)
        
        self.tk_preview_img = ImageTk.PhotoImage(preview_copy)
        self.preview_canvas.delete("all")
        self.preview_canvas.config(width=pw, height=ph)
        self.preview_canvas.create_image(0, 0, anchor="nw", image=self.tk_preview_img)

    def update_size_options(self):
        for widget in self.size_buttons_frame.winfo_children():
            if isinstance(widget, tk.Radiobutton) and widget.cget("value") != "custom":
                widget.destroy()

        w, h = self.original_w, self.original_h
        if self.crop_var.get() != "original":
            target_ratio = eval(self.crop_var.get().replace(':', '/'))
            if w/h > target_ratio:
                w = int(h * target_ratio)
            else:
                h = int(w / target_ratio)
        
        aspect_ratio = w / h if h != 0 else 1.0
        
        sizes = {"Orjinal": "original"}
        if w > 854: sizes[f"Küçük ({854}x{int(854/aspect_ratio)})"] = "small"
        if w > 1280: sizes[f"Orta ({1280}x{int(1280/aspect_ratio)})"] = "medium"
        if w > 1920: sizes[f"Büyük ({1920}x{int(1920/aspect_ratio)})"] = "large"
        
        for text, value in reversed(list(sizes.items())):
            rb = tk.Radiobutton(self.size_buttons_frame, text=text, variable=self.size_var,
                          value=value, command=self.toggle_custom_size_entries)
            rb.pack(anchor="w")
        
        if "medium" in sizes.values():
            self.size_var.set("medium")
        else:
            self.size_var.set("original")

    def toggle_custom_size_entries(self):
        state = 'normal' if self.size_var.get() == "custom" else 'disabled'
        self.width_entry.config(state=state)
        self.height_entry.config(state=state)

    def start_drag(self, event):
        self.dragging = True
        self.last_drag_x = event.x
        self.last_drag_y = event.y

    # İYİLEŞTİRME: Sürükleme sınırları anlık olarak kontrol ediliyor.
    def on_drag(self, event):
        if not self.dragging or self.crop_var.get() == "original": return
        
        dx = event.x - self.last_drag_x
        dy = event.y - self.last_drag_y
        pw, ph = self.original_preview_img.size
        target_ratio = eval(self.crop_var.get().replace(':', '/'))
        
        if pw / ph > target_ratio:
            crop_h = ph
            crop_w = int(crop_h * target_ratio)
            max_offset_x = pw - crop_w
            new_x = self.crop_x_offset_preview + dx
            self.crop_x_offset_preview = max(0, min(new_x, max_offset_x))
        else:
            crop_w = pw
            crop_h = int(crop_w / target_ratio)
            max_offset_y = ph - crop_h
            new_y = self.crop_y_offset_preview + dy
            self.crop_y_offset_preview = max(0, min(new_y, max_offset_y))

        self.last_drag_x = event.x
        self.last_drag_y = event.y
        self.update_preview()

    def stop_drag(self, event):
        self.dragging = False

    def apply_and_save(self):
        final_image = self.image_to_save.copy()
        if self.crop_var.get() != "original":
            h, w = final_image.shape[:2]
            target_ratio = eval(self.crop_var.get().replace(':', '/'))
            if w/h > target_ratio:
                new_h, new_w = h, int(h * target_ratio)
            else:
                new_w, new_h = w, int(w / target_ratio)
            crop_x = int(self.crop_x_offset_preview * self.scale_w)
            crop_y = int(self.crop_y_offset_preview * self.scale_h)
            crop_x = max(0, min(crop_x, w - new_w))
            crop_y = max(0, min(crop_y, h - new_h))
            final_image = final_image[crop_y:crop_y+new_h, crop_x:crop_x+new_w]

        size_mode = self.size_var.get()
        if size_mode != "original":
            h, w = final_image.shape[:2]
            aspect_ratio = w / h if h != 0 else 1.0
            
            target_w, target_h = 0, 0
            if size_mode == "small": target_w = 854
            elif size_mode == "medium": target_w = 1280
            elif size_mode == "large": target_w = 1920
            
            # HATA DÜZELTMESİ: Özel boyut için en-boy oranı koruma mantığı
            elif size_mode == "custom":
                try:
                    w_entry, h_entry = self.width_entry.get().strip(), self.height_entry.get().strip()
                    if w_entry and h_entry:
                        target_w, target_h = int(w_entry), int(h_entry)
                    elif w_entry:
                        target_w = int(w_entry)
                        target_h = int(target_w / aspect_ratio) if aspect_ratio > 0 else 0
                    elif h_entry:
                        target_h = int(h_entry)
                        target_w = int(target_h * aspect_ratio)
                    else:
                        messagebox.showerror("Hata", "Özel boyut için en az bir değer girmelisiniz.", parent=self.top)
                        return
                except ValueError:
                    messagebox.showerror("Hata", "Özel boyut için geçerli sayılar girin.", parent=self.top)
                    return
            
            if target_w != 0 and target_h == 0:
                target_h = int(target_w / aspect_ratio) if aspect_ratio > 0 else 0

            if target_w > 0 and target_h > 0:
                final_image = cv2.resize(final_image, (target_w, target_h), interpolation=cv2.INTER_AREA)

        # Dosya kaydetme diyaloğu... (devamı aynı)
        original_filepath = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPG file", "*.jpg"), ("PNG file", "*.png"), ("BMP file", "*.bmp")]
        )
        if not original_filepath: return
        
        directory, filename_ext = os.path.split(original_filepath)
        filename, ext = os.path.splitext(filename_ext)

        modifications = []
        crop_names = {"21:9": "manset", "16:9": "galeri", "4:3": "klasik", "1:1": "kare"}
        if self.crop_var.get() != "original":
            modifications.append(crop_names.get(self.crop_var.get(), self.crop_var.get()))
        if self.size_var.get() != "original":
            modifications.append(self.size_var.get())

        new_filename = filename + ("_" + "_".join(modifications) if modifications else "")
        filepath = os.path.join(directory, new_filename + ext)
        
        try:
            if ext.lower() in ('.jpg', '.jpeg'):
                cv2.imwrite(filepath, final_image, [cv2.IMWRITE_JPEG_QUALITY, self.quality_scale.get()])
            else:
                cv2.imwrite(filepath, final_image)
            
            messagebox.showinfo("Başarılı", f"Fotoğraf başarıyla kaydedildi:\n{os.path.normpath(filepath)}", parent=self.top)
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Kaydetme Hatası", f"Bir hata oluştu: {e}", parent=self.top)


# ==============================================================================
# BÖLÜM 1.5: FİLİGRAN EKLEME DİYALOG PENCERESİ
# (Bu sınıf önceki yanıttaki haliyle doğru ve değiştirilmedi)
# ==============================================================================
class WatermarkDialog:
    # ... Önceki yanıtta verilen WatermarkDialog sınıfının kodu burada yer almalı ...
    def __init__(self, parent, cv_image):
        self.top = tk.Toplevel(parent)
        self.top.title("Filigran Ekle")
        self.top.transient(parent)
        self.top.grab_set()
        self.base_image_pil = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGBA))
        self.result_image = None
        main_frame = tk.Frame(self.top, padx=15, pady=15)
        main_frame.pack(expand=True, fill="both")
        self.watermark_type = tk.StringVar(value="text")
        type_frame = tk.LabelFrame(main_frame, text="1. Filigran Türü", padx=10, pady=10)
        type_frame.pack(fill="x", pady=(0, 10))
        tk.Radiobutton(type_frame, text="Metin Filigranı", variable=self.watermark_type, value="text", command=self.toggle_options).pack(anchor="w")
        tk.Radiobutton(type_frame, text="Logo (Resim) Filigranı", variable=self.watermark_type, value="logo", command=self.toggle_options).pack(anchor="w")
        self.text_frame = tk.LabelFrame(main_frame, text="2. Metin Ayarları", padx=10, pady=10)
        self.text_frame.pack(fill="x", pady=5)
        tk.Label(self.text_frame, text="Metin:").grid(row=0, column=0, sticky="w", pady=2)
        self.text_entry = tk.Entry(self.text_frame, width=30)
        self.text_entry.grid(row=0, column=1, columnspan=2, sticky="ew")
        self.text_entry.insert(0, "* KVKK gereği bazı yüzler bulanıklaştırılmıştır.")
        tk.Label(self.text_frame, text="Yazı Boyutu:").grid(row=1, column=0, sticky="w", pady=2)
        self.font_size_entry = tk.Entry(self.text_frame, width=5)
        self.font_size_entry.grid(row=1, column=1, sticky="w")
        self.font_size_entry.insert(0, "12")
        tk.Label(self.text_frame, text="Renk:").grid(row=2, column=0, sticky="w", pady=2)
        self.color_button = tk.Button(self.text_frame, text="Renk Seç", command=self.choose_color)
        self.color_button.grid(row=2, column=1, sticky="w")
        self.text_color = (255, 255, 255)
        self.logo_frame = tk.LabelFrame(main_frame, text="2. Logo Ayarları", padx=10, pady=10)
        self.logo_path_var = tk.StringVar()
        tk.Label(self.logo_frame, text="Logo Dosyası:").grid(row=0, column=0, sticky="w")
        tk.Entry(self.logo_frame, textvariable=self.logo_path_var, state="readonly", width=30).grid(row=0, column=1, sticky="ew")
        tk.Button(self.logo_frame, text="...", command=self.browse_logo).grid(row=0, column=2, padx=5)
        tk.Label(self.logo_frame, text="Boyut (%):").grid(row=1, column=0, sticky="w", pady=5)
        self.logo_size_scale = tk.Scale(self.logo_frame, from_=1, to=100, orient="horizontal", length=200)
        self.logo_size_scale.set(10)
        self.logo_size_scale.grid(row=1, column=1, columnspan=2, sticky="ew")
        common_frame = tk.LabelFrame(main_frame, text="3. Ortak Ayarlar", padx=10, pady=10)
        common_frame.pack(fill="x", pady=5)
        tk.Label(common_frame, text="Konum:").grid(row=0, column=0, sticky="w")
        self.position_var = tk.StringVar(value="bottom_right")
        positions = {"Sağ Alt": "bottom_right", "Sol Alt": "bottom_left", "Sağ Üst": "top_right", "Sol Üst": "top_left", "Orta": "center"}
        pos_col = 1
        for text, value in positions.items():
            tk.Radiobutton(common_frame, text=text, variable=self.position_var, value=value).grid(row=0, column=pos_col, sticky="w")
            pos_col += 1
        tk.Label(common_frame, text="Şeffaflık (%):").grid(row=1, column=0, sticky="w", pady=5)
        self.opacity_scale = tk.Scale(common_frame, from_=0, to=100, orient="horizontal", length=300)
        self.opacity_scale.set(70)
        self.opacity_scale.grid(row=1, column=1, columnspan=len(positions), sticky="ew")
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        tk.Button(button_frame, text="Uygula", command=self.apply, bg="#4CAF50", fg="white").pack(side="right", padx=5)
        tk.Button(button_frame, text="İptal", command=self.top.destroy).pack(side="right")
        self.toggle_options()
    def toggle_options(self):
        if self.watermark_type.get() == "text":
            self.logo_frame.pack_forget()
            self.text_frame.pack(fill="x", pady=5)
        else:
            self.text_frame.pack_forget()
            self.logo_frame.pack(fill="x", pady=5)
    def choose_color(self):
        color_code = colorchooser.askcolor(title="Metin Rengi Seçin")
        if color_code and color_code[0]: self.text_color = tuple(int(c) for c in color_code[0])
    def browse_logo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if path: self.logo_path_var.set(path)
    def apply(self):
        base_image = self.base_image_pil.copy()
        watermark_obj, ww, wh = None, 0, 0
        if self.watermark_type.get() == "logo":
            logo_path = self.logo_path_var.get()
            if not logo_path: return messagebox.showerror("Hata", "Lütfen bir logo dosyası seçin.", parent=self.top)
            try: logo = Image.open(logo_path).convert("RGBA")
            except Exception as e: return messagebox.showerror("Hata", f"Logo açılamadı: {e}", parent=self.top)
            size_percent = self.logo_size_scale.get()
            target_width = int(base_image.width * (size_percent / 100))
            ratio = target_width / logo.width
            target_height = int(logo.height * ratio)
            logo = logo.resize((target_width, target_height), Image.Resampling.LANCZOS)
            logo_data = logo.getdata()
            new_data = []
            opacity_percent = self.opacity_scale.get() / 100
            for item in logo_data:
                new_alpha = int(item[3] * opacity_percent)
                new_data.append((item[0], item[1], item[2], new_alpha))
            logo.putdata(new_data)
            watermark_obj = logo
            ww, wh = watermark_obj.size
        else:
            text = self.text_entry.get()
            if not text: return messagebox.showerror("Hata", "Lütfen filigran metnini girin.", parent=self.top)
            try: font_size = int(self.font_size_entry.get())
            except ValueError: return messagebox.showerror("Hata", "Yazı boyutu geçerli bir sayı olmalı.", parent=self.top)
            try: font = ImageFont.truetype("arial.ttf", font_size)
            except IOError: font = ImageFont.load_default()
            draw = ImageDraw.Draw(base_image)
            _, _, ww, wh = draw.textbbox((0, 0), text, font=font)
            opacity = int(255 * (self.opacity_scale.get() / 100))
            final_text_color = self.text_color + (opacity,)
            watermark_obj = (text, font, final_text_color)
        if watermark_obj is None: return
        margin = 10
        pos_choice = self.position_var.get()
        if pos_choice == "top_left": position = (margin, margin)
        elif pos_choice == "top_right": position = (base_image.width - ww - margin, margin)
        elif pos_choice == "bottom_left": position = (margin, base_image.height - wh - margin)
        elif pos_choice == "center": position = ((base_image.width - ww) // 2, (base_image.height - wh) // 2)
        else: position = (base_image.width - ww - margin, base_image.height - wh - margin)
        if self.watermark_type.get() == "logo":
            base_image.paste(watermark_obj, position, mask=watermark_obj)
            final_image_pil = base_image
        else:
            text, font, color = watermark_obj
            txt_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            draw.text(position, text, font=font, fill=color)
            final_image_pil = Image.alpha_composite(base_image, txt_layer)
        final_image_pil = final_image_pil.convert("RGB")
        self.result_image = cv2.cvtColor(np.array(final_image_pil), cv2.COLOR_RGB2BGR)
        self.top.destroy()


# ==============================================================================
# BÖLÜM 2: ANA UYGULAMA PENCERESİ
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
        self.root.minsize(800, 600)
        
        self.cv_image, self.tk_image, self.selection_rect = None, None, None
        self.start_x, self.start_y = 0, 0
        self.image_offset_x, self.image_offset_y = 0, 0
        self.display_image_w, self.display_image_h = 1, 1

        self.canvas = tk.Canvas(root, cursor="cross", bg='gray20')
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", side="bottom", pady=5)
        
        self.btn_open = tk.Button(btn_frame, text="Fotoğraf Aç", command=self.open_image)
        self.btn_open.pack(side="left", padx=10, pady=5)
        
        # DEĞİŞTİRİLDİ: Ayarların kaydedilmesi/yüklenmesi için Tkinter değişkenleri kullanılıyor
        self.effect_type = tk.StringVar(value="blur")
        self.selection_type = tk.StringVar(value="oval")
        self.blur_value = tk.IntVar(value=19)
        self.pixel_value = tk.IntVar(value=7)

        effect_frame = tk.LabelFrame(btn_frame, text="Efekt")
        effect_frame.pack(side="left", padx=5, pady=5)
        tk.Radiobutton(effect_frame, text="Blur", variable=self.effect_type, value="blur").pack(side="left")
        tk.Radiobutton(effect_frame, text="Pixel", variable=self.effect_type, value="pixel").pack(side="left")

        self.blur_scale = tk.Scale(btn_frame, from_=3, to=99, orient="horizontal", label="Blur Şiddeti", resolution=2, length=150, variable=self.blur_value)
        self.blur_scale.pack(side="left", padx=5, pady=5)

        self.pixel_scale = tk.Scale(btn_frame, from_=2, to=50, orient="horizontal", label="Pixel Boyutu", length=150, variable=self.pixel_value)
        self.pixel_scale.pack(side="left", padx=5, pady=5)
        
        selection_frame = tk.LabelFrame(btn_frame, text="Seçim Şekli")
        selection_frame.pack(side="left", padx=5, pady=5)
        tk.Radiobutton(selection_frame, text="Kare", variable=self.selection_type, value="rectangle").pack(side="left")
        tk.Radiobutton(selection_frame, text="Yuvarlak", variable=self.selection_type, value="oval").pack(side="left")
        
        self.btn_watermark = tk.Button(btn_frame, text="Filigran Ekle...", command=self.show_watermark_dialog, state="disabled")
        self.btn_watermark.pack(side="left", padx=10)

        right_btn_frame = tk.Frame(btn_frame)
        right_btn_frame.pack(side="right", padx=10)
        self.btn_save = tk.Button(right_btn_frame, text="Kaydet...", command=self.show_save_options, state="disabled")
        self.btn_save.pack(fill="x")
        self.btn_undo = tk.Button(right_btn_frame, text="Geri Al (Ctrl+Z)", command=self.undo, state="disabled")
        self.btn_undo.pack(fill="x", pady=5)

        self.history, self.current_step = [], -1

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind('<Configure>', self.on_window_resize)
        self.root.bind('<Control-z>', self.undo)

        # YENİ: Ayarları yükle ve kapanırken kaydetme protokolünü ayarla
        self.load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # YENİ: Ayarları yükleme fonksiyonu
    def load_settings(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                settings = json.load(f)
                self.effect_type.set(settings.get("effect_type", "blur"))
                self.selection_type.set(settings.get("selection_type", "oval"))
                self.blur_value.set(settings.get("blur_value", 19))
                self.pixel_value.set(settings.get("pixel_value", 7))
        except (FileNotFoundError, json.JSONDecodeError):
            pass # Dosya yoksa veya bozuksa varsayılan değerler kalır, hata vermeye gerek yok.

    # YENİ: Ayarları kaydetme fonksiyonu
    def save_settings(self):
        settings = {
            "effect_type": self.effect_type.get(),
            "selection_type": self.selection_type.get(),
            "blur_value": self.blur_value.get(),
            "pixel_value": self.pixel_value.get(),
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=4)

    # YENİ: Pencere kapatılırken çağrılacak fonksiyon
    def on_closing(self):
        self.save_settings()
        self.root.destroy()
    
    # ... (Geri kalan ImageToolApp metodları aynı kalacak) ...
    def add_to_history(self, image_state):
        if self.current_step < len(self.history) - 1:
            self.history = self.history[:self.current_step + 1]
        self.history.append(image_state.copy())
        self.current_step += 1
        self.btn_undo.config(state="normal")
    
    def undo(self, event=None):
        if self.current_step > 0:
            self.current_step -= 1
            self.cv_image = self.history[self.current_step].copy()
            self.update_display_image()
            if self.current_step == 0:
                self.btn_undo.config(state="disabled")

    def update_window_title(self, filepath=None):
        base_title = "Miflon - Görsel Araç Seti"
        if filepath:
            self.root.title(f"{os.path.basename(filepath)} - {base_title}")
        else:
            self.root.title(base_title)

    def open_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")])
        if not filepath: return
        try:
            pil_image = Image.open(filepath)
            if pil_image.mode == 'RGBA':
                self.cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGR)
            else:
                self.cv_image = cv2.cvtColor(np.array(pil_image.convert('RGB')), cv2.COLOR_RGB2BGR)
            
            self.update_window_title(filepath)
            self.history = []
            self.current_step = -1
            self.add_to_history(self.cv_image)
            self.update_display_image()
            self.btn_save.config(state="normal")
            self.btn_watermark.config(state="normal")
            self.btn_undo.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Hata", f"Resim açılırken hata oluştu: {str(e)}")
        
    def on_window_resize(self, event=None):
        if self.cv_image is not None:
            self.update_display_image()
            
    def update_display_image(self):
        if self.cv_image is None: return
        image_rgb = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        canvas_width, canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_width < 10 or canvas_height < 10: return
        
        img_ratio = pil_image.width / pil_image.height if pil_image.height > 0 else 1
        canvas_ratio = canvas_width / canvas_height if canvas_height > 0 else 1
        
        if img_ratio > canvas_ratio:
            new_width = canvas_width - 10
            new_height = int(new_width / img_ratio)
        else:
            new_height = canvas_height - 10
            new_width = int(new_height * img_ratio)
        
        resized_pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        self.display_image_w, self.display_image_h = resized_pil_image.size
        self.tk_image = ImageTk.PhotoImage(resized_pil_image)
        
        self.canvas.delete("all")
        self.image_offset_x = (canvas_width - self.display_image_w) // 2
        self.image_offset_y = (canvas_height - self.display_image_h) // 2
        self.canvas.create_image(self.image_offset_x, self.image_offset_y, anchor="nw", image=self.tk_image)

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.selection_rect: self.canvas.delete(self.selection_rect)

    def on_mouse_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.selection_rect: self.canvas.delete(self.selection_rect)
        shape_method = self.canvas.create_oval if self.selection_type.get() == "oval" else self.canvas.create_rectangle
        self.selection_rect = shape_method(self.start_x, self.start_y, cur_x, cur_y, outline='red', width=2)

    def on_button_release(self, event):
        if self.cv_image is not None and self.start_x is not None:
            end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            if self.selection_rect: self.canvas.delete(self.selection_rect); self.selection_rect = None
            self.apply_effect_to_selection(self.start_x, self.start_y, end_x, end_y)
            self.start_x, self.start_y = None, None
            
    def apply_pixelate(self, img, pixel_size):
        h, w = img.shape[:2]
        if w < pixel_size or h < pixel_size or pixel_size <= 0: return img
        temp = cv2.resize(img, (w // pixel_size, h // pixel_size), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)

    def apply_effect_to_selection(self, start_x, start_y, end_x, end_y):
        x1, y1 = min(start_x, end_x) - self.image_offset_x, min(start_y, end_y) - self.image_offset_y
        x2, y2 = max(start_x, end_x) - self.image_offset_x, max(start_y, end_y) - self.image_offset_y
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(self.display_image_w, x2), min(self.display_image_h, y2)
        if (x2 - x1) <= 0 or (y2 - y1) <= 0: return

        h_orig, w_orig = self.cv_image.shape[:2]
        w_ratio = w_orig / self.display_image_w if self.display_image_w > 0 else 1
        h_ratio = h_orig / self.display_image_h if self.display_image_h > 0 else 1
        
        x1_orig, x2_orig = int(x1 * w_ratio), int(x2 * w_ratio)
        y1_orig, y2_orig = int(y1 * h_ratio), int(y2 * h_ratio)
        
        image_copy = self.cv_image.copy()
        roi_original = image_copy[y1_orig:y2_orig, x1_orig:x2_orig]
        if roi_original.size == 0: return
        
        if self.effect_type.get() == "blur":
            k = self.blur_value.get(); k = k if k % 2 == 1 else k + 1
            processed_roi = cv2.GaussianBlur(roi_original, (k, k), 0)
        else:
            processed_roi = self.apply_pixelate(roi_original, self.pixel_value.get())

        if self.selection_type.get() == "oval":
            mask = np.zeros(roi_original.shape[:2], dtype=np.uint8)
            center = (roi_original.shape[1]//2, roi_original.shape[0]//2)
            axes = (roi_original.shape[1]//2, roi_original.shape[0]//2)
            cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
            final_roi = np.where(mask[..., np.newaxis] == 255, processed_roi, roi_original)
        else:
            final_roi = processed_roi
            
        image_copy[y1_orig:y2_orig, x1_orig:x2_orig] = final_roi
        self.cv_image = image_copy
        self.add_to_history(self.cv_image)
        self.update_display_image()

    def show_save_options(self):
        if self.cv_image is not None:
            SaveOptionsDialog(self.root, self.cv_image)

    def show_watermark_dialog(self):
        if self.cv_image is None: return
        dialog = WatermarkDialog(self.root, self.cv_image)
        self.root.wait_window(dialog.top)
        if dialog.result_image is not None:
            self.cv_image = dialog.result_image
            self.add_to_history(self.cv_image)
            self.update_display_image()
            messagebox.showinfo("Başarılı", "Filigran başarıyla uygulandı.")


# ==============================================================================
# BÖLÜM 3: UYGULAMAYI BAŞLATMA
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToolApp(root)
    root.mainloop()