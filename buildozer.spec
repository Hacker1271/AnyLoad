[app]

# App title and package name
title = AnyLoad
package.name = anyload
package.domain = com.anyload

# Source code directory
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# App version
version = 1.1

# Requirements - STRICTLY KivyMD 1.2.0
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pyjnius,android,requests,certifi,yt-dlp,sqlite3,libffi,openssl

# Permissions for Android 11-13+
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,POST_NOTIFICATIONS,ACCESS_NETWORK_STATE,WAKE_LOCK

# Android API and NDK
android.api = 33
android.minapi = 21
android.ndk = 25b

# Architectures (includes 32-bit for budget devices)
android.archs = arm64-v8a,armeabi-v7a

# App icon and presplash
#icon.filename = %(source.dir)s/assets/logo.png
#presplash.filename = %(source.dir)s/assets/logo.png

# Orientation
orientation = portrait

# Services
#services = DownloadService:service.py

# Android features
android.features = android.hardware.touchscreen

# Gradle dependencies
android.gradle_dependencies = 

# Java options
android.add_jars = 

# Android manifest
android.manifest.intent_filters = 

# Wakelock to prevent sleep during downloads
android.wakelock = True

# Logcat filters
android.logcat_filters = *:S python:D

# Copy library instead of symlinking
android.copy_libs = 1

# Skip update of included dependencies
android.skip_update = False

# Don't copy __pycache__
android.no_byte_compile_python = True

[buildozer]

# Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# Display warning if buildozer is run as root
warn_on_root = 1

# Build directory
build_dir = ./.buildozer

# Binary directory
bin_dir = ./bin
