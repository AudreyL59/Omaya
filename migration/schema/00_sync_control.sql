-- ============================================================================
--  Table de controle de la synchro HFSQL -> PostgreSQL
--  Curseur incremental par table (cf. migration/SYNC_WINDEV_SPEC.md sec.3).
--  Appliquee en premier (prefixe 00_) par migration/apply_schema.py.
--  Placee dans un schema dedie "sync" (et non "public") : depuis PG 15,
--  public n'accorde plus CREATE aux non-proprietaires.
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS sync;

CREATE TABLE IF NOT EXISTS sync.sync_control (
    schema_name  text      NOT NULL,   -- schema PG cible (adv, ticket, rh...)
    table_name   text      NOT NULL,   -- nom HFSQL d'origine (TK_Liste...)
    last_modif   timestamp,            -- max(ModifDate) deja synchronise
    last_run     timestamp,            -- horodatage de la derniere passe
    rows_synced  bigint    DEFAULT 0,  -- compteur cumule (info)
    PRIMARY KEY (schema_name, table_name)
);
