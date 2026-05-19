"""Diagnostic du docx Contenu d'un ticket CttW (FI_CttW Plan 2).

But : comprendre OU et COMMENT le logo bas-gauche dupliqué est stocke
(corps ancre par page vs pied de page), pour corriger sans tatonner.

Usage (SUR LE SERVEUR, venv) :
    .\\venv\\Scripts\\python.exe scripts\\diag_cttw_docx.py <IDTK_Liste>
"""

import base64
import sys
import zipfile
import io
import re
import collections

sys.path.insert(0, ".")

from app.core.database import get_connection  # noqa: E402


def main(id_ticket: int):
    db = get_connection("ticket_rh")
    r = db.query_one(
        "SELECT IDTK_Liste, Contenu FROM TK_DemandeCttW WHERE IDTK_Liste = ?",
        (int(id_ticket),),
    )
    v = r.get("Contenu") if r else None
    if not v:
        print("Contenu vide/introuvable pour", id_ticket)
        return
    raw = v if isinstance(v, bytes) else base64.b64decode(v)
    print(f"docx: {len(raw)} octets")

    z = zipfile.ZipFile(io.BytesIO(raw))
    names = z.namelist()
    print("--- parties ---")
    for n in names:
        if n.endswith(".xml") or "media" in n:
            print(" ", n)

    def analyse(xmlname: str):
        if xmlname not in names:
            return
        xml = z.read(xmlname).decode("utf-8", "ignore")
        n_inline = xml.count("<wp:inline")
        n_anchor = xml.count("<wp:anchor")
        # positionV relativeFrom des anchors
        relv = re.findall(r'<wp:positionV[^>]*relativeFrom="([^"]+)"', xml)
        relh = re.findall(r'<wp:positionH[^>]*relativeFrom="([^"]+)"', xml)
        # images referencees (r:embed)
        embeds = re.findall(r'r:embed="([^"]+)"', xml)
        # behindDoc / wrap
        behind = len(re.findall(r'behindDoc="1"', xml))
        print(f"\n=== {xmlname} ===")
        print(f"  inline={n_inline}  anchor={n_anchor}  behindDoc={behind}")
        print(f"  positionV relativeFrom: {collections.Counter(relv)}")
        print(f"  positionH relativeFrom: {collections.Counter(relh)}")
        print(f"  r:embed (count par rId): {collections.Counter(embeds)}")
        # offsets verticaux des anchors (pour voir 'bas de page')
        offv = re.findall(r"<wp:positionV.*?<wp:posOffset>(-?\d+)</wp:posOffset>",
                          xml, re.S)
        if offv:
            vals = sorted(set(int(x) for x in offv))
            print(f"  posOffset V (EMU) min={vals[0]} max={vals[-1]} "
                  f"n_distinct={len(vals)}")
        # sectPr / footer refs
        print(f"  <w:sectPr>={xml.count('<w:sectPr')}  "
              f"footerReference={xml.count('footerReference')}  "
              f"<w:lastRenderedPageBreak>={xml.count('lastRenderedPageBreak')}  "
              f"<w:br w:type=\"page\">={xml.count('w:type=&quot;page&quot;')}")

    # Dump complet footer1.xml + 1er anchor du corps (placement paraphe)
    if "word/footer1.xml" in names:
        print("\n##### word/footer1.xml (BRUT) #####")
        print(z.read("word/footer1.xml").decode("utf-8", "ignore"))
    docxml = z.read("word/document.xml").decode("utf-8", "ignore")
    i = docxml.find("<wp:anchor")
    if i >= 0:
        j = docxml.find("</wp:anchor>", i)
        print("\n##### 1er <wp:anchor> du corps (extrait) #####")
        print(docxml[i:j + 12][:2500])

    analyse("word/document.xml")
    for n in names:
        if re.match(r"word/footer\d+\.xml$", n):
            analyse(n)
        if re.match(r"word/header\d+\.xml$", n):
            analyse(n)

    # rels : quelle image derriere chaque rId
    for rel in ["word/_rels/document.xml.rels"] + [
        f"word/_rels/{n.split('/')[-1]}.rels"
        for n in names if re.match(r"word/footer\d+\.xml$", n)
    ]:
        if rel in names:
            rx = z.read(rel).decode("utf-8", "ignore")
            imgs = re.findall(r'Id="([^"]+)"[^>]*Target="([^"]*media[^"]*)"', rx)
            if imgs:
                print(f"\n--- {rel} (images) ---")
                for i, t in imgs:
                    print(f"  {i} -> {t}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/diag_cttw_docx.py <IDTK_Liste>")
        sys.exit(1)
    main(int(sys.argv[1]))
