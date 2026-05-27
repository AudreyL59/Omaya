CREATE SCHEMA IF NOT EXISTS ticket_dpae;


CREATE TABLE ticket_dpae.pgt_tk_demande_dpae (
    id_tk_demande_dpae       bigint NOT NULL,  -- IDTK_DemandeDPAE
    id_tk_liste              bigint,  -- IDTK_Liste
    civilite                 smallint,  -- Civilité
    op_crea                  bigint,  -- OPCrea
    date_crea                timestamp,  -- dateCrea
    idorganigramme           bigint,  -- idorganigramme
    nom                      text,  -- NOM
    nom_marital              text,  -- NOM_MARITAL
    prenom                   text,  -- PRENOM
    num_ss                   text,  -- NUMSS
    dnaiss                   date,  -- DNAISS
    cpam                     text,  -- CPAM
    lnaiss                   text,  -- LNAISS
    dep_naiss                integer,  -- DEPNAISS
    num_cin                  text,  -- NUMCIN
    coopte                   boolean,  -- Coopté
    coopteur                 bigint,  -- Coopteur
    adresse1                 text,  -- ADRESSE1
    ville                    text,  -- VILLE
    cp                       varchar(5),  -- Cp
    gsm                      text,  -- GSM
    mail                     text,  -- MAIL
    urg_nom                  text,  -- URGNOM
    urg_lien                 text,  -- URGLIEN
    urg_tel                  text,  -- URGTEL
    date_debut               date,  -- DateDébut
    mutuelle                 boolean,  -- MUTUELLE
    mut_date                 date,  -- MUTDATE
    modif_date               timestamp,  -- ModifDate
    modif_elem               varchar(5),  -- ModifELEM
    modif_op                 bigint,  -- ModifOP
    travailleur_handi        boolean,  -- TravailleurHandi
    situation_fam            smallint,  -- SituationFam
    avec_enfant              boolean,  -- AvecEnfant
    nb_enfants               smallint,  -- NbEnfants
    id_tk_demande_dpae_auto  bigint,  -- IDTK_DemandeDPAEAuto
    j_odirecte               boolean,  -- JOdirecte
    jo_coopteur              bigint,  -- JOCoopteur
    nationalite              text,  -- NATIONALITE
    CONSTRAINT pk_pgt_tk_demande_dpae PRIMARY KEY (id_tk_demande_dpae),
    CONSTRAINT uq_pgt_tk_demande_dpae_auto UNIQUE (id_tk_demande_dpae_auto)
);
CREATE INDEX ix_pgt_tk_demande_dpae_id_tk_liste ON ticket_dpae.pgt_tk_demande_dpae (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_dpae_idorganigramme ON ticket_dpae.pgt_tk_demande_dpae (idorganigramme);
CREATE INDEX ix_pgt_tk_demande_dpae_coopte ON ticket_dpae.pgt_tk_demande_dpae (coopte);
CREATE INDEX ix_pgt_tk_demande_dpae_coopteur ON ticket_dpae.pgt_tk_demande_dpae (coopteur);
CREATE INDEX ix_pgt_tk_demande_dpae_date_debut ON ticket_dpae.pgt_tk_demande_dpae (date_debut);
CREATE INDEX ix_pgt_tk_demande_dpae_modif_date ON ticket_dpae.pgt_tk_demande_dpae (modif_date);

CREATE TABLE ticket_dpae.pgt_tk_demande_dpae_photo (
    id_tk_demande_dpae             bigint,  -- IDTK_DemandeDPAE
    op_crea                        bigint,  -- OPCrea
    date_crea                      timestamp,  -- dateCrea
    nom                            text,  -- NOM
    modif_date                     timestamp,  -- ModifDate
    modif_elem                     varchar(5),  -- ModifELEM
    modif_op                       bigint,  -- ModifOP
    id_tk_demande_dpae_photo       bigint NOT NULL,  -- IDTK_DemandeDPAEPhoto
    photo                          bytea,  -- PHOTO
    nom_fichier                    varchar(50),  -- NomFichier
    doc_pdf                        bytea,  -- DocPDF
    id_tk_demande_dpae_photo_auto  bigint,  -- IDTK_DemandeDPAEPhotoAuto
    id_tk_liste                    bigint,  -- IDTK_Liste
    id_tk_type_photo_dpae          bigint,  -- IDTK_TypePhotoDPAE
    CONSTRAINT pk_pgt_tk_demande_dpae_photo PRIMARY KEY (id_tk_demande_dpae_photo),
    CONSTRAINT uq_pgt_tk_demande_dpae_photo_auto UNIQUE (id_tk_demande_dpae_photo_auto)
);
CREATE INDEX ix_pgt_tk_demande_dpae_photo_id_tk_demande_dpae ON ticket_dpae.pgt_tk_demande_dpae_photo (id_tk_demande_dpae);
CREATE INDEX ix_pgt_tk_demande_dpae_photo_modif_date ON ticket_dpae.pgt_tk_demande_dpae_photo (modif_date);
CREATE INDEX ix_pgt_tk_demande_dpae_photo_id_tk_liste ON ticket_dpae.pgt_tk_demande_dpae_photo (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_dpae_photo_id_tk_type_photo_dpae ON ticket_dpae.pgt_tk_demande_dpae_photo (id_tk_type_photo_dpae);

CREATE TABLE ticket_dpae.pgt_tk_demande_dpae_photo_temp (
    id_tk_demande_dpae_photo_temp  bigint NOT NULL,  -- IDTK_DemandeDPAEPhoto_Temp
    id_tk_type_photo_dpae          bigint,  -- IDTK_TypePhotoDPAE
    id_tk_liste                    bigint,  -- IDTK_Liste
    fichier                        text,  -- Fichier
    modif_date                     timestamp,  -- ModifDate
    modif_elem                     varchar(5),  -- ModifELEM
    modif_op                       bigint,  -- ModifOP
    CONSTRAINT pk_pgt_tk_demande_dpae_photo_temp PRIMARY KEY (id_tk_demande_dpae_photo_temp)
);
CREATE INDEX ix_pgt_tk_demande_dpae_photo_temp_id_tk_type_photo_dpae ON ticket_dpae.pgt_tk_demande_dpae_photo_temp (id_tk_type_photo_dpae);
CREATE INDEX ix_pgt_tk_demande_dpae_photo_temp_id_tk_liste ON ticket_dpae.pgt_tk_demande_dpae_photo_temp (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_dpae_photo_temp_modif_date ON ticket_dpae.pgt_tk_demande_dpae_photo_temp (modif_date);

CREATE TABLE ticket_dpae.pgt_tk_dpae_doc_demat (
    id_tk_liste                bigint,  -- IDTK_Liste
    id_tk_dpae_doc_demat       bigint NOT NULL,  -- IDTK_DPAE_DocDemat
    date_signature             date,  -- DateSignature
    num_semaine                smallint,  -- NumSemaine
    nb_masque_tissu            integer,  -- nbMasqueTissu
    nb_masque_jetable          integer,  -- nbMasqueJetable
    nb_visiere                 integer,  -- nbVisiere
    nb_gel_hydro               integer,  -- nbGelHydro
    nb_lingettes               integer,  -- nbLingettes
    photo                      bytea,  -- PHOTO
    signature                  bytea,  -- Signature
    lu_app                     bytea,  -- luApp
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOP
    modif_elem                 varchar(5),  -- ModifELEM
    id_ste                     bigint,  -- IdSte
    type_doc                   varchar(10),  -- TypeDoc
    id_doc_rh                  bigint,  -- IDdocRH
    cmu                        boolean,  -- CMU
    mutuelle                   boolean,  -- MUTUELLE
    nom_mutuelle               text,  -- NomMutuelle
    date_fin_mutuelle          date,  -- DateFinMutuelle
    id_tk_dpae_doc_demat_auto  bigint,  -- IDTK_DPAE_DocDematAuto
    contenu                    bytea,  -- Contenu
    CONSTRAINT pk_pgt_tk_dpae_doc_demat PRIMARY KEY (id_tk_dpae_doc_demat),
    CONSTRAINT uq_pgt_tk_dpae_doc_demat_auto UNIQUE (id_tk_dpae_doc_demat_auto)
);
CREATE INDEX ix_pgt_tk_dpae_doc_demat_id_tk_liste ON ticket_dpae.pgt_tk_dpae_doc_demat (id_tk_liste);
CREATE INDEX ix_pgt_tk_dpae_doc_demat_date_signature ON ticket_dpae.pgt_tk_dpae_doc_demat (date_signature);
CREATE INDEX ix_pgt_tk_dpae_doc_demat_modif_date ON ticket_dpae.pgt_tk_dpae_doc_demat (modif_date);
CREATE INDEX ix_pgt_tk_dpae_doc_demat_id_ste ON ticket_dpae.pgt_tk_dpae_doc_demat (id_ste);

CREATE TABLE ticket_dpae.pgt_tk_type_photo_dpae (
    id_tk_type_photo_dpae       bigint NOT NULL,  -- IDTK_TypePhotoDPAE
    lib_type_doc                varchar(50),  -- LibTypeDoc
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOP
    modif_elem                  varchar(5),  -- ModifELEM
    desactiver                  boolean,  -- Desactiver
    nb_page                     smallint,  -- nbPage
    code_type_doc               varchar(50),  -- CodeTypeDoc
    imp_en_duo                  boolean,  -- ImpEnDuo
    id_tk_type_photo_dpae_auto  bigint,  -- IDTK_TypePhotoDPAEAuto
    CONSTRAINT pk_pgt_tk_type_photo_dpae PRIMARY KEY (id_tk_type_photo_dpae),
    CONSTRAINT uq_pgt_tk_type_photo_dpae_auto UNIQUE (id_tk_type_photo_dpae_auto)
);
CREATE INDEX ix_pgt_tk_type_photo_dpae_modif_date ON ticket_dpae.pgt_tk_type_photo_dpae (modif_date);
