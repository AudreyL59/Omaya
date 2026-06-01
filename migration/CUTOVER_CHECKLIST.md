# Checklist de cutover HFSQL → PG (fin octobre 2026)

> Liste exhaustive de tout ce qui doit basculer côté code/infra le jour J.
> Auto-généré + complété à la main au fur et à mesure de la migration phase 1.

---

## 1. Backend Python — fichiers avec connexions HFSQL résiduelles (30)

Pendant la phase 1, le mode est **hybride** : lectures sur PG (sauf exceptions),
écritures sur HFSQL pour que WinDev les voie. Au cutover, **TOUT** doit passer
sur PG.

### A. Écritures à basculer (INSERT/UPDATE/DELETE)
Pour chaque fichier, remplacer `get_connection("xxx")` par `get_pg_connection("xxx")`
sur les queries d'écriture, et réécrire le SQL :
- table : `xxx` → `pgt_xxx`
- colonnes : PascalCase → snake_case
- placeholders `?` restent (la couche les convertit en `%s`)
- bool `= 1` → `= TRUE`, `= 0` → `= FALSE`
- `TOP N` → `LIMIT N`
- `attach_memo(...)` HFSQL → équivalent PG (UPDATE bytea avec `psycopg2.Binary`)

| Fichier | Schemas HFSQL | Nb writes |
|---|---|---|
| `app/intranets/vendeur/services/agenda_recrutement.py` | recrutement, ticket, ticket_dpae | 3 |
| `app/intranets/vendeur/services/cooptation.py` | recrutement | 2 |
| `app/intranets/vendeur/services/cvtheque.py` | recrutement | 1 |
| `app/intranets/vendeur/services/prise_rdv.py` | recrutement | 2 |
| `app/shared/production/service.py` | divers | 1 (+ INSERT job, soft-delete) |
| `app/shared/tickets/router.py` | ticket | (2 UPDATE TK_Liste statuer/supprimer) |
| `app/shared/tickets/service.py` | ticket | 1 |
| `app/shared/tickets/forms/attexocash.py` | rh, ticket, ticket_rh | 1 |
| `app/shared/tickets/forms/avance.py` | rh, ticket, ticket_bo | 1 |
| `app/shared/tickets/forms/cartepro.py` | rh, ticket_bo | 0 directs (attach_memo) |
| `app/shared/tickets/forms/cdeexocash.py` | divers, rh, ticket, ticket_rh | 4 |
| `app/shared/tickets/forms/code_vendeur.py` | rh, ticket, ticket_bo | 1 |
| `app/shared/tickets/forms/conges.py` | rh, ticket, ticket_rh | 1 |
| `app/shared/tickets/forms/cttcourtage.py` | adv, rh, ticket, ticket_bo | 1 |
| `app/shared/tickets/forms/cttw.py` | rh, ticket, ticket_rh | 1 |
| `app/shared/tickets/forms/cttw_demande.py` | ticket_rh | 0 directs |
| `app/shared/tickets/forms/cttw_pdf.py` | — | 0 (PDF + memos binaires) |
| `app/shared/tickets/forms/docdistrib.py` | rh, ticket, ticket_bo | 0 directs |
| `app/shared/tickets/forms/dpae.py` | ticket_dpae | 0 directs |
| `app/shared/tickets/forms/dpaedistrib.py` | ticket_bo | 0 directs |
| `app/shared/tickets/forms/factdistrib.py` | rh, ticket, ticket_bo | 1 |
| `app/shared/tickets/forms/facturedr.py` | divers, rh, ticket, ticket_bo | 2 |
| `app/shared/tickets/forms/fourniture.py` | ticket_bo | 0 directs |
| `app/shared/tickets/forms/mutuelle.py` | ticket_rh | 0 directs |
| `app/shared/tickets/forms/rdvtech.py` | adv, ticket, ticket_bo | 0 directs |
| `app/shared/tickets/forms/resa.py` | ticket_bo | 0 directs |
| `app/shared/tickets/forms/sosbo.py` | adv, rh, ticket, ticket_bo | 5 |
| `app/shared/tickets/forms/sosju.py` | ticket_rh | 0 directs |
| `app/shared/tickets/forms/ulease.py` | rh, ticket, ticket_rh | 1 |
| `app/shared/tickets/forms/ulease_pv.py` | rh, ticket, ticket_rh | 1 |

### B. Lectures HFSQL volontaires à basculer aussi (cohérence immédiate impossible avec lag PG)

Ces fonctions lisent HFSQL pour des raisons spécifiques de cohérence
immédiate. Au cutover (HFSQL absent), elles **doivent** lire PG :

1. **`app/shared/tickets/service.py`** :
   - `list_tickets_modified_since` (long polling — le lag PG casserait le live-update)
   - `load_ticket_raw` (prélude à un UPDATE save)

2. **`app/shared/production/service.py`** :
   - `count_active_jobs` (quota anti-DoS — doit voir le job qu'on vient de créer)
   - `list_jobs` (UX : on doit voir son job juste après "Lancer l'extraction")
   - `get_job` (idem)
   - `_load_pending_queue` (calcul de position dans la file)

3. **Tous les forms tickets** : les helpers `_xxx_info`, `_xxx_mail`, `_xxx_gsm`,
   `load_*` partagés avec `save_*` (read-modify-write). À auditer fichier par
   fichier — la règle est simple : si la donnée vient d'être écrite en HFSQL
   dans la même session utilisateur, on doit la relire avec cohérence
   immédiate.

---

## 2. Bridge HFSQL — à supprimer après cutover

- `app/core/database/hfsql_bridge.py` — module de pont vers WinDev (`@DLLCALL@`)
- `app/core/database/connections.py` — classe `HFSQLConnection`, `get_connection`,
  `get_db`
- `app/core/database/__init__.py` — réexports

Garder ces modules JUSQU'À ce que les 30 fichiers de la section 1 soient migrés.
Une fois la bascule complète, supprimer et faire un `grep -r "get_connection"`
pour vérifier qu'il ne reste plus rien.

---

## 3. Code WinDev (programme `sync_engine.wl`) — à arrêter

- `migration/windev/sync_engine.wl` — moteur de sync HFSQL→PG (incrémental + curseur)
- Planificateur Windows interne — désactiver la tâche planifiée toutes les 15 min
- `sync.sync_control` table PG — garder en archive (témoin de la dernière sync) ou drop

---

## 4. Base HFSQL — décommissionnement

- **Backup final** des 10 bases HFSQL (Bdd_Omaya_ADV, _Divers, _Recrutement, _RH,
  _Scool, _Ticket, _Ticket_BO, _Ticket_DPAE, _Ticket_RH, _Ulease) → archivage
  cold storage (ex. Glacier / DSM Hyper Backup)
- **Réplication HFSQL existante** (interne ↔ OVH) — désactiver une fois sûr
- **Serveur HFSQL Classic/CS** — peut être arrêté

---

## 5. SymmetricDS — config post-cutover

- Confirmer que la réplication PG ↔ PG continue (interne ↔ OVH)
- Plus de phase de "PG read-only" : le code écrit dans PG, SymmetricDS propage
- Optionnel : resserrer encore `job.push.period.time.ms` (5s actuel → 1s ?) si
  besoin de plus de réactivité

---

## 6. Vérifications à faire le jour J

### Avant la bascule (geler les écritures)
1. Mode maintenance sur WinDev (interdire les écritures utilisateurs)
2. Dernière passe de `SyncAllTables()` manuelle → drainer tous les deltas
3. Vérifier `sync.sync_control` : `last_run` proche de maintenant pour toutes les 298 tables
4. Drainer SymmetricDS : `sym_outgoing_batch` = tout `OK`, zéro `NE`/`ER`

### Validation pré-cutover
1. `COUNT(*)` HFSQL vs PG interne pour les 298 tables (script à écrire)
2. Checksums sur les tables critiques (`salarie`, `client`, `contrat`, `ticket_*`)
3. PG OVH = PG interne (via SymmetricDS, déjà validé)

### Bascule code
1. Migrer les 30 fichiers (`get_connection` → `get_pg_connection`)
2. Réécrire les SQL HFSQL → PG (préfixe pgt_, snake_case, LIMIT, etc.)
3. Supprimer le bridge HFSQL
4. Tests fumée sur chaque intranet (login + 1 action par module)
5. Mise en prod

### Rollback (au cas où)
- HFSQL reste intact (juste en lecture seule pendant le cutover)
- Si problème : remettre WinDev en service, désactiver la nouvelle code,
  resync les éventuelles écritures faites sur PG entre le cutover et le
  rollback (via SymmetricDS, déjà actif PG↔PG)

---

## 7. Cleanup post-cutover (J+30)

- Supprimer `debug_crypto.py` (utilitaire de debug ponctuel)
- Archiver `migration/windev/` (moteur sync inutile)
- Supprimer `migration/SYNC_WINDEV_SPEC.md` (historique)
- Garder `migration/symmetricds/` + `migration/schema/` (toujours utile pour
  réplication PG↔PG)
- Documenter la nouvelle architecture (un seul DB PG, plus de bridge)
