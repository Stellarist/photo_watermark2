# Photo Watermark Tool 

A full-featured desktop application for adding text or image watermarks to photos. Supports batch processing, real-time preview, and template management.

## Features

### 1. File Handling
- **Import Images**: Drag-and-drop single image or import via file chooser
- **Batch Import**: Select multiple images at once or import an entire folder
- **Image List**: Display imported images with filename list (thumbnails optional)
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
- **Real-time Preview**: All adjustments are shown immediately in the preview
- **Position Presets**: 3x3 grid (corners, edges, center)
- **Rotation**: Rotate watermark at any angle
- **Image Switching**: Click list to switch previewed image

### 4. Export
- **Output Folder**: Choose output directory; original folder overwrite is discouraged by default
- **File Naming**: Keep original name, add prefix, or add suffix
- **Quality**: JPEG quality slider (1-100)
- **Batch Export**: Process all imported images

### 5. Templates
- **Save Templates**: Save current watermark settings
- **Load Templates**: Quickly apply saved settings
- **Manage Templates**: Rename or delete templates
- **Auto Load**: Load last used settings on startup

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
1. **Import Images**: Click "Select Images" or "Select Folder"
2. **Configure Watermark**: Choose type, content, style in the left panel
3. **Preview**: Inspect in the right-side preview window
4. **Choose Output**: Set output folder and naming rules
5. **Export**: Click "Start Export" to process all images

### Advanced
- **Templates**: Save/load commonly used settings
- **Real-time Preview**
- **Batch Processing**
- **Format Conversion**

## Tech

- **UI**: Tkinter
- **Imaging**: Pillow (PIL)
- **Multithreading**: Background export to keep UI responsive
- **Config Persistence**: JSON templates and settings
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
