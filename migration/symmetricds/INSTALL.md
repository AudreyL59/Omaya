# Installation SymmetricDS — pas à pas (Windows, PG 16)

Réplication bidirectionnelle `erp_db` entre **interne** (192.168.1.203, nœud
d'enregistrement) et **OVH** (10.8.0.6). À faire **sur les deux serveurs**, sauf
mention contraire.

---

## 0. Prérequis (sur CHAQUE serveur)
- **Java 17** (JRE Temurin/Adoptium) installé, `java -version` OK.
- Le **port 31415** ouvert entre les 2 serveurs (pare-feu Windows + routage VPN, **dans les deux sens**).
- Accès `psql` (fourni avec PostgreSQL) ou pgAdmin.

## 1. Créer le schéma de métadonnées SymmetricDS (sur CHAQUE serveur)
`erp_user` ne peut pas écrire dans `public` (PG15+) → les tables `sym_*` vont dans un schéma dédié :
```sql
CREATE SCHEMA IF NOT EXISTS symmetricds AUTHORIZATION erp_user;
```
(en local sur chaque serveur, ou à distance : `psql -h 192.168.1.203 -U erp_user -d erp_db -c "..."`)

## 2. Télécharger + décompresser SymmetricDS (sur CHAQUE serveur)
- Récupérer **`symmetric-server-3.x.x.zip`** sur https://symmetricds.org (édition open source, JDBC PostgreSQL inclus).
- Décompresser dans `C:\symmetricds`.

## 3. Vérifier le port HTTP
Dans `C:\symmetricds\conf\symmetric-server.properties` :
```
http.port=31415
```

## 4. Déposer la config moteur (le bon fichier par serveur)
- **Interne** : copier `interne.properties` → `C:\symmetricds\engines\`
- **OVH** : copier `ovh.properties` → `C:\symmetricds\engines\`
- Dans chaque fichier, **renseigner `db.password`** (mot de passe `erp_user`).

## 5. Démarrer le nœud INTERNE en premier
```
cd C:\symmetricds\bin
sym            ::  démarrage console (Ctrl+C pour arrêter)
```
Au 1er démarrage, SymmetricDS **crée les tables `sym_*`** dans le schéma `symmetricds`.

## 6. Charger la configuration (sur l'INTERNE)
Une fois les `sym_*` créées (étape 5), depuis le dossier `migration/symmetricds/` :
```
psql -h localhost -U erp_user -d erp_db -f sym_config_base.sql
psql -h localhost -U erp_user -d erp_db -f sym_triggers.sql
```
Puis créer les triggers de capture sur les tables de données :
```
cd C:\symmetricds\bin
symadmin --engine erp-interne sync-triggers
```

> 💡 **Valider d'abord sur 2 tables** : avant de charger tout `sym_triggers.sql`,
> tu peux ne charger que `sym_config_base.sql` + 2 `INSERT INTO sym_trigger…`
> (ex. `ticket.pgt_tk_statut` + une table `bytea`), faire `sync-triggers`, tester
> l'aller-retour, puis charger le fichier complet et refaire `sync-triggers`.

## 7. Démarrer le nœud OVH
```
cd C:\symmetricds\bin
sym
```
Il **s'enregistre automatiquement** auprès de l'interne (registration.url). Vérifier
dans les logs « registered » / dans `symmetricds.sym_node` (2 lignes attendues).

## 8. Chargement initial (quand l'interne aura des données via le sync WinDev)
Pousser l'état complet de l'interne vers OVH :
```
symadmin --engine erp-interne reload-node ovh
```

## 9. Passer en service Windows (prod, sur CHAQUE serveur)
```
cd C:\symmetricds\bin
sym_service.bat install
net start SymmetricDS
```

## 10. Vérifier que ça réplique
- Insérer une ligne sur l'interne dans une table suivie → elle apparaît sur OVH (et inversement).
- Surveiller : tables `symmetricds.sym_outgoing_batch` / `sym_incoming_batch`
  (statut `OK`), et les logs `C:\symmetricds\logs\`.

---

## Rappels
- **12 tables sans PK** : désormais dotées d'une PK déduite (`id_<table>`) → OK pour SymmetricDS.
- **Conflits** : « le plus récent gagne » sur `modif_date` (6 tables sans `modif_date` ont un override `USE_PK_DATA/FALLBACK`).
- **Canal `erp_blob`** : isole les 47 tables à `bytea` (photos/docs) pour ne pas bloquer le flux principal.
- Régénérer les triggers après évolution du schéma : `python ../generate_symmetricds.py`.
