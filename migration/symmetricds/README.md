# SymmetricDS — réplication bidirectionnelle PostgreSQL (interne ↔ OVH)

Réplication **multi-maître** de `erp_db` entre le serveur **interne** (192.168.1.203,
nœud d'enregistrement) et **OVH** (10.8.0.6), conflits arbitrés **« le plus récent
gagne »** (`modif_date`). Cible **SymmetricDS 3.x**, **PostgreSQL 16 / Windows**.

```
  SymmetricDS interne  <──HTTP 31415 (VPN)──>  SymmetricDS OVH
        │ localhost                                  │ localhost
     PG interne  ────────── répliqué ──────────  PG OVH
```

## Fichiers
| Fichier | Rôle |
|---|---|
| `interne.properties` / `ovh.properties` | config moteur d'un nœud (→ `engines/` de chaque serveur) |
| `sym_config_base.sql` | groupe `erp`, lien `erp→erp`, canaux `erp_data`/`erp_blob`, routeur, conflit `newer_wins` |
| `sym_triggers.sql` | 1 trigger/table (298) + overrides de conflit (tables sans `modif_date`) — **généré** par `../generate_symmetricds.py` |

## Mise en place
1. **JRE 17** + **SymmetricDS** installés sur **chaque** serveur.
2. Copier `interne.properties` dans `engines/` de l'interne, `ovh.properties` dans `engines/` d'OVH. **Renseigner `db.password`.**
3. **Réseau** : ouvrir le **port 31415** entre les deux serveurs (pare-feu + routage VPN dans les 2 sens).
4. Démarrer SymmetricDS **sur l'interne** (crée les tables `sym_*`).
5. Charger la config dans `erp_db` de l'interne :
   ```
   psql -h localhost -U erp_user -d erp_db -f sym_config_base.sql
   psql -h localhost -U erp_user -d erp_db -f sym_triggers.sql
   ```
6. Créer les triggers de capture : `symadmin --engine erp-interne sync-triggers`.
7. Démarrer SymmetricDS **sur OVH** → il s'enregistre automatiquement auprès de l'interne.
8. (Quand l'interne aura des données via le sync WinDev) chargement initial vers OVH :
   `symadmin --engine erp-interne reload-node ovh`.

## ⚠️ À régler avant la prod
- **12 tables sans clé primaire** (cf. sortie de `generate_symmetricds.py` : `dialoguehisto`,
  `notificationpush`, `sfr_cluster_objectif`, `formation_*`, etc.) : **SymmetricDS a besoin
  d'une clé** pour identifier/arbitrer les lignes. → leur ajouter une PK (surrogate) en PG
  **ou** ne pas charger leurs triggers tant que ce n'est pas fait.
- **Valider d'abord sur 2 tables** (une simple + une à `bytea`) avant d'activer les 298 :
  ne charger que quelques `sym_trigger` au début, vérifier l'aller-retour interne↔OVH et la
  résolution de conflit, puis charger tout `sym_triggers.sql`.
- **Conflit `newer_wins`** : repose sur `modif_date`. Les 6 tables sans cette colonne ont un
  override `USE_PK_DATA/FALLBACK` (généré).

## Régénérer les triggers
Après toute évolution du schéma / mapping :
```
python ../generate_symmetricds.py
```
