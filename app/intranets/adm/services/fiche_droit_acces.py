"""
Onglet 'Accès Omaya' (Droit d'accès) de la fiche salarie ADM.

Transposition de FI_SalarieDroitAcces.

Etape 1 :
  - Liste des droits du salarie (JOIN pgt_type_droit_acces /
    pgt_salarie_droit_acces) avec rupture par Categorie.
  - Bouton 'Activer/desactiver la selection' : toggle droit_actif
    pour chaque ligne cochee.
  - Bouton 'Supprimer' : soft delete (modif_elem='suppr').

Etape 2 (commit suivant) :
  - 2 popups d'ajout : Intranet/Appli (ADM=0, FDV=1) et Omaya Software
    (ADM=1, FDV=0, restreint aux droits de l'operateur connecte).
  - Bouton 'Choisir ce profil' (categorie pgt_profil_droit_acces).

Etape 3 :
  - Bouton 'Envoyer code Omaya' : genere/recupere MDP + envoie mail + SMS.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime
from typing import Any

from app.core.database.pg import get_pg_connection


# --- Decodage RTF -> texte brut -------------------------------------------

_RTF_HEAD = re.compile(r"^\s*\{?\\rtf", re.IGNORECASE)


def _rtf_to_text(s: str) -> str:
    """Convertit une description stockee en RTF -> texte brut.

    Prefere striprtf si la lib est installee, sinon fallback regex
    qui couvre la majorite des cas (\\par, \\'XX hex cp1252,
    \\uNNN? unicode signe, suppression des commandes \\cmd, groupes
    header fonttbl/colortbl/...)."""
    if not s:
        return ""
    if not _RTF_HEAD.match(s):
        return s.strip()
    try:
        from striprtf.striprtf import rtf_to_text  # type: ignore
        return rtf_to_text(s).strip()
    except Exception:
        pass
    # Fallback regex
    out = s
    # Groupes header a supprimer entierement (un seul niveau d'imbrication)
    for tag in ("fonttbl", "colortbl", "stylesheet", "info", "generator",
                "pict", "datastore", "themedata"):
        out = re.sub(
            r"\{\s*\\" + tag + r"[^{}]*(\{[^{}]*\})*\s*\}",
            "",
            out,
            flags=re.IGNORECASE | re.DOTALL,
        )
    # \'XX (hex en cp1252)
    def _hex(m: re.Match) -> str:
        try:
            return bytes([int(m.group(1), 16)]).decode("cp1252", errors="replace")
        except Exception:
            return ""
    out = re.sub(r"\\'([0-9a-fA-F]{2})", _hex, out)
    # \uNNN? (codepoint signe 16 bits) - on consomme le caractere de
    # fallback (souvent '?' ou un espace).
    def _u(m: re.Match) -> str:
        try:
            code = int(m.group(1))
            if code < 0:
                code += 65536
            return chr(code)
        except Exception:
            return ""
    out = re.sub(r"\\u(-?\d+)\s?\??", _u, out)
    # Sauts de ligne
    out = re.sub(r"\\par[d]?\b", "\n", out)
    out = re.sub(r"\\line\b", "\n", out)
    out = re.sub(r"\\tab\b", "\t", out)
    # Autres commandes : \mot ou \mot-NN
    out = re.sub(r"\\\*?[a-zA-Z]+-?\d*\s?", "", out)
    # Caracteres echappes \\, \{, \}
    out = out.replace("\\\\", "\\").replace("\\{", "{").replace("\\}", "}")
    # Reste des accolades
    out = re.sub(r"[{}]", "", out)
    # Compactage espaces
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n[ \t]+", "\n", out)
    return out.strip()


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def load_droits(id_salarie: int) -> list[dict]:
    """Liste des droits attribues au salarie, JOIN sur le catalogue."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT
              sda.id_salarie_droit_acces,
              tda.id_type_droit_acces,
              tda.lib_droit,
              tda.code_interne,
              tda.description,
              tda.adm,
              tda.fdv,
              tda.categorie,
              sda.droit_actif
           FROM rh.pgt_salarie_droit_acces sda
           INNER JOIN rh.pgt_type_droit_acces tda
             ON sda.id_type_droit_acces = tda.id_type_droit_acces
           WHERE sda.id_salarie = ?
             AND sda.modif_elem NOT LIKE '%suppr%'
             AND tda.modif_elem NOT LIKE '%suppr%'
           ORDER BY tda.categorie ASC NULLS LAST, tda.lib_droit ASC""",
        (int(id_salarie),),
    )
    return [
        {
            "id_salarie_droit_acces": str(r.get("id_salarie_droit_acces") or ""),
            "id_type_droit_acces": _int(r.get("id_type_droit_acces")),
            "lib_droit": _str(r.get("lib_droit")),
            "code_interne": _str(r.get("code_interne")),
            "description": _rtf_to_text(_str(r.get("description"))),
            "adm": bool(r.get("adm")),
            "fdv": bool(r.get("fdv")),
            "categorie": _str(r.get("categorie")),
            "droit_actif": bool(r.get("droit_actif")),
        }
        for r in rows
    ]


def toggle_droits(id_salarie: int, id_types: list[int], op_id: int) -> dict:
    """Btn 'Activer/desactiver la selection' : toggle droit_actif pour
    chaque ligne cochee. Si la combinaison (id_salarie, id_type) n'existe
    pas en base, on l'ignore (cf. WinDev HLitRecherche puis HModifie)."""
    db = get_pg_connection("rh")
    nb_toggled = 0
    for id_type in id_types:
        if not id_type:
            continue
        row = db.query_one(
            """SELECT id_salarie_droit_acces, droit_actif
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ? AND id_type_droit_acces = ?
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(id_salarie), int(id_type)),
        )
        if not row:
            continue
        new_actif = not bool(row.get("droit_actif"))
        db.query(
            """UPDATE rh.pgt_salarie_droit_acces SET
                  droit_actif = ?,
                  modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                WHERE id_salarie_droit_acces = ?""",
            (
                new_actif,
                int(op_id),
                int(row.get("id_salarie_droit_acces")),
            ),
        )
        nb_toggled += 1
    return {"ok": True, "nb_toggled": nb_toggled}


def list_droits_disponibles(
    id_salarie: int, adm: bool, fdv: bool, op_user_id: int
) -> list[dict]:
    """Liste des droits disponibles a attribuer.

    Transposition des req SQL de Fen_SalarieDroitAjout (ADM=0, FDV=1)
    et Fen_ChoixDroitPerso (ADM=1, FDV=0, IDSalarie=usersCial).

    Filtrage selon WinDev :
      - Type du droit (adm / fdv).
      - WHERE salarie_droit_acces.id_salarie = ParamIDSalarie.
        - Pour Intranet/Appli (FDV) : ParamIDSalarie = id_salarie de la
          fiche -> retourne les droits attribues, listing principal.
          MAIS la popup d'ajout WinDev semble afficher tous les droits
          non-attribues pour selection (un INNER JOIN sur sda.id_salarie
          retourne les droits deja la, ce qui est etrange pour un
          'ajout'). On suit donc l'esprit : on liste TOUS les droits du
          type, le frontend peut ensuite afficher l'etat (attribue ou
          pas).
        - Pour Omaya Software (ADM) : ParamIDSalarie = usersCial -> on
          ne propose que les droits que l'operateur connecte possede.

    Retourne pour chaque droit : id, lib, code_interne, description,
    categorie, deja_attribue (au salarie cible), droit_actif (au salarie
    cible).
    """
    db = get_pg_connection("rh")
    # 1) Liste des droits du catalogue filtres ADM/FDV
    rows_cat = db.query(
        """SELECT id_type_droit_acces, lib_droit, code_interne,
                  description, categorie
           FROM rh.pgt_type_droit_acces
           WHERE adm = ? AND fdv = ?
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
           ORDER BY categorie ASC NULLS LAST, lib_droit ASC""",
        (bool(adm), bool(fdv)),
    )
    if not rows_cat:
        return []

    # 2) Si on est sur le mode 'Omaya Software' (ADM=1), filtrer par
    #    les droits que op_user_id possede deja activement.
    if adm and op_user_id:
        droits_user = db.query(
            """SELECT id_type_droit_acces
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ?
                 AND COALESCE(droit_actif, FALSE) = TRUE
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(op_user_id),),
        )
        ok_ids = {_int(r.get("id_type_droit_acces")) for r in droits_user}
        rows_cat = [r for r in rows_cat if _int(r.get("id_type_droit_acces")) in ok_ids]

    # 3) Etat sur le salarie cible (deja attribue, actif ?)
    droits_sal = db.query(
        """SELECT id_type_droit_acces, droit_actif
           FROM rh.pgt_salarie_droit_acces
           WHERE id_salarie = ?
             AND modif_elem NOT LIKE '%suppr%'""",
        (int(id_salarie),),
    )
    etat_map = {
        _int(r.get("id_type_droit_acces")): bool(r.get("droit_actif"))
        for r in droits_sal
    }

    return [
        {
            "id_type_droit_acces": _int(r.get("id_type_droit_acces")),
            "lib_droit": _str(r.get("lib_droit")),
            "code_interne": _str(r.get("code_interne")),
            "description": _rtf_to_text(_str(r.get("description"))),
            "categorie": _str(r.get("categorie")),
            "deja_attribue": _int(r.get("id_type_droit_acces")) in etat_map,
            "droit_actif": etat_map.get(_int(r.get("id_type_droit_acces")), False),
        }
        for r in rows_cat
    ]


def attribuer_droits(
    id_salarie: int, id_types: list[int], droit_actif: bool, op_id: int
) -> dict:
    """Btn 'Valider ce(s) droit(s)' : INSERT si nouveau, sinon UPDATE
    avec droit_actif (Activer/Desactiver).

    Cf. Fen_ChoixDroitPerso / Fen_SalarieDroitAjout :
      si HTrouve = Faux -> INSERT droit_actif=Vrai (avec confirm UX)
      sinon -> UPDATE droit_actif=<param> (selon choix 'Activer' ou
      'Desactiver').
    """
    db = get_pg_connection("rh")
    nb_inserted = 0
    nb_updated = 0
    for id_type in id_types:
        if not id_type:
            continue
        row = db.query_one(
            """SELECT id_salarie_droit_acces
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ? AND id_type_droit_acces = ?
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(id_salarie), int(id_type)),
        )
        if row:
            db.query(
                """UPDATE rh.pgt_salarie_droit_acces SET
                      droit_actif = ?,
                      modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
                    WHERE id_salarie_droit_acces = ?""",
                (
                    bool(droit_actif),
                    int(op_id),
                    int(row.get("id_salarie_droit_acces")),
                ),
            )
            nb_updated += 1
        else:
            new_id = _new_id()
            db.query(
                """INSERT INTO rh.pgt_salarie_droit_acces
                      (id_salarie_droit_acces, id_salarie,
                       id_type_droit_acces, droit_actif,
                       modif_date, modif_op, modif_elem)
                   VALUES (?, ?, ?, ?, NOW(), ?, 'new')""",
                (
                    new_id,
                    int(id_salarie),
                    int(id_type),
                    True,  # Cf. WinDev : a la creation, toujours actif
                    int(op_id),
                ),
            )
            nb_inserted += 1
    return {"ok": True, "nb_inserted": nb_inserted, "nb_updated": nb_updated}


def list_profils() -> list[str]:
    """Combo 'Profil' : DISTINCT categorie de pgt_type_poste."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT DISTINCT categorie FROM rh.pgt_type_poste
           WHERE categorie IS NOT NULL AND TRIM(categorie) <> ''
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
           ORDER BY categorie ASC"""
    )
    return [_str(r.get("categorie")) for r in rows if r.get("categorie")]


def apply_profil(id_salarie: int, categorie: str, op_id: int) -> dict:
    """Btn 'Choisir ce profil' : applique tous les droits associes a une
    categorie via pgt_profil_droit_acces. INSERT si nouveau, UPDATE
    droit_actif=True si deja la."""
    if not categorie or not categorie.strip():
        return {"ok": False, "error": "Profil requis"}
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT id_type_droit_acces FROM rh.pgt_profil_droit_acces
           WHERE categorie = ?
             AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
        (categorie.strip(),),
    )
    id_types = [
        _int(r.get("id_type_droit_acces"))
        for r in rows
        if r.get("id_type_droit_acces")
    ]
    if not id_types:
        return {"ok": True, "nb_inserted": 0, "nb_updated": 0, "categorie": categorie}
    return {
        **attribuer_droits(id_salarie, id_types, droit_actif=True, op_id=op_id),
        "categorie": categorie,
    }


def soft_delete_droits(id_salarie: int, id_types: list[int], op_id: int) -> dict:
    """Btn 'Supprimer' : soft delete pour chaque (id_salarie, id_type)."""
    db = get_pg_connection("rh")
    nb_deleted = 0
    for id_type in id_types:
        if not id_type:
            continue
        row = db.query_one(
            """SELECT id_salarie_droit_acces
               FROM rh.pgt_salarie_droit_acces
               WHERE id_salarie = ? AND id_type_droit_acces = ?
                 AND modif_elem NOT LIKE '%suppr%'""",
            (int(id_salarie), int(id_type)),
        )
        if not row:
            continue
        db.query(
            """UPDATE rh.pgt_salarie_droit_acces SET
                  modif_date = NOW(), modif_op = ?, modif_elem = 'suppr'
                WHERE id_salarie_droit_acces = ?""",
            (int(op_id), int(row.get("id_salarie_droit_acces"))),
        )
        nb_deleted += 1
    return {"ok": True, "nb_deleted": nb_deleted}


# --- Btn 'Envoyer code Omaya' --------------------------------------------

# Jeu de caracteres WinDev MonJeu (avec les caracteres speciaux repetes
# pour augmenter leur probabilite de tirage par GenereMotDePasse).
_MONJEU = (
    "0123456789abcdefghijklmnopqrstuvwxyz0123456789"
    ".!@$*.!@$*"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ".!@$*"
)


def _generate_mdp(length: int = 12) -> str:
    """Equivalent de GenereMotDePasse(12, MonJeu) WinDev."""
    return "".join(secrets.choice(_MONJEU) for _ in range(length))


def _aes_key() -> bytes:
    """Cle AES128 : MD5(UTF8(HASH_SECRET_KEY)). Transposition exacte de
    `bufCle = HashChaine(HA_MD5_128, ChaineVersUTF8(HASH_SECRET_KEY))`."""
    from app.core.config import HASH_SECRET_KEY
    if not HASH_SECRET_KEY:
        raise RuntimeError("HASH_SECRET_KEY non defini en config")
    return hashlib.md5(HASH_SECRET_KEY.encode("utf-8")).digest()


def _aes_encrypt(plain: str) -> bytes:
    """AES-128 CBC avec IV nul (defaut WinDev crypteAES128) + padding PKCS7."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    key = _aes_key()
    iv = b"\x00" * 16
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plain.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    enc = cipher.encryptor()
    return enc.update(padded) + enc.finalize()


def _aes_decrypt(cipher_bytes: bytes) -> str:
    """AES-128 CBC IV nul + depadding PKCS7."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    key = _aes_key()
    iv = b"\x00" * 16
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    dec = cipher.decryptor()
    padded = dec.update(cipher_bytes) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return plain.decode("utf-8", errors="replace")


def _mdp_from_stored(stored: str) -> str | None:
    """Decrypte mdp_crypte (stocke en base64 ou hex selon historique).

    Si le format n'est pas reconnu, retourne None (l'appelant regenerera
    un nouveau MDP)."""
    if not stored:
        return None
    import base64
    s = stored.strip()
    try:
        raw = base64.b64decode(s, validate=True)
    except Exception:
        try:
            raw = bytes.fromhex(s)
        except Exception:
            return None
    if len(raw) % 16 != 0:
        return None
    try:
        return _aes_decrypt(raw)
    except Exception:
        return None


def _store_mdp(mdp_clair: str) -> str:
    """Chiffre et retourne la representation a stocker (base64)."""
    import base64
    raw = _aes_encrypt(mdp_clair)
    return base64.b64encode(raw).decode("ascii")


def send_codes_omaya(id_salarie: int, op_user_id: int, op_user_login: str) -> dict:
    """Btn 'Envoyer code Omaya' :
      - Verifie/repare le login (si vide ou != mail -> recalcule via mail,
        avec suffixe random en cas de collision).
      - Recupere ou genere le MDP (decrypt si dispo, sinon nouveau +
        sauvegarde chiffre).
      - Envoi mail (intranet@omaya.fr -> mail salarie + Cci intranet
        + Cci op_user_login si pas un super-user 6/4/224).
      - Envoi SMS si tel mobile present.

    Retourne {ok, mail_envoye, sms_envoye, sms_result, login}.
    """
    db = get_pg_connection("rh")
    sal = db.query_one(
        """SELECT id_salarie, nom, prenom, login, mdp_crypte, modif_elem
           FROM rh.pgt_salarie WHERE id_salarie = ?""",
        (int(id_salarie),),
    )
    if not sal:
        return {"ok": False, "error": "Salarie introuvable"}
    if "supp" in (sal.get("modif_elem") or "").lower():
        return {
            "ok": False,
            "error": "Vous n'etes pas autorise a renouveler ce mot de passe",
        }

    coord = db.query_one(
        """SELECT mail, tel_mob FROM rh.pgt_salarie_coordonnees
           WHERE id_salarie = ?""",
        (int(id_salarie),),
    ) or {}
    mail = (coord.get("mail") or "").strip().lower()
    if not mail:
        return {"ok": False, "error": "Aucun mail enregistre pour ce salarie"}

    # 1) Login : si vide ou different du mail -> recalcule
    login_actuel = (sal.get("login") or "").strip()
    if not login_actuel or login_actuel.lower() != mail:
        candidat = mail
        # Verification collision (autre salarie avec ce login)
        for _ in range(10):
            existe = db.query_one(
                """SELECT id_salarie FROM rh.pgt_salarie
                   WHERE LOWER(login) = ? AND id_salarie <> ?""",
                (candidat.lower(), int(id_salarie)),
            )
            if not existe:
                break
            candidat = f"{_str(sal.get('nom'))}{secrets.randbelow(1000)}"
        login_actuel = candidat
        db.query(
            """UPDATE rh.pgt_salarie SET
                  login = ?, modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
               WHERE id_salarie = ?""",
            (login_actuel, int(id_salarie), int(id_salarie)),
        )

    # 2) MDP : recupere ou genere
    mdp_stored = (sal.get("mdp_crypte") or "").strip()
    mdp_clair = _mdp_from_stored(mdp_stored) if mdp_stored else None
    if not mdp_clair:
        mdp_clair = _generate_mdp(12)
        try:
            stored = _store_mdp(mdp_clair)
        except Exception as e:
            return {"ok": False, "error": f"Chiffrement MDP : {e}"}
        db.query(
            """UPDATE rh.pgt_salarie SET
                  mdp_crypte = ?, modif_date = NOW(), modif_op = ?, modif_elem = 'modif'
               WHERE id_salarie = ?""",
            (stored, int(id_salarie), int(id_salarie)),
        )

    # 3) Envoi mail
    sujet = "Code accès Intranet OMAYA"
    html = (
        "<font face='arial' style='font-size:10pt;'>"
        "<p>Bonjour,</p>"
        "<p>https://groupe-exo.omaya.fr</p>"
        f"<p>Votre accès à l'intranet a été validé pour cet identifiant : {login_actuel}</p>"
        f"<p>Votre mot de passe : {mdp_clair}</p>"
        "<p>Cdt<br/>Service INTRANET</p>"
        "</font>"
    )
    cc_list: list[str] = []
    cci_list = ["intranet@omaya.fr"]
    # Super-users : pas de Cci a l'operateur
    if id_salarie not in (6, 4, 224) and op_user_login:
        cci_list.append(op_user_login)

    mail_envoye = False
    try:
        from app.shared.notifications.mail import envoi_mail
        envoi_mail(
            destinataires=[mail],
            cc=cc_list,
            cci=cci_list,
            sujet=sujet,
            html=html,
            expediteur="intranet@omaya.fr",
        )
        mail_envoye = True
    except Exception:
        import sys, traceback
        traceback.print_exc(file=sys.stderr)

    # 4) Envoi SMS si tel mobile
    sms_envoye = False
    sms_result = ""
    gsm = "".join(c for c in (coord.get("tel_mob") or "") if c.isdigit())
    if gsm:
        nom_prenom = (
            f"{_capitalize(_str(sal.get('prenom')))} {_str(sal.get('nom'))}"
        ).strip()
        texte = (
            "Vos codes intranet\n"
            "https://groupe-exo.omaya.fr\n"
            f"Votre identifiant : {login_actuel}\n"
            f"Votre mot de passe : {mdp_clair}"
        )
        try:
            from app.shared.notifications.sms import envoi_sms
            sms_result = envoi_sms(texte, gsm, "", "OMAYA-Info") or ""
            sms_envoye = "ok" in sms_result.lower() or "envoy" in sms_result.lower()
        except Exception as e:
            sms_result = f"Erreur SMS : {e}"

    return {
        "ok": True,
        "mail_envoye": mail_envoye,
        "sms_envoye": sms_envoye,
        "sms_result": sms_result,
        "login": login_actuel,
    }


def _capitalize(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()
