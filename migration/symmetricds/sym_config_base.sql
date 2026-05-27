-- ============================================================================
--  SymmetricDS - configuration de base (replication bidirectionnelle erp_db)
--  Cible : SymmetricDS 3.x. A charger sur le noeud d'enregistrement (interne)
--  APRES le 1er demarrage de SymmetricDS (qui cree les tables sym_*),
--  PUIS charger sym_triggers.sql, puis `symadmin sync-triggers`.
--  Politique de conflit globale : le plus recent gagne (modif_date).
-- ============================================================================

-- Les tables sym_* sont dans le schema "symmetricds" (cf. currentSchema).
SET search_path TO symmetricds, public;

-- 1 seul groupe de noeuds (multi-maitre symetrique). Le lien erp->erp pousse
-- vers les AUTRES noeuds du groupe (anti-boucle gere par SymmetricDS).
INSERT INTO sym_node_group (node_group_id, description)
VALUES ('erp', 'Serveurs PostgreSQL ERP (interne + OVH)');

INSERT INTO sym_node_group_link (source_node_group_id, target_node_group_id, data_event_action)
VALUES ('erp', 'erp', 'P');   -- P = Push

-- Canaux : donnees normales + un canal dedie aux gros LOB (bytea : photos, docs)
INSERT INTO sym_channel (channel_id, processing_order, max_batch_size, max_batch_to_send, enabled, contains_big_lob, description)
VALUES ('erp_data', 10, 10000, 100, 1, 0, 'Donnees ERP');
INSERT INTO sym_channel (channel_id, processing_order, max_batch_size, max_batch_to_send, enabled, contains_big_lob, description)
VALUES ('erp_blob', 20, 100,   10,  1, 1, 'Tables a memo binaire (bytea)');

-- Routeur erp -> erp
INSERT INTO sym_router (router_id, source_node_group_id, target_node_group_id, router_type, create_time, last_update_time)
VALUES ('erp2erp', 'erp', 'erp', 'default', current_timestamp, current_timestamp);

-- Conflit global : NEWER_WINS sur la colonne modif_date (le plus recent gagne).
-- (Les tables SANS modif_date recoivent un override dans sym_triggers.sql.)
INSERT INTO sym_conflict (conflict_id, source_node_group_id, target_node_group_id,
    detect_type, detect_expression, resolve_type, ping_back,
    resolve_changes_only, resolve_row_only, create_time, last_update_time)
VALUES ('newer_wins', 'erp', 'erp', 'USE_TIMESTAMP', 'modif_date', 'NEWER_WINS',
    'SINGLE_ROW', 1, 0, current_timestamp, current_timestamp);
