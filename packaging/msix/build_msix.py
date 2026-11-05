"""Construit le package Microsoft Store (MSIX) a partir de l'exe PyInstaller.

Usage : python packaging/msix/build_msix.py "dist/RL Stats.exe" dist/RLStats.msix

Le package n'est pas signe : le Store le signe a la publication. Necessite le
SDK Windows (makeappx.exe, makepri.exe), present sur les runners GitHub windows-latest.

Logos : sans variantes "targetsize-XX_altform-unplated", la barre des taches et le
menu Demarrer posent l'icone 44 px agrandie sur un fond de la couleur d'accent (bleu).
Les variantes ne sont trouvees par Windows que via resources.pri (makepri).
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
SCALES = {100: 1.0, 125: 1.25, 150: 1.5, 200: 2.0, 400: 4.0}
TARGET_SIZES = (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256)


def logo_files():
    """{nom du fichier dans Assets: taille en px}"""
    files = {}
    for base, size in (("StoreLogo", 50), ("Square44x44Logo", 44), ("Square150x150Logo", 150)):
        for scale, factor in SCALES.items():
            px = round(size * factor)
            if px <= 256:  # pas d'agrandissement au-dela de l'image source
                files[f"{base}.scale-{scale}.png"] = px
    for px in TARGET_SIZES:
        for suffix in ("", "_altform-unplated", "_altform-lightunplated"):
            files[f"Square44x44Logo.targetsize-{px}{suffix}.png"] = px
    return files


def app_version():
    with open(os.path.join(ROOT, "rl_stats.pyw"), encoding="utf-8") as f:
        version = re.search(r'^APP_VERSION = "(.+)"', f.read(), re.M).group(1)
    return version + ".0"  # le Store exige 4 nombres, le dernier a 0


def find_sdk_tool(name):
    found = shutil.which(name)
    if found:
        return found
    kits = os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Windows Kits", "10", "bin")
    candidates = sorted(glob.glob(os.path.join(kits, "10.*", "x64", name + ".exe")))
    if not candidates:
        sys.exit(f"{name}.exe introuvable : installer le SDK Windows")
    return candidates[-1]


def icon_at(ico_path, px):
    """Image px x px : l'image native du .ico si elle existe (plus nette), sinon la 256 reduite."""
    with Image.open(ico_path) as ico:
        sizes = ico.info.get("sizes", set())
        ico.size = (px, px) if (px, px) in sizes else (256, 256)
        img = ico.convert("RGBA")
    return img if img.size == (px, px) else img.resize((px, px), Image.LANCZOS)


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
    ico = os.path.join(ROOT, "rl_stats.ico")
    for name, px in logo_files().items():
        icon_at(ico, px).save(os.path.join(stage, "Assets", name))

    # Index des ressources : sans lui, Windows ne voit pas les variantes de logos
    makepri = find_sdk_tool("makepri")
    priconfig = os.path.join(ROOT, "build", "priconfig.xml")
    subprocess.run([makepri, "createconfig", "/cf", priconfig, "/dq", "lang-en-US", "/pv", "10.0.0", "/o"], check=True)
    subprocess.run([makepri, "new", "/pr", stage, "/cf", priconfig, "/mn", os.path.join(stage, "AppxManifest.xml"),
                    "/of", os.path.join(stage, "resources.pri"), "/o"], check=True)

    subprocess.run([find_sdk_tool("makeappx"), "pack", "/o", "/d", stage, "/p", out], check=True)
    print(f"{out} ({app_version()})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
