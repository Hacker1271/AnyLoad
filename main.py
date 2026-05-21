# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
# ANYLOAD V1.1 - ELITE PRODUCTION BUILD
# ═══════════════════════════════════════════════════════════════════════════
# CRITICAL: Graphics fix MUST be first line
import os
os.environ['KIVY_GRAPHICS'] = 'sdl2'

import sys
import threading
import re
from pathlib import Path
from datetime import datetime

# Kivy Core
from kivy.config import Config
Config.set('kivy', 'text_resource_encoding', 'utf-8')

from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.clipboard import Clipboard
from kivy.animation import Animation
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.utils import platform

# KivyMD (STRICTLY v1.2.0)
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.toast import toast as kivymd_toast

# App modules
from downloader import DownloadEngine, ThumbnailDownloader
from database import get_database

# Desktop testing
Window.size = (360, 800)

# ═══════════════════════════════════════════════════════════════════════════
# UNIVERSAL FONT REGISTRATION (NO TOFU)
# ═══════════════════════════════════════════════════════════════════════════
def register_universal_font():
    """Register NotoSans to support Bengali, Arabic, Japanese, etc."""
    font_path = Path(__file__).parent / "assets" / "NotoSans-Regular.ttf"
    if font_path.exists():
        LabelBase.register(
            name='Roboto',
            fn_regular=str(font_path),
            fn_bold=str(font_path),
            fn_italic=str(font_path),
            fn_bolditalic=str(font_path)
        )
        print(f"[✓] Universal Font Loaded: {font_path}")
    else:
        print("[!] Warning: NotoSans-Regular.ttf not found. Unicode may break.")

register_universal_font()


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOM WIDGETS
# ═══════════════════════════════════════════════════════════════════════════
class ActionButton(MDCard):
    """Premium 3D Pill Button with micro-animation"""
    text = StringProperty("")
    icon = StringProperty("")
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            anim = Animation(scale_x=0.95, scale_y=0.95, duration=0.1)
            anim.start(self)
            return super().on_touch_down(touch)
        return super().on_touch_down(touch)
    
    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            anim = Animation(scale_x=1.0, scale_y=1.0, duration=0.1)
            anim.start(self)
        return super().on_touch_up(touch)


class TaskCard(MDCard):
    """Premium 3-Layer Horizontal Task Card"""
    task_id = StringProperty("")
    url = StringProperty("")  # For resume
    mode = StringProperty("")  # For resume
    filename = StringProperty("Preparing...")
    thumbnail = StringProperty("assets/logo.png")
    badge = StringProperty("MP4")  # MP4 or MP3
    progress = NumericProperty(0)
    percent_text = StringProperty("0%")
    speed = StringProperty("-- KB/s")
    eta = StringProperty("--:--")
    size_info = StringProperty("0 MB / 0 MB")
    status = StringProperty("waiting")  # waiting, downloading, paused, completed, failed
    status_text = StringProperty("WAITING")
    bottom_row_text = StringProperty("WAITING  •  ETA --:--  •  0 MB / 0 MB")
    play_pause_icon = StringProperty("pause")
    is_paused = BooleanProperty(False)
    downloaded_bytes = NumericProperty(0)
    total_bytes = NumericProperty(0)
    
    def toggle_pause(self):
        app = MDApp.get_running_app()
        if self.is_paused:
            app.resume_task(self.task_id)
        else:
            app.pause_task(self.task_id)
    
    def cancel(self):
        app = MDApp.get_running_app()
        app.cancel_task(self.task_id)


class LibraryCard(MDCard):
    """Media Library Card with Thumbnail & Play"""
    filename = StringProperty("")
    thumbnail = StringProperty("assets/logo.png")
    filepath = StringProperty("")
    file_type = StringProperty("video")  # video or audio
    
    def play_media(self):
        """Play media when card is clicked"""
        app = MDApp.get_running_app()
        app.play_media(self.filepath)
    
    def show_options(self):
        """Show options menu (called by three-dots button)"""
        app = MDApp.get_running_app()
        app.show_file_options(self.filename, self.filepath)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP CLASS
# ═══════════════════════════════════════════════════════════════════════════
class AnyLoadApp(MDApp):
    # Active download indicator
    is_active_download = BooleanProperty(False)
    dot_text = StringProperty(".")
    
    # Queue Management
    active_tasks = ListProperty([])  # Currently downloading
    waiting_tasks = ListProperty([])  # Queued
    max_concurrent = NumericProperty(3)  # From configs
    
    # Task engines (task_id -> DownloadEngine)
    task_engines = {}
    
    # Dialog reference
    about_dialog = ObjectProperty(None)
    
    def build(self):
        """Build the app UI"""
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Teal"
        
        # Setup storage
        self._setup_storage()
        
        # Load UI
        return Builder.load_file("ui.kv")
    
    def on_start(self):
        """Post-build initialization"""
        # Request permissions after 1 second
        Clock.schedule_once(self._request_permissions, 1)
        
        # Start splash animation (only if ids are available)
        Clock.schedule_once(self._start_splash, 0.5)
        
        # Auto-switch to home after 3 seconds
        Clock.schedule_once(lambda dt: self._switch_screen('home'), 3)
        
        # Check clipboard
        Clock.schedule_once(self._check_clipboard, 4)
        
        # Load library
        Clock.schedule_once(lambda dt: self.refresh_library(), 3.5)
    
    def on_pause(self):
        """CRITICAL: Prevent Android from killing app in background"""
        return True
    
    def on_resume(self):
        """Resume from background"""
        return True
    
    # ═══════════════════════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════
    def _setup_storage(self):
        """Create app directories"""
        if platform == 'android':
            base = Path("/sdcard/Download/AnyLoad")
        else:
            base = Path.home() / "Downloads" / "AnyLoad"
        
        self.base_path = base
        for folder in ["Videos", "Audio", "Playlists", ".thumbnails", ".temp"]:
            (base / folder).mkdir(parents=True, exist_ok=True)
        
        # Vault .nomedia
        vault = base / "Vault"
        vault.mkdir(exist_ok=True)
        (vault / ".nomedia").touch()
        
        # Initialize database
        self.db = get_database(base)
        
        print(f"[✓] Storage initialized: {base}")
    
    def _request_permissions(self, dt):
        """Request Android 13+ permissions"""
        if platform != 'android':
            return
        
        try:
            from android.permissions import request_permissions, Permission
            from android import api_version
            
            perms = [Permission.INTERNET]
            
            if api_version >= 33:  # Android 13+
                perms.extend([
                    Permission.READ_MEDIA_VIDEO,
                    Permission.READ_MEDIA_AUDIO,
                    Permission.POST_NOTIFICATIONS
                ])
            else:
                perms.extend([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE
                ])
            
            request_permissions(perms)
            print("[✓] Permissions requested")
        except Exception as e:
            print(f"[!] Permission error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # SPLASH & ANIMATIONS
    # ═══════════════════════════════════════════════════════════════════════
    def _start_splash(self, dt):
        """Animate splash dots"""
        # Skip if root not ready
        if not self.root or not hasattr(self.root, 'ids'):
            return
        
        try:
            # Simple animation - just let it show
            pass
        except Exception as e:
            print(f"[!] Splash animation error: {e}")
    
    def _switch_screen(self, screen_name):
        """Switch screen with validation"""
        try:
            self.root.ids.content_manager.current = screen_name
        except Exception as e:
            print(f"[!] Screen switch error: {e}")
    
    def start_download_indicator(self):
        """Start top bar animated dots"""
        self.is_active_download = True
        self._animate_top_dots()
    
    def stop_download_indicator(self):
        """Stop top bar animated dots"""
        self.is_active_download = False
        self.dot_text = "."
    
    def _animate_top_dots(self):
        """Animate top bar dots with text cycling"""
        if not self.is_active_download:
            return
        
        def cycle_dots(dt):
            if not self.is_active_download:
                self.dot_text = "."
                return
            
            if self.dot_text == ".":
                self.dot_text = ".."
            elif self.dot_text == "..":
                self.dot_text = "..."
            else:
                self.dot_text = "."
        
        Clock.schedule_interval(cycle_dots, 0.5)
    
    # ═══════════════════════════════════════════════════════════════════════
    # NAVIGATION & DIALOGS
    # ═══════════════════════════════════════════════════════════════════════
    def open_drawer(self):
        """Open navigation drawer"""
        try:
            self.root.ids.nav_drawer.set_state("open")
        except Exception as e:
            print(f"[!] Drawer open error: {e}")
    
    def close_drawer(self):
        """Close navigation drawer"""
        try:
            self.root.ids.nav_drawer.set_state("close")
        except Exception as e:
            print(f"[!] Drawer close error: {e}")
    
    def show_download_history(self):
        """Navigate to library screen"""
        self.close_drawer()
        try:
            self.root.ids.content_manager.current = 'library'
        except Exception as e:
            print(f"[!] Navigate to library error: {e}")
    
    def show_supported_sites(self):
        """Show supported platforms dialog"""
        self.close_drawer()
        
        sites_text = """• YouTube (Videos & Playlists)
• Facebook (Videos & Stories)
• Instagram (Posts, Reels, Stories)
• Twitter/X (Videos)
• TikTok (Videos)
• SoundCloud (Audio)
• Vimeo (Videos)
• Dailymotion (Videos)
• Reddit (Videos)
• And 1000+ more sites!

Powered by yt-dlp engine."""
        
        dialog = MDDialog(
            title="Supported Platforms",
            text=sites_text,
            size_hint=(0.85, None),
            md_bg_color=(0.1, 0.1, 0.1, 1),
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="CLOSE",
                    font_name="Roboto",
                    theme_text_color="Custom",
                    text_color=(0, 0.82, 0.63, 1),
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        
        # Apply fonts
        dialog.ids.title.font_name = "Roboto"
        dialog.ids.title.theme_text_color = "Custom"
        dialog.ids.title.text_color = (1, 1, 1, 1)
        dialog.ids.text.font_name = "Roboto"
        dialog.ids.text.theme_text_color = "Custom"
        dialog.ids.text.text_color = (0.85, 0.85, 0.85, 1)
        
        dialog.open()
    
    def share_app(self):
        """Share app via Android native share"""
        self.close_drawer()
        
        try:
            if platform != 'android':
                self.show_toast("Share is only available on Android")
                return
            
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            String = autoclass('java.lang.String')
            
            # Get current activity
            currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
            
            # Create share message
            share_message = "Download AnyLoad: The fastest, ad-free media downloader for Android! \ud83d\ude80"
            
            # Create share intent
            intent = Intent(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_TEXT, share_message)
            
            # Create chooser
            chooser = Intent.createChooser(intent, cast('java.lang.CharSequence', String("Share AnyLoad via")))
            currentActivity.startActivity(chooser)
            
            print("[\u2713] Share intent launched")
        
        except Exception as e:
            print(f"[!] Share app error: {e}")
            import traceback
            traceback.print_exc()
            self.show_toast("Failed to share")
    
    def show_report_issue(self):
        """Show report issue dialog"""
        self.close_drawer()
        
        report_text = """Found a bug or issue?

Please report it to:

\u2709\ufe0f Email: support@anyload.app
\ud83d\udc1b GitHub: github.com/anyload/issues

Include:
\u2022 Device model
\u2022 Android version
\u2022 Steps to reproduce
\u2022 Screenshots (if possible)

We appreciate your feedback!"""
        
        dialog = MDDialog(
            title="Report an Issue",
            text=report_text,
            size_hint=(0.85, None),
            md_bg_color=(0.1, 0.1, 0.1, 1),
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="CLOSE",
                    font_name="Roboto",
                    theme_text_color="Custom",
                    text_color=(0, 0.82, 0.63, 1),
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        
        # Apply fonts
        dialog.ids.title.font_name = "Roboto"
        dialog.ids.title.theme_text_color = "Custom"
        dialog.ids.title.text_color = (1, 1, 1, 1)
        dialog.ids.text.font_name = "Roboto"
        dialog.ids.text.theme_text_color = "Custom"
        dialog.ids.text.text_color = (0.85, 0.85, 0.85, 1)
        
        dialog.open()
    
    def show_about_dialog(self):
        """Show premium about dialog"""
        self.close_drawer()
        
        about_text = """AnyLoad is a premium, lightweight media downloader.

\ud83d\ude80 KEY FEATURES:
\u2022 Powered by yt-dlp engine
\u2022 High-quality downloads
\u2022 Universal Unicode support
\u2022 Intelligent queue management
\u2022 1000+ supported sites

\ud83d\udee1\ufe0f PHILOSOPHY:
\u2022 No Ads, No Bloatware
\u2022 Privacy-focused
\u2022 Open architecture

\ud83d\udc68\u200d\ud83d\udcbb DEVELOPER:
Built with \u2764\ufe0f by Nirob & AI Partner

Version 1.1.0
\u00a9 2024 AnyLoad"""
        
        dialog = MDDialog(
            title="About AnyLoad",
            text=about_text,
            size_hint=(0.85, None),
            md_bg_color=(0.1, 0.1, 0.1, 1),
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="CLOSE",
                    font_name="Roboto",
                    theme_text_color="Custom",
                    text_color=(0, 0.82, 0.63, 1),
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        
        # Apply fonts
        dialog.ids.title.font_name = "Roboto"
        dialog.ids.title.theme_text_color = "Custom"
        dialog.ids.title.text_color = (1, 1, 1, 1)
        dialog.ids.text.font_name = "Roboto"
        dialog.ids.text.theme_text_color = "Custom"
        dialog.ids.text.text_color = (0.85, 0.85, 0.85, 1)
        
        dialog.open()
    
    def switch_to_configs(self):
        """Switch to configs screen"""
        try:
            self.root.ids.content_manager.current = 'configs'
        except Exception as e:
            print(f"[!] Switch to configs error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # CLIPBOARD & URL VALIDATION
    # ═══════════════════════════════════════════════════════════════════════
    def _check_clipboard(self, dt):
        """Check if clipboard has URL"""
        try:
            text = Clipboard.paste()
            if text and ("http://" in text or "https://" in text):
                self.show_toast("🔗 Link detected in clipboard!")
        except Exception as e:
            print(f"[!] Clipboard check error: {e}")
    
    def paste_url(self):
        """Smart paste with cursor reset"""
        try:
            text = Clipboard.paste()
            if text:
                url_field = self.root.ids.url_input
                url_field.text = text.strip()
                url_field.cursor = (0, 0)  # Move cursor to start
                self.validate_url()
                self.show_toast("✓ Pasted")
        except Exception as e:
            print(f"[!] Paste error: {e}")
    
    def validate_url(self):
        """Real-time URL validation"""
        try:
            url = self.root.ids.url_input.text.strip()
            error_label = self.root.ids.url_error
            
            if not url:
                error_label.text = "URL cannot be empty"
                error_label.opacity = 1
                return False
            
            if not re.match(r'https?://', url):
                error_label.text = "Invalid URL format"
                error_label.opacity = 1
                return False
            
            error_label.opacity = 0
            return True
        except Exception as e:
            print(f"[!] Validation error: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # DOWNLOAD FLOW
    # ═══════════════════════════════════════════════════════════════════════
    def start_download(self, mode):
        """
        Start download with queue management
        mode: 'auto', 'audio', 'playlist'
        """
        if not self.validate_url():
            return
        
        url = self.root.ids.url_input.text.strip()
        
        # Generate task ID
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        # Create task card
        task_data = {
            'task_id': task_id,
            'url': url,
            'mode': mode,
            'filename': 'Connecting...',
            'thumbnail': 'assets/logo.png',
            'badge': 'MP3' if mode == 'audio' else 'MP4',
            'progress': 0,
            'speed': '-- KB/s',
            'eta': '--:--',
            'status': 'waiting'
        }
        
        # Add to queue
        if len(self.active_tasks) < self.max_concurrent:
            self.active_tasks.append(task_id)
            task_data['status'] = 'downloading'
            self._execute_download(task_data)
        else:
            self.waiting_tasks.append(task_id)
        
        # Add card to UI
        self._add_task_card(task_data)
        
        # Switch to tasks tab
        self.root.ids.content_manager.current = 'tasks'
        
        # Start indicator
        self.start_download_indicator()
    
    @mainthread
    def _add_task_card(self, task_data):
        """Add task card to UI"""
        try:
            container = self.root.ids.task_container
            
            # Remove empty label if exists
            for widget in container.children[:]:
                if isinstance(widget, MDLabel) and widget.text == "No active downloads":
                    container.remove_widget(widget)
                    break
            
            # Create card
            card = TaskCard(**task_data)
            container.add_widget(card)
            print(f"[✓] Task card added: {task_data['task_id']}")
        except Exception as e:
            print(f"[!] Add task card error: {e}")
            import traceback
            traceback.print_exc()
    
    def _execute_download(self, task_data):
        """Execute download in background thread"""
        def download_thread():
            task_id = task_data['task_id']
            
            # Create download engine
            engine = DownloadEngine(
                url=task_data['url'],
                mode=task_data['mode'],
                base_path=self.base_path,
                progress_callback=self._on_progress_update,
                task_id=task_id
            )
            
            # Store engine reference
            self.task_engines[task_id] = engine
            
            # Execute download
            success, filepath, error = engine.run()
            
            # Remove engine reference
            if task_id in self.task_engines:
                del self.task_engines[task_id]
            
            # Handle result
            if success:
                self._on_download_complete(task_id, filepath)
            else:
                self._on_download_failed(task_id, error or "Download failed")
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    @mainthread
    def _on_progress_update(self, data):
        """Handle progress updates from download engine"""
        task_id = data.pop('task_id')
        self._update_task_progress(task_id, **data)
    
    @mainthread
    def _update_task_progress(self, task_id, **kwargs):
        """Update task card progress with combined bottom row"""
        try:
            container = self.root.ids.task_container
            for card in container.children:
                if isinstance(card, TaskCard) and card.task_id == task_id:
                    # Update individual properties
                    for key, value in kwargs.items():
                        setattr(card, key, value)
                    
                    # Build combined bottom row text
                    status_map = {
                        'waiting': 'WAITING',
                        'downloading': 'DOWNLOADING',
                        'paused': 'PAUSED',
                        'completed': 'COMPLETED',
                        'failed': 'FAILED'
                    }
                    card.status_text = status_map.get(card.status, 'UNKNOWN')
                    card.percent_text = f"{int(card.progress)}%"
                    card.play_pause_icon = "play" if card.is_paused else "pause"
                    card.bottom_row_text = f"{card.status_text}  •  ETA {card.eta}  •  {card.size_info}"
                    break
        except Exception as e:
            print(f"[!] Update progress error: {e}")
    
    @mainthread
    def _on_download_complete(self, task_id, filepath):
        """Handle download completion"""
        try:
            # Update card to 100%
            self._update_task_progress(task_id, progress=100, status='completed')
            
            # Save to database
            if filepath:
                file_path = Path(filepath)
                file_type = 'audio' if file_path.suffix == '.mp3' else 'video'
                
                # Get file size
                size_bytes = file_path.stat().st_size if file_path.exists() else 0
                
                # Download thumbnail
                thumbnail_path = None
                if file_type == 'audio':
                    thumbnail_path = ThumbnailDownloader.extract_from_audio(
                        file_path,
                        self.base_path / ".thumbnails"
                    )
                
                # Save to database
                self.db.add_media(
                    filepath=str(file_path),
                    filename=file_path.name,
                    file_type=file_type,
                    size_bytes=size_bytes,
                    thumbnail_path=thumbnail_path
                )
            
            # Wait 2s then remove card
            Clock.schedule_once(lambda dt: self._remove_task_card(task_id), 2)
            
            # Refresh library
            Clock.schedule_once(lambda dt: self.refresh_library(), 2.5)
            
            # Remove from active tasks
            if task_id in self.active_tasks:
                self.active_tasks.remove(task_id)
            
            # Start next waiting task
            self._start_next_waiting_task()
            
            # Show notification
            self.show_toast("✓ Download completed!")
        except Exception as e:
            print(f"[!] Complete handler error: {e}")
    
    @mainthread
    def _on_download_failed(self, task_id, error):
        """Handle download failure"""
        try:
            # Check if it's a pause (not a real failure)
            if error == "PAUSED":
                self._update_task_progress(
                    task_id, 
                    status='paused', 
                    is_paused=True,
                    speed='Paused'
                )
                print(f"[✓] Task {task_id} paused successfully")
            else:
                self._update_task_progress(task_id, status='failed', speed=error)
            
            if task_id in self.active_tasks:
                self.active_tasks.remove(task_id)
            
            self._start_next_waiting_task()
        except Exception as e:
            print(f"[!] Failed handler error: {e}")
    
    def _start_next_waiting_task(self):
        """Start next task from waiting queue"""
        if self.waiting_tasks and len(self.active_tasks) < self.max_concurrent:
            next_task_id = self.waiting_tasks.pop(0)
            self.active_tasks.append(next_task_id)
            
            # Update card status and start download
            # (Implementation in PART 2)
        
        # Stop indicator if no active tasks
        if not self.active_tasks:
            self.stop_download_indicator()
    
    @mainthread
    def _remove_task_card(self, task_id):
        """Remove task card from UI"""
        try:
            container = self.root.ids.task_container
            for card in container.children[:]:
                if isinstance(card, TaskCard) and card.task_id == task_id:
                    container.remove_widget(card)
                    print(f"[✓] Task card removed: {task_id}")
                    break
            
            # Show empty label if no tasks
            if not any(isinstance(w, TaskCard) for w in container.children):
                empty_label = MDLabel(
                    text="No active downloads",
                    font_style="Subtitle1",
                    theme_text_color="Hint",
                    halign="center",
                    size_hint_y=None,
                    height="50dp"
                )
                container.add_widget(empty_label)
        except Exception as e:
            print(f"[!] Remove card error: {e}")
    
    def pause_task(self, task_id):
        """Pause a download task"""
        try:
            # Check if task is already completed
            container = self.root.ids.task_container
            for card in container.children:
                if isinstance(card, TaskCard) and card.task_id == task_id:
                    if card.status == 'completed':
                        print(f"[!] Task {task_id} already completed, ignoring pause")
                        return
                    break
            
            if task_id in self.task_engines:
                self.task_engines[task_id].pause()
                print(f"[✓] Pause signal sent to task {task_id}")
        except Exception as e:
            print(f"[!] Pause error: {e}")
    
    def resume_task(self, task_id):
        """Resume a paused task by spawning new thread"""
        try:
            # Find the task card to get URL and mode
            container = self.root.ids.task_container
            task_card = None
            
            for card in container.children:
                if isinstance(card, TaskCard) and card.task_id == task_id:
                    task_card = card
                    break
            
            if not task_card:
                print(f"[!] Task card not found for {task_id}")
                return
            
            # Update UI state
            self._update_task_progress(
                task_id, 
                is_paused=False, 
                status='downloading',
                speed='Resuming...'
            )
            
            # Spawn new download thread (yt-dlp will resume from .part file)
            task_data = {
                'task_id': task_id,
                'url': task_card.url,
                'mode': task_card.mode
            }
            
            self._execute_download(task_data)
            print(f"[✓] Resume thread spawned for task {task_id}")
        
        except Exception as e:
            print(f"[!] Resume error: {e}")
    
    def cancel_task(self, task_id):
        """Cancel a download task"""
        try:
            # Cancel engine
            if task_id in self.task_engines:
                self.task_engines[task_id].cancel()
                del self.task_engines[task_id]
            
            # Mark as cancelled
            self._update_task_progress(task_id, status='cancelled')
            
            # Remove from queues
            if task_id in self.active_tasks:
                self.active_tasks.remove(task_id)
            if task_id in self.waiting_tasks:
                self.waiting_tasks.remove(task_id)
            
            # Remove card
            self._remove_task_card(task_id)
            
            # Start next waiting task
            self._start_next_waiting_task()
        except Exception as e:
            print(f"[!] Cancel error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # LIBRARY
    # ═══════════════════════════════════════════════════════════════════════
    @mainthread
    def refresh_library(self):
        """Refresh library from filesystem"""
        try:
            videos = []
            audios = []
            
            # Get from database
            video_records = self.db.get_all_media('video')
            audio_records = self.db.get_all_media('audio')
            
            # Format for RecycleView
            for record in video_records:
                if Path(record['filepath']).exists():
                    videos.append({
                        'filename': record['filename'],
                        'thumbnail': record['thumbnail_path'] or 'assets/logo.png',
                        'filepath': record['filepath'],
                        'file_type': 'video'
                    })
            
            for record in audio_records:
                if Path(record['filepath']).exists():
                    audios.append({
                        'filename': record['filename'],
                        'thumbnail': record['thumbnail_path'] or 'assets/logo.png',
                        'filepath': record['filepath'],
                        'file_type': 'audio'
                    })
            
            # Update RecycleViews
            self.root.ids.video_rv.data = videos
            self.root.ids.audio_rv.data = audios
            
            print(f"[✓] Library refreshed: {len(videos)} videos, {len(audios)} audios")
        except Exception as e:
            print(f"[!] Library refresh error: {e}")
    
    def play_media(self, filepath):
        """Play media file"""
        try:
            if platform == 'android':
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                
                intent = Intent(Intent.ACTION_VIEW)
                uri = Uri.fromFile(File(filepath))
                mime = "video/*" if filepath.endswith('.mp4') else "audio/*"
                intent.setDataAndType(uri, mime)
                PythonActivity.mActivity.startActivity(intent)
            else:
                import subprocess
                if sys.platform == 'linux':
                    subprocess.Popen(['xdg-open', filepath])
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', filepath])
                elif sys.platform == 'win32':
                    os.startfile(filepath)
        except Exception as e:
            print(f"[!] Play media error: {e}")
            self.show_toast("Failed to open media")
    
    def show_file_options(self, filename, filepath):
        """Show compact premium options modal"""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.list import MDList, OneLineIconListItem
        from kivymd.uix.list import IconLeftWidget
        
        # Create compact list container
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=0,
            padding=0
        )
        
        # Create list
        options_list = MDList(
            spacing=0,
            padding=0
        )
        
        # Custom list item class with reduced height
        class CompactOptionItem(OneLineIconListItem):
            def __init__(self, text, icon, icon_color, action_callback, **kwargs):
                super().__init__(**kwargs)
                self.text = text
                self.font_name = "Roboto"
                self.theme_text_color = "Custom"
                self.text_color = (1, 1, 1, 1)
                self._height = 48
                self.action_callback = action_callback
                
                # Add icon
                icon_widget = IconLeftWidget(icon=icon)
                icon_widget.theme_text_color = "Custom"
                icon_widget.text_color = icon_color
                self.add_widget(icon_widget)
            
            def on_release(self):
                self.action_callback()
        
        # Store dialog reference
        dialog_ref = [None]
        
        def create_action(action_type):
            def action():
                if dialog_ref[0]:
                    dialog_ref[0].dismiss()
                Clock.schedule_once(lambda dt: self._execute_file_action(action_type, filename, filepath), 0.2)
            return action
        
        # Add compact options
        options_list.add_widget(
            CompactOptionItem(
                text="Share",
                icon="share-variant",
                icon_color=(0, 0.82, 0.63, 1),
                action_callback=create_action('share')
            )
        )
        
        options_list.add_widget(
            CompactOptionItem(
                text="Rename",
                icon="pencil",
                icon_color=(0, 0.82, 0.63, 1),
                action_callback=create_action('rename')
            )
        )
        
        options_list.add_widget(
            CompactOptionItem(
                text="Details",
                icon="information-outline",
                icon_color=(0, 0.82, 0.63, 1),
                action_callback=create_action('details')
            )
        )
        
        options_list.add_widget(
            CompactOptionItem(
                text="Delete",
                icon="delete",
                icon_color=(0.8, 0.2, 0.2, 1),
                action_callback=create_action('delete')
            )
        )
        
        content.add_widget(options_list)
        
        # Create compact dialog
        dialog = MDDialog(
            title=filename,
            type="custom",
            content_cls=content,
            size_hint=(0.75, None),
            width="280dp",
            md_bg_color=(0.1, 0.1, 0.1, 1),
            radius=[20, 20, 20, 20]
        )
        
        # Apply title font
        dialog.ids.title.font_name = "Roboto"
        dialog.ids.title.theme_text_color = "Custom"
        dialog.ids.title.text_color = (1, 1, 1, 1)
        
        dialog_ref[0] = dialog
        dialog.open()
    
    def _execute_file_action(self, action, filename, filepath):
        """Execute file action after dialog dismissal"""
        if action == 'share':
            self.share_file(filepath)
        elif action == 'rename':
            self.rename_file(filename, filepath)
        elif action == 'details':
            self.show_details(filepath)
        elif action == 'delete':
            self.delete_file(filename, filepath)
    
    def share_file(self, filepath):
        """Share file using Android native share"""
        try:
            if platform != 'android':
                self.show_toast("Share is only available on Android")
                return
            
            from jnius import autoclass, cast
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            String = autoclass('java.lang.String')
            Uri = autoclass('android.net.Uri')
            File = autoclass('java.io.File')
            FileProvider = autoclass('androidx.core.content.FileProvider')
            
            # Get current activity
            currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
            
            # Create file object
            file_obj = File(filepath)
            
            # Get file URI using FileProvider (Android 7+)
            try:
                authority = currentActivity.getPackageName() + ".fileprovider"
                uri = FileProvider.getUriForFile(currentActivity, authority, file_obj)
            except:
                # Fallback for older Android
                uri = Uri.fromFile(file_obj)
            
            # Determine MIME type
            mime_type = "video/*" if filepath.endswith('.mp4') else "audio/*"
            
            # Create share intent
            intent = Intent(Intent.ACTION_SEND)
            intent.setType(mime_type)
            intent.putExtra(Intent.EXTRA_STREAM, uri)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            
            # Create chooser
            chooser = Intent.createChooser(intent, cast('java.lang.CharSequence', String("Share via")))
            currentActivity.startActivity(chooser)
            
            print(f"[✓] Share intent launched for: {filepath}")
        
        except Exception as e:
            print(f"[!] Share error: {e}")
            import traceback
            traceback.print_exc()
            self.show_toast("Failed to share file")
    
    def rename_file(self, old_filename, old_filepath):
        """Show compact rename dialog"""
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.boxlayout import MDBoxLayout
        
        # Create compact text field container
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            padding=["10dp", "5dp"],
            spacing="10dp"
        )
        
        # Create text field
        text_field = MDTextField(
            text=old_filename,
            hint_text="Enter new filename",
            font_name="Roboto",
            mode="rectangle",
            size_hint_x=1,
            multiline=False
        )
        
        content.add_widget(text_field)
        
        # Create compact dialog
        dialog = MDDialog(
            title="Rename File",
            type="custom",
            content_cls=content,
            size_hint=(0.8, None),
            md_bg_color=(0.1, 0.1, 0.1, 1),
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    font_name="Roboto",
                    theme_text_color="Custom",
                    text_color=(0.5, 0.5, 0.5, 1),
                    on_release=lambda x: dialog.dismiss()
                ),
                MDFlatButton(
                    text="RENAME",
                    font_name="Roboto",
                    theme_text_color="Custom",
                    text_color=(0, 0.82, 0.63, 1),
                    on_release=lambda x: self._confirm_rename(old_filepath, text_field.text, dialog)
                )
            ]
        )
        
        # Apply title font
        dialog.ids.title.font_name = "Roboto"
        dialog.ids.title.theme_text_color = "Custom"
        dialog.ids.title.text_color = (1, 1, 1, 1)
        
        dialog.open()
    
    def _confirm_rename(self, old_filepath, new_filename, dialog):
        """Execute rename operation"""
        dialog.dismiss()
        
        try:
            old_path = Path(old_filepath)
            
            # Validate new filename
            if not new_filename or new_filename.strip() == "":
                self.show_toast("Filename cannot be empty")
                return
            
            # Sanitize filename
            new_filename = new_filename.strip()
            
            # Keep original extension
            if not new_filename.endswith(old_path.suffix):
                new_filename += old_path.suffix
            
            # Create new path
            new_path = old_path.parent / new_filename
            
            # Check if file exists
            if not old_path.exists():
                self.show_toast("Original file not found")
                self.db.delete_media(old_filepath)
                self.refresh_library()
                return
            
            # Check if new name already exists
            if new_path.exists() and new_path != old_path:
                self.show_toast("File with this name already exists")
                return
            
            # Rename physical file
            old_path.rename(new_path)
            
            # Update database
            self.db.update_media_path(str(old_path), str(new_path))
            
            # Refresh library
            self.refresh_library()
            
            self.show_toast(f"✓ Renamed to {new_filename}")
            print(f"[✓] File renamed: {old_path} -> {new_path}")
        
        except Exception as e:
            print(f"[!] Rename error: {e}")
            import traceback
            traceback.print_exc()
            self.show_toast("Failed to rename file")
    
    def show_details(self, filepath):
        """Show compact file details dialog"""
        try:
            # Get media info from database
            media = self.db.get_media_by_path(filepath)
            
            if not media:
                self.show_toast("File details not found")
                return
            
            # Check if file exists
            file_path = Path(filepath)
            file_exists = file_path.exists()
            
            # Format size
            size_mb = media['size_bytes'] / (1024 * 1024) if media['size_bytes'] else 0
            size_str = f"{size_mb:.2f} MB"
            
            # Format date
            try:
                date_obj = datetime.fromisoformat(media['download_date'])
                date_str = date_obj.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = media['download_date']
            
            # Build compact details text
            details = f"""Type: {media['file_type'].upper()}
Format: {media['format'] or 'Unknown'}
Quality: {media['quality'] or 'Unknown'}
Size: {size_str}
Date: {date_str}
Status: {'✓ Exists' if file_exists else '✗ Missing'}"""
            
            # Create compact dialog
            dialog = MDDialog(
                title=media['filename'],
                text=details,
                size_hint=(0.8, None),
                md_bg_color=(0.1, 0.1, 0.1, 1),
                radius=[20, 20, 20, 20],
                buttons=[
                    MDFlatButton(
                        text="CLOSE",
                        font_name="Roboto",
                        theme_text_color="Custom",
                        text_color=(0, 0.82, 0.63, 1),
                        on_release=lambda x: dialog.dismiss()
                    )
                ]
            )
            
            # Apply fonts
            dialog.ids.title.font_name = "Roboto"
            dialog.ids.title.theme_text_color = "Custom"
            dialog.ids.title.text_color = (1, 1, 1, 1)
            dialog.ids.text.font_name = "Roboto"
            dialog.ids.text.theme_text_color = "Custom"
            dialog.ids.text.text_color = (0.85, 0.85, 0.85, 1)
            
            dialog.open()
        
        except Exception as e:
            print(f"[!] Show details error: {e}")
            import traceback
            traceback.print_exc()
            self.show_toast("Failed to load details")
    
    def delete_file(self, filename, filepath):
        """Show compact delete confirmation dialog"""
        dialog = MDDialog(
            title="Delete File?",
            text=f"Are you sure you want to delete:\n{filename}\n\nThis cannot be undone.",
            size_hint=(0.8, None),
            md_bg_color=(0.1, 0.1, 0.1, 1),
            radius=[20, 20, 20, 20],
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    font_name="Roboto",
                    theme_text_color="Custom",
                    text_color=(0.5, 0.5, 0.5, 1),
                    on_release=lambda x: dialog.dismiss()
                ),
                MDFlatButton(
                    text="DELETE",
                    font_name="Roboto",
                    theme_text_color="Custom",
                    text_color=(0.8, 0.2, 0.2, 1),
                    on_release=lambda x: self._confirm_delete(filepath, dialog)
                )
            ]
        )
        
        # Apply fonts
        dialog.ids.title.font_name = "Roboto"
        dialog.ids.title.theme_text_color = "Custom"
        dialog.ids.title.text_color = (1, 1, 1, 1)
        dialog.ids.text.font_name = "Roboto"
        dialog.ids.text.theme_text_color = "Custom"
        dialog.ids.text.text_color = (0.85, 0.85, 0.85, 1)
        
        dialog.open()
    
    def _confirm_delete(self, filepath, dialog):
        """Execute delete operation"""
        dialog.dismiss()
        
        try:
            file_path = Path(filepath)
            
            # Get media info for thumbnail
            media = self.db.get_media_by_path(filepath)
            
            # Delete physical file
            if file_path.exists():
                file_path.unlink()
                print(f"[✓] File deleted: {filepath}")
            else:
                print(f"[!] File not found: {filepath}")
            
            # Delete thumbnail if exists
            if media and media['thumbnail_path']:
                thumb_path = Path(media['thumbnail_path'])
                if thumb_path.exists():
                    thumb_path.unlink()
                    print(f"[✓] Thumbnail deleted: {media['thumbnail_path']}")
            
            # Delete from database
            self.db.delete_media(filepath)
            
            # Refresh library
            self.refresh_library()
            
            self.show_toast("✓ File deleted")
        
        except Exception as e:
            print(f"[!] Delete error: {e}")
            import traceback
            traceback.print_exc()
            self.show_toast("Failed to delete file")
    
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════
    def show_toast(self, message):
        """Show toast notification"""
        print(f"[TOAST] {message}")
        try:
            if platform == 'android':
                kivymd_toast(message)
            else:
                # Desktop fallback
                kivymd_toast(message)
        except Exception as e:
            print(f"[!] Toast error: {e}")



# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    AnyLoadApp().run()
