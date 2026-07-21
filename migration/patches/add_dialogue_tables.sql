-- Ajout des 4 tables du module Dialogues absentes du schema PG initial.
-- Extrait de migration/schema/divers.sql (regenere via generate_schema.py
-- apres ajout des XLSX correspondants dans D:\Claude\Table HFSQL\Bdd_Omaya_Divers).
--
-- A executer une seule fois par base (interne + OVH).
-- SymmetricDS : sym_triggers.sql regenere en parallele — reappliquer sur le
-- noeud d'enregistrement (interne) pour propager les triggers.
--
-- Prerequis : schema 'divers' deja cree (existe deja avec les 4 tables
--   dialogue* d'origine : dialoguemsg / dialoguedest / dialoguehisto /
--   dialoguelu). Ces 4 nouvelles tables completent le module.

BEGIN;

CREATE TABLE IF NOT EXISTS divers.pgt_dialogues (
    id_dialogues         bigint NOT NULL,  -- IDDialogues
    id_dialogue_theme    bigint,           -- IDDialogueTheme
    expediteur           bigint,           -- Expéditeur
    sujet                text,             -- Sujet
    id_dialogue_statut   bigint,           -- IDDialogueStatut
    a_conserve           varchar(50),      -- AConservé
    date_heure_creation  timestamp,        -- DateHeureCreation
    prive                boolean,          -- Privé
    modif_date           timestamp,        -- ModifDate
    modif_op             bigint,           -- ModifOp
    modif_elem           varchar(5),       -- ModifElem
    CONSTRAINT pk_pgt_dialogues PRIMARY KEY (id_dialogues)
);
CREATE INDEX IF NOT EXISTS ix_pgt_dialogues_id_dialogue_theme  ON divers.pgt_dialogues (id_dialogue_theme);
CREATE INDEX IF NOT EXISTS ix_pgt_dialogues_id_dialogue_statut ON divers.pgt_dialogues (id_dialogue_statut);
CREATE INDEX IF NOT EXISTS ix_pgt_dialogues_modif_date         ON divers.pgt_dialogues (modif_date);


CREATE TABLE IF NOT EXISTS divers.pgt_dialoguestatut (
    id_dialogue_statut  bigint NOT NULL,  -- IDDialogueStatut
    lib_statut          varchar(50),      -- LibStatut
    couleur_statut      integer,          -- CouleurStatut
    modif_date          timestamp,        -- ModifDate
    modif_op            bigint,           -- ModifOp
    modif_elem          varchar(5),       -- ModifElem
    CONSTRAINT pk_pgt_dialoguestatut PRIMARY KEY (id_dialogue_statut)
);
CREATE INDEX IF NOT EXISTS ix_pgt_dialoguestatut_modif_date ON divers.pgt_dialoguestatut (modif_date);


CREATE TABLE IF NOT EXISTS divers.pgt_dialoguetheme (
    id_dialogue_theme  bigint NOT NULL,  -- IDDialogueTheme
    lib_theme          text,             -- LibTheme
    code_droit         varchar(10),      -- CodeDroit
    modif_date         timestamp,        -- ModifDate
    modif_op           bigint,            -- ModifOp
    modif_elem         varchar(5),        -- ModifElem
    CONSTRAINT pk_pgt_dialoguetheme PRIMARY KEY (id_dialogue_theme)
);
CREATE INDEX IF NOT EXISTS ix_pgt_dialoguetheme_modif_date ON divers.pgt_dialoguetheme (modif_date);


CREATE TABLE IF NOT EXISTS divers.pgt_dialoguepj (
    id_dialogue_pj       bigint NOT NULL,  -- IDDialoguePJ
    id_dialogues         bigint,           -- IDDialogues
    id_dialogue_msg      bigint,           -- IDDialogueMSG
    nom_fic              varchar(100),     -- NomFic
    date_heure_creation  timestamp,        -- DateHeureCreation
    expediteur           bigint,           -- Expéditeur
    modif_date           timestamp,        -- ModifDate
    modif_op             bigint,           -- ModifOp
    modif_elem           varchar(5),       -- ModifElem
    CONSTRAINT pk_pgt_dialoguepj PRIMARY KEY (id_dialogue_pj)
);
CREATE INDEX IF NOT EXISTS ix_pgt_dialoguepj_id_dialogues    ON divers.pgt_dialoguepj (id_dialogues);
CREATE INDEX IF NOT EXISTS ix_pgt_dialoguepj_id_dialogue_msg ON divers.pgt_dialoguepj (id_dialogue_msg);
CREATE INDEX IF NOT EXISTS ix_pgt_dialoguepj_modif_date      ON divers.pgt_dialoguepj (modif_date);

COMMIT;
