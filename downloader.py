# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# ANYLOAD V1.1 - SMART DOWNLOAD ENGINE
# ═══════════════════════════════════════════════════════════════════════════
import os
import re
import time
import hashlib
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOM LOGGER FOR YT-DLP
# ═══════════════════════════════════════════════════════════════════════════
class MyLogger:
    """Custom logger for yt-dlp (prevents crash)"""
    def debug(self, msg):
        pass  # Suppress debug messages
    
    def warning(self, msg):
        pass  # Suppress warnings
    
    def error(self, msg):
        print(f"[yt-dlp] {msg}")


class DownloadEngine:
    """
    Elite download engine with:
    - Lazy yt-dlp import (prevents boot timeout)
    - Metadata fallback (no crash on extraction failure)
    - Unicode-safe filename sanitization
    - Progress hooks with speed/ETA
    - Pause/Resume/Cancel support (using .part file resume)
    """
    
    def __init__(
        self,
        url: str,
        mode: str,
        base_path: Path,
        progress_callback: Callable,
        task_id: str
    ):
        self.url = url
        self.mode = mode  # 'auto', 'audio', 'playlist'
        self.base_path = Path(base_path)
        self.progress_callback = progress_callback
        self.task_id = task_id
        
        # Control flags
        self.is_cancelled = False
        self.is_paused = False
        
        # Metadata
        self.title = "AnyLoad Media"
        self.thumbnail_url = None
        self.duration = None
        self.filesize = None
    
    def cancel(self):
        """Cancel the download"""
        self.is_cancelled = True
        print(f"[✓] Task {self.task_id} cancelled")
    
    def pause(self):
        """Pause the download (raises exception in progress hook)"""
        self.is_paused = True
        print(f"[✓] Task {self.task_id} paused")
    
    def run(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute download
        Returns: (success: bool, filepath: str, error: str)
        """
        # CRITICAL: Lazy import to prevent boot timeout
        try:
            import yt_dlp
        except ImportError:
            error = "yt-dlp not installed"
            print(f"[✗] {error}")
            return False, None, error
        
        # Step 1: Extract metadata (with fallback)
        self._extract_metadata_safe()
        
        # Step 2: Prepare download options
        opts = self._build_yt_dlp_options()
        
        # Step 3: Execute download with retries
        return self._execute_download(yt_dlp, opts)
    
    # ═══════════════════════════════════════════════════════════════════════
    # METADATA EXTRACTION (SAFE)
    # ═══════════════════════════════════════════════════════════════════════
    def _extract_metadata_safe(self):
        """
        Extract metadata with timeout and fallback
        If fails, use default values (NO CRASH)
        """
        try:
            import yt_dlp
            
            # Quick metadata extraction (no download)
            opts = {
                'logger': MyLogger(),
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'socket_timeout': 10,
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                
                if info:
                    self.title = self._sanitize_filename(
                        info.get('title', 'AnyLoad Media')
                    )
                    self.thumbnail_url = info.get('thumbnail')
                    self.duration = info.get('duration')
                    self.filesize = info.get('filesize') or info.get('filesize_approx')
                    
                    # Update UI with real title
                    self.progress_callback({
                        'task_id': self.task_id,
                        'filename': self.title,
                        'thumbnail': self._download_thumbnail(),
                        'progress': 0,
                        'speed': 'Starting...',
                        'eta': '--:--'
                    })
                    
                    print(f"[✓] Metadata extracted: {self.title}")
        
        except Exception as e:
            # FALLBACK: Use default values (NO CRASH)
            print(f"[!] Metadata extraction failed: {e}")
            print(f"[✓] Using fallback: {self.title}")
            
            self.progress_callback({
                'task_id': self.task_id,
                'filename': self.title,
                'thumbnail': 'assets/logo.png',
                'progress': 0,
                'speed': 'Connecting...',
                'eta': '--:--'
            })
    
    def _download_thumbnail(self) -> str:
        """Download thumbnail and cache locally"""
        if not self.thumbnail_url:
            return 'assets/logo.png'
        
        try:
            import requests
            import hashlib
            
            cache_dir = self.base_path / ".thumbnails"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            url_hash = hashlib.md5(self.thumbnail_url.encode()).hexdigest()
            cache_file = cache_dir / f"{url_hash}.jpg"
            
            if cache_file.exists():
                return str(cache_file)
            
            response = requests.get(self.thumbnail_url, timeout=10)
            response.raise_for_status()
            cache_file.write_bytes(response.content)
            print(f"[✓] Thumbnail downloaded: {cache_file.name}")
            
            return str(cache_file)
        except Exception as e:
            print(f"[!] Thumbnail download failed: {e}")
            return 'assets/logo.png'
    
    # ═══════════════════════════════════════════════════════════════════════
    # YT-DLP OPTIONS BUILDER
    # ═══════════════════════════════════════════════════════════════════════
    def _build_yt_dlp_options(self) -> dict:
        """Build yt-dlp options based on mode"""
        
        # Determine output directory
        if self.mode == 'audio':
            output_dir = self.base_path / "Audio"
        elif self.mode == 'playlist':
            output_dir = self.base_path / "Playlists"
        else:
            output_dir = self.base_path / "Videos"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Output template
        if self.mode == 'playlist':
            outtmpl = str(output_dir / '%(playlist_title)s' / '%(title)s.%(ext)s')
        else:
            outtmpl = str(output_dir / '%(title)s.%(ext)s')
        
        # Base options
        opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [self._progress_hook],
            'logger': MyLogger(),  # CRITICAL: Custom logger to prevent crash
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'continuedl': True,
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,
            'ignoreerrors': False,
            'encoding': 'utf-8',
            'restrictfilenames': False,  # Keep Unicode
            'windowsfilenames': False,
            'socket_timeout': 30,
        }
        
        # Mode-specific options
        if self.mode == 'audio':
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'writethumbnail': True,
                'embedthumbnail': True,
            })
        elif self.mode == 'playlist':
            opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'noplaylist': False,
            })
        else:  # auto (best quality)
            opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
            })
        
        return opts
    
    # ═══════════════════════════════════════════════════════════════════════
    # DOWNLOAD EXECUTION
    # ═══════════════════════════════════════════════════════════════════════
    def _execute_download(self, yt_dlp, opts: dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """Execute download with retry logic"""
        
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            if self.is_cancelled and not self.is_paused:
                return False, None, "Cancelled by user"
            
            try:
                print(f"[→] Download attempt {attempt}/{max_retries}")
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    # Download
                    info = ydl.extract_info(self.url, download=True)
                    
                    if self.is_cancelled and not self.is_paused:
                        return False, None, "Cancelled by user"
                    
                    # Get output filepath
                    if self.mode == 'playlist':
                        # For playlists, return the directory
                        filepath = str(self.base_path / "Playlists" / info.get('playlist_title', 'Playlist'))
                    else:
                        filepath = ydl.prepare_filename(info)
                        
                        # For audio, change extension to .mp3
                        if self.mode == 'audio':
                            filepath = Path(filepath).with_suffix('.mp3')
                    
                    print(f"[✓] Download completed: {filepath}")
                    return True, str(filepath), None
            
            except ValueError as e:
                if "PAUSED_BY_USER" in str(e):
                    print(f"[✓] Download paused, .part file preserved")
                    return False, None, "PAUSED"
                raise
            
            except Exception as e:
                error_msg = str(e)
                print(f"[✗] Attempt {attempt} failed: {error_msg}")
                
                # Check for HTTP 416 error (corrupted .part file)
                if "416" in error_msg or "Requested range not satisfiable" in error_msg:
                    print(f"[!] Corrupted .part file detected, cleaning up...")
                    self._cleanup_part_files("")
                
                # Check if error is fatal
                if self._is_fatal_error(error_msg):
                    return False, None, error_msg
                
                # Wait before retry
                if attempt < max_retries:
                    time.sleep(2 * attempt)
        
        # All retries failed
        return False, None, "Download failed after multiple attempts"
    
    # ═══════════════════════════════════════════════════════════════════════
    # PROGRESS HOOK
    # ═══════════════════════════════════════════════════════════════════════
    def _progress_hook(self, d: dict):
        """
        yt-dlp progress hook
        Called during download with progress info
        """
        # AGGRESSIVE CHECK: Check pause/cancel at the very start
        if self.is_paused or self.is_cancelled:
            if self.is_paused:
                raise ValueError("PAUSED_BY_USER")
            else:
                raise Exception("Download cancelled")
        
        if d['status'] == 'downloading':
            # Check again during download
            if self.is_paused or self.is_cancelled:
                if self.is_paused:
                    raise ValueError("PAUSED_BY_USER")
                else:
                    raise Exception("Download cancelled")
            
            # Extract progress data
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            
            # Calculate percentage
            if total > 0:
                progress = (downloaded / total) * 100
            else:
                progress = 0
            
            # Format speed
            if speed:
                if speed > 1024 * 1024:
                    speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                else:
                    speed_str = f"{speed / 1024:.1f} KB/s"
            else:
                speed_str = "-- KB/s"
            
            # Format ETA
            if eta:
                mins, secs = divmod(int(eta), 60)
                eta_str = f"{mins:02d}:{secs:02d}"
            else:
                eta_str = "--:--"
            
            # Send to UI
            self.progress_callback({
                'task_id': self.task_id,
                'filename': self.title,
                'progress': progress,
                'speed': speed_str,
                'eta': eta_str,
                'downloaded_bytes': downloaded,
                'total_bytes': total
            })
        
        elif d['status'] == 'finished':
            # Final check before marking as finished
            if self.is_paused:
                raise ValueError("PAUSED_BY_USER")
            if self.is_cancelled:
                raise Exception("Download cancelled")
            
            print(f"[✓] Download finished, processing...")
            self.progress_callback({
                'task_id': self.task_id,
                'filename': self.title,
                'progress': 100,
                'speed': 'Processing...',
                'eta': '00:00'
            })
    
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename while KEEPING Unicode characters
        Only remove filesystem-unsafe characters
        """
        # Remove filesystem-unsafe characters
        unsafe_chars = r'[<>:"/\\|?*]'
        filename = re.sub(unsafe_chars, '_', filename)
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        
        # Limit length (255 bytes for most filesystems)
        if len(filename.encode('utf-8')) > 200:
            filename = filename[:100]
        
        return filename or "AnyLoad_Media"
    
    def _is_fatal_error(self, error_msg: str) -> bool:
        """Check if error is fatal (no retry needed)"""
        fatal_keywords = [
            'private video',
            'copyright',
            'not available',
            'removed',
            'deleted',
            'geo-restricted',
            'sign in',
            'login required'
        ]
        
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in fatal_keywords)
    
    def _cleanup_part_files(self, outtmpl: str):
        """Delete corrupted .part files to allow fresh download"""
        try:
            # Determine output directory based on mode
            if self.mode == 'audio':
                output_dir = self.base_path / "Audio"
            elif self.mode == 'playlist':
                output_dir = self.base_path / "Playlists"
            else:
                output_dir = self.base_path / "Videos"
            
            # Find and delete all .part files in the directory
            if output_dir.exists():
                for part_file in output_dir.glob('*.part'):
                    try:
                        part_file.unlink()
                        print(f"[✓] Deleted corrupted file: {part_file.name}")
                    except Exception as e:
                        print(f"[!] Failed to delete {part_file.name}: {e}")
                
                # Also check for .part files with the sanitized title
                if self.title:
                    sanitized = self._sanitize_filename(self.title)
                    for part_file in output_dir.glob(f'{sanitized}*.part'):
                        try:
                            part_file.unlink()
                            print(f"[✓] Deleted corrupted file: {part_file.name}")
                        except Exception as e:
                            print(f"[!] Failed to delete {part_file.name}: {e}")
        
        except Exception as e:
            print(f"[!] Cleanup error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# THUMBNAIL DOWNLOADER
# ═══════════════════════════════════════════════════════════════════════════
class ThumbnailDownloader:
    """Download and cache video thumbnails"""
    
    @staticmethod
    def download(url: str, cache_dir: Path) -> Optional[str]:
        """
        Download thumbnail from URL
        Returns: cached filepath or None
        """
        if not url:
            return None
        
        try:
            import requests
            
            # Create cache directory
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate cache filename
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cache_file = cache_dir / f"{url_hash}.jpg"
            
            # Return if already cached
            if cache_file.exists():
                return str(cache_file)
            
            # Download
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Save
            cache_file.write_bytes(response.content)
            print(f"[✓] Thumbnail cached: {cache_file}")
            
            return str(cache_file)
        
        except Exception as e:
            print(f"[!] Thumbnail download failed: {e}")
            return None
    
    @staticmethod
    def extract_from_audio(audio_path: Path, cache_dir: Path) -> Optional[str]:
        """
        Extract embedded thumbnail from audio file
        Returns: cached filepath or None
        """
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, APIC
            
            # Generate cache filename
            file_hash = hashlib.md5(str(audio_path).encode()).hexdigest()
            cache_file = cache_dir / f"{file_hash}_audio.jpg"
            
            # Return if already cached
            if cache_file.exists():
                return str(cache_file)
            
            # Extract from ID3 tags
            audio = MP3(audio_path, ID3=ID3)
            
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    cache_file.write_bytes(tag.data)
                    print(f"[✓] Audio thumbnail extracted: {cache_file}")
                    return str(cache_file)
            
            return None
        
        except Exception as e:
            print(f"[!] Audio thumbnail extraction failed: {e}")
            return None
