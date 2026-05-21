# 🚀 AnyLoad - CI/CD Setup Guide

## ✅ Complete Automated Build System

This repository is configured for **fully automated Android APK builds** via GitHub Actions. Every push to `main` branch triggers a production-ready APK build.

---

## 📦 What's Included

### 1. **buildozer.spec** (Production-Ready)
- ✅ App: AnyLoad v1.1.0
- ✅ Package: com.nirob.anyload
- ✅ API Level: 33 (Android 13)
- ✅ NDK: 25b
- ✅ Architectures: arm64-v8a, armeabi-v7a (64-bit + 32-bit)
- ✅ All yt-dlp dependencies included
- ✅ Android 13+ permissions configured

### 2. **.github/workflows/main.yml** (CI/CD Pipeline)
- ✅ Ubuntu 22.04 runner
- ✅ Python 3.11
- ✅ JDK 17 (Temurin)
- ✅ Cython 0.29.33 (stability)
- ✅ SDK environment fix (critical)
- ✅ Artifact upload with v4
- ✅ Build summary generation

### 3. **main.py** (App Persistence)
- ✅ `on_pause()` returns True (prevents Android kill)
- ✅ `on_resume()` implemented
- ✅ Background download support

---

## 🛠️ Setup Instructions

### Step 1: Prepare Assets (Required)

Before pushing to GitHub, add these files to `assets/` folder:

```bash
mkdir -p assets
```

**a) Logo (Required)**
```bash
# Add your logo as: assets/logo.png
# Recommended size: 512x512px PNG
```

**b) Universal Font (Required)**
```bash
# Download NotoSans font
wget https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf -O assets/NotoSans-Regular.ttf
```

### Step 2: Push to GitHub

```bash
git add .
git commit -m "Initial commit with CI/CD setup"
git push origin main
```

### Step 3: Monitor Build

1. Go to your GitHub repository
2. Click **Actions** tab
3. Watch the build progress (15-30 minutes first time)
4. Download APK from **Artifacts** section

---

## 📥 Download APK

After successful build:

1. Navigate to **Actions** → Latest workflow run
2. Scroll to **Artifacts** section
3. Download **AnyLoad-APK.zip**
4. Extract and install on Android device

---

## 🔧 Build Configuration Details

### Requirements (buildozer.spec)
```
python3, kivy==2.3.0, kivymd==1.2.0, pillow, requests, certifi, 
urllib3, charset-normalizer, idna, pyjnius, android, yt-dlp, 
mutagen, websockets, brotli, pycryptodomex
```

### Android Permissions
```
INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, 
MANAGE_EXTERNAL_STORAGE, READ_MEDIA_VIDEO, READ_MEDIA_AUDIO, 
POST_NOTIFICATIONS, ACCESS_NETWORK_STATE, WAKE_LOCK
```

### Critical SDK Fix
The workflow includes this fix to bypass GitHub's broken Android SDK:
```bash
unset ANDROID_HOME
unset ANDROID_SDK_ROOT
unset ANDROID_NDK_HOME
```

This forces Buildozer to download and use its own fresh SDK/NDK.

---

## 🐛 Troubleshooting

### Build Fails with "SDK not found"
**Solution:** The workflow automatically handles this with environment variable unset.

### Build Fails with "Cython error"
**Solution:** Workflow uses Cython 0.29.33 (tested and stable).

### APK not created
**Solution:** Check workflow logs in Actions tab. Look for red ❌ marks.

### Font not found warning
**Solution:** Add `assets/NotoSans-Regular.ttf` before building.

---

## 🎯 Local Build (Optional)

If you want to build locally instead of using CI/CD:

```bash
# Install buildozer
pip install buildozer

# Build APK
buildozer android debug

# Install on device
buildozer android deploy run
```

---

## 📊 Build Time

- **First build:** 15-30 minutes (downloads SDK/NDK)
- **Subsequent builds:** 5-10 minutes (cached)

---

## 🔐 Security Notes

- PIN hashing uses SHA256
- Database uses parameterized queries (SQL injection safe)
- Filenames sanitized (path traversal safe)
- No hardcoded credentials

---

## 📱 Compatibility

- **Minimum:** Android 5.0 (API 21)
- **Target:** Android 13 (API 33)
- **Architectures:** 64-bit + 32-bit ARM
- **Languages:** Universal Unicode support

---

## 🎉 You're Ready!

Push your code and get a perfectly working APK automatically! 🚀

**Questions?** Check the workflow logs in GitHub Actions.

---

## 📝 Version History

- **v1.1.0** - Initial release with full CI/CD automation
  - Premium UI with Dark/Teal theme
  - Smart queue management
  - Pause/Resume support
  - 1000+ supported sites
  - Universal font support

---

**Built with ❤️ by Nirob & AI Partner**
