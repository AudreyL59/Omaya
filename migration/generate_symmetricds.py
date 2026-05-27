"""Genere la config SymmetricDS (triggers + overrides de conflit) depuis
migration/mapping/columns.csv.

Sortie : migration/symmetricds/sym_triggers.sql
  - un sym_trigger + sym_trigger_router par table (routeur erp2erp)
  - canal 'erp_blob' pour les tables a colonne bytea, 'erp_data' sinon
  - override de conflit (USE_PK_DATA/FALLBACK) pour les tables SANS modif_date
    (la politique globale 'newer_wins' sur modif_date ne s'y applique pas)
  - rapport : tables blob / sans modif_date / sans PK (ces dernieres a traiter,
    SymmetricDS a besoin d'une cle pour detecter les conflits)

A appliquer APRES sym_config_base.sql, sur le serveur d'enregistrement (interne).
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "mapping" / "columns.csv"
OUT = HERE / "symmetricds" / "sym_triggers.sql"


def main() -> None:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    # Regroupe par (schema, pg_table)
    tables: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"has_modif": False, "has_blob": False, "has_pk": False})
    order: list[tuple[str, str]] = []
    for r in rows:
        key = (r["schema"], r["pg_table"])
        if key not in tables:
            order.append(key)
        t = tables[key]
        if r["pg_column"] == "modif_date":
            t["has_modif"] = True
        if r["pg_type"] == "bytea":
            t["has_blob"] = True
        if r["pk"] == "1":
            t["has_pk"] = True

    lines = [
        "-- ============================================================",
        "--  SymmetricDS : triggers + overrides de conflit (genere)",
        "--  A appliquer apres sym_config_base.sql sur le noeud 'interne'.",
        "-- ============================================================",
        "",
        "-- Tables sym_* dans le schema dedie (cf. currentSchema).",
        "SET search_path TO symmetricds, public;",
        "",
    ]
    no_modif, no_pk, n_blob = [], [], 0
    for schema, pg_table in order:
        t = tables[(schema, pg_table)]
        trig = f"{schema}_{pg_table}"
        channel = "erp_blob" if t["has_blob"] else "erp_data"
        if t["has_blob"]:
            n_blob += 1
        lines.append(
            "INSERT INTO sym_trigger (trigger_id, source_schema_name, "
            "source_table_name, channel_id, sync_on_insert, sync_on_update, "
            "sync_on_delete, last_update_time, create_time) VALUES "
            f"('{trig}', '{schema}', '{pg_table}', '{channel}', 1, 1, 1, "
            "current_timestamp, current_timestamp);")
        lines.append(
            "INSERT INTO sym_trigger_router (trigger_id, router_id, "
            "initial_load_order, last_update_time, create_time) VALUES "
            f"('{trig}', 'erp2erp', 100, current_timestamp, current_timestamp);")
        if not t["has_modif"]:
            no_modif.append((schema, pg_table))
            # Le conflit global 'newer_wins' (modif_date) ne s'applique pas :
            # override par table -> detection par PK, repli FALLBACK.
            lines.append(
                "INSERT INTO sym_conflict (conflict_id, source_node_group_id, "
                "target_node_group_id, target_schema_name, target_table_name, "
                "detect_type, resolve_type, ping_back, resolve_changes_only, "
                "resolve_row_only, create_time, last_update_time) VALUES "
                f"('cf_{trig}', 'erp', 'erp', '{schema}', '{pg_table}', "
                "'USE_PK_DATA', 'FALLBACK', 'SINGLE_ROW', 0, 0, "
                "current_timestamp, current_timestamp);")
        if not t["has_pk"]:
            no_pk.append((schema, pg_table))
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"{len(order)} tables -> {OUT}")
    print(f"  canal erp_blob (bytea) : {n_blob}")
    print(f"  sans modif_date (override conflit) : {len(no_modif)}")
    print(f"  SANS PK (a traiter, cle requise pour SymmetricDS) : {len(no_pk)}")
    for s, t in no_pk:
        print(f"     - {s}.{t}")


if __name__ == "__main__":
    main()
