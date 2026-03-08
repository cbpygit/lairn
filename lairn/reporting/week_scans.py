"""Weekly scan collection, normalization, and PDF merge functionality."""
from datetime import date, datetime
from pathlib import Path
from typing import Optional
import re
import shutil
import subprocess
import tempfile

from loguru import logger

try:
    from PIL import Image
    import img2pdf
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False

from pypdf import PdfWriter, PdfReader


# Filename patterns for scan files
PATTERN_GESCANNT = re.compile(
    r"Gescannt_(\d{8})[-_](\d{4,9})(?:\s\(\d+\))?\.(.+)$",
    re.IGNORECASE
)
PATTERN_PIXEL = re.compile(
    r"PXL_(\d{8})_(\d{9}(?:\.\w+)?)\.(.+)$",
    re.IGNORECASE
)
PATTERN_WHATSAPP = re.compile(
    r"IMG-(\d{8})-WA(\d+)(?:\s\(\d+\))?\.(.+)$",
    re.IGNORECASE
)


def parse_gescannt_filename(filename: str) -> Optional[datetime]:
    """Parse timestamp from Gescannt_YYYYMMDD-HHMM*.ext format.
    
    Supports:
    - Gescannt_YYYYMMDD-HHMM.pdf
    - Gescannt_YYYYMMDD-HHMMSSmmm.jpg
    - Gescannt_YYYYMMDD_HHMMSSmmm.jpg (underscore variant)
    """
    match = PATTERN_GESCANNT.match(filename)
    if not match:
        return None
    
    date_str, time_str, _ = match.groups()
    
    # Parse date part
    try:
        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
    except (ValueError, IndexError):
        return None
    
    # Parse time part (HHMM or HHMMSSmmm)
    try:
        if len(time_str) == 4:
            # HHMM format
            hour = int(time_str[0:2])
            minute = int(time_str[2:4])
            second = 0
            microsecond = 0
        elif len(time_str) >= 6:
            # HHMMSSmmm format (or longer)
            hour = int(time_str[0:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            # Microsecond part (milliseconds if present)
            if len(time_str) > 6:
                ms_str = time_str[6:]
                microsecond = int(ms_str) * 1000  # Convert milliseconds to microseconds
            else:
                microsecond = 0
        else:
            return None
            
        return datetime(year, month, day, hour, minute, second, microsecond)
    except (ValueError, IndexError):
        return None


def parse_pixel_filename(filename: str) -> Optional[datetime]:
    """Parse timestamp from PXL_YYYYMMDD_HHMMSSmmm*.ext format.
    
    Example: PXL_20251213_083927158.jpg
    """
    match = PATTERN_PIXEL.match(filename)
    if not match:
        return None
    
    date_str, time_str, _ = match.groups()
    
    # Remove any extra dots/suffixes from time_str (e.g., "083927158.PORTRAIT")
    time_str = time_str.split('.')[0]
    
    try:
        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:6])
        # Last 3 digits are milliseconds
        millisecond = int(time_str[6:9])
        microsecond = millisecond * 1000
        
        return datetime(year, month, day, hour, minute, second, microsecond)
    except (ValueError, IndexError):
        return None


def parse_whatsapp_filename(filename: str) -> Optional[datetime]:
    """Parse date from WhatsApp image filename format IMG-YYYYMMDD-WAxxxx.ext.

    Example: IMG-20260305-WA0009.jpg
    Time defaults to midnight since WhatsApp filenames carry no time information.
    """
    match = PATTERN_WHATSAPP.match(filename)
    if not match:
        return None

    date_str, _, _ = match.groups()

    try:
        year = int(date_str[0:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        return datetime(year, month, day, 0, 0, 0)
    except (ValueError, IndexError):
        return None


def parse_scan_filename(filename: str) -> Optional[datetime]:
    """Parse timestamp from any supported scan filename format."""
    dt = parse_gescannt_filename(filename)
    if dt:
        return dt

    dt = parse_pixel_filename(filename)
    if dt:
        return dt

    dt = parse_whatsapp_filename(filename)
    if dt:
        return dt

    return None


def normalize_pixel_images(scans_dir: Path) -> list[tuple[Path, Path]]:
    """Rename all Pixel images to Gescannt_YYYYMMDD-HHMMSSmmm.jpg format.
    
    Returns list of (old_path, new_path) tuples for renamed files.
    Handles collisions by appending _dup1, _dup2, etc.
    """
    if not scans_dir.exists():
        logger.warning(f"Scans directory does not exist: {scans_dir}")
        return []
    
    renamed = []
    
    for file_path in scans_dir.iterdir():
        if not file_path.is_file():
            continue
        
        filename = file_path.name
        
        # Check if it's a Pixel image
        dt = parse_pixel_filename(filename)
        if not dt:
            continue
        
        # Get the original extension
        original_ext = file_path.suffix.lower()
        
        # Build new filename: Gescannt_YYYYMMDD-HHMMSSmmm.ext
        new_name = f"Gescannt_{dt.strftime('%Y%m%d')}-{dt.strftime('%H%M%S')}{dt.microsecond // 1000:03d}{original_ext}"
        new_path = scans_dir / new_name
        
        # Handle collisions
        counter = 1
        while new_path.exists() and new_path != file_path:
            stem = new_name.rsplit('.', 1)[0]
            ext = new_name.rsplit('.', 1)[1] if '.' in new_name else ''
            new_name = f"{stem}_dup{counter}.{ext}" if ext else f"{stem}_dup{counter}"
            new_path = scans_dir / new_name
            counter += 1
        
        # Rename the file
        if new_path != file_path:
            try:
                shutil.move(str(file_path), str(new_path))
                logger.info(f"Renamed: {filename} -> {new_name}")
                renamed.append((file_path, new_path))
            except Exception as e:
                logger.error(f"Failed to rename {filename}: {e}")
    
    return renamed


def collect_week_scans(scans_dir: Path, start_date: date, end_date: date) -> list[Path]:
    """Collect all scan files (PDFs and images) for the given week.
    
    Returns sorted list of file paths (by timestamp extracted from filename).
    """
    if not scans_dir.exists():
        logger.warning(f"Scans directory does not exist: {scans_dir}")
        return []
    
    matched_files = []
    supported_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
    
    for file_path in scans_dir.iterdir():
        if not file_path.is_file():
            continue
        
        # Check extension
        if file_path.suffix.lower() not in supported_extensions:
            continue
        
        # Parse timestamp
        dt = parse_scan_filename(file_path.name)
        if not dt:
            continue
        
        file_date = dt.date()
        
        # Check if in week range
        if start_date <= file_date <= end_date:
            matched_files.append((dt, file_path))
    
    # Sort by timestamp
    matched_files.sort(key=lambda x: x[0])
    
    return [path for _, path in matched_files]


def image_to_pdf_bytes(image_path: Path, max_size: int = 2500, jpeg_quality: int = 75) -> bytes:
    """Convert an image to a single-page PDF with downsampling and JPEG compression.
    
    Args:
        image_path: Path to the image file
        max_size: Maximum dimension (width or height) in pixels
        jpeg_quality: JPEG quality (0-100)
    
    Returns:
        PDF bytes
    """
    if not IMAGING_AVAILABLE:
        raise RuntimeError("Pillow and img2pdf are required for image processing")
    
    with Image.open(image_path) as img:
        # Auto-orient based on EXIF
        try:
            img = Image.Image.transpose(img, Image.Transpose.EXIF)
        except Exception:
            # If EXIF orientation fails, continue without it
            pass
        
        # Convert to RGB (required for JPEG)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # Downsample if needed
        width, height = img.size
        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to temporary JPEG
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            img.save(tmp_path, 'JPEG', quality=jpeg_quality, optimize=True)
        
        try:
            # Convert JPEG to PDF
            pdf_bytes = img2pdf.convert(str(tmp_path))
            return pdf_bytes
        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)


def merge_scans_to_pdf(scan_files: list[Path], output_path: Path) -> None:
    """Merge all scan files (PDFs and images) into a single PDF.
    
    PDFs are appended directly, images are converted with compression.
    """
    if not scan_files:
        logger.warning("No scan files to merge")
        return
    
    writer = PdfWriter()
    
    for scan_file in scan_files:
        ext = scan_file.suffix.lower()
        
        try:
            if ext == '.pdf':
                # Append PDF pages directly
                reader = PdfReader(scan_file)
                for page in reader.pages:
                    writer.add_page(page)
                logger.debug(f"Added PDF: {scan_file.name} ({len(reader.pages)} pages)")
            
            elif ext in {'.jpg', '.jpeg', '.png'}:
                # Convert image to compressed PDF
                pdf_bytes = image_to_pdf_bytes(scan_file)
                
                # Create a temporary PDF file
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    tmp_path.write_bytes(pdf_bytes)
                
                try:
                    reader = PdfReader(tmp_path)
                    for page in reader.pages:
                        writer.add_page(page)
                    logger.debug(f"Added image: {scan_file.name}")
                finally:
                    tmp_path.unlink(missing_ok=True)
        
        except Exception as e:
            logger.error(f"Failed to process {scan_file.name}: {e}")
            continue
    
    # Write merged PDF
    with open(output_path, 'wb') as f:
        writer.write(f)
    
    logger.info(f"Merged {len(scan_files)} files into {output_path}")


def compress_pdf_with_ghostscript(input_path: Path, output_path: Path) -> bool:
    """Compress PDF using Ghostscript with ebook settings.
    
    Returns True if successful, False if gs not available or failed.
    """
    # Check if gs is available
    try:
        result = subprocess.run(
            ['gs', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False
    except (subprocess.SubprocessError, FileNotFoundError):
        return False
    
    # Run gs compression
    try:
        cmd = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/ebook',  # 150 dpi, good compression
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={output_path}',
            str(input_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"Compressed PDF with Ghostscript: {input_path.name}")
            return True
        else:
            logger.error(f"Ghostscript compression failed: {result.stderr}")
            return False
    
    except Exception as e:
        logger.error(f"Ghostscript compression error: {e}")
        return False


def build_week_scans_pdf(
    scans_dir: Path,
    start_date: date,
    end_date: date,
    output_path: Path,
    normalize_pixel: bool = True,
    compress: bool = True
) -> bool:
    """Build a merged and compressed PDF of all scans for the given week.
    
    Args:
        scans_dir: Directory containing scan files
        start_date: Start of the week (Monday)
        end_date: End of the week (Sunday)
        output_path: Where to write the final PDF
        normalize_pixel: Whether to rename Pixel images first
        compress: Whether to compress with Ghostscript (if available)
    
    Returns:
        True if successful, False otherwise
    """
    if not IMAGING_AVAILABLE:
        logger.error("Pillow and img2pdf are required for scan processing. Install with: poetry add pillow img2pdf")
        return False
    
    if not scans_dir or not scans_dir.exists():
        logger.warning(f"Scans directory not available: {scans_dir}")
        return False
    
    # Step 1: Normalize Pixel images
    if normalize_pixel:
        logger.info("Normalizing Pixel image filenames...")
        renamed = normalize_pixel_images(scans_dir)
        if renamed:
            logger.info(f"Renamed {len(renamed)} Pixel images")
    
    # Step 2: Collect scans for the week
    logger.info(f"Collecting scans for week {start_date} to {end_date}...")
    scan_files = collect_week_scans(scans_dir, start_date, end_date)
    
    if not scan_files:
        logger.info("No scan files found for this week")
        return False
    
    logger.info(f"Found {len(scan_files)} scan files")
    
    # Step 3: Merge into PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        merge_scans_to_pdf(scan_files, tmp_path)
        
        # Step 4: Compress with Ghostscript if available
        if compress:
            logger.info("Attempting Ghostscript compression...")
            if compress_pdf_with_ghostscript(tmp_path, output_path):
                logger.info(f"Created compressed scans PDF: {output_path}")
            else:
                logger.warning("Ghostscript not available or compression failed. Using uncompressed PDF.")
                logger.warning("Install Ghostscript for better compression: sudo apt-get install ghostscript")
                shutil.move(str(tmp_path), str(output_path))
        else:
            # Just move the merged PDF
            shutil.move(str(tmp_path), str(output_path))
        
        return True
    
    finally:
        # Clean up temp file if it still exists
        tmp_path.unlink(missing_ok=True)

