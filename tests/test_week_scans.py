"""Tests for weekly scan collection and processing."""
from datetime import date, datetime
from pathlib import Path
import tempfile
import shutil

import pytest

from lairn.reporting.week_scans import (
    parse_gescannt_filename,
    parse_pixel_filename,
    parse_scan_filename,
    normalize_pixel_images,
    collect_week_scans,
)


class TestFilenameParser:
    """Test filename parsing functions."""
    
    def test_parse_gescannt_hhmm(self):
        """Test parsing Gescannt_YYYYMMDD-HHMM.pdf format."""
        dt = parse_gescannt_filename("Gescannt_20260109-1052.pdf")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 9
        assert dt.hour == 10
        assert dt.minute == 52
        assert dt.second == 0
        assert dt.microsecond == 0
    
    def test_parse_gescannt_hhmmssmmm(self):
        """Test parsing Gescannt_YYYYMMDD-HHMMSSmmm.jpg format."""
        dt = parse_gescannt_filename("Gescannt_20251213-083927158.jpg")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 12
        assert dt.day == 13
        assert dt.hour == 8
        assert dt.minute == 39
        assert dt.second == 27
        assert dt.microsecond == 158000  # 158 milliseconds in microseconds
    
    def test_parse_gescannt_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        dt = parse_gescannt_filename("gescannt_20260109-1052.PDF")
        assert dt is not None
        assert dt.year == 2026
    
    def test_parse_gescannt_underscore_separator(self):
        """Test parsing with underscore separator (alternative format)."""
        dt = parse_gescannt_filename("Gescannt_20250811_110923544.jpg")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 8
        assert dt.day == 11
        assert dt.hour == 11
        assert dt.minute == 9
        assert dt.second == 23
        assert dt.microsecond == 544000
    
    def test_parse_gescannt_duplicate_suffix(self):
        """Test parsing filenames with duplicate suffix like ' (2)'."""
        dt = parse_gescannt_filename("Gescannt_20260130-0951 (2).pdf")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 30
        assert dt.hour == 9
        assert dt.minute == 51
    
    def test_parse_gescannt_invalid(self):
        """Test invalid Gescannt filenames return None."""
        assert parse_gescannt_filename("invalid.pdf") is None
        assert parse_gescannt_filename("Gescannt_2026-01-09.pdf") is None
        assert parse_gescannt_filename("Gescannt_20260109.pdf") is None
    
    def test_parse_pixel_basic(self):
        """Test parsing PXL_YYYYMMDD_HHMMSSmmm.jpg format."""
        dt = parse_pixel_filename("PXL_20251213_083927158.jpg")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 12
        assert dt.day == 13
        assert dt.hour == 8
        assert dt.minute == 39
        assert dt.second == 27
        assert dt.microsecond == 158000  # 158 milliseconds
    
    def test_parse_pixel_portrait(self):
        """Test parsing Pixel filename with PORTRAIT suffix."""
        dt = parse_pixel_filename("PXL_20251215_114444872.PORTRAIT.jpg")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 12
        assert dt.day == 15
        assert dt.hour == 11
        assert dt.minute == 44
        assert dt.second == 44
        assert dt.microsecond == 872000
    
    def test_parse_pixel_invalid(self):
        """Test invalid Pixel filenames return None."""
        assert parse_pixel_filename("invalid.jpg") is None
        assert parse_pixel_filename("PXL_20251213.jpg") is None
    
    def test_parse_scan_filename(self):
        """Test the combined parser function."""
        # Should parse Gescannt format
        dt1 = parse_scan_filename("Gescannt_20260109-1052.pdf")
        assert dt1 is not None
        assert dt1.year == 2026
        
        # Should parse Pixel format
        dt2 = parse_scan_filename("PXL_20251213_083927158.jpg")
        assert dt2 is not None
        assert dt2.year == 2025
        
        # Should return None for invalid
        assert parse_scan_filename("invalid.pdf") is None


class TestPixelNormalization:
    """Test Pixel image renaming functionality."""
    
    def test_normalize_pixel_images(self):
        """Test basic Pixel image normalization."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create test Pixel files
            pixel_file1 = tmpdir / "PXL_20251213_083927158.jpg"
            pixel_file2 = tmpdir / "PXL_20251215_114444872.PORTRAIT.jpg"
            other_file = tmpdir / "Gescannt_20260109-1052.pdf"
            
            pixel_file1.touch()
            pixel_file2.touch()
            other_file.touch()
            
            # Normalize
            renamed = normalize_pixel_images(tmpdir)
            
            # Check that 2 files were renamed
            assert len(renamed) == 2
            
            # Check that new files exist
            expected1 = tmpdir / "Gescannt_20251213-083927158.jpg"
            expected2 = tmpdir / "Gescannt_20251215-114444872.jpg"
            
            assert expected1.exists()
            assert expected2.exists()
            
            # Check that original Pixel files no longer exist
            assert not pixel_file1.exists()
            assert not pixel_file2.exists()
            
            # Check that other file was not touched
            assert other_file.exists()
    
    def test_normalize_pixel_collision(self):
        """Test collision handling when target filename already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create a Pixel file and a file it would collide with
            pixel_file = tmpdir / "PXL_20251213_083927158.jpg"
            collision_file = tmpdir / "Gescannt_20251213-083927158.jpg"
            
            pixel_file.touch()
            collision_file.write_text("existing")
            
            # Normalize
            renamed = normalize_pixel_images(tmpdir)
            
            # Should have renamed with _dup1 suffix
            assert len(renamed) == 1
            expected = tmpdir / "Gescannt_20251213-083927158_dup1.jpg"
            assert expected.exists()
            
            # Original collision file should still exist
            assert collision_file.exists()
            assert collision_file.read_text() == "existing"


class TestWeekCollection:
    """Test week-based scan file collection."""
    
    def test_collect_week_scans(self):
        """Test collecting scans for a specific week."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create files for different dates
            # Week 2 of 2026 is Jan 5-11
            before_week = tmpdir / "Gescannt_20260104-1000.pdf"  # Sunday before
            monday = tmpdir / "Gescannt_20260105-1000.pdf"
            wednesday = tmpdir / "Gescannt_20260107-1400.pdf"
            sunday = tmpdir / "Gescannt_20260111-2000.pdf"
            after_week = tmpdir / "Gescannt_20260112-1000.pdf"  # Monday after
            
            for f in [before_week, monday, wednesday, sunday, after_week]:
                f.touch()
            
            # Collect week 2
            start_date = date(2026, 1, 5)  # Monday
            end_date = date(2026, 1, 11)  # Sunday
            
            scans = collect_week_scans(tmpdir, start_date, end_date)
            
            # Should have exactly 3 files (Mon, Wed, Sun)
            assert len(scans) == 3
            
            # Check they're in chronological order
            assert scans[0].name == "Gescannt_20260105-1000.pdf"
            assert scans[1].name == "Gescannt_20260107-1400.pdf"
            assert scans[2].name == "Gescannt_20260111-2000.pdf"
    
    def test_collect_week_scans_mixed_formats(self):
        """Test collecting scans with mixed Gescannt and Pixel formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create mixed format files for the same week
            gescannt = tmpdir / "Gescannt_20260105-1000.pdf"
            pixel = tmpdir / "PXL_20260107_140000000.jpg"
            gescannt_jpg = tmpdir / "Gescannt_20260109-083927158.jpg"
            
            for f in [gescannt, pixel, gescannt_jpg]:
                f.touch()
            
            # Collect week 2
            start_date = date(2026, 1, 5)
            end_date = date(2026, 1, 11)
            
            scans = collect_week_scans(tmpdir, start_date, end_date)
            
            # Should have all 3 files
            assert len(scans) == 3
            
            # Should be sorted chronologically
            assert scans[0].name == "Gescannt_20260105-1000.pdf"
            assert scans[1].name == "PXL_20260107_140000000.jpg"
            assert scans[2].name == "Gescannt_20260109-083927158.jpg"
    
    def test_collect_week_scans_supported_extensions(self):
        """Test that only supported extensions are collected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Create files with different extensions
            pdf = tmpdir / "Gescannt_20260105-1000.pdf"
            jpg = tmpdir / "Gescannt_20260106-1000.jpg"
            jpeg = tmpdir / "Gescannt_20260107-1000.jpeg"
            png = tmpdir / "Gescannt_20260108-1000.png"
            txt = tmpdir / "Gescannt_20260109-1000.txt"  # Not supported
            docx = tmpdir / "Gescannt_20260110-1000.docx"  # Not supported
            
            for f in [pdf, jpg, jpeg, png, txt, docx]:
                f.touch()
            
            start_date = date(2026, 1, 5)
            end_date = date(2026, 1, 11)
            
            scans = collect_week_scans(tmpdir, start_date, end_date)
            
            # Should only collect pdf, jpg, jpeg, png
            assert len(scans) == 4
            extensions = {s.suffix.lower() for s in scans}
            assert extensions == {'.pdf', '.jpg', '.jpeg', '.png'}
    
    def test_collect_week_scans_empty(self):
        """Test collecting from an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            start_date = date(2026, 1, 5)
            end_date = date(2026, 1, 11)
            
            scans = collect_week_scans(tmpdir, start_date, end_date)
            
            assert scans == []
    
    def test_collect_week_scans_nonexistent_dir(self):
        """Test collecting from a non-existent directory."""
        tmpdir = Path("/nonexistent/directory")
        
        start_date = date(2026, 1, 5)
        end_date = date(2026, 1, 11)
        
        scans = collect_week_scans(tmpdir, start_date, end_date)
        
        assert scans == []

