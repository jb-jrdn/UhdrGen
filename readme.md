UhdrGen
========

Convert SDR + HDR images to Ultra HDR with gainmap.

Description
-----------
This project provides a Python tool to generate single HDR jpg with Gain map,
from SDR/HDR pair.
Lightroom does not allow precise control over the processing of the SDR version of HDR images with a Gain Map.
Combining an SDR image with an HDR image to create an Ultra HDR image with a Gain Map
provides the best compromise for all types of displays, offering fine-grained control over each displayed version.
Additionally, the HDR images created work perfectly for Instagram posts,
which is not always the case with exports from Lightroom.

Features
--------
- Convert SDR + HDR → Ultra HDR (gainmap JPEG)
- Process single files or entire folders (batch mode)
- Supported formats:
    - SDR: JPEG
    - HDR: AVIF
- Works on Mac, Linux, and Windows
- Uses Python libraries: numpy, Pillow, pillow-heif, OpenCV, colour-science

Installation
------------
1. Clone the project:
   git clone https://github.com/<your-username>/UhdrGen.git
   cd UhdrGen

2. Create a virtual environment:
   python3 -m venv venv
   source venv/bin/activate       # macOS / Linux
   # venv\Scripts\Activate.ps1    # Windows PowerShell

3. Install dependencies:
   pip install -r requirements.txt

4. Install ultrahdr_app:
    macOS (using Homebrew):
        brew install libultrahdr
    Windows:
        1. Download the precompiled `libultrahdr` binaries from the official website or GitHub releases.
        2. Add the folder containing `libultrahdr.dll` to your system PATH, or place the DLL in the same folder as your Python scripts.

Usage
-----

Single file mode:
   python main.py --sdr path/to/image_sdr.png --hdr path/to/image_hdr.exr --output path/to/output.jpg

Batch mode (entire folder):
- SDR and HDR images must share the same base name with suffixes `_sdr` / `_hdr`:
    image1_sdr.jpg / image1_hdr.avif
    image2_sdr.jpg / image2_hdr.avif

   python main.py --dir path/to/images/

CLI Options
-----------
--sdr          : Path to the SDR image (single file mode)
--hdr          : Path to the HDR image (single file mode)
--dir          : Directory containing SDR/HDR image pairs (batch mode)
--output       : Output file (single mode) or output folder (batch mode)
--mode         : Conversion mode (default: sdr_hdr_uhdr)

