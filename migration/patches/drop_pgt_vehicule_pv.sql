-- Suppression de la table obsolete ulease.pgt_vehicule_pv.
-- Remplacee par ulease.pgt_vehicule_amende (code applicatif deja migre :
-- app/intranets/adm/services/vehicule_pv.py utilise pgt_vehicule_amende).
--
-- A executer une seule fois par base (interne + OVH).
-- SymmetricDS : le trigger correspondant a deja ete retire de sym_triggers.sql
-- (regenerer sym_triggers via `python migration/generate_symmetricds.py` +
-- reappliquer sur le noeud interne pour propager le DROP dans sym_trigger).
--
-- Prerequis : verifier qu'aucun code applicatif ne reference plus la table
--   grep -r "pgt_vehicule_pv" app/ frontend/    -- doit renvoyer 0 hit

BEGIN;
DROP TABLE IF EXISTS ulease.pgt_vehicule_pv;
-- Nettoyage des metadonnees SymmetricDS (si sym_* est sur cette base)
DELETE FROM sym_trigger_router WHERE trigger_id = 'ulease_pgt_vehicule_pv';
DELETE FROM sym_trigger        WHERE trigger_id = 'ulease_pgt_vehicule_pv';
COMMIT;
