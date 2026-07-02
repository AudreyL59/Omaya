"""Helpers communs a tous les imports ADM (OEN/ENI/IAG/PRO/SFR).

Cf. WinDev procedure traiterClient (globale) : gestion centralisee
de la creation/enrichissement d'un client par mail.

Logique WinDev fidele :
1. Normalisation (mail lower, gsm formate, adresse/nom sans accent)
2. Geocodage via api-adresse.data.gouv.fr (best-effort, on ignore
   les erreurs reseau pour ne pas bloquer l'import)
3. Recherche par mail :
   - 1 match : UPDATE si client.ModifDate < info.ModifDate OU ForceMAJ
   - 0 match (ou mail vide) : INSERT nouveau client (avec id fourni
     ou genere)
4. Retourne idClient
"""

from datetime import date, datetime
from typing import Any, Optional
from unicodedata import normalize as _unicode_norm, category as _unicode_cat

from app.core.database.pg import get_pg_connection


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _new_id() -> int:
    """Cf. WinDev idEntierDateHeureSys - id 8 octets base timestamp."""
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S")) * 1000 + n.microsecond // 1000


def _clean(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _sans_accent(s: str) -> str:
    """Cf. WinDev ccSansAccent : NFD -> supprime les marques combinantes.

    'école' -> 'ecole', 'Français' -> 'Francais'
    """
    if not s: return ""
    return "".join(c for c in _unicode_norm("NFD", s)
                    if _unicode_cat(c) != "Mn")


def _sans_accent_upper(s: str) -> str:
    """Cf. WinDev ccSansAccent + ccMajuscule."""
    return _sans_accent(s).upper()


def _formate_num_tel(tel: str) -> str:
    """Cf. WinDev FormateNumTel : normalise un numero FR.

    Regle simplifiee : garde uniquement les chiffres, prefixe '0' si
    9 chiffres commencant par 6-7 (mobile FR sans le 0).
    """
    if not tel: return ""
    digits = "".join(c for c in str(tel) if c.isdigit())
    # +33 6 12 34 56 78 -> 0612345678
    if digits.startswith("33") and len(digits) == 11:
        digits = "0" + digits[2:]
    elif len(digits) == 9 and digits[0] in "67":
        digits = "0" + digits
    return digits


def _geocode_adresse(adresse: str, cp: str, ville: str) -> Optional[dict]:
    """Cf. WinDev appel https://api-adresse.data.gouv.fr/search.

    Renvoie dict {latitude, longitude, adresse, cp, ville} ou None.
    Best-effort : si l'API est down, on retourne None (l'import continue).
    """
    if not (adresse and cp and ville):
        return None
    try:
        import urllib.parse
        import urllib.request
        import json as _json
        params = urllib.parse.urlencode({
            "q": adresse, "postcode": cp, "city": ville, "limit": 1,
        })
        url = f"https://api-adresse.data.gouv.fr/search/?{params}"
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            if resp.status != 200: return None
            data = _json.load(resp)
        feats = data.get("features") or []
        if not feats: return None
        f0 = feats[0]
        coords = (f0.get("geometry") or {}).get("coordinates") or []
        props = f0.get("properties") or {}
        if len(coords) < 2: return None
        return {
            "longitude": float(coords[0]),
            "latitude": float(coords[1]),
            "adresse": _sans_accent_upper(props.get("name") or adresse),
            "cp": props.get("postcode") or cp,
            "ville": _sans_accent_upper(props.get("city") or ville),
        }
    except Exception:
        return None


def _normaliser_info_client(info: dict) -> dict:
    """Applique les normalisations WinDev sur info_client (in-place)."""
    out = dict(info)  # copie defensive

    # Mail en minuscule
    mail = _clean(out.get("mail"))
    if mail: out["mail"] = mail.lower()

    # modif_date par defaut a maintenant
    md = out.get("modif_date")
    if not isinstance(md, (date, datetime)):
        out["modif_date"] = datetime.now()

    # GSM formate
    gsm = _clean(out.get("gsm"))
    if gsm: out["gsm"] = _formate_num_tel(gsm)

    # NOM finit par PRENOM -> tronquer NOM (cas des doublons de saisie)
    nom = _clean(out.get("nom"))
    prenom = _clean(out.get("prenom"))
    if nom and prenom and nom.lower().endswith(prenom.lower()):
        nom = nom[: -len(prenom)].strip()
    if nom: out["nom"] = _sans_accent(nom).upper()
    if prenom: out["prenom"] = _sans_accent(prenom)

    # Geocodage si adresse complete
    adr = _clean(out.get("adresse1"))
    cp = _clean(out.get("cp"))
    ville = _clean(out.get("ville"))
    if adr and cp and ville:
        geo = _geocode_adresse(adr, cp, ville)
        if geo:
            out["latitude_deg"] = geo["latitude"]
            out["longitude_deg"] = geo["longitude"]
            out["adresse1"] = geo["adresse"]
            out["cp"] = geo["cp"]
            out["ville"] = geo["ville"]

    return out


# ---------------------------------------------------------------------------
# traiter_client - fonction principale (cf. WinDev traiterClient)
# ---------------------------------------------------------------------------

def traiter_client(info_client: dict, force_maj: bool = False,
                    op_id: int = 0) -> int:
    """Cf. WinDev traiterClient(infoClient est un ST_CLIENT, ForceMAJ).

    Cherche le client par mail (case-insensitive) et :
    - Si 1 match : UPDATE si client.modif_date < info.modif_date OU force_maj
    - Sinon : INSERT avec l'id fourni (info.id_client) ou genere
    Retourne id_client.

    Args:
        info_client: dict avec les cles pgt_client (nom, prenom, mail, gsm,
            adresse1, cp, ville, date_naiss, ...). Une cle 'id_client'
            optionnelle force l'id en creation.
        force_maj: si True, met a jour meme si modif_date en base est
            posterieure.
        op_id: id du salarie qui declenche l'action (fallback si
            info_client['op_saisie']/'modif_op' vides).

    Returns:
        int : id_client (existant ou nouvellement cree). 0 en cas d'erreur.
    """
    info = _normaliser_info_client(info_client)
    db = get_pg_connection("adv")
    mail = _clean(info.get("mail"))

    # Recherche par mail (uniquement si non vide)
    existing = None
    if mail:
        try:
            rows = db.query(
                """SELECT id_client, modif_date
                     FROM adv.pgt_client
                    WHERE LOWER(mail) = ? AND mail <> ''
                      AND (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')
                    ORDER BY nom DESC""",
                (mail,),
            ) or []
            # WinDev : ne match QUE si exactement 1 resultat
            if len(rows) == 1:
                existing = rows[0]
        except Exception:
            existing = None

    # Cas 1 : trouve un unique client par mail
    if existing:
        id_client = int(existing["id_client"])
        try:
            db_modif = existing.get("modif_date")
            info_modif = info.get("modif_date")
            # WinDev : UPDATE si BDD.ModifDate < info.ModifDate OU ForceMAJ
            need_update = force_maj
            if not need_update and isinstance(db_modif, (date, datetime)):
                if isinstance(info_modif, (date, datetime)):
                    need_update = db_modif < info_modif
            if need_update:
                _update_client(db, id_client, info, op_id)
            return id_client
        except Exception:
            return id_client

    # Cas 2 : creation
    id_client = int(info.get("id_client") or 0) or _new_id()
    try:
        # Verifier si l'id existe deja (WinDev HLitRecherche + si Faux)
        r = db.query_one(
            "SELECT 1 FROM adv.pgt_client WHERE id_client = ? LIMIT 1",
            (id_client,),
        )
        if r:
            # Deja existe : re-genere un id et retry
            id_client = _new_id()
        _insert_client(db, id_client, info, op_id)
    except Exception:
        return 0
    return id_client


def _insert_client(db, id_client: int, info: dict, op_id: int) -> None:
    """INSERT dans adv.pgt_client (cf. WinDev HAjoute)."""
    op = int(info.get("op_saisie") or info.get("modif_op") or op_id or 0)
    db.query(
        """INSERT INTO adv.pgt_client (
              id_client_auto, id_client, civilite, nom, prenom, date_naiss,
              loca_proprio, adr_bat, adresse1, adresse2, cp, ville, pays,
              tel, gsm, mail, opt_partenaire,
              date_saisie, op_saisie, info_interne,
              latitude_deg, longitude_deg,
              modif_op, modif_date, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?,
                   NOW(), ?, ?,
                   ?, ?,
                   ?, NOW(), 'new')""",
        (id_client, id_client,
         int(info.get("civilite") or 1),
         _clean(info.get("nom")), _clean(info.get("prenom")),
         info.get("date_naiss"),
         bool(info.get("loca_proprio")),
         _clean(info.get("adr_bat")),
         _clean(info.get("adresse1")), _clean(info.get("adresse2")),
         _clean(info.get("cp")), _clean(info.get("ville")),
         _clean(info.get("pays")) or "FRANCE",
         _clean(info.get("tel")), _clean(info.get("gsm")),
         _clean(info.get("mail")), bool(info.get("opt_partenaire")),
         op, _clean(info.get("info_interne")),
         info.get("latitude_deg") or 0,
         info.get("longitude_deg") or 0,
         op),
    )


def _update_client(db, id_client: int, info: dict, op_id: int) -> None:
    """UPDATE de adv.pgt_client (cf. WinDev HModifie)."""
    op = int(info.get("modif_op") or info.get("op_saisie") or op_id or 0)
    db.query(
        """UPDATE adv.pgt_client SET
              civilite = ?, nom = ?, prenom = ?, date_naiss = ?,
              loca_proprio = ?, adr_bat = ?,
              adresse1 = ?, adresse2 = ?, cp = ?, ville = ?,
              pays = ?, tel = ?, gsm = ?, mail = ?,
              op_saisie = COALESCE(NULLIF(?, 0), op_saisie),
              info_interne = ?,
              latitude_deg = ?, longitude_deg = ?,
              modif_op = ?, modif_date = NOW(), modif_elem = 'modif'
            WHERE id_client = ?""",
        (int(info.get("civilite") or 1),
         _clean(info.get("nom")), _clean(info.get("prenom")),
         info.get("date_naiss"),
         bool(info.get("loca_proprio")),
         _clean(info.get("adr_bat")),
         _clean(info.get("adresse1")), _clean(info.get("adresse2")),
         _clean(info.get("cp")), _clean(info.get("ville")),
         _clean(info.get("pays")) or "FRANCE",
         _clean(info.get("tel")), _clean(info.get("gsm")),
         _clean(info.get("mail")),
         int(info.get("op_saisie") or 0),
         _clean(info.get("info_interne")),
         info.get("latitude_deg") or 0,
         info.get("longitude_deg") or 0,
         op, int(id_client)),
    )
