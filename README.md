# Photo Watermark Tool 

A full-featured desktop application for adding text or image watermarks to photos. Supports batch processing, real-time preview, and template management.

## Features

### 1. File Handling
- **Import Images**: Drag-and-drop single image or import via file chooser
- **Batch Import**: Select multiple images at once or import an entire folder
- **Image List**: Display imported images with filename list (thumbnails optional)
- **Clear-on-Import**: Selecting Images/Folder clears the current list first
- **Supported Formats**: JPEG, PNG, BMP, TIFF, WebP
- **Output Formats**: Choose output as JPEG or PNG

### 2. Watermark Types
- **Text Watermark**:
  - Custom text content
  - Select installed system fonts
  - Font size and color
  - Opacity control (0-100%)
  - Shadow effect for readability
- **Image Watermark**:
  - Supports PNG with alpha transparency
  - Scalable size
  - Opacity control

### 3. Layout and Style
- **Real-time Preview**: All adjustments (text, font, color, opacity, image scale/opacity, rotation, position) update the preview instantly
- **Position Presets**: 3x3 grid (corners, edges, center)
- **Rotation**: Rotate watermark at any angle (applies to text and image watermarks)
- **Image Switching**: Click list to switch previewed image

### 4. Export
- **Output Folder**: Choose output directory; if none selected, defaults to `./output` (auto-created)
- **File Naming**: Keep original name, add prefix, or add suffix
- **Quality**: JPEG quality slider (1-100)
- **Batch Export**: Process all imported images

### 5. Templates
- **Save Templates**: Save current watermark settings
- **Load Templates**: Quickly apply saved settings
- **Manage Templates**: Delete templates (rename by saving a new one and deleting the old)
- **Storage Location**: Each template is an individual JSON file under `templates/` (e.g. `templates/MyPreset.json`)
- **Startup Load**: All `templates/*.json` are discovered and listed automatically

## Installation & Run

### Option A: Direct Run (Recommended)
```powershell
# 1) Install dependencies
pip install -r requirements.txt

# 2) Run the GUI app
python watermark_gui.py
```

### Option B: Virtual Environment
```powershell
# 1) Create venv
python -m venv .venv

# 2) Activate venv
. .venv\Scripts\Activate.ps1

# 3) Install dependencies
pip install -r requirements.txt

# 4) Run the app
python watermark_gui.py
```

## Usage

### Basic Workflow
1. **Import Images**: Click "Select Images" or "Select Folder" (current list will be cleared)
2. **Configure Watermark**: Choose type, content, style in the left panel
   - Empty text content falls back to current datetime (e.g. `2025-09-25 14:30`)
3. **Preview**: Changes reflect instantly in the right-side preview
4. **Choose Output**: Set output folder and naming rules (or use default `./output`)
5. **Export**: Click "Start Export" (also available in the top toolbar)

### Advanced
- **Templates**: Save/load commonly used settings
- **Real-time Preview**
- **Batch Processing**
- **Format Conversion**

## Tech

- **UI**: Tkinter
- **Imaging**: Pillow (PIL)
- **Multithreading**: Background export to keep UI responsive
- **Config Persistence**: Templates as individual JSON files in `templates/`
- **Font Fallback**: Robust TrueType font fallback (Windows Fonts, DejaVuSans) to ensure visible text watermarks
- **Errors**: Friendly error messages

## Changelog

**v2.0** - GUI Release
- New graphical UI
- Text and image watermark types
- Real-time preview
- Template management
- Batch export
- Multiple image formats
- Improved UX

**v1.0** - CLI Release
- EXIF date watermarking
- CLI arguments
- Basic file processing
