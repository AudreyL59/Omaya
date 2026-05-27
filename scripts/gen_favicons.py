"""Genere les favicons des intranets depuis le logo OMAYA.

Source : frontend/<app>/src/assets/logo-omaya.png (200x200 RGBA).
Sortie (dans frontend/<app>/public/) :
  - favicon.ico  (16/32/48 multi-resolution)
  - favicon.png  (64x64)
  - apple-touch-icon.png (180x180)
"""

import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = ["adm", "vendeur"]


def gen(app: str) -> None:
    src = os.path.join(ROOT, "frontend", app, "src", "assets", "logo-omaya.png")
    pub = os.path.join(ROOT, "frontend", app, "public")
    im = Image.open(src).convert("RGBA")

    # favicon.ico multi-resolution
    im.save(
        os.path.join(pub, "favicon.ico"),
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )
    # favicon.png 64x64
    im.resize((64, 64), Image.LANCZOS).save(os.path.join(pub, "favicon.png"))
    # apple-touch-icon 180x180
    im.resize((180, 180), Image.LANCZOS).save(
        os.path.join(pub, "apple-touch-icon.png")
    )
    print(f"[{app}] favicon.ico / favicon.png / apple-touch-icon.png OK")


for a in APPS:
    gen(a)
