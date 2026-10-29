"""Construit le package Microsoft Store (MSIX) a partir de l'exe PyInstaller.

Usage : python packaging/msix/build_msix.py "dist/RL Stats.exe" dist/RLStats.msix

Le package n'est pas signe : le Store le signe a la publication. Necessite le
SDK Windows (makeappx.exe), present sur les runners GitHub windows-latest.
"""

import glob
import os
import re
import shutil
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LOGOS = {"StoreLogo.png": 50, "Square44x44Logo.png": 44, "Square150x150Logo.png": 150}


def app_version():
    with open(os.path.join(ROOT, "rl_stats.pyw"), encoding="utf-8") as f:
        version = re.search(r'^APP_VERSION = "(.+)"', f.read(), re.M).group(1)
    return version + ".0"  # le Store exige 4 nombres, le dernier a 0


def find_makeappx():
    found = shutil.which("makeappx")
    if found:
        return found
    kits = os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Windows Kits", "10", "bin")
    candidates = sorted(glob.glob(os.path.join(kits, "10.*", "x64", "makeappx.exe")))
    if not candidates:
        sys.exit("makeappx.exe introuvable : installer le SDK Windows")
    return candidates[-1]


def main(exe, out):
    with open(os.path.join(HERE, "AppxManifest.xml"), encoding="utf-8") as f:
        manifest = f.read().replace("{VERSION}", app_version())
    if "TODO_" in manifest:
        sys.exit("AppxManifest.xml : renseigner l'identite du package (Partner Center > Identite du produit)")

    stage = os.path.join(ROOT, "build", "msix")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(os.path.join(stage, "Assets"))
    with open(os.path.join(stage, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest)
    shutil.copy(exe, os.path.join(stage, "RLStats.exe"))
    with Image.open(os.path.join(ROOT, "rl_stats.ico")) as ico:
        ico.size = (256, 256)
        icon = ico.convert("RGBA")
    for name, size in LOGOS.items():
        icon.resize((size, size), Image.LANCZOS).save(os.path.join(stage, "Assets", name))

    subprocess.run([find_makeappx(), "pack", "/o", "/d", stage, "/p", out], check=True)
    print(f"{out} ({app_version()})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
