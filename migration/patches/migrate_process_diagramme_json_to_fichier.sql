-- Migration : les diagrammes existants stockes dans
-- pgt_process.diagramme_json (V2, add_process_diagramme_json.sql) sont
-- deplaces vers pgt_process_fichier avec extension '.excalidraw'.
--
-- Rationale : permet d'avoir N diagrammes par process (comme le WinDev
-- original ou les .wddiag etaient stockes comme des fichiers). Evite
-- une nouvelle table.
--
-- Idempotent : ne migre que les process qui n'ont pas deja un fichier
-- .excalidraw en base.

BEGIN;

INSERT INTO divers.pgt_process_fichier
    (id_process_fichier, id_process, titre, contenu_fichier, extension,
     taille_fic, date_crea, derniere_modif, ope_crea, ope_modif,
     modif_date, modif_op, modif_elem)
SELECT
    (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::bigint * 1000 + p.id_process % 1000000,
    p.id_process,
    'Diagramme principal',
    convert_to(p.diagramme_json, 'UTF8'),
    '.excalidraw',
    length(convert_to(p.diagramme_json, 'UTF8')),
    COALESCE(p.derniere_modif, p.date_crea, now()),
    COALESCE(p.derniere_modif, p.date_crea, now()),
    COALESCE(p.ope_modif, p.ope_crea, 0),
    COALESCE(p.ope_modif, p.ope_crea, 0),
    now(), 0, 'new'
FROM divers.pgt_process p
WHERE p.diagramme_json IS NOT NULL
  AND length(p.diagramme_json) > 0
  AND (p.modif_elem IS NULL OR p.modif_elem <> 'suppr')
  AND NOT EXISTS (
      SELECT 1 FROM divers.pgt_process_fichier f
       WHERE f.id_process = p.id_process
         AND lower(f.extension) = '.excalidraw'
         AND (f.modif_elem IS NULL OR f.modif_elem <> 'suppr')
  );

COMMIT;
