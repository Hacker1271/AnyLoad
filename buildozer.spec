[app]

# (str) Title of your application
title = AnyLoad

# (str) Package name
package.name = anyload

# (str) Package domain (needed for android/ios packaging)
package.domain = com.hacker1271

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py, png, jpg, kv, ttf

# (str) Application versioning (method 1)
version = 1.1.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
# CRITICAL: Python version MUST match hostpython3 - p4a now uses 3.14.2
requirements = python3, kivy==2.3.0, kivymd==1.2.0, pyjnius, requests, certifi, yt-dlp, sqlite3, libffi, openssl
# (str) Presplash of the application
presplash.filename = %(source.dir)s/assets/logo.png

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/logo.png

# (str) Supported orientation (landscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE, READ_MEDIA_VIDEO, READ_MEDIA_AUDIO, POST_NOTIFICATIONS

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid network timeouts or macos fixes
android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only.
android.accept_sdk_license = True

# (str) Android entry point, default is ok for Kivy-based app
android.entrypoint = org.kivy.android.PythonActivity

# (list) The Android architectures to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) The format used to package the app for release mode (aab or apk or aar).
android.release_artifact = apk

# (str) The format used to package the app for debug mode (apk or aar).
android.debug_artifact = apk

# (str) Presplash background color (for android toolchain)
android.presplash_color = #0D0D0D

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

# (bool) Enable NDK API compatibility
android.ndk_api = 21

# (bool) Use legacy build system if needed
p4a.source_dir = 

# (str) Gradle dependencies
android.gradle_dependencies = 

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
