-- Patch : ajoute a ticket_bo.pgt_tk_call_sfr les 10 colonnes qui existent
-- cote HFSQL OVH mais qui manquent dans le schema PG interne (les
-- descriptifs XLSX n'avaient pas ete resynchronises avec les evolutions
-- WinDev sur cette table).
--
-- Le manque bloquait :
--   - la fiche ticket Fibre (SELECT mobile2, mob_propo_vend,
--     anomalie_mobile, id_tk_call_sfr_type_anomalie, info_cplt_anomalie)
--   - le WS AnomalieMobile (UPDATE anomalie_mobile,
--     id_tk_call_sfr_type_anomalie, info_cplt_anomalie)
--
-- Cf. `d:/Claude/Table HFSQL/Bdd_Omaya_Ticket_BO/Table TK_CallSFR.xlsx`
-- pour la spec HFSQL de reference.
--
-- Idempotent : chaque ADD COLUMN utilise IF NOT EXISTS ; les CREATE INDEX
-- utilisent IF NOT EXISTS.

-- ============================================================================
-- 10 colonnes
-- ============================================================================

ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS id_offres_sfr                 bigint;
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS mobile2                       varchar(10);
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS test_eligibilite              bytea;
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS mob_propo_vend                boolean;
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS anomalie_mobile               boolean;
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS id_tk_call_sfr_type_anomalie  bigint;
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS id_tk_liste_ref_anomalie      bigint;
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS info_cplt_anomalie            text;
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS ticket_diff                   boolean;
ALTER TABLE ticket_bo.pgt_tk_call_sfr
    ADD COLUMN IF NOT EXISTS kbis                          varchar(50);


-- ============================================================================
-- 2 index (correspondent aux "cles avec doublon" HFSQL cf. generate_schema.py)
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_pgt_tk_call_sfr_id_offres_sfr
    ON ticket_bo.pgt_tk_call_sfr (id_offres_sfr);

CREATE INDEX IF NOT EXISTS ix_pgt_tk_call_sfr_id_tk_call_sfr_type_anomalie
    ON ticket_bo.pgt_tk_call_sfr (id_tk_call_sfr_type_anomalie);
