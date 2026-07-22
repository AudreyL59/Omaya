-- Ajout de la colonne diagramme_json sur pgt_process pour l'editeur
-- web tldraw (remplace le .wddiag natif WinDev, qui reste dans le
-- champ 'diagramme' bytea pour recuperation ulterieure si besoin).
--
-- Format : JSON serialise du snapshot tldraw (editor.getSnapshot()).
-- Idempotent : IF NOT EXISTS. A appliquer sur interne + OVH.

ALTER TABLE divers.pgt_process
    ADD COLUMN IF NOT EXISTS diagramme_json TEXT;

-- Pas d'index : la colonne n'est jamais interrogee dans une clause WHERE,
-- seulement lue par id_process (deja index PK) puis chargee cote client.
