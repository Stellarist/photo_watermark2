import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, font
from tkinter import scrolledtext
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageColor
import threading
import queue

class WatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Watermark Tool - Windows Edition")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Application state
        self.images = []  # Store image path list
        self.current_image_index = 0
        self.watermark_config = {
            'text': 'Watermark Text',
            'font_family': 'Arial',
            'font_size': 48,
            'color': '#FFFFFF',
            'opacity': 80,
            'position': 'bottom-right',
            'rotation': 0,
            'image_path': None,
            'image_scale': 1.0,
            'image_opacity': 80
        }
        self.templates = {}
        self.output_dir = None
        self.preview_image = None
        self.original_image = None
        
        # Create interface
        self.create_widgets()
        self.load_templates()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top toolbar with prominent Export button
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="Preview", command=self.update_preview).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Start Export", command=self.start_export).pack(side=tk.LEFT, padx=(10, 0))
        
        # Left control panel (scrollable)
        left_container = ttk.Frame(main_frame)
        left_container.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.left_canvas = tk.Canvas(left_container, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_container, orient=tk.VERTICAL, command=self.left_canvas.yview)
        self.left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_canvas.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        
        left_panel = ttk.Frame(self.left_canvas)
        self.left_canvas.create_window((0, 0), window=left_panel, anchor=tk.NW)
        
        # Update scrollregion when content changes
        def _on_left_panel_configure(event):
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))
            # Keep a reasonable width for the canvas to avoid horizontal scroll
            self.left_canvas.configure(width=min(420, left_panel.winfo_reqwidth()))
        left_panel.bind("<Configure>", _on_left_panel_configure)
        
        # Enable mouse wheel scrolling when cursor is over the left panel
        def _bind_wheel(event):
            self.left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        def _unbind_wheel(event):
            self.left_canvas.unbind_all("<MouseWheel>")
        def _on_mousewheel(event):
            # On Windows, delta is multiples of 120
            self.left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        left_panel.bind("<Enter>", _bind_wheel)
        left_panel.bind("<Leave>", _unbind_wheel)
        
        # Right preview panel
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.create_file_panel(left_panel)
        self.create_watermark_panel(left_panel)
        self.create_export_panel(left_panel)
        self.create_template_panel(left_panel)
        self.create_preview_panel(right_panel)
        
    def _resolve_font_path(self, family_name: str) -> Optional[str]:
        """Resolve a usable TTF/TTC path for the given font family on Windows.
        Tries common filenames in the Windows Fonts directory and generic fallbacks."""
        try:
            windows_dir = os.environ.get('WINDIR', r'C:\\Windows')
            fonts_dir = os.path.join(windows_dir, 'Fonts')
            candidates = []
            # From family name
            if family_name:
                base = family_name.replace(' ', '')
                candidates += [
                    f"{base}.ttf", f"{base}.ttc",
                    f"{base}.TTF", f"{base}.TTC",
                    f"{family_name}.ttf", f"{family_name}.ttc",
                ]
            # Common Latin and CJK fonts
            candidates += [
                'arial.ttf', 'calibri.ttf', 'times.ttf', 'cour.ttf',
                'msyh.ttc', 'msyh.ttf', 'msyhbd.ttc',  # Microsoft YaHei
                'simsun.ttc', 'simhei.ttf',            # SimSun / SimHei
                'Tahoma.ttf', 'Verdana.ttf'
            ]
            for cand in candidates:
                cand_path = os.path.join(fonts_dir, cand)
                if os.path.exists(cand_path):
                    return cand_path
        except Exception:
            pass
        return None

    def _get_truetype_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Get a scalable font. Try requested family, then Windows Fonts, then DejaVuSans, else default."""
        family = None
        try:
            family = self.font_family.get()
        except Exception:
            family = 'Arial'
        # 1) Try direct by family (works if Pillow can locate it)
        try:
            return ImageFont.truetype(family, size)
        except Exception:
            pass
        # 2) Try resolve Windows font path
        resolved = self._resolve_font_path(family)
        if resolved:
            try:
                return ImageFont.truetype(resolved, size)
            except Exception:
                pass
        # 3) Try DejaVuSans bundled with PIL
        try:
            return ImageFont.truetype('DejaVuSans.ttf', size)
        except Exception:
            pass
        # 4) Fallback to small default bitmap font
        return ImageFont.load_default()

    def create_file_panel(self, parent):
        # File import panel
        file_frame = ttk.LabelFrame(parent, text="File Processing", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Import buttons
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Select Images", command=self.select_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Select Folder", command=self.select_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Clear List", command=self.clear_images).pack(side=tk.LEFT)
        
        # Image list
        list_frame = ttk.Frame(file_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.image_listbox = tk.Listbox(list_frame, height=8, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.image_listbox.yview)
        self.image_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
    def create_watermark_panel(self, parent):
        # Watermark settings panel
        watermark_frame = ttk.LabelFrame(parent, text="Watermark Settings", padding=10)
        watermark_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Watermark type selection
        type_frame = ttk.Frame(watermark_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(type_frame, text="Type:").pack(side=tk.LEFT)
        self.watermark_type = tk.StringVar(value="text")
        ttk.Radiobutton(type_frame, text="Text", variable=self.watermark_type, 
                       value="text", command=self.on_watermark_type_change).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(type_frame, text="Image", variable=self.watermark_type, 
                       value="image", command=self.on_watermark_type_change).pack(side=tk.LEFT, padx=(10, 0))
        
        # Text watermark settings
        self.text_frame = ttk.Frame(watermark_frame)
        self.text_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Text content
        text_content_frame = ttk.Frame(self.text_frame)
        text_content_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(text_content_frame, text="Content:").pack(side=tk.LEFT)
        self.text_entry = ttk.Entry(text_content_frame, textvariable=tk.StringVar(value=self.watermark_config['text']))
        self.text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.text_entry.bind('<KeyRelease>', self.on_text_change)
        
        # Font settings
        font_frame = ttk.Frame(self.text_frame)
        font_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(font_frame, text="Font:").pack(side=tk.LEFT)
        self.font_family = tk.StringVar(value=self.watermark_config['font_family'])
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_family, width=15)
        font_combo['values'] = self.get_system_fonts()
        font_combo.pack(side=tk.LEFT, padx=(10, 5))
        font_combo.bind('<<ComboboxSelected>>', self.on_font_change)
        
        ttk.Label(font_frame, text="Size:").pack(side=tk.LEFT, padx=(10, 0))
        self.font_size = tk.IntVar(value=self.watermark_config['font_size'])
        font_size_spin = ttk.Spinbox(font_frame, from_=8, to=200, textvariable=self.font_size, width=8, command=self.on_font_change)
        font_size_spin.pack(side=tk.LEFT, padx=(5, 0))
        font_size_spin.bind('<KeyRelease>', self.on_font_change)
        
        # Color and opacity
        color_frame = ttk.Frame(self.text_frame)
        color_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(color_frame, text="Color:").pack(side=tk.LEFT)
        self.color_var = tk.StringVar(value=self.watermark_config['color'])
        color_entry = ttk.Entry(color_frame, textvariable=self.color_var, width=10)
        color_entry.pack(side=tk.LEFT, padx=(10, 5))
        ttk.Button(color_frame, text="Choose", command=self.choose_color).pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(color_frame, text="Opacity:").pack(side=tk.LEFT, padx=(20, 0))
        self.opacity = tk.IntVar(value=self.watermark_config['opacity'])
        opacity_scale = ttk.Scale(color_frame, from_=0, to=100, variable=self.opacity, orient=tk.HORIZONTAL, command=lambda v: self.on_opacity_change())
        opacity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        # Also update on mouse release for safety
        opacity_scale.bind('<ButtonRelease-1>', self.on_opacity_change)
        
        # Image watermark settings
        self.image_frame = ttk.Frame(watermark_frame)
        self.image_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Image selection
        img_select_frame = ttk.Frame(self.image_frame)
        img_select_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(img_select_frame, text="Image:").pack(side=tk.LEFT)
        self.image_path_var = tk.StringVar()
        image_entry = ttk.Entry(img_select_frame, textvariable=self.image_path_var, state='readonly')
        image_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        ttk.Button(img_select_frame, text="Select", command=self.select_watermark_image).pack(side=tk.LEFT)
        
        # Image scaling and opacity
        img_scale_frame = ttk.Frame(self.image_frame)
        img_scale_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(img_scale_frame, text="Scale:").pack(side=tk.LEFT)
        self.image_scale = tk.DoubleVar(value=self.watermark_config['image_scale'])
        scale_scale = ttk.Scale(img_scale_frame, from_=0.1, to=2.0, variable=self.image_scale, orient=tk.HORIZONTAL, command=lambda v: self.on_image_scale_change())
        scale_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        scale_scale.bind('<ButtonRelease-1>', self.on_image_scale_change)
        
        ttk.Label(img_scale_frame, text="Opacity:").pack(side=tk.LEFT, padx=(20, 0))
        self.image_opacity = tk.IntVar(value=self.watermark_config['image_opacity'])
        img_opacity_scale = ttk.Scale(img_scale_frame, from_=0, to=100, variable=self.image_opacity, orient=tk.HORIZONTAL, command=lambda v: self.on_image_opacity_change())
        img_opacity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        img_opacity_scale.bind('<ButtonRelease-1>', self.on_image_opacity_change)
        
        # Position settings
        position_frame = ttk.LabelFrame(watermark_frame, text="Position Settings", padding=5)
        position_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 9-grid position selection
        grid_frame = ttk.Frame(position_frame)
        grid_frame.pack(fill=tk.X, pady=(0, 10))
        
        positions = [
            ('top-left', 'Top-Left'), ('top-center', 'Top-Center'), ('top-right', 'Top-Right'),
            ('middle-left', 'Middle-Left'), ('center', 'Center'), ('middle-right', 'Middle-Right'),
            ('bottom-left', 'Bottom-Left'), ('bottom-center', 'Bottom-Center'), ('bottom-right', 'Bottom-Right')
        ]
        
        self.position_var = tk.StringVar(value=self.watermark_config['position'])
        for i, (value, text) in enumerate(positions):
            row, col = i // 3, i % 3
            ttk.Radiobutton(grid_frame, text=text, variable=self.position_var, 
                           value=value, command=self.on_position_change).grid(row=row, column=col, padx=2, pady=2)
        
        # Rotation settings
        rotation_frame = ttk.Frame(position_frame)
        rotation_frame.pack(fill=tk.X)
        
        ttk.Label(rotation_frame, text="Rotation:").pack(side=tk.LEFT)
        self.rotation = tk.IntVar(value=self.watermark_config['rotation'])
        rotation_scale = ttk.Scale(rotation_frame, from_=-180, to=180, variable=self.rotation, orient=tk.HORIZONTAL, command=lambda v: self.on_rotation_change())
        rotation_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        rotation_scale.bind('<ButtonRelease-1>', self.on_rotation_change)
        
        # Hide image watermark settings initially
        self.image_frame.pack_forget()
        
    def create_export_panel(self, parent):
        # Export settings panel
        export_frame = ttk.LabelFrame(parent, text="Export Settings", padding=10)
        export_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Output folder
        output_frame = ttk.Frame(export_frame)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(output_frame, text="Output Folder:").pack(anchor=tk.W)
        output_path_frame = ttk.Frame(output_frame)
        output_path_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.output_path_var = tk.StringVar()
        output_entry = ttk.Entry(output_path_frame, textvariable=self.output_path_var, state='readonly')
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(output_path_frame, text="Select", command=self.select_output_folder).pack(side=tk.LEFT)
        
        # File naming rules
        naming_frame = ttk.Frame(export_frame)
        naming_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(naming_frame, text="File Naming:").pack(anchor=tk.W)
        
        self.naming_rule = tk.StringVar(value="prefix")
        ttk.Radiobutton(naming_frame, text="Add Prefix", variable=self.naming_rule, value="prefix").pack(anchor=tk.W)
        ttk.Radiobutton(naming_frame, text="Add Suffix", variable=self.naming_rule, value="suffix").pack(anchor=tk.W)
        ttk.Radiobutton(naming_frame, text="Keep Original", variable=self.naming_rule, value="original").pack(anchor=tk.W)
        
        # Prefix/suffix settings
        prefix_frame = ttk.Frame(naming_frame)
        prefix_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(prefix_frame, text="Prefix:").pack(side=tk.LEFT)
        self.prefix_var = tk.StringVar(value="wm_")
        ttk.Entry(prefix_frame, textvariable=self.prefix_var, width=10).pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(prefix_frame, text="Suffix:").pack(side=tk.LEFT)
        self.suffix_var = tk.StringVar(value="_watermarked")
        ttk.Entry(prefix_frame, textvariable=self.suffix_var, width=15).pack(side=tk.LEFT, padx=(5, 0))
        
        # Output format
        format_frame = ttk.Frame(export_frame)
        format_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(format_frame, text="Output Format:").pack(side=tk.LEFT)
        self.output_format = tk.StringVar(value="JPEG")
        ttk.Radiobutton(format_frame, text="JPEG", variable=self.output_format, value="JPEG").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(format_frame, text="PNG", variable=self.output_format, value="PNG").pack(side=tk.LEFT, padx=(10, 0))
        
        # JPEG quality settings
        quality_frame = ttk.Frame(export_frame)
        quality_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(quality_frame, text="JPEG Quality:").pack(side=tk.LEFT)
        self.quality = tk.IntVar(value=92)
        quality_scale = ttk.Scale(quality_frame, from_=1, to=100, variable=self.quality, orient=tk.HORIZONTAL)
        quality_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # Export button
        export_btn_frame = ttk.Frame(export_frame)
        export_btn_frame.pack(fill=tk.X)
        
        ttk.Button(export_btn_frame, text="Start Export", command=self.start_export).pack(fill=tk.X)
        
    def create_template_panel(self, parent):
        # Template management panel
        template_frame = ttk.LabelFrame(parent, text="Template Management", padding=10)
        template_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Template operation buttons
        template_btn_frame = ttk.Frame(template_frame)
        template_btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(template_btn_frame, text="Save Template", command=self.save_template).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(template_btn_frame, text="Load Template", command=self.load_template).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(template_btn_frame, text="Delete Template", command=self.delete_template).pack(side=tk.LEFT)
        
        # Template list
        template_list_frame = ttk.Frame(template_frame)
        template_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.template_listbox = tk.Listbox(template_list_frame, height=6)
        template_scrollbar = ttk.Scrollbar(template_list_frame, orient=tk.VERTICAL, command=self.template_listbox.yview)
        self.template_listbox.configure(yscrollcommand=template_scrollbar.set)
        
        self.template_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        template_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.template_listbox.bind('<Double-Button-1>', self.on_template_double_click)
        
    def create_preview_panel(self, parent):
        # Preview panel
        preview_frame = ttk.LabelFrame(parent, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Preview canvas
        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_canvas = tk.Canvas(canvas_frame, bg='white', relief=tk.SUNKEN, bd=1)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Preview controls
        control_frame = ttk.Frame(preview_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="Previous", command=self.prev_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Next", command=self.next_image).pack(side=tk.LEFT, padx=(0, 5))
        
        self.image_info_label = ttk.Label(control_frame, text="Please select images")
        self.image_info_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(20, 0))
        
    def get_system_fonts(self):
        """Get system font list"""
        try:
            import tkinter.font as tkFont
            fonts = list(tkFont.families())
            # Filter common fonts
            common_fonts = ['Arial', 'Calibri', 'Microsoft YaHei', 'SimHei', 'SimSun', 'Times New Roman', 'Courier New']
            available_fonts = [f for f in common_fonts if f in fonts]
            return available_fonts + [f for f in fonts if f not in common_fonts][:20]
        except:
            return ['Arial', 'Calibri', 'Microsoft YaHei', 'SimHei', 'SimSun']
    
    def select_images(self):
        """Select image files"""
        filetypes = [
            ('Image Files', '*.jpg *.jpeg *.png *.bmp *.tiff *.webp'),
            ('JPEG Files', '*.jpg *.jpeg'),
            ('PNG Files', '*.png'),
            ('BMP Files', '*.bmp'),
            ('TIFF Files', '*.tiff'),
            ('All Files', '*.*')
        ]
        
        files = filedialog.askopenfilenames(
            title="Select Image Files",
            filetypes=filetypes
        )
        
        if files:
            prev_empty = len(self.images) == 0
            self.images.extend(files)
            self.update_image_list()
            if prev_empty and self.images:
                self.current_image_index = 0
                try:
                    self.image_listbox.selection_clear(0, tk.END)
                    self.image_listbox.selection_set(self.current_image_index)
                except Exception:
                    pass
                self.load_current_image()
    
    def select_folder(self):
        """Select folder"""
        folder = filedialog.askdirectory(title="Select Image Folder")
        if folder:
            folder_path = Path(folder)
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
            
            prev_empty = len(self.images) == 0
            for file_path in folder_path.rglob('*'):
                if file_path.suffix.lower() in image_extensions:
                    self.images.append(str(file_path))
            
            self.update_image_list()
            if prev_empty and self.images:
                self.current_image_index = 0
                try:
                    self.image_listbox.selection_clear(0, tk.END)
                    self.image_listbox.selection_set(self.current_image_index)
                except Exception:
                    pass
                self.load_current_image()
    
    def clear_images(self):
        """Clear image list"""
        self.images.clear()
        self.image_listbox.delete(0, tk.END)
        self.preview_canvas.delete("all")
        self.image_info_label.config(text="Please select images")
    
    def update_image_list(self):
        """Update image list display"""
        self.image_listbox.delete(0, tk.END)
        for i, img_path in enumerate(self.images):
            filename = Path(img_path).name
            self.image_listbox.insert(tk.END, f"{i+1}. {filename}")
        # Keep selection in sync with current index
        if self.images:
            try:
                self.image_listbox.selection_clear(0, tk.END)
                self.image_listbox.selection_set(self.current_image_index)
            except Exception:
                pass
    
    def on_image_select(self, event):
        """Image selection event"""
        selection = self.image_listbox.curselection()
        if selection:
            self.current_image_index = selection[0]
            self.load_current_image()
    
    def load_current_image(self):
        """Load currently selected image"""
        if not self.images or self.current_image_index >= len(self.images):
            return
        
        try:
            image_path = self.images[self.current_image_index]
            self.original_image = Image.open(image_path)
            self.update_preview()
            
            # Update image info
            filename = Path(image_path).name
            size = self.original_image.size
            self.image_info_label.config(text=f"{filename} ({size[0]}x{size[1]})")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def update_preview(self):
        """Update preview"""
        if not self.original_image:
            return
        
        try:
            # Create watermarked image
            watermarked_image = self.apply_watermark(self.original_image.copy())
            
            # Resize for preview
            preview_image = self.resize_for_preview(watermarked_image)
            
            # Convert to Tkinter format
            self.preview_image = ImageTk.PhotoImage(preview_image)
            
            # Clear canvas and display image
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
            
        except Exception as e:
            messagebox.showerror("Error", f"Preview update failed: {e}")
    
    def resize_for_preview(self, image, max_size=(800, 600)):
        """Resize image for preview"""
        img_width, img_height = image.size
        max_width, max_height = max_size
        
        # Calculate scale ratio
        scale = min(max_width / img_width, max_height / img_height)
        
        if scale < 1:
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def apply_watermark(self, image):
        """Apply watermark to image"""
        if self.watermark_type.get() == "text":
            return self.apply_text_watermark(image)
        else:
            return self.apply_image_watermark(image)
    
    def apply_text_watermark(self, image):
        """Apply text watermark"""
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Create base transparent overlay sized to the image
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        
        # Get font (robust TrueType fallback so watermark is visible)
        font = self._get_truetype_font(self.font_size.get())
        
        # Get text (fallback to current date/time if empty)
        text = self.text_entry.get()
        if not text or text.strip() == "":
            text = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Measure text size using a temporary draw context
        tmp_draw = ImageDraw.Draw(overlay)
        bbox = tmp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Get color and opacity
        try:
            color = ImageColor.getrgb(self.color_var.get())
        except:
            color = (255, 255, 255)
        
        opacity = int(self.opacity.get() * 2.55)  # Convert to 0-255 range
        
        # Create a separate watermark layer sized to the text, draw text then rotate
        shadow_offset = 2
        text_layer_w = text_width + shadow_offset
        text_layer_h = text_height + shadow_offset
        text_layer = Image.new("RGBA", (text_layer_w, text_layer_h), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        
        shadow_color = (0, 0, 0, min(255, opacity))
        text_color = (*color, opacity)
        
        # Draw shadow and text using bbox offset to avoid clipping ascenders/descenders
        origin_x = -bbox[0]
        origin_y = -bbox[1]
        text_draw.text((origin_x + shadow_offset, origin_y + shadow_offset), text, font=font, fill=shadow_color)
        text_draw.text((origin_x, origin_y), text, font=font, fill=text_color)
        
        # Apply rotation
        angle = self.rotation.get() if hasattr(self, 'rotation') else 0
        if angle:
            text_layer = text_layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        
        # Compute position based on rotated size
        position = self.get_watermark_position(image.size, text_layer.size)
        
        # Paste rotated text layer onto overlay using its alpha
        overlay.paste(text_layer, position, text_layer)
        
        # Merge layers
        return Image.alpha_composite(image, overlay)
    
    def apply_image_watermark(self, image):
        """Apply image watermark"""
        if not self.watermark_config['image_path']:
            return image
        
        try:
            watermark_img = Image.open(self.watermark_config['image_path'])
            if watermark_img.mode != "RGBA":
                watermark_img = watermark_img.convert("RGBA")
            
            # Adjust watermark size
            scale = self.image_scale.get()
            new_size = (int(watermark_img.width * scale), int(watermark_img.height * scale))
            watermark_img = watermark_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Adjust opacity
            opacity = int(self.image_opacity.get() * 2.55)
            if opacity < 255:
                alpha = watermark_img.split()[-1]
                alpha = alpha.point(lambda p: int(p * opacity / 255))
                watermark_img.putalpha(alpha)
            
            # Apply rotation if any
            angle = self.rotation.get() if hasattr(self, 'rotation') else 0
            if angle:
                watermark_img = watermark_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
            
            # Calculate position
            position = self.get_watermark_position(image.size, watermark_img.size)
            
            # Create transparent layer
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            overlay.paste(watermark_img, position, watermark_img)
            
            return Image.alpha_composite(image, overlay)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply image watermark: {e}")
            return image
    
    def get_watermark_position(self, image_size, watermark_size):
        """Calculate watermark position"""
        img_width, img_height = image_size
        wm_width, wm_height = watermark_size
        margin = 20
        
        position = self.position_var.get()
        
        if position == "top-left":
            return (margin, margin)
        elif position == "top-center":
            return ((img_width - wm_width) // 2, margin)
        elif position == "top-right":
            return (img_width - wm_width - margin, margin)
        elif position == "middle-left":
            return (margin, (img_height - wm_height) // 2)
        elif position == "center":
            return ((img_width - wm_width) // 2, (img_height - wm_height) // 2)
        elif position == "middle-right":
            return (img_width - wm_width - margin, (img_height - wm_height) // 2)
        elif position == "bottom-left":
            return (margin, img_height - wm_height - margin)
        elif position == "bottom-center":
            return ((img_width - wm_width) // 2, img_height - wm_height - margin)
        else:  # bottom-right
            return (img_width - wm_width - margin, img_height - wm_height - margin)
    
    def prev_image(self):
        """Previous image"""
        if self.images and self.current_image_index > 0:
            self.current_image_index -= 1
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(self.current_image_index)
            self.load_current_image()
    
    def next_image(self):
        """Next image"""
        if self.images and self.current_image_index < len(self.images) - 1:
            self.current_image_index += 1
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(self.current_image_index)
            self.load_current_image()
    
    def on_watermark_type_change(self):
        """Watermark type changed"""
        if self.watermark_type.get() == "text":
            self.text_frame.pack(fill=tk.X, pady=(0, 10))
            self.image_frame.pack_forget()
        else:
            self.text_frame.pack_forget()
            self.image_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.update_preview()
    
    def on_text_change(self, event=None):
        """Text content changed"""
        self.watermark_config['text'] = self.text_entry.get()
        self.update_preview()
    
    def on_font_change(self, event=None):
        """Font changed"""
        self.watermark_config['font_family'] = self.font_family.get()
        self.watermark_config['font_size'] = self.font_size.get()
        self.update_preview()
    
    def choose_color(self):
        """Choose color"""
        color = colorchooser.askcolor(title="Choose Text Color", color=self.color_var.get())
        if color[1]:
            self.color_var.set(color[1])
            self.watermark_config['color'] = color[1]
            self.update_preview()
    
    def on_opacity_change(self, event=None):
        """Opacity changed"""
        self.watermark_config['opacity'] = self.opacity.get()
        self.update_preview()
    
    def select_watermark_image(self):
        """Select watermark image"""
        filetypes = [
            ('Image Files', '*.png *.jpg *.jpeg *.bmp'),
            ('PNG Files', '*.png'),
            ('All Files', '*.*')
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select Watermark Image",
            filetypes=filetypes
        )
        
        if file_path:
            self.image_path_var.set(file_path)
            self.watermark_config['image_path'] = file_path
            self.update_preview()
    
    def on_image_scale_change(self, event=None):
        """Image scale changed"""
        self.watermark_config['image_scale'] = self.image_scale.get()
        self.update_preview()
    
    def on_image_opacity_change(self, event=None):
        """Image opacity changed"""
        self.watermark_config['image_opacity'] = self.image_opacity.get()
        self.update_preview()
    
    def on_position_change(self):
        """Position changed"""
        self.watermark_config['position'] = self.position_var.get()
        self.update_preview()
    
    def on_rotation_change(self, event=None):
        """Rotation angle changed"""
        self.watermark_config['rotation'] = self.rotation.get()
        self.update_preview()
    
    def select_output_folder(self):
        """Select output folder"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path_var.set(folder)
            self.output_dir = folder
    
    def start_export(self):
        """Start export"""
        if not self.images:
            messagebox.showwarning("Warning", "Please select images to process first")
            return
        
        if not self.output_dir:
            # Default to ./output if not selected
            default_out = os.path.join(os.getcwd(), 'output')
            self.output_dir = default_out
            try:
                Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create default output folder: {e}")
                return
            # Reflect in UI field
            try:
                self.output_path_var.set(self.output_dir)
            except Exception:
                pass
        
        # Run export in background thread
        self.progress.start()
        export_thread = threading.Thread(target=self.export_images)
        export_thread.daemon = True
        export_thread.start()
    
    def export_images(self):
        """Export images (executed in background thread)"""
        try:
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            success_count = 0
            total_count = len(self.images)
            
            for i, image_path in enumerate(self.images):
                try:
                    # Load original image
                    original = Image.open(image_path)
                    
                    # Apply watermark
                    watermarked = self.apply_watermark(original)
                    
                    # Generate output filename
                    input_path = Path(image_path)
                    output_filename = self.generate_output_filename(input_path)
                    output_file = output_path / output_filename
                    
                    # Save image
                    if self.output_format.get() == "JPEG":
                        if watermarked.mode == "RGBA":
                            watermarked = watermarked.convert("RGB")
                        watermarked.save(output_file, "JPEG", quality=self.quality.get())
                    else:
                        watermarked.save(output_file, "PNG")
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"Failed to process {image_path}: {e}")
            
            # Show result on main thread
            self.root.after(0, self.export_finished, success_count, total_count)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Export failed: {e}"))
        finally:
            self.root.after(0, self.progress.stop)
    
    def generate_output_filename(self, input_path):
        """Generate output filename"""
        stem = input_path.stem
        suffix = input_path.suffix
        
        if self.naming_rule.get() == "prefix":
            return f"{self.prefix_var.get()}{stem}{suffix}"
        elif self.naming_rule.get() == "suffix":
            return f"{stem}{self.suffix_var.get()}{suffix}"
        else:
            return f"{stem}{suffix}"
    
    def export_finished(self, success_count, total_count):
        """Export finished"""
        self.progress.stop()
        messagebox.showinfo("Done", f"Export completed!\nSuccessfully processed: {success_count}/{total_count} images")
    
    def save_template(self):
        """Save template"""
        template_name = tk.simpledialog.askstring("Save Template", "Enter template name:")
        if not template_name:
            return
        
        # Collect current settings
        template = {
            'watermark_type': self.watermark_type.get(),
            'text': self.text_entry.get(),
            'font_family': self.font_family.get(),
            'font_size': self.font_size.get(),
            'color': self.color_var.get(),
            'opacity': self.opacity.get(),
            'image_path': self.watermark_config['image_path'],
            'image_scale': self.image_scale.get(),
            'image_opacity': self.image_opacity.get(),
            'position': self.position_var.get(),
            'rotation': self.rotation.get()
        }
        
        self.templates[template_name] = template
        self.save_templates()
        self.update_template_list()
        messagebox.showinfo("Success", f"Template '{template_name}' saved")
    
    def load_template(self):
        """Load template"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a template to load")
            return
        
        template_name = self.template_listbox.get(selection[0])
        if template_name in self.templates:
            template = self.templates[template_name]
            
            # Apply template settings
            self.watermark_type.set(template['watermark_type'])
            self.text_entry.delete(0, tk.END)
            self.text_entry.insert(0, template['text'])
            self.font_family.set(template['font_family'])
            self.font_size.set(template['font_size'])
            self.color_var.set(template['color'])
            self.opacity.set(template['opacity'])
            self.image_scale.set(template['image_scale'])
            self.image_opacity.set(template['image_opacity'])
            self.position_var.set(template['position'])
            self.rotation.set(template['rotation'])
            
            if template['image_path']:
                self.image_path_var.set(template['image_path'])
                self.watermark_config['image_path'] = template['image_path']
            
            # Update UI
            self.on_watermark_type_change()
            self.update_preview()
            
            messagebox.showinfo("Success", f"Template '{template_name}' loaded")
    
    def delete_template(self):
        """Delete template"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a template to delete")
            return
        
        template_name = self.template_listbox.get(selection[0])
        if messagebox.askyesno("Confirm", f"Are you sure to delete template '{template_name}'?"):
            del self.templates[template_name]
            self.save_templates()
            self.update_template_list()
            messagebox.showinfo("Success", f"Template '{template_name}' deleted")
    
    def on_template_double_click(self, event):
        """Double click to load template"""
        self.load_template()
    
    def update_template_list(self):
        """Update template list"""
        self.template_listbox.delete(0, tk.END)
        for template_name in self.templates.keys():
            self.template_listbox.insert(tk.END, template_name)
    
    def load_templates(self):
        """Load templates"""
        try:
            config_file = Path("watermark_templates.json")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.templates = json.load(f)
                self.update_template_list()
        except Exception as e:
            print(f"Failed to load templates: {e}")
    
    def save_templates(self):
        """Save templates"""
        try:
            config_file = Path("watermark_templates.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save templates: {e}")


def main():
    root = tk.Tk()
    app = WatermarkApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
