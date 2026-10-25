"""Build a portable, self-contained Windows x64 distribution."""
import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formatkae.core import VERSION, find_tools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", default="", help="Folder containing ffmpeg.exe and ffprobe.exe")
    parser.add_argument("--zip", action="store_true", help="Also create a portable ZIP")
    parser.add_argument("--dist-dir", default=str(ROOT / "dist"), help="Output directory; use a separate folder when the installed app is running")
    parser.add_argument("--skip-freeze", action="store_true", help="Refresh assets and ZIP for an already built executable")
    args = parser.parse_args()
    if sys.platform != "win32" or platform.architecture()[0] != "64bit":
        raise SystemExit("Build with Windows x64 Python.")
    ffmpeg, ffprobe = find_tools(args.ffmpeg)
    if not (ROOT / "assets" / "app.ico").exists():
        raise SystemExit("Generate assets/app.ico before packaging.")
    dist_dir = Path(args.dist_dir).resolve()
    target = dist_dir / "FormatKae"
    if args.skip_freeze:
        if not (target / "FormatKae.exe").is_file():
            raise SystemExit("No existing executable; build without --skip-freeze first.")
    else:
        # PyInstaller can reuse the EXE when an ICO changes at the same path.
        # Recreate the small launcher so every build embeds the current artwork.
        (ROOT / "build" / "FormatKae" / "EXE-00.toc").unlink(missing_ok=True)
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(dist_dir), str(ROOT / "FormatKae.spec")], cwd=ROOT, check=True)
    engine = target / "ffmpeg" / "bin"
    engine.mkdir(parents=True, exist_ok=True)
    for binary in (ffmpeg, ffprobe):
        shutil.copy2(binary, engine / binary.name)
    for name in ("README.md", "THIRD_PARTY_NOTICES.md", "TEST_REPORT.md"):
        shutil.copy2(ROOT / name, target / name)
    licenses = target / "licenses"
    licenses.mkdir(exist_ok=True)
    if (ROOT / "assets" / "licenses").is_dir():
        shutil.copytree(ROOT / "assets" / "licenses", licenses, dirs_exist_ok=True)
    for name in ("LICENSE", "README.txt"):
        source = ffmpeg.parent.parent / name
        if source.exists():
            shutil.copy2(source, licenses / f"FFmpeg-{name}")
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
    import PySide6
    pyside = Path(PySide6.__file__).parent
    if (pyside / "support").is_dir():
        for source in pyside.rglob("*LICENSE*"):
            if source.is_file() and source.suffix.lower() in {".txt", ".md", ""}:
                shutil.copy2(source, licenses / ("PySide6-" + source.name))
    for info in (pyside.parent.glob("*.dist-info")):
        if info.name.lower().startswith(("pyside6", "shiboken6", "pyinstaller")):
            for pattern in ("*LICENSE*", "*COPYING*"):
                for source in info.rglob(pattern):
                    if source.is_file():
                        shutil.copy2(source, licenses / (info.name + "-" + source.name))
    # Include buildable application sources alongside the dynamically linked Qt libraries.
    source_root = target / "source"
    source_root.mkdir(exist_ok=True)
    for name in ("main.py", "requirements.txt", "FormatKae.spec", "README.md", "THIRD_PARTY_NOTICES.md", "TEST_REPORT.md", "build.ps1", "run.ps1", ".gitignore"):
        shutil.copy2(ROOT / name, source_root / name)
    for folder in ("formatkae", "scripts", "tests", "assets"):
        shutil.copytree(ROOT / folder, source_root / folder, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manifest = {}
    for binary in (target / "FormatKae.exe", engine / "ffmpeg.exe", engine / "ffprobe.exe"):
        with binary.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        manifest[str(binary.relative_to(target))] = digest
    (target / "SHA256SUMS.txt").write_text("\n".join(f"{v}  {k}" for k, v in manifest.items()) + "\n", encoding="utf-8")
    if args.zip:
        release = ROOT / "release"
        release.mkdir(exist_ok=True)
        archive = release / f"FormatKae-{VERSION}-win-x64-portable.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as output:
            for path in target.rglob("*"):
                if path.is_file():
                    output.write(path, path.relative_to(target.parent))
        print(f"ZIP: {archive}")
    print(f"EXE: {target / 'FormatKae.exe'}")


if __name__ == "__main__":
    main()
