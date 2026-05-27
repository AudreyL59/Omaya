# Spécification — Programme WinDev de synchronisation HFSQL → PostgreSQL

> Réplication **unidirectionnelle** HFSQL (source de vérité, WinDev actif) →
> PostgreSQL (réplica), **incrémentale** via `ModifDate`, en attendant la
> bascule big-bang. Voir la stratégie globale dans la mémoire projet.

---

## 1. Principe

- **Sens unique** : HFSQL → PostgreSQL. Tant que WinDev tourne, HFSQL est la
  seule source qui écrit. PG est un miroir, jamais écrit par les utilisateurs.
- **Incrémental** : à chaque passe, on ne traite que les lignes modifiées
  depuis la dernière synchro (`ModifDate >= curseur`).
- **Idempotent** : chaque ligne est appliquée en **UPSERT** (insert ou update
  selon la PK) → rejouer une passe ne casse rien.
- **Fraîcheur relâchée** : en phase 1 personne n'utilise PG, donc une passe
  toutes les 15–30 min suffit. On resserre près de la bascule.

---

## 2. Architecture WinDev recommandée

**Décrire les tables PG dans l'analyse WinDev** (c'est pour ça que les tables
PG sont préfixées `pgt_` : éviter la collision de noms avec les fichiers HFSQL
dans la même analyse).

1. Ajouter une **connexion PostgreSQL** (Accès Natif PostgreSQL) — `HOuvreConnexion`
   / `HChangeConnexion`, params host/port/base/user/mdp (serveur interne en
   dev, OVH en prod).
2. Importer les tables `pgt_*` comme **fichiers de données** de l'analyse.
3. La synchro devient une **copie enregistrement → enregistrement** : WinDev
   gère nativement la conversion des types **et le transfert des mémos
   binaires** (→ `bytea`), sans construire de SQL ni gérer l'échappement.

> Alternative (si l'import de schéma PG est pénible) : exécuter du SQL
> `INSERT ... ON CONFLICT` via `HExécuteRequêteSQL` sur la connexion PG. Plus
> de contrôle mais il faut gérer l'échappement et surtout le binaire
> (paramètres liés obligatoires pour les mémos) → moins simple. **L'approche
> fichiers-de-données est préférée.**

### Moteur générique piloté par le mapping
Plutôt que coder 298 tables à la main, un **moteur générique** lit la table de
correspondance (`migration/mapping/columns.csv` : `hfsql_table, pg_table,
hfsql_column, pg_column, pg_type, pk`) et, par **indirection** (`{ }`), copie
champ à champ :

```
POUR CHAQUE ligne_mapping DE la table courante
    {fichierPG + "." + pg_column} = {fichierHF + "." + hfsql_column}
FIN
```

→ un seul traitement couvre toutes les tables. Les noms diffèrent (snake_case),
d'où l'usage du mapping (pas de copie automatique par nom).

---

## 3. Curseur de synchro (incrémental)

Une table de contrôle **dans PG**, schéma dédié `sync` (pas `public` : depuis
PG 15 `public` n'accorde plus `CREATE` aux non-propriétaires) :

```sql
CREATE SCHEMA IF NOT EXISTS sync;
CREATE TABLE IF NOT EXISTS sync.sync_control (
    schema_name   text      NOT NULL,
    table_name    text      NOT NULL,   -- nom HFSQL
    last_modif    timestamp,            -- max(ModifDate) traité
    last_run      timestamp,
    rows_synced   bigint    DEFAULT 0,
    PRIMARY KEY (schema_name, table_name)
);
```

Par table, à chaque passe :
1. Lire le `last_modif` courant (0 / NULL au 1ᵉʳ run → **chargement initial total**).
2. Source HFSQL : sélectionner les lignes `WHERE ModifDate >= last_modif`
   (requête ou `HFiltre` trié sur `ModifDate`).
3. UPSERT chaque ligne dans PG (cf. §4).
4. `last_modif = max(ModifDate)` du lot ; `last_run = maintenant` ; `rows_synced += n`.

> `>=` + UPSERT idempotent : on peut retraiter la ligne pile au curseur sans
> risque (mieux que `>` qui pourrait en manquer une à la seconde près).

---

## 4. UPSERT par enregistrement

Avec l'approche fichiers-de-données :
```
HLitRecherche(fichierPG, cle_pk, valeur_pk_source)
SI HTrouve(fichierPG) ALORS
    ... (copie des champs) ...
    HModifie(fichierPG)
SINON
    HRAZ(fichierPG)
    ... (copie des champs) ...
    HAjoute(fichierPG)
FIN
```
- La **PK = clé métier** (`id_*`, cf. colonne `pk` du mapping), **pas**
  l'« Identifiant automatique ». On insère les ID explicitement (générés par
  WinDev) ; PG ne doit PAS auto-générer.
- Copier **aussi** les colonnes `*_auto` (Identifiant auto) telles quelles.

---

## 5. Conversions de types

| Source HFSQL | Cible PG | Règle |
|---|---|---|
| Date+Heure | `timestamp` | WinDev gère (sinon ISO `AAAA-MM-JJ HH:MM:SS`) |
| Date | `date` | idem (`AAAA-MM-JJ`) |
| Booléen | `boolean` | direct |
| Entier / Identifiant auto | `bigint`/`integer`/`smallint` | direct |
| Texte / Mémo texte | `varchar`/`text` | **encodage → UTF-8** (HFSQL ANSI/latin-1) |
| Mémo binaire/image | `bytea` | transfert natif (gros volumes : ticket_rh, recrutement) |
| Réel / Monétaire | `double precision`/`numeric` | direct |

⚠️ **Dates stockées en texte** : certaines colonnes « date » sont des champs
**Unicode** dans HFSQL (ex. `DATEPAIEMENT`) → mappées en `varchar`, **copiées
telles quelles** (pas de parsing). Conversion en vrai `date` = décision
ultérieure.

⚠️ **Accents/encodage** : valider que les accents passent bien (HFSQL ANSI →
PG UTF-8). Test sur une table à accents (`client`, `salarie`).

---

## 6. Suppressions

- **Suppression logique** (`ModifELEM = 'suppr'`) : c'est une modif comme une
  autre → la ligne est upsertée avec `modif_elem = 'suppr'`. **On ne supprime
  rien dans PG** : le réplica reflète HFSQL à l'identique, et l'appli filtre
  déjà `modif_elem <> 'suppr'`. ✅ Aucun traitement spécial.
- **Suppression physique** (`HSupprime`) : la ligne disparaît de HFSQL → la
  synchro par `ModifDate` ne la voit pas → orphelin résiduel dans PG. À gérer
  par une **passe de réconciliation périodique** (cf. §9). Si l'ERP ne fait que
  du soft-delete, le risque est nul.

---

## 7. Chargement initial

- 1ᵉʳ run (curseur vide) = **full load** de toutes les tables (les ~25 Go de
  mémos de `ticket_rh` + `recrutement` passent une fois). Lancer hors heures de
  prod ; la lecture native WinDev est rapide.
- Ensuite : incrémental, léger.

---

## 8. Tables sans clé unique (12)

`dialoguehisto/lu/msg`, `notificationpush`, `SFR_ClusterObjectif`,
`salarie_progevo`, `ProgEvo_Objectifs`, `Formation_barèmeNote/Bulletin/PrevRecrut`,
`Bulletin_Mention`, `tk_callsfr_typeanomalie`.

Pas de PK → pas d'UPSERT possible. Options :
- **Truncate + reload** à chaque passe (recommandé : tables petites/périphériques),
- ou clé composite naturelle si une combinaison de colonnes est unique.

---

## 9. Ordonnancement, cutover, validation

- **Déploiement par site (Cas A retenu)** : HFSQL est déjà répliqué entre le
  serveur interne et OVH (réplication HFSQL existante). On déploie donc le
  **même exe de sync sur chaque serveur**, pointé sur son **HFSQL local → son
  PG local** (LAN, pas de transfert de blobs via VPN). Curseur `sync.sync_control`
  propre à chaque PG. **Aucune réplication PG↔PG nécessaire.**
- **Cadence** : phase 1 = planificateur Windows lance l'exe toutes les 15–30 min
  (ou service WinDev). Pré-bascule : resserrer.
- **Cutover (big-bang)** :
  1. Geler les écritures WinDev (mode maintenance),
  2. **passe de synchro finale** (delta),
  3. **validation** : comparer `COUNT(*)` HFSQL vs PG par table (+ checksums sur
     tables clés),
  4. basculer l'appli sur PG, retirer le bridge,
  5. **rollback** : HFSQL reste intact ; en cas de souci on revient sur WinDev.
- **Réconciliation** (périodique + avant cutover) : comparer les ensembles de PK
  HFSQL vs PG pour rattraper d'éventuels manques / suppressions physiques.

---

## 10. Ordre de traitement des tables

Sans contraintes FK en PG, **l'ordre est libre** (pas de violation référentielle).
On peut traiter dans l'ordre du mapping. (Si on ajoutait des FK plus tard, il
faudrait charger les tables parentes d'abord.)

---

## 11. Points à valider en amont (POC sur 1 table)

Avant d'industrialiser les 298 tables, valider sur **une table simple**
(`ticket.pgt_tk_statut`) puis **une table à mémo binaire** (`ticket_rh` /
`ulease`) :
1. Connexion native PG OK (interne + OVH).
2. Import du schéma PG dans l'analyse + copie enregistrement OK.
3. Accents corrects (UTF-8).
4. Mémo binaire → `bytea` lisible côté PG (rouvrir l'image).
5. Curseur `sync_control` lu/écrit correctement.
6. Idempotence : relancer 2× la même passe → 0 doublon, données identiques.
