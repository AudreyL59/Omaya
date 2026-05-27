CREATE SCHEMA IF NOT EXISTS scool;


CREATE TABLE scool.pgt_bulletin_mention (
    id_bulletin_mention  bigint,  -- IDBulletin_Mention
    lib_mention          varchar(50),  -- LibMention
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOP
    modif_elem           varchar(5),  -- ModifELEM
);
CREATE INDEX ix_pgt_bulletin_mention_modif_date ON scool.pgt_bulletin_mention (modif_date);

CREATE TABLE scool.pgt_formateur (
    niveau             smallint,  -- Niveau
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOP
    modif_elem         varchar(5),  -- ModifELEM
    formateur_actif    boolean,  -- FormateurActif
    id_formateur       bigint  NOT NULL,  -- IDFormateur
    i_dformateur_auto  bigint,  -- IDformateurAuto
    CONSTRAINT pk_pgt_formateur PRIMARY KEY (id_formateur),
    CONSTRAINT uq_pgt_formateur_auto UNIQUE (i_dformateur_auto)
);
CREATE INDEX ix_pgt_formateur_modif_date ON scool.pgt_formateur (modif_date);

CREATE TABLE scool.pgt_formation (
    i_dformation        bigint  NOT NULL,  -- IDformation
    intitule            text,  -- INTITULE
    nb_heure_salle      numeric,  -- nb_HeureSalle
    nb_heure_terrain    numeric,  -- nb_HeureTerrain
    ville_formation     varchar(20),  -- Ville_Formation
    date_debut          date,  -- DateDebut
    date_fin            date,  -- DateFin
    type_produit        varchar(10),  -- TypeProduit
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    modif_elem          varchar(5),  -- ModifELEM
    categorie           varchar(5),  -- Catégorie
    formateur1          bigint,  -- Formateur1
    formateur2          bigint,  -- Formateur2
    formateur3          bigint,  -- Formateur3
    formateur4          bigint,  -- Formateur4
    formateur5          bigint,  -- Formateur5
    heure_jour_salle    numeric,  -- HeureJourSalle
    heure_jour_terrain  numeric,  -- HeureJourTerrain
    duree               numeric,  -- Durée
    formation_active    boolean,  -- FormationActive
    i_dformation_auto   bigint,  -- IDformationAuto
    dest_promo          bigint,  -- DestPromo
    formation_cloturee  boolean,  -- FormationCloturee
    CONSTRAINT pk_pgt_formation PRIMARY KEY (i_dformation),
    CONSTRAINT uq_pgt_formation_auto UNIQUE (i_dformation_auto)
);
CREATE INDEX ix_pgt_formation_modif_date ON scool.pgt_formation (modif_date);
CREATE INDEX ix_pgt_formation_formation_active ON scool.pgt_formation (formation_active);

CREATE TABLE scool.pgt_formation_bareme_note (
    id_formation_bareme_note  bigint,  -- IDFormation_barèmeNote
    id_formation              bigint,  -- IDFormation
    type_note                 varchar(50),  -- TypeNote
    palier                    double precision,  -- Palier
    note                      numeric,  -- Note
    sens_recherche            varchar(4),  -- SensRecherche
    coeff                     smallint,  -- Coeff
    position_bulletin         smallint,  -- PositionBulletin
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOP
    modif_elem                varchar(5),  -- ModifELEM
);
CREATE INDEX ix_pgt_formation_bareme_note_id_formation ON scool.pgt_formation_bareme_note (id_formation);
CREATE INDEX ix_pgt_formation_bareme_note_modif_date ON scool.pgt_formation_bareme_note (modif_date);

CREATE TABLE scool.pgt_formation_bulletin (
    id_formation_bulletin  bigint,  -- IDFormation_Bulletin
    id_formation           bigint,  -- IDFormation
    id_salarie             bigint,  -- IDSalarie
    du                     date,  -- Du
    au                     date,  -- Au
    nb_jours_form          smallint,  -- nbJoursForm
    nb_jours_pres          smallint,  -- nbJoursPres
    note_assiduite         numeric,  -- NoteAssiduite
    objectif_ctt           smallint,  -- ObjectifCtt
    nb_ctt_hr              smallint,  -- nbCttHR
    note_ctt_hr            numeric,  -- NoteCttHR
    nb_cqt_hr              smallint,  -- nbCqtHR
    note_cqt               numeric,  -- NoteCQT
    nb_prem_hr             smallint,  -- nbPremHR
    note_prem              numeric,  -- NotePREM
    nb_mob_hr              smallint,  -- nbMobHR
    note_mob               numeric,  -- NoteMOB
    objectif_decale        boolean,  -- ObjectifDécalé
    note_obj_decale        numeric,  -- NoteObjDécalé
    objectif_coopt         smallint,  -- ObjectifCoopt
    nb_coopt               smallint,  -- nbCoopt
    note_coopt             numeric,  -- NoteCoopt
    note_app_theo          numeric,  -- NoteAPP_Théo
    note_app_pratique      numeric,  -- NoteAPP_Pratique
    id_bulletin_mention    bigint,  -- IDBulletin_Mention
    observation            text,  -- Observation
    axe_travail            text,  -- AxeTravail
    type_bulletin          boolean,  -- TypeBulletin
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOP
    modif_elem             varchar(5),  -- ModifELEM
);
CREATE INDEX ix_pgt_formation_bulletin_id_formation ON scool.pgt_formation_bulletin (id_formation);
CREATE INDEX ix_pgt_formation_bulletin_id_salarie ON scool.pgt_formation_bulletin (id_salarie);
CREATE INDEX ix_pgt_formation_bulletin_id_bulletin_mention ON scool.pgt_formation_bulletin (id_bulletin_mention);
CREATE INDEX ix_pgt_formation_bulletin_modif_date ON scool.pgt_formation_bulletin (modif_date);

CREATE TABLE scool.pgt_formation_evenement (
    id_formation_evenement_auto  bigint,  -- IDFormationEvenementAuto
    id_formation_evenement       bigint  NOT NULL,  -- IDFormationEvenement
    id_formation                 bigint,  -- IDFormation
    id_salarie                   bigint,  -- IDSalarie
    date                         date,  -- DATE
    intitule                     text,  -- INTITULE
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOP
    modif_elem                   varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_formation_evenement PRIMARY KEY (id_formation_evenement),
    CONSTRAINT uq_pgt_formation_evenement_auto UNIQUE (id_formation_evenement_auto)
);
CREATE INDEX ix_pgt_formation_evenement_id_formation ON scool.pgt_formation_evenement (id_formation);
CREATE INDEX ix_pgt_formation_evenement_id_salarie ON scool.pgt_formation_evenement (id_salarie);
CREATE INDEX ix_pgt_formation_evenement_date ON scool.pgt_formation_evenement (date);
CREATE INDEX ix_pgt_formation_evenement_modif_date ON scool.pgt_formation_evenement (modif_date);

CREATE TABLE scool.pgt_formation_prev_recrut (
    id_formation_prev_recrut  bigint,  -- IDFormation_PrevRecrut
    id_formation              bigint,  -- IDFormation
    id_prevision_recrut       bigint,  -- IDPrevisionRecrut
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOP
    modif_elem                varchar(5),  -- ModifELEM
);
CREATE INDEX ix_pgt_formation_prev_recrut_id_formation ON scool.pgt_formation_prev_recrut (id_formation);
CREATE INDEX ix_pgt_formation_prev_recrut_id_prevision_recrut ON scool.pgt_formation_prev_recrut (id_prevision_recrut);
CREATE INDEX ix_pgt_formation_prev_recrut_modif_date ON scool.pgt_formation_prev_recrut (modif_date);

CREATE TABLE scool.pgt_formation_programme (
    i_dformation_programme_auto  bigint,  -- IDformation_programmeAuto
    i_dformation_programme       bigint  NOT NULL,  -- IDformation_programme
    id_formation                 bigint,  -- idFormation
    num_semaine                  smallint,  -- NumSemaine
    date                         date,  -- Date
    salle                        numeric,  -- Salle
    terrain                      numeric,  -- Terrain
    duree                        numeric,  -- Durée
    horaires                     varchar(50),  -- Horaires
    objectif                     double precision,  -- objectif
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOP
    modif_elem                   varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_formation_programme PRIMARY KEY (i_dformation_programme),
    CONSTRAINT uq_pgt_formation_programme_auto UNIQUE (i_dformation_programme_auto)
);
CREATE INDEX ix_pgt_formation_programme_id_formation ON scool.pgt_formation_programme (id_formation);
CREATE INDEX ix_pgt_formation_programme_modif_date ON scool.pgt_formation_programme (modif_date);

CREATE TABLE scool.pgt_formation_salarie (
    id_salarie                 bigint,  -- IDSalarie
    date_debut                 date,  -- DateDebut
    date_fin                   date,  -- DateFin
    idorganigramme             bigint,  -- idorganigramme
    i_dformation               bigint,  -- IDformation
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOP
    modif_elem                 varchar(5),  -- ModifELEM
    i_dformation_salarie_auto  bigint  NOT NULL,  -- IDformation_SalarieAuto
    livrable                   boolean,  -- Livrable
    i_dformation_id_salarie    varchar(16),  -- IDformationIDSalarie
    CONSTRAINT pk_pgt_formation_salarie PRIMARY KEY (i_dformation_salarie_auto)
);
CREATE INDEX ix_pgt_formation_salarie_id_salarie ON scool.pgt_formation_salarie (id_salarie);
CREATE INDEX ix_pgt_formation_salarie_idorganigramme ON scool.pgt_formation_salarie (idorganigramme);
CREATE INDEX ix_pgt_formation_salarie_i_dformation ON scool.pgt_formation_salarie (i_dformation);
CREATE INDEX ix_pgt_formation_salarie_modif_date ON scool.pgt_formation_salarie (modif_date);

CREATE TABLE scool.pgt_form_modele (
    id_modele_form_auto  bigint,  -- IDModèleFormAuto
    id_modele_form       bigint  NOT NULL,  -- IDModèleForm
    intitule             text,  -- INTITULE
    categorie            varchar(5),  -- Catégorie
    nb_heure_salle       numeric,  -- nb_HeureSalle
    nb_heure_terrain     numeric,  -- nb_HeureTerrain
    heure_jour_salle     numeric,  -- HeureJourSalle
    heure_jour_terrain   numeric,  -- HeureJourTerrain
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOP
    modif_elem           varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_form_modele PRIMARY KEY (id_modele_form),
    CONSTRAINT uq_pgt_form_modele_auto UNIQUE (id_modele_form_auto)
);
CREATE INDEX ix_pgt_form_modele_modif_date ON scool.pgt_form_modele (modif_date);

CREATE TABLE scool.pgt_form_modele_programme (
    id_modele_programme_auto  bigint,  -- IDModèle_ProgrammeAuto
    id_modele_programme       bigint  NOT NULL,  -- IDModèle_Programme
    id_modele_form            bigint,  -- IDModèleForm
    date                      smallint,  -- Date
    salle                     numeric,  -- Salle
    terrain                   numeric,  -- Terrain
    duree                     numeric,  -- Durée
    horaires                  varchar(50),  -- Horaires
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOP
    modif_elem                varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_form_modele_programme PRIMARY KEY (id_modele_programme),
    CONSTRAINT uq_pgt_form_modele_programme_auto UNIQUE (id_modele_programme_auto)
);
CREATE INDEX ix_pgt_form_modele_programme_id_modele_form ON scool.pgt_form_modele_programme (id_modele_form);
CREATE INDEX ix_pgt_form_modele_programme_modif_date ON scool.pgt_form_modele_programme (modif_date);
