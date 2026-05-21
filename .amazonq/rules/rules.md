# 🚀 ANYLOAD V1.1 - AI & DEVELOPER MASTER INSTRUCTION GUIDE

**ATTENTION AI / DEVELOPER:** 
If you are reading this file, you are tasked with building, modifying, or debugging the "AnyLoad" Android Media Downloader app. You MUST strictly adhere to every rule in this document. Failure to do so will result in Android build failures, layout rendering issues, or silent crashes on budget devices (e.g., Unisoc processors).

---

## 🛑 1. CRITICAL CRASH-PREVENTION RULES (NON-NEGOTIABLE)

1. **The Radius Bug (`ValueError: 'border_radius' must have 4, got 0`):**
   - Kivy 2.3.0 is exceptionally strict about radius values.
   - ALL `radius` properties in `MDCard` or any rounded widgets MUST have exactly 4 values. 
   - **WRONG:** `radius: [15,]` or `radius: 15`
   - **CORRECT:** `radius: [15, 15, 15, 15]`

2. **KivyMD Version Mismatch (`KeyError: 'Caption'`):**
   - We are strictly using **KivyMD 1.2.0**.
   - Do NOT use Material 3 (v2.0) syntax. Use `font_style: "H6"`, `"Subtitle1"`, `"Caption"`. NEVER use `"body-small"`, `"title-large"`, etc.

3. **Navigation Layout Hierarchy (`NavigationDrawerContentError`):**
   - `MDNavigationLayout` can ONLY contain `ScreenManager` and `MDNavigationDrawer` as its direct children.
   - Do NOT put Top Bars or Bottom Navigation directly inside `MDNavigationLayout`. They must go inside the screens.

4. **The Black Screen Bug (Graphics Fix):**
   - The VERY FIRST LINE of `main.py` MUST BE: 
     `import os; os.environ['KIVY_GRAPHICS'] = 'sdl2'`

5. **Lazy Loading yt-dlp (Boot Timeout Crash):**
   - NEVER `import yt_dlp` globally at the top of `main.py` or `downloader.py`. Import it LOCALLY inside the background download thread to ensure the app boots in < 2 seconds.

6. **No FFmpeg Subprocess:**
   - Do NOT use `subprocess.run(['ffmpeg'])`. Android lacks this native binary. Rely entirely on `yt-dlp` formatting options.

7. **Android Background Anti-Kill:**
   - Add `def on_pause(self): return True` inside the main `MDApp` class.

8. **The Tofu Bug (□□□):**
   - Do NOT use special Unicode characters (like '●') for animated dots. Use Kivy `Canvas` (`Ellipse`) instructions.
   - Globally register `assets/NotoSans-Regular.ttf` for universal language support (Bengali, Arabic, etc.).

---

## 🏗️ 2. BUILDOZER & CI/CD RULES (PREVENT BUILD FAILS)

1. **Requirements:** `python3, kivy==2.3.0, kivymd==1.2.0, pyjnius, android, requests, certifi, yt-dlp, sqlite3, libffi, openssl`. (sqlite3, libffi, and openssl are MUST-HAVES for yt-dlp to work).
2. **Buildozer Specs:** Target `android.api = 33`, `android.ndk = 25b`, `android.archs = arm64-v8a, armeabi-v7a`.
3. **No Non-ASCII Characters:** Remove ALL non-English characters from `buildozer.spec` (even in comments) to prevent `UnicodeError`.
4. **GitHub Actions Fix:** In `.github/workflows/main.yml`, use `actions/upload-artifact@v4`. Add `unset ANDROID_HOME` and `unset ANDROID_SDK_ROOT` before the buildozer command to bypass GitHub's broken SDK path bug.

---

## 🎨 3. UI/UX BLUEPRINT (Dark & Teal Theme)

- **Theme Colors:** Pure Dark background (`#0D0D0D`), Teal Accents (`#00D2A0`), Card backgrounds (`#1A1A1A`).
- **Splash Screen:** Center Logo (`assets/logo.png`) + 3 blinking dots. Switches to 'home' after 3s.
- **Top Bar:** "ANYLOAD" horizontal title. 3 blinking dots below it (visible ONLY when `is_active_download == True`). Right-aligned hamburger menu.
- **Home Tab:** 
  - 3D pill-shaped URL input card with a paste button (auto moves cursor to index 0). 
  - 3 Solid Teal action pill-buttons: `Auto Best Quality`, `Audio Only`, `Playlist Download`.
- **Tasks Tab:** Horizontal TaskCards (Thumbnail, MP4 badge, Slim Progress bar, Speed, ETA). Buttons: Pause/Resume/Cancel. **Vanish Logic:** Card must vanish and move to Library on 100% completion.
- **Library Tab:** 3 Sub-tabs (Videos, Audio, Playlists). Reads from `sqlite3`. 3-dot menus for Details, Rename, Delete.
- **Configs Tab:** App Branding. Max download slider (1-5), Wi-Fi toggle, Change Path button.
- **Bottom Navigation:** Use `MDGridLayout` (cols: 4, size_hint_x: 1, spacing: 0, padding: 0) to align 4 tabs perfectly without overlapping icons/text.

---

## ⚙️ 4. APP ARCHITECTURE (5-FILE SYSTEM)

If you are asked to generate the app, break it into these files:
1. `main.py`: The Controller. Manages screens, Queue logic, thread-safe UI updates (`@mainthread`), and Android 13 permissions (`READ_MEDIA_VIDEO`, `READ_MEDIA_AUDIO`, `POST_NOTIFICATIONS`).
2. `ui.kv`: The View. Pure layout, no logic.
3. `downloader.py`: The Engine. Background `yt-dlp` execution with progress hooks. Implements fallback for metadata extraction.
4. `buildozer.spec`: The Android compilation config.
5. `.github/workflows/main.yml`: The CI/CD pipeline script.

---
**FINAL NOTE TO AI:** Do NOT auto-optimize or ignore the rules in section 1 and 2. They are hard-earned fixes for specific Kivy/Android bugs. Acknowledge this document before generating any code.