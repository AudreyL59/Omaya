-- Le champ pgt_process_fichier.extension est varchar(10), trop court
-- pour '.excalidraw' (11 caracteres). Utilise pour stocker les
-- diagrammes Excalidraw comme fichiers du process.
--
-- Idempotent : ALTER COLUMN TYPE ne fait rien si le type est deja OK.
-- A appliquer sur interne + OVH.

ALTER TABLE divers.pgt_process_fichier
    ALTER COLUMN extension TYPE varchar(20);
