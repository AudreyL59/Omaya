"""
Test isolé de la concurrence du bridge HFSQL.

Lance N queries en parallèle via ThreadPoolExecutor et mesure :
  - temps total (parallèle vs séquentiel)
  - taux de succès / erreurs
  - latence par query (min / med / max)

Sert à valider que le pool de workers parallèles pour les extractions
de production peut effectivement scaler sans saturer le bridge ou le
serveur HFSQL.

Usage :
    cd "D:\\Claude\\Projet Omaya"
    python scripts/test_hfsql_concurrency.py
    python scripts/test_hfsql_concurrency.py --concurrency 1,2,5,10 --queries 20

Aucune écriture / mutation : 100% lecture (SELECT TOP).
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Permet l'import du package app quand lancé à la racine
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import get_connection


# --- Set de queries de test (lecture seule, 1 par BDD principale) -----
TEST_QUERIES = [
    ("rh", "SELECT TOP 50 IDSalarie, NOM, PRENOM FROM salarie ORDER BY IDSalarie DESC"),
    ("rh", "SELECT TOP 30 idorganigramme, Lib_ORGA, IdPARENT FROM organigramme"),
    ("adv", "SELECT TOP 20 IDTypeEtat, LibType FROM TypeEtatContrat"),
    ("divers", "SELECT TOP 50 IDProductionExtractionJob, Statut FROM ProductionExtractionJob ORDER BY DateCrea DESC"),
    ("ticket", "SELECT TOP 20 IDTK_Liste, DATECREA FROM TK_Liste ORDER BY DATECREA DESC"),
]


def run_one(idx: int, db_key: str, sql: str) -> dict:
    """Exécute une query, retourne dict {ok, ms, n_rows, err}."""
    t0 = time.perf_counter()
    try:
        db = get_connection(db_key)
        rows = db.query(sql)
        ms = (time.perf_counter() - t0) * 1000
        return {
            "idx": idx, "db": db_key, "ok": True,
            "ms": ms, "n_rows": len(rows or []), "err": "",
        }
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000
        return {
            "idx": idx, "db": db_key, "ok": False,
            "ms": ms, "n_rows": 0, "err": f"{type(e).__name__}: {e}",
        }


def run_batch(concurrency: int, n_queries: int, verbose: bool = False) -> dict:
    """Lance n_queries en parallèle avec un pool de `concurrency` threads.

    Les queries sont piochées en round-robin dans TEST_QUERIES.
    """
    tasks = []
    for i in range(n_queries):
        db_key, sql = TEST_QUERIES[i % len(TEST_QUERIES)]
        tasks.append((i, db_key, sql))

    t0 = time.perf_counter()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(run_one, *t) for t in tasks]
        for f in as_completed(futures):
            r = f.result()
            results.append(r)
            if verbose:
                status = "OK " if r["ok"] else "ERR"
                err = f" — {r['err']}" if r["err"] else ""
                print(f"  [{r['idx']:>2}] {status} {r['db']:<8} {r['ms']:>7.0f} ms  rows={r['n_rows']}{err}")
    total_ms = (time.perf_counter() - t0) * 1000

    ok = [r for r in results if r["ok"]]
    ko = [r for r in results if not r["ok"]]
    times = [r["ms"] for r in ok] or [0.0]
    return {
        "concurrency": concurrency,
        "n_queries": n_queries,
        "total_ms": total_ms,
        "ok": len(ok),
        "ko": len(ko),
        "min_ms": min(times),
        "med_ms": statistics.median(times),
        "p95_ms": _percentile(times, 95),
        "max_ms": max(times),
        "errors": [r["err"] for r in ko][:5],
    }


def _percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def main():
    parser = argparse.ArgumentParser(description="Test concurrence bridge HFSQL")
    parser.add_argument(
        "--concurrency", default="1,2,5,10",
        help="Niveaux de parallélisme à tester (séparés par virgule). Défaut: 1,2,5,10",
    )
    parser.add_argument(
        "--queries", type=int, default=20,
        help="Nombre de queries par niveau. Défaut: 20",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Affiche le détail de chaque query",
    )
    args = parser.parse_args()

    levels = [int(x) for x in args.concurrency.split(",") if x.strip()]

    print("=" * 78)
    print("Test concurrence bridge HFSQL — lectures uniquement (SELECT TOP)")
    print(f"Niveaux : {levels} | Queries par niveau : {args.queries}")
    print("=" * 78)

    summaries = []
    for c in levels:
        print(f"\n>>> Concurrency = {c}")
        s = run_batch(c, args.queries, verbose=args.verbose)
        summaries.append(s)
        print(
            f"    total {s['total_ms']:>7.0f} ms | "
            f"OK {s['ok']:>2} / KO {s['ko']:>2} | "
            f"min {s['min_ms']:>5.0f} | med {s['med_ms']:>5.0f} | "
            f"p95 {s['p95_ms']:>5.0f} | max {s['max_ms']:>5.0f}"
        )
        if s["errors"]:
            print("    ERREURS (5 premières) :")
            for e in s["errors"]:
                print(f"      - {e}")

    # Tableau récap
    print("\n" + "=" * 78)
    print("RÉCAP")
    print("=" * 78)
    print(f"{'Conc.':>6} | {'Total':>8} | {'/query':>7} | {'OK/KO':>8} | {'med':>5} | {'p95':>5} | {'max':>5}")
    print("-" * 78)
    for s in summaries:
        per_q = s["total_ms"] / s["n_queries"]
        ok_ko = f"{s['ok']}/{s['ko']}"
        print(
            f"{s['concurrency']:>6} | "
            f"{s['total_ms']:>7.0f}ms | "
            f"{per_q:>6.0f}ms | "
            f"{ok_ko:>8} | "
            f"{s['med_ms']:>4.0f}ms | "
            f"{s['p95_ms']:>4.0f}ms | "
            f"{s['max_ms']:>4.0f}ms"
        )

    # Verdict
    print("\nVERDICT :")
    base = next((s for s in summaries if s["concurrency"] == 1), None)
    if base and base["ok"] > 0:
        for s in summaries:
            if s["concurrency"] == 1:
                continue
            if s["ko"] > 0:
                print(f"  /!\\ concurrency={s['concurrency']} : {s['ko']} erreurs — risque de saturation")
                continue
            speedup = (base["total_ms"] * (s["n_queries"] / base["n_queries"])) / s["total_ms"]
            efficiency = speedup / s["concurrency"] * 100
            verdict = "BON" if efficiency > 60 else "MOYEN" if efficiency > 30 else "MAUVAIS"
            print(
                f"  concurrency={s['concurrency']:>2} : "
                f"speedup x{speedup:.2f} | efficacité {efficiency:.0f}% | {verdict}"
            )
    print()


if __name__ == "__main__":
    main()
