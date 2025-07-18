import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np

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
        self.crop_var = tk.StringVar(value="original")
        crop_ratios = {
            "Kırpma Yok (Orijinal)": "original", "Manşet (21:9)": "21:9",
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
        self.width_entry.grid(row=0, column=1)
        tk.Label(self.custom_frame, text="Yükseklik:").grid(row=0, column=2)
        self.height_entry = tk.Entry(self.custom_frame, width=7)
        self.height_entry.grid(row=0, column=3)

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
        self.scale_w = self.original_w / self.original_preview_img.width
        self.scale_h = self.original_h / self.original_preview_img.height

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
        
        aspect_ratio = w / h
        
        sizes = {"Orijinal": "original"}
        if w > 854: sizes[f"Küçük ({854}x{int(854/aspect_ratio)})"] = "small"
        if w > 1280: sizes[f"Orta ({1280}x{int(1280/aspect_ratio)})"] = "medium"
        if w > 1920: sizes[f"Büyük ({1920}x{int(1920/aspect_ratio)})"] = "large"
        
        for text, value in sizes.items():
            tk.Radiobutton(self.size_buttons_frame, text=text, variable=self.size_var,
                          value=value, command=self.toggle_custom_size_entries).pack(anchor="w")
        
        if "medium" in [v for k,v in sizes.items()]:
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

    def on_drag(self, event):
        if not self.dragging or self.crop_var.get() == "original": return
        dx = event.x - self.last_drag_x
        dy = event.y - self.last_drag_y
        self.crop_x_offset_preview += dx
        self.crop_y_offset_preview += dy
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
                new_h = h; new_w = int(h * target_ratio)
            else:
                new_w = w; new_h = int(w / target_ratio)
            
            crop_x = int(self.crop_x_offset_preview * self.scale_w)
            crop_y = int(self.crop_y_offset_preview * self.scale_h)
            crop_x = max(0, min(crop_x, w - new_w))
            crop_y = max(0, min(crop_y, h - new_h))
            final_image = final_image[crop_y:crop_y+new_h, crop_x:crop_x+new_w]

        size_mode = self.size_var.get()
        if size_mode != "original":
            h, w = final_image.shape[:2]
            aspect_ratio = w / h
            
            target_w, target_h = 0, 0
            if size_mode == "small": target_w = 854
            elif size_mode == "medium": target_w = 1280
            elif size_mode == "large": target_w = 1920
            elif size_mode == "custom":
                try:
                    target_w = int(self.width_entry.get())
                    target_h = int(self.height_entry.get())
                except ValueError:
                    messagebox.showerror("Hata", "Özel boyut için geçerli sayılar girin.", parent=self.top)
                    return
            
            if target_h == 0:
                target_h = int(target_w / aspect_ratio)

            final_image = cv2.resize(final_image, (target_w, target_h), interpolation=cv2.INTER_AREA)

        filepath = filedialog.asksaveasfilename(
            defaultextension=".jpg", initialfile="islenmis_gorsel.jpg",
            filetypes=[("JPG file", "*.jpg"), ("PNG file", "*.png"), ("BMP file", "*.bmp")]
        )
        if not filepath: return
        
        try:
            if filepath.lower().endswith(('.jpg', '.jpeg')):
                cv2.imwrite(filepath, final_image, [cv2.IMWRITE_JPEG_QUALITY, self.quality_scale.get()])
            else:
                cv2.imwrite(filepath, final_image)
            messagebox.showinfo("Başarılı", f"Fotoğraf başarıyla kaydedildi:\n{filepath}", parent=self.top)
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Kaydetme Hatası", f"Bir hata oluştu: {e}", parent=self.top)


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
        
        self.cv_image = None
        self.tk_image = None
        self.selection_rect = None
        self.start_x, self.start_y = 0, 0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.display_image_w = 1
        self.display_image_h = 1

        self.canvas = tk.Canvas(root, cursor="cross", bg='gray20')
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        btn_frame = tk.Frame(root)
        btn_frame.pack(fill="x", side="bottom", pady=5)
        
        self.btn_open = tk.Button(btn_frame, text="Fotoğraf Aç", command=self.open_image)
        self.btn_open.pack(side="left", padx=10, pady=5)
        
        self.effect_type = tk.StringVar(value="blur")
        effect_frame = tk.LabelFrame(btn_frame, text="Efekt")
        effect_frame.pack(side="left", padx=5, pady=5)
        tk.Radiobutton(effect_frame, text="Blur", variable=self.effect_type, value="blur").pack(side="left")
        tk.Radiobutton(effect_frame, text="Pixel", variable=self.effect_type, value="pixel").pack(side="left")

        self.blur_scale = tk.Scale(btn_frame, from_=3, to=99, orient="horizontal", label="Blur Şiddeti", resolution=2, length=150)
        self.blur_scale.set(19)
        self.blur_scale.pack(side="left", padx=5, pady=5)

        self.pixel_scale = tk.Scale(btn_frame, from_=2, to=50, orient="horizontal", label="Pixel Boyutu", length=150)
        self.pixel_scale.set(7)
        self.pixel_scale.pack(side="left", padx=5, pady=5)
        
        self.selection_type = tk.StringVar(value="oval")
        selection_frame = tk.LabelFrame(btn_frame, text="Seçim Şekli")
        selection_frame.pack(side="left", padx=5, pady=5)
        tk.Radiobutton(selection_frame, text="Kare", variable=self.selection_type, value="rectangle").pack(side="left")
        tk.Radiobutton(selection_frame, text="Yuvarlak", variable=self.selection_type, value="oval").pack(side="left")

        right_btn_frame = tk.Frame(btn_frame)
        right_btn_frame.pack(side="right", padx=10)
        self.btn_save = tk.Button(right_btn_frame, text="Kaydet...", command=self.show_save_options, state="disabled")
        self.btn_save.pack(fill="x")
        self.btn_undo = tk.Button(right_btn_frame, text="Geri Al (Ctrl+Z)", command=self.undo, state="disabled")
        self.btn_undo.pack(fill="x", pady=5)

        self.history = []
        self.current_step = -1

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.root.bind('<Configure>', self.on_window_resize)
        self.root.bind('<Control-z>', self.undo)

    def add_to_history(self, image_state):
        if self.current_step < len(self.history) - 1:
            self.history = self.history[:self.current_step + 1]
        self.history.append(image_state)
        self.current_step += 1
        self.btn_undo.config(state="normal")
    
    def undo(self, event=None):
        if self.current_step > 0:
            self.current_step -= 1
            self.cv_image = self.history[self.current_step].copy()
            self.update_display_image()
            if self.current_step == 0:
                self.btn_undo.config(state="disabled")

    def open_image(self):
    filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")])
    if not filepath: return
    
    try:
        # PIL ile okuma deneyin (daha çok dosya formatını destekler)
        pil_image = Image.open(filepath)
        img_array = np.array(pil_image)
        
        # RGB ise BGR'ye dönüştürün (OpenCV için)
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            self.cv_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            # Gri tonlamalı veya RGBA için
            self.cv_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
        self.history = []
        self.current_step = -1
        self.add_to_history(self.cv_image.copy())
        self.update_display_image()
        self.btn_save.config(state="normal")
    except Exception as e:
        messagebox.showerror("Hata", f"Resim açılırken hata oluştu: {str(e)}")
        
    def on_window_resize(self, event=None):
        if self.cv_image is not None:
            self.update_display_image()
            
    def update_display_image(self):
        image_rgb = cv2.cvtColor(self.cv_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        img_ratio = pil_image.width / pil_image.height
        canvas_ratio = canvas_width / canvas_height
        
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
        if self.cv_image is not None:
            end_x, end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            if self.selection_rect: self.canvas.delete(self.selection_rect); self.selection_rect = None
            self.apply_effect_to_selection(self.start_x, self.start_y, end_x, end_y)
            
    def apply_pixelate(self, img, pixel_size):
        h, w = img.shape[:2]
        if w < pixel_size or h < pixel_size: return img
        temp = cv2.resize(img, (w // pixel_size, h // pixel_size), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)

    def apply_effect_to_selection(self, start_x, start_y, end_x, end_y):
        x1_on_img = min(start_x, end_x) - self.image_offset_x
        y1_on_img = min(start_y, end_y) - self.image_offset_y
        x2_on_img = max(start_x, end_x) - self.image_offset_x
        y2_on_img = max(start_y, end_y) - self.image_offset_y
        
        x1_on_img = max(0, x1_on_img)
        y1_on_img = max(0, y1_on_img)
        x2_on_img = min(self.display_image_w, x2_on_img)
        y2_on_img = min(self.display_image_h, y2_on_img)

        if (x2_on_img - x1_on_img) <= 0 or (y2_on_img - y1_on_img) <= 0: return

        original_h, original_w = self.cv_image.shape[:2]
        w_ratio = original_w / self.display_image_w
        h_ratio = original_h / self.display_image_h
        
        x1 = int(x1_on_img * w_ratio)
        x2 = int(x2_on_img * w_ratio)
        y1 = int(y1_on_img * h_ratio)
        y2 = int(y2_on_img * h_ratio)

        image_copy = self.cv_image.copy()
        roi_original = image_copy[y1:y2, x1:x2]
        
        if roi_original.size == 0: return
        
        if self.effect_type.get() == "blur":
            k = self.blur_scale.get(); k = k if k % 2 == 1 else k + 1
            processed_roi = cv2.GaussianBlur(roi_original, (k, k), 0)
        else:
            processed_roi = self.apply_pixelate(roi_original, self.pixel_scale.get())

        if self.selection_type.get() == "oval":
            mask = np.zeros(roi_original.shape[:2], dtype=np.uint8)
            cv2.ellipse(mask, (roi_original.shape[1]//2, roi_original.shape[0]//2),
                        (roi_original.shape[1]//2, roi_original.shape[0]//2), 0, 0, 360, 255, -1)
            final_roi = np.where(mask[:, :, np.newaxis] == 255, processed_roi, roi_original)
        else:
            final_roi = processed_roi
            
        image_copy[y1:y2, x1:x2] = final_roi
        self.cv_image = image_copy
        self.update_display_image()
        self.add_to_history(self.cv_image.copy())

    def show_save_options(self):
        if self.cv_image is not None:
            SaveOptionsDialog(self.root, self.cv_image)

# ==============================================================================
# BÖLÜM 3: UYGULAMAYI BAŞLATMA
# ==============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToolApp(root)
    root.mainloop()
