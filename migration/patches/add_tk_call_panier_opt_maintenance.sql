-- Patch : ajoute la colonne opt_maintenance a ticket_bo.pgt_tk_call_panier.
--
-- La colonne existait cote HFSQL OVH mais manquait dans le schema PG
-- interne. La proc WinDev Call/.../Panier/Produit/Ajout ecrit cette
-- colonne (Opt_Maintenance), et la fiche Energie cote Vendeur la lit
-- pour afficher l'option 'PLENICOACH DEPANNAGE PREMIUM' (ENI).
--
-- Idempotent (ADD COLUMN IF NOT EXISTS).

ALTER TABLE ticket_bo.pgt_tk_call_panier
    ADD COLUMN IF NOT EXISTS opt_maintenance boolean;
