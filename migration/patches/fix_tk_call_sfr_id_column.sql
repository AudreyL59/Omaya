-- Patch : renomme les colonnes ID de ticket_bo.pgt_tk_call_sfr pour
-- coller au HFSQL (IDtk_CallSFR et IDtk_CallSFRAuto, et non IDtk_Call /
-- IDtk_CallAuto qui appartiennent a TK_Call - autre table).
--
-- Le bug etait visible dans le logiciel de synchro :
--   ERREUR ticket_bo.TK_CallSFR : L'element 'TK_CallSFR.IDtk_Call' est inconnu.
--
-- Idempotent : utilise des blocs DO + check sur information_schema pour
-- ne rien faire si la colonne est deja renommee.

DO $$
BEGIN
    -- 1. Renomme id_tk_call -> id_tk_call_sfr
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ticket_bo'
          AND table_name = 'pgt_tk_call_sfr'
          AND column_name = 'id_tk_call'
    ) THEN
        ALTER TABLE ticket_bo.pgt_tk_call_sfr
            RENAME COLUMN id_tk_call TO id_tk_call_sfr;
    END IF;

    -- 2. Renomme id_tk_call_auto -> id_tk_call_sfr_auto
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'ticket_bo'
          AND table_name = 'pgt_tk_call_sfr'
          AND column_name = 'id_tk_call_auto'
    ) THEN
        ALTER TABLE ticket_bo.pgt_tk_call_sfr
            RENAME COLUMN id_tk_call_auto TO id_tk_call_sfr_auto;
    END IF;
END $$;
