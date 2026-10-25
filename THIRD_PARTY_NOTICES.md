# Third-party notices

FormatKae uses the following third-party components. Their respective licenses apply.

## FFmpeg / ffprobe

This package contains the user's existing Gyan Windows full build:
`2026-08-30-git-818cecc6e1-full_build`, built with `--enable-gpl --enable-version3`.
The upstream distribution's LICENSE and README are copied unmodified to `licenses/FFmpeg-*`.
This build includes GPL components; do not describe this FFmpeg build as LGPL-only.

- Project and licensing: https://ffmpeg.org/ and https://ffmpeg.org/legal.html
- Build provider and source information: https://www.gyan.dev/ffmpeg/builds/
- FFmpeg source repository: https://git.ffmpeg.org/ffmpeg.git (revision prefix `818cecc6e1`)
- Build configuration: run `ffmpeg/bin/ffmpeg.exe -version`.

For redistribution, obtain the corresponding sources for this exact build, including enabled
third-party libraries and build scripts, from its provider and comply with the supplied GPL terms.
This local package preserves the provided binaries; it does not include a complete corresponding
source archive for FFmpeg and every statically linked dependency.

## Qt / PySide6 / Shiboken6

Qt for Python (PySide6 Essentials and Shiboken6), version pinned in `source/requirements.txt`.
These modules are distributed as separate, dynamically loaded files under `_internal`.
Use the applicable LGPLv3/GPLv3/commercial terms of the original packages.
Do not restrict replacement or reverse engineering for debugging modifications to LGPL libraries.
Package-provided licenses are copied into `licenses` where present.

- https://doc.qt.io/qtforpython-6/licenses.html
- https://www.qt.io/licensing/open-source-lgpl-obligations
- https://code.qt.io/pyside/pyside-setup.git

## Python

Python 3.12 runtime, Python Software Foundation License. See `licenses/Python-LICENSE.txt`.
https://www.python.org/psf/license/

## PyInstaller

The executable is packaged with PyInstaller. Its bootloader exception allows distributing
bundled applications under their own terms. License text is included from the installed package.
https://pyinstaller.org/en/stable/license.html

The `source` directory contains the FormatKae application source and build scripts.
No media uploaded by the user is included in this distribution.
