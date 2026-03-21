# ARCHITECT_M4.md — PetClip Studio: Windows Portable Packaging (M4)

## 1. Packaging Approach

**Recommended: PyInstaller + ZIP bundle**

- PyInstaller freezes the FastAPI backend into a standalone Windows executable
- FFmpeg is bundled as a separate binary (cannot be compiled into the .exe)
- All files ship inside a `.zip` folder, not a single .exe

**Why not alternatives:**
- **Docker**: Good for servers, but incompatible with the M4 deliverable of a portable .exe
- **Nuitka**: Adds compilation complexity without meaningful benefit here; PyInstaller is sufficient and simpler

---

## 2. Files to Create / Modify for M4

### New files to create
| File | Purpose |
|------|---------|
| `scripts/build_win.ps1` | Windows build script (PyInstaller + packaging) |
| `scripts/build_linux.sh` | Linux/macOS build helper (optional packaging) |
| `scripts/bundle_ffmpeg.py` | Helper to download the correct FFmpeg build |
| `backend/app/main.spec` | PyInstaller spec file (defines binary graph, data files) |
| `PORTABLE_README.txt` | End-user instructions shipped inside the zip |
| `PORTABLE_LAUNCH.bat` | Simple batch launcher for non-technical users |

### Files to modify
| File | Change |
|------|--------|
| `backend/requirements.txt` | Add `pyinstaller==6.x` (dev-only) |
| `backend/app/main.py` | Add `if __name__ == "__main__"` block with `uvicorn.run()` for PyInstaller compatibility |
| `.gitignore` | Ensure `dist/`, `build/`, `*.spec` are ignored |

---

## 3. build_win.ps1 — Step by Step

```
1. $SRC = "backend"          # source root
2. $OUT = "dist/pet-clip-studio"   # staging dir
3. Clean: Remove-Item -Recurse dist/, build/, backend/*.spec
4. Stage static dirs: mkdir $OUT/uploads $OUT/outputs $OUT/data
5. Download FFmpeg: python scripts/bundle_ffmpeg.py --dest $OUT
   - Download ffmpeg-release-essentials.zip from gyan.dev
   - Extract only ffprobe.exe + ffmpeg.exe into $OUT
6. Copy Python app: cp -r backend/app $OUT/app
7. Copy env template: cp .env.example $OUT/.env.example
8. Copy launch scripts: cp PORTABLE_LAUNCH.bat $OUT/
9. Run PyInstaller:
   pyinstaller backend/app/main.spec --clean
10. Copy spec output: mv dist/main/exe/* $OUT/   (or rename accordingly)
11. Package: Compress-Archive -Path "$OUT/*" -DestinationPath "PetClipStudio-Portable.zip"
12. Output: "PetClipStudio-Portable.zip"
```

**PyInstaller `main.spec` key settings:**
- `a.binaries` includes FFmpeg .exe files (not recursed into Python extensions)
- `datas` includes `app/` as non-binary data, plus `../.env.example`
- `hiddenimports` = `["uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto", ...]` (all uvicorn submodules)
- `console=False` (GUI app, no CMD window)
- `single_file=False` (one-dir mode, so FFmpeg can live alongside)

---

## 4. build_linux.sh — Step by Step

```
1. $OUT="dist/pet-clip-studio"
2. Clean: rm -rf dist/ build/ *.spec
3. mkdir -p $OUT/{uploads,outputs,data}
4. apt-get install -y ffmpeg    # or: download static build
5. cp -r backend/app $OUT/app
6. cp .env.example $OUT/.env.example
7. python -m venv $OUT/venv
8. $OUT/venv/bin/pip install -r backend/requirements.txt
9. zip -r PetClipStudio-Linux.zip $OUT/
```

---

## 5. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **FFmpeg bundling** | High | Ship as separate .exe alongside app; use `ffmpeg-release-essentials` (not full build) to reduce size ~80–120MB |
| **PyInstaller + FastAPI/uvicorn** | Medium | Use `--hidden-import` for all uvicorn/httpx submodules; test that uvicorn can actually import after freeze |
| **WSL2 path issues** | Medium | Build must run on native Windows (not WSL) OR use `pyinstaller --distpath` with explicit Windows path to avoid Linux binary contamination |
| **Python runtime size** | Low–Medium | `backend/requirements.txt` is lightweight (~10 packages); total zip should be ~150–250MB (acceptable for a desktop app) |
| **Cross-compilation from WSL** | Medium | **Do NOT** cross-compile from WSL; PyInstaller on WSL produces Linux binaries. Developer runs `build_win.ps1` on a Windows host (PowerShell) with Python 3.10 installed. |

---

## 6. Recommendation: .exe vs .zip

**Ship a `.zip` folder, not a single `.exe`.**

Rationale:
- FFmpeg **must** live as `ffmpeg.exe` on disk alongside the app binary — it cannot be embedded in a single executable
- The ZIP lets users inspect the directory structure, back up configs, and replace the FFmpeg binary if needed
- A single `.exe` would require embedding FFmpeg via a loader/helper, adding unnecessary complexity
- Users expect a "portable app" ZIP they can unzip anywhere and double-click to run

**Deliverable filename:** `PetClipStudio-Portable.zip`
