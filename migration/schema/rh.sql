CREATE SCHEMA IF NOT EXISTS rh;


CREATE TABLE rh.pgt_absence (
    id_absence_auto                    bigint,  -- IdAbsenceAuto
    id_absence                         bigint NOT NULL,  -- IdAbsence
    id_salarie                         bigint,  -- IDSalarie
    id_type_absence                    integer,  -- IDTypeAbsence
    date_debut                         date,  -- DateDEBUT
    date_fin                           date,  -- DateFIN
    nbj                                integer,  -- NBJ
    nbj_ouvres                         integer,  -- NBJ_OUVRES
    nb_samedi                          smallint,  -- nbSamedi
    periode                            varchar(9),  -- Période
    modif_op                           bigint,  -- ModifOP
    modif_date                         timestamp,  -- ModifDate
    modif_elem                         varchar(5),  -- ModifELEM
    optim_cle_comp_id_sal_absen_absen  varchar(24),  -- OptimCleComp_IDSal_absen_absen
    optim_cle_comp_id_sal_absen        varchar(16),  -- OptimCleComp_IDSal_absen
    CONSTRAINT pk_pgt_absence PRIMARY KEY (id_absence),
    CONSTRAINT uq_pgt_absence_auto UNIQUE (id_absence_auto)
);
CREATE INDEX ix_pgt_absence_id_salarie ON rh.pgt_absence (id_salarie);
CREATE INDEX ix_pgt_absence_id_type_absence ON rh.pgt_absence (id_type_absence);
CREATE INDEX ix_pgt_absence_date_debut ON rh.pgt_absence (date_debut);
CREATE INDEX ix_pgt_absence_date_fin ON rh.pgt_absence (date_fin);
CREATE INDEX ix_pgt_absence_modif_date ON rh.pgt_absence (modif_date);

CREATE TABLE rh.pgt_derogation_orga (
    id_derogation_orga_auto  bigint,  -- IDDerogationOrgaAuto
    id_derogation_orga       bigint NOT NULL,  -- IDDerogationOrga
    id_salarie               bigint,  -- IDSalarie
    idorganigramme           bigint,  -- idorganigramme
    date_debut               date,  -- DateDEBUT
    date_fin                 date,  -- DATEFIN
    modif_op                 bigint,  -- ModifOP
    modif_elem               varchar(5),  -- ModifELEM
    modif_date               timestamp,  -- ModifDate
    CONSTRAINT pk_pgt_derogation_orga PRIMARY KEY (id_derogation_orga),
    CONSTRAINT uq_pgt_derogation_orga_auto UNIQUE (id_derogation_orga_auto)
);
CREATE INDEX ix_pgt_derogation_orga_id_salarie ON rh.pgt_derogation_orga (id_salarie);
CREATE INDEX ix_pgt_derogation_orga_idorganigramme ON rh.pgt_derogation_orga (idorganigramme);
CREATE INDEX ix_pgt_derogation_orga_modif_date ON rh.pgt_derogation_orga (modif_date);

CREATE TABLE rh.pgt_doc_distrib (
    id_doc_distrib            bigint NOT NULL,  -- IDDoc_Distrib
    id_ste                    bigint,  -- IdSte
    id_gerant                 bigint,  -- IdGérant
    id_type_doc_distributeur  bigint,  -- IDTypeDocDistributeur
    date_prevue               date,  -- DatePrévue
    date_depot                date,  -- DateDépot
    nom_fichier               text,  -- NomFichier
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_doc_distrib PRIMARY KEY (id_doc_distrib)
);
CREATE INDEX ix_pgt_doc_distrib_id_ste ON rh.pgt_doc_distrib (id_ste);
CREATE INDEX ix_pgt_doc_distrib_id_gerant ON rh.pgt_doc_distrib (id_gerant);
CREATE INDEX ix_pgt_doc_distrib_id_type_doc_distributeur ON rh.pgt_doc_distrib (id_type_doc_distributeur);
CREATE INDEX ix_pgt_doc_distrib_modif_date ON rh.pgt_doc_distrib (modif_date);

CREATE TABLE rh.pgt_doc_courtage (
    id_doc_courtage      bigint NOT NULL,  -- IDdocCourtage
    titre                varchar(255),  -- Titre
    info_cpl             varchar(50),  -- InfoCpl
    id_groupe_operateur  bigint,  -- IDGroupeOpérateur
    contenu              bytea,  -- Contenu
    datecrea             timestamp,  -- Datecrea
    doc_actif            boolean,  -- DocActif
    prioritaire          boolean,  -- Prioritaire
    id_ste               bigint,  -- IdSte
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_doc_courtage PRIMARY KEY (id_doc_courtage)
);
CREATE INDEX ix_pgt_doc_courtage_id_ste ON rh.pgt_doc_courtage (id_ste);
CREATE INDEX ix_pgt_doc_courtage_modif_date ON rh.pgt_doc_courtage (modif_date);

CREATE TABLE rh.pgt_doc_rh (
    id_doc_rh              bigint NOT NULL,  -- IDdocRH
    id_type_doc            bigint,  -- IDTypeDoc
    titre                  varchar(255),  -- Titre
    info_cpl               varchar(50),  -- InfoCpl
    id_type_produit        bigint,  -- IDTypeProduit
    contenu                bytea,  -- Contenu
    datecrea               timestamp,  -- Datecrea
    doc_actif              boolean,  -- DocActif
    prioritaire            boolean,  -- Prioritaire
    id_ste                 bigint,  -- IdSte
    doc_dpae               boolean,  -- DocDPAE
    doc_dpae_distrib       boolean,  -- DocDPAE_Distrib
    id_tk_type_photo_dpae  bigint,  -- IDTK_TypePhotoDPAE
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOp
    modif_elem             varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_doc_rh PRIMARY KEY (id_doc_rh)
);
CREATE INDEX ix_pgt_doc_rh_id_type_doc ON rh.pgt_doc_rh (id_type_doc);
CREATE INDEX ix_pgt_doc_rh_id_ste ON rh.pgt_doc_rh (id_ste);
CREATE INDEX ix_pgt_doc_rh_modif_date ON rh.pgt_doc_rh (modif_date);

CREATE TABLE rh.pgt_doc_rhtype (
    id_type_doc_auto  bigint,  -- IDTypeDocAuto
    id_type_doc       bigint NOT NULL,  -- IDTypeDoc
    lib_type          text,  -- Lib_Type
    modif_op          bigint,  -- ModifOP
    modif_date        timestamp,  -- ModifDate
    modif_elem        varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_doc_rhtype PRIMARY KEY (id_type_doc),
    CONSTRAINT uq_pgt_doc_rhtype_auto UNIQUE (id_type_doc_auto)
);
CREATE INDEX ix_pgt_doc_rhtype_lib_type ON rh.pgt_doc_rhtype (lib_type);
CREATE INDEX ix_pgt_doc_rhtype_modif_date ON rh.pgt_doc_rhtype (modif_date);

CREATE TABLE rh.pgt_mutuelle (
    id_mutuelle_auto  bigint,  -- IDmutuelleAuto
    id_mutuelle       smallint NOT NULL,  -- IdMutuelle
    lib_mutuelle      varchar(50),  -- Lib_Mutuelle
    is_actif          boolean,  -- IsActif
    modif_date        timestamp,  -- ModifDate
    modif_op          bigint,  -- ModifOp
    modif_elem        varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_mutuelle PRIMARY KEY (id_mutuelle),
    CONSTRAINT uq_pgt_mutuelle_auto UNIQUE (id_mutuelle_auto)
);
CREATE INDEX ix_pgt_mutuelle_modif_date ON rh.pgt_mutuelle (modif_date);

CREATE TABLE rh.pgt_note_frais (
    id_note_frais_auto  bigint,  -- IDNoteFraisAuto
    id_note_frais       bigint NOT NULL,  -- IDNoteFrais
    id_salarie          bigint,  -- IDSalarie
    id_note_frais_type  bigint,  -- IDNoteFraisType
    periode_note        date,  -- PériodeNote
    date                date,  -- Date
    description         text,  -- Description
    montant_ttc         numeric(19,4),  -- MontantTTC
    montant_ht          numeric(19,4),  -- MontantHT
    montant_tva         numeric(19,4),  -- MontantTVA
    photo_ticket        bytea,  -- PhotoTicket
    verifiee            boolean,  -- Vérifiée
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_note_frais PRIMARY KEY (id_note_frais),
    CONSTRAINT uq_pgt_note_frais_auto UNIQUE (id_note_frais_auto)
);
CREATE INDEX ix_pgt_note_frais_id_salarie ON rh.pgt_note_frais (id_salarie);
CREATE INDEX ix_pgt_note_frais_id_note_frais_type ON rh.pgt_note_frais (id_note_frais_type);
CREATE INDEX ix_pgt_note_frais_modif_date ON rh.pgt_note_frais (modif_date);

CREATE TABLE rh.pgt_note_frais_type (
    id_note_frais_type_auto  bigint,  -- IDNoteFraisTypeAuto
    id_note_frais_type       bigint NOT NULL,  -- IDNoteFraisType
    lib_type_note_frais      varchar(50),  -- LibTypeNoteFrais
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOP
    modif_elem               varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_note_frais_type PRIMARY KEY (id_note_frais_type),
    CONSTRAINT uq_pgt_note_frais_type_auto UNIQUE (id_note_frais_type_auto)
);
CREATE INDEX ix_pgt_note_frais_type_modif_date ON rh.pgt_note_frais_type (modif_date);

CREATE TABLE rh.pgt_organigramme (
    id_organigramme_auto  bigint,  -- IdOrganigrammeAuto
    idorganigramme        bigint NOT NULL,  -- idorganigramme
    id_parent             bigint,  -- IdPARENT
    lib_orga              text,  -- Lib_ORGA
    in_visible_podium     boolean,  -- InVisiblePODIUM
    in_visible_effectif   boolean,  -- InVisibleEffectif
    memo                  text,  -- Mémo
    secteur               text,  -- Secteur
    id_type_orga          integer,  -- IDTypeOrga
    id_type_niveau_orga   integer,  -- IDTypeNiveauOrga
    id_type_produit       bigint,  -- IDTypeProduit
    id_ste                bigint,  -- IdSte
    id_distri             bigint,  -- IdDistri
    capacite              smallint,  -- Capacité
    ville                 text,  -- VILLE
    nom_resp              text,  -- NomResp
    modif_date            timestamp,  -- ModifDate
    modif_op              bigint,  -- ModifOP
    modif_elem            varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_organigramme PRIMARY KEY (idorganigramme),
    CONSTRAINT uq_pgt_organigramme_auto UNIQUE (id_organigramme_auto)
);
CREATE INDEX ix_pgt_organigramme_id_parent ON rh.pgt_organigramme (id_parent);
CREATE INDEX ix_pgt_organigramme_secteur ON rh.pgt_organigramme (secteur);
CREATE INDEX ix_pgt_organigramme_id_type_orga ON rh.pgt_organigramme (id_type_orga);
CREATE INDEX ix_pgt_organigramme_id_type_niveau_orga ON rh.pgt_organigramme (id_type_niveau_orga);
CREATE INDEX ix_pgt_organigramme_id_type_produit ON rh.pgt_organigramme (id_type_produit);
CREATE INDEX ix_pgt_organigramme_id_ste ON rh.pgt_organigramme (id_ste);
CREATE INDEX ix_pgt_organigramme_modif_date ON rh.pgt_organigramme (modif_date);

CREATE TABLE rh.pgt_profil_droit_acces (
    id_profil_droit_acces          bigint NOT NULL,  -- IDProfilDroitAccès
    id_type_droit_acces            integer,  -- IDTypeDroitAccès
    categorie                      varchar(15),  -- Catégorie
    id_type_droit_acces_categorie  varchar(19),  -- IDTypeDroitAccèsCatégorie
    modif_date                     timestamp,  -- ModifDate
    modif_op                       bigint,  -- ModifOp
    modif_elem                     varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_profil_droit_acces PRIMARY KEY (id_profil_droit_acces)
);
CREATE INDEX ix_pgt_profil_droit_acces_id_type_droit_acces ON rh.pgt_profil_droit_acces (id_type_droit_acces);
CREATE INDEX ix_pgt_profil_droit_acces_categorie ON rh.pgt_profil_droit_acces (categorie);
CREATE INDEX ix_pgt_profil_droit_acces_modif_date ON rh.pgt_profil_droit_acces (modif_date);

CREATE TABLE rh.pgt_salarie (
    id_salarie_auto    bigint,  -- IDsalarieAuto
    id_salarie         bigint NOT NULL,  -- IDSalarie
    civilite           smallint,  -- Civilité
    nom                text,  -- Nom
    nom_marital        text,  -- Nom_Marital
    prenom             text,  -- Prenom
    sexe               varchar(1),  -- Sexe
    nationalite        text,  -- Nationalité
    date_naiss         date,  -- Date_Naiss
    lieu_naiss         text,  -- Lieu_Naiss
    dep_naiss          smallint,  -- Dep_Naiss
    num_ss             text,  -- Num_SS
    cpam               text,  -- CPAM
    num_cin            text,  -- NumCIN
    situation_fam      smallint,  -- SituationFam
    avec_enfant        boolean,  -- AvecEnfant
    nb_enfants         smallint,  -- NbEnfants
    travailleur_handi  boolean,  -- TravailleurHandi
    matricule_tr       varchar(15),  -- MatriculeTR
    agenda_actif       boolean,  -- AgendaActif
    op_crea            bigint,  -- OPCREA
    datecrea           timestamp,  -- Datecrea
    photo              bytea,  -- Photo
    login              text,  -- LOGIN
    mdp_crypte         varchar(50),  -- MDPCrypte
    id_utilisateur     integer,  -- IDUtilisateur
    active_log         boolean,  -- ActiveLog
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOp
    modif_elem         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salarie PRIMARY KEY (id_salarie),
    CONSTRAINT uq_pgt_salarie_auto UNIQUE (id_salarie_auto)
);
CREATE INDEX ix_pgt_salarie_login ON rh.pgt_salarie (login);
CREATE INDEX ix_pgt_salarie_id_utilisateur ON rh.pgt_salarie (id_utilisateur);
CREATE INDEX ix_pgt_salarie_modif_date ON rh.pgt_salarie (modif_date);

CREATE TABLE rh.pgt_salarie_adf (
    id_salarie_adf_auto  bigint,  -- IdSalarie_ADFAuto
    id_salarie_adf       bigint NOT NULL,  -- IDsalarie_ADF
    id_salarie           bigint,  -- IDSalarie
    date                 date,  -- Date
    horaires             varchar(7),  -- Horaires
    id_formateur         bigint,  -- IDFormateur
    id_agence            bigint,  -- IDAgence
    nb_ctt_vendeur       bigint,  -- NBCttVendeur
    nb_ctt_formateur     bigint,  -- NBCttFormateur
    observations         text,  -- Observations
    axe_travail1         text,  -- AxeTravail1
    axe_travail2         text,  -- AxeTravail2
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salarie_adf PRIMARY KEY (id_salarie_adf),
    CONSTRAINT uq_pgt_salarie_adf_auto UNIQUE (id_salarie_adf_auto)
);
CREATE INDEX ix_pgt_salarie_adf_id_salarie ON rh.pgt_salarie_adf (id_salarie);
CREATE INDEX ix_pgt_salarie_adf_id_formateur ON rh.pgt_salarie_adf (id_formateur);
CREATE INDEX ix_pgt_salarie_adf_modif_date ON rh.pgt_salarie_adf (modif_date);

CREATE TABLE rh.pgt_salarie_adf_item (
    id_salarie_adf_item  bigint NOT NULL,  -- IDsalarie_ADF_Item
    id_salarie_adf       bigint,  -- IDsalarie_ADF
    id_type_adf_item     bigint,  -- IDTypeADF_Item
    note                 smallint,  -- Note
    datecrea             timestamp,  -- Datecrea
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salarie_adf_item PRIMARY KEY (id_salarie_adf_item)
);
CREATE INDEX ix_pgt_salarie_adf_item_id_salarie_adf ON rh.pgt_salarie_adf_item (id_salarie_adf);
CREATE INDEX ix_pgt_salarie_adf_item_id_type_adf_item ON rh.pgt_salarie_adf_item (id_type_adf_item);
CREATE INDEX ix_pgt_salarie_adf_item_modif_date ON rh.pgt_salarie_adf_item (modif_date);

CREATE TABLE rh.pgt_salarie_avance (
    id_salarie_avance  bigint NOT NULL,  -- IDsalarie_avance
    id_salarie         bigint,  -- IDSalarie
    mois_salaire       date,  -- MoisSalaire
    montant            numeric(19,4),  -- Montant
    detai_avance       text,  -- DétaiAvance
    date_effective     date,  -- DateEffective
    date_crea          timestamp,  -- DateCrea
    op_crea            bigint,  -- OpCrea
    id_tk_liste        bigint,  -- IDTK_Liste
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOP
    modif_elem         varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_salarie_avance PRIMARY KEY (id_salarie_avance)
);
CREATE INDEX ix_pgt_salarie_avance_id_salarie ON rh.pgt_salarie_avance (id_salarie);
CREATE INDEX ix_pgt_salarie_avance_id_tk_liste ON rh.pgt_salarie_avance (id_tk_liste);
CREATE INDEX ix_pgt_salarie_avance_modif_date ON rh.pgt_salarie_avance (modif_date);

CREATE TABLE rh.pgt_salarie_coordonnees (
    id_salarie_coordonnees  bigint,  -- IDsalarie_coordonnées
    id_salarie              bigint NOT NULL,  -- IDSalarie
    adresse1                text,  -- Adresse1
    adresse2                text,  -- Adresse2
    cp                      varchar(5),  -- CP
    ville                   text,  -- Ville
    tel_fixe                varchar(15),  -- TélFixe
    tel_mob                 varchar(15),  -- TélMob
    mail                    text,  -- Mail
    mail2                   text,  -- Mail2
    urg_nom                 text,  -- UrgNom
    urg_lien                text,  -- UrgLien
    urg_tel                 text,  -- UrgTél
    iban                    text,  -- IBAN
    bic                     text,  -- BIC
    modif_date              timestamp,  -- ModifDate
    modif_op                bigint,  -- ModifOp
    modif_elem              varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salarie_coordonnees PRIMARY KEY (id_salarie),
    CONSTRAINT uq_pgt_salarie_coordonnees_auto UNIQUE (id_salarie_coordonnees)
);
CREATE INDEX ix_pgt_salarie_coordonnees_modif_date ON rh.pgt_salarie_coordonnees (modif_date);

CREATE TABLE rh.pgt_salarie_decl_presence (
    id_declaratif_presence_auto  bigint,  -- IDdeclaratif_presenceAuto
    id_declaratif_presence       bigint NOT NULL,  -- IDdeclaratif_presence
    id_salarie                   bigint,  -- IDSalarie
    date                         date,  -- Date
    presence                     boolean,  -- Presence
    motifabsence                 bigint,  -- Motifabsence
    periode_absence              smallint,  -- PeriodeAbsence
    type_journee                 smallint,  -- TypeJournée
    is_scool                     boolean,  -- IsScool
    emargement_matin             bytea,  -- emargementMatin
    emargement_aprem             bytea,  -- emargementAprem
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOP
    modif_elem                   varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_salarie_decl_presence PRIMARY KEY (id_declaratif_presence),
    CONSTRAINT uq_pgt_salarie_decl_presence_auto UNIQUE (id_declaratif_presence_auto)
);
CREATE INDEX ix_pgt_salarie_decl_presence_id_salarie ON rh.pgt_salarie_decl_presence (id_salarie);
CREATE INDEX ix_pgt_salarie_decl_presence_modif_date ON rh.pgt_salarie_decl_presence (modif_date);

CREATE TABLE rh.pgt_salarie_decl_production (
    id_declaratif_production_auto  bigint,  -- IDdeclaratif_productionAuto
    id_declaratif_production       bigint NOT NULL,  -- IDdeclaratif_production
    id_salarie                     bigint,  -- IDSalarie
    date                           date,  -- Date
    id_type_prod_dec               bigint,  -- IdTypeProdDec
    nb_brut                        integer,  -- nbBrut
    nb_adf                         integer,  -- nbADF
    is_scool                       boolean,  -- IsScool
    modif_op                       bigint,  -- ModifOP
    modif_date                     timestamp,  -- ModifDate
    modif_elem                     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_salarie_decl_production PRIMARY KEY (id_declaratif_production),
    CONSTRAINT uq_pgt_salarie_decl_production_auto UNIQUE (id_declaratif_production_auto)
);
CREATE INDEX ix_pgt_salarie_decl_production_id_salarie ON rh.pgt_salarie_decl_production (id_salarie);
CREATE INDEX ix_pgt_salarie_decl_production_id_type_prod_dec ON rh.pgt_salarie_decl_production (id_type_prod_dec);
CREATE INDEX ix_pgt_salarie_decl_production_modif_date ON rh.pgt_salarie_decl_production (modif_date);

CREATE TABLE rh.pgt_salarie_doc_rh (
    id_salarie_doc_rh        bigint NOT NULL,  -- IDsalarie_docRH
    id_doc_rhtype            bigint,  -- IDdocRHTYPE
    id_salarie               bigint,  -- IDSalarie
    id_da                    bigint,  -- ID_DA
    id_docusign              text,  -- IdDocusign
    date_edition             timestamp,  -- DATE_Edition
    recu                     boolean,  -- RECU
    recu_date                timestamp,  -- RECUDATE
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOP
    modif_elem               varchar(5),  -- ModifELEM
    id_salarie_date_edition  varchar(16),  -- IDSalarieDATE_Edition
    CONSTRAINT pk_pgt_salarie_doc_rh PRIMARY KEY (id_salarie_doc_rh)
);
CREATE INDEX ix_pgt_salarie_doc_rh_id_doc_rhtype ON rh.pgt_salarie_doc_rh (id_doc_rhtype);
CREATE INDEX ix_pgt_salarie_doc_rh_id_salarie ON rh.pgt_salarie_doc_rh (id_salarie);
CREATE INDEX ix_pgt_salarie_doc_rh_id_da ON rh.pgt_salarie_doc_rh (id_da);
CREATE INDEX ix_pgt_salarie_doc_rh_modif_date ON rh.pgt_salarie_doc_rh (modif_date);

CREATE TABLE rh.pgt_salarie_doc_ulease (
    id_salarie_doc_ulease    bigint NOT NULL,  -- IDsalarie_docUlease
    id_doc_ulease_type       bigint,  -- IDdocUleaseTYPE
    id_salarie               bigint,  -- IDSalarie
    id_da                    bigint,  -- ID_DA
    id_docusign              text,  -- IdDocusign
    date_edition             timestamp,  -- DATE_Edition
    recu                     boolean,  -- RECU
    recu_date                timestamp,  -- RECUDATE
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOP
    modif_elem               varchar(5),  -- ModifELEM
    id_salarie_date_edition  varchar(16),  -- IDSalarieDATE_Edition
    CONSTRAINT pk_pgt_salarie_doc_ulease PRIMARY KEY (id_salarie_doc_ulease)
);
CREATE INDEX ix_pgt_salarie_doc_ulease_id_doc_ulease_type ON rh.pgt_salarie_doc_ulease (id_doc_ulease_type);
CREATE INDEX ix_pgt_salarie_doc_ulease_id_salarie ON rh.pgt_salarie_doc_ulease (id_salarie);
CREATE INDEX ix_pgt_salarie_doc_ulease_id_da ON rh.pgt_salarie_doc_ulease (id_da);
CREATE INDEX ix_pgt_salarie_doc_ulease_modif_date ON rh.pgt_salarie_doc_ulease (modif_date);

CREATE TABLE rh.pgt_salarie_droit_acces (
    id_salarie_droit_acces          bigint NOT NULL,  -- IDsalarie_droitAccès
    id_salarie                      bigint,  -- IDSalarie
    id_type_droit_acces             integer,  -- IDTypeDroitAccès
    droit_actif                     boolean,  -- DroitActif
    modif_date                      timestamp,  -- ModifDate
    modif_op                        bigint,  -- ModifOp
    modif_elem                      varchar(5),  -- ModifElem
    id_salarie_id_type_droit_acces  varchar(12),  -- IDSalarieIDTypeDroitAccès
    CONSTRAINT pk_pgt_salarie_droit_acces PRIMARY KEY (id_salarie_droit_acces)
);
CREATE INDEX ix_pgt_salarie_droit_acces_id_salarie ON rh.pgt_salarie_droit_acces (id_salarie);
CREATE INDEX ix_pgt_salarie_droit_acces_id_type_droit_acces ON rh.pgt_salarie_droit_acces (id_type_droit_acces);
CREATE INDEX ix_pgt_salarie_droit_acces_modif_date ON rh.pgt_salarie_droit_acces (modif_date);

CREATE TABLE rh.pgt_salarie_embauche (
    id_salarie_embauche    bigint,  -- IDsalarie_embauche
    id_salarie             bigint NOT NULL,  -- IDSalarie
    date_debut             date,  -- DateDebut
    date_fin_per_essai     date,  -- DateFinPerEssai
    date_anciennete        date,  -- DateAncienneté
    en_activite            boolean,  -- EnActivité
    dpae_date              date,  -- DPAE_date
    dpae_num               varchar(10),  -- DPAE_num
    dpae_ope               bigint,  -- DPAE_Opé
    id_type_poste          smallint,  -- IdTypePoste
    id_type_ctt            integer,  -- IDTypeCtt
    id_type_horaire        integer,  -- IDTypeHoraire
    id_ste                 bigint,  -- IdSte
    id_ste_dpae_energie    bigint,  -- idSteDpaeEnergie
    id_ste_dpae_fibre      bigint,  -- idSteDpaeFibre
    coopte                 boolean,  -- Coopté
    coopteur               bigint,  -- Coopteur
    j_odirecte             boolean,  -- JOdirecte
    jo_coopteur            bigint,  -- JOCoopteur
    resp_equipe            boolean,  -- RespEquipe
    resp_adjoint           boolean,  -- RespAdjoint
    chauffeur              boolean,  -- Chauffeur
    multi_prod             boolean,  -- MultiProd
    en_pause               boolean,  -- EnPause
    id_absence             bigint,  -- IdAbsence
    id_cvtheque            bigint,  -- IDcvtheque
    cin_envoyee            boolean,  -- CIN_envoyée
    cj_envoye              boolean,  -- CJ_envoyé
    formation_iag          boolean,  -- FormationIAG
    formation_iag_date     date,  -- FormationIAG_Date
    formation_iag_score    smallint,  -- FormationIAG_Score
    permis_vente_suspendu  boolean,  -- PermisVenteSuspendu
    permis_cumul_primes    smallint,  -- PermisCumulPrimes
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOp
    modif_elem             varchar(5),  -- ModifElem
    id_salarie_trans_prod  bigint,  -- IdSalarieTransProd
    CONSTRAINT pk_pgt_salarie_embauche PRIMARY KEY (id_salarie),
    CONSTRAINT uq_pgt_salarie_embauche_auto UNIQUE (id_salarie_embauche)
);
CREATE INDEX ix_pgt_salarie_embauche_id_type_poste ON rh.pgt_salarie_embauche (id_type_poste);
CREATE INDEX ix_pgt_salarie_embauche_id_type_ctt ON rh.pgt_salarie_embauche (id_type_ctt);
CREATE INDEX ix_pgt_salarie_embauche_id_type_horaire ON rh.pgt_salarie_embauche (id_type_horaire);
CREATE INDEX ix_pgt_salarie_embauche_id_ste ON rh.pgt_salarie_embauche (id_ste);
CREATE INDEX ix_pgt_salarie_embauche_id_ste_dpae_energie ON rh.pgt_salarie_embauche (id_ste_dpae_energie);
CREATE INDEX ix_pgt_salarie_embauche_id_ste_dpae_fibre ON rh.pgt_salarie_embauche (id_ste_dpae_fibre);
CREATE INDEX ix_pgt_salarie_embauche_id_absence ON rh.pgt_salarie_embauche (id_absence);
CREATE INDEX ix_pgt_salarie_embauche_id_cvtheque ON rh.pgt_salarie_embauche (id_cvtheque);
CREATE INDEX ix_pgt_salarie_embauche_modif_date ON rh.pgt_salarie_embauche (modif_date);

CREATE TABLE rh.pgt_salarie_infotbx (
    id_salarie_info_tbx  bigint NOT NULL,  -- IDsalarie_infoTbx
    id_salarie           bigint,  -- IDSalarie
    idorganigramme       bigint,  -- idorganigramme
    mois_salaire         date,  -- MoisSalaire
    scool                boolean,  -- Scool
    montant_ik           numeric(19,4),  -- MontantIK
    montant_retenu       numeric(19,4),  -- MontantRetenu
    motif_retenu         text,  -- MotifRetenu
    commentaire_da       text,  -- CommentaireDA
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOP
    modif_elem           varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_salarie_infotbx PRIMARY KEY (id_salarie_info_tbx)
);
CREATE INDEX ix_pgt_salarie_infotbx_id_salarie ON rh.pgt_salarie_infotbx (id_salarie);
CREATE INDEX ix_pgt_salarie_infotbx_idorganigramme ON rh.pgt_salarie_infotbx (idorganigramme);
CREATE INDEX ix_pgt_salarie_infotbx_modif_date ON rh.pgt_salarie_infotbx (modif_date);

CREATE TABLE rh.pgt_salarie_livret (
    id_salarie_livret         bigint NOT NULL,  -- IDsalarie_Livret
    id_salarie                bigint,  -- IDSalarie
    id_type_operation_livret  integer,  -- IDTypeOperationLivret
    id_challenge              bigint,  -- IDChallenge
    id_tk_liste               bigint,  -- IDTK_Liste
    montant_credit            numeric(19,4),  -- MontantCrédit
    montant_debit             numeric(19,4),  -- MontantDébit
    date_operation            timestamp,  -- DateOpération
    operateur                 bigint,  -- Operateur
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salarie_livret PRIMARY KEY (id_salarie_livret)
);
CREATE INDEX ix_pgt_salarie_livret_id_salarie ON rh.pgt_salarie_livret (id_salarie);
CREATE INDEX ix_pgt_salarie_livret_id_type_operation_livret ON rh.pgt_salarie_livret (id_type_operation_livret);
CREATE INDEX ix_pgt_salarie_livret_id_challenge ON rh.pgt_salarie_livret (id_challenge);
CREATE INDEX ix_pgt_salarie_livret_id_tk_liste ON rh.pgt_salarie_livret (id_tk_liste);
CREATE INDEX ix_pgt_salarie_livret_modif_date ON rh.pgt_salarie_livret (modif_date);

CREATE TABLE rh.pgt_salarie_mutuelle (
    id_salarie_mutuelle            bigint,  -- IDsalarie_mutuelle
    id_salarie                     bigint NOT NULL,  -- IDSalarie
    adhesion                       boolean,  -- Adhésion
    adhesion_date                  date,  -- AdhésionDate
    mutuelle_dossier               boolean,  -- Mutuelle_Dossier
    id_mutuelle                    smallint,  -- IdMutuelle
    mutuelle_att_ss                boolean,  -- Mutuelle_AttSS
    mutuelle_rib                   boolean,  -- Mutuelle_RIB
    mutuelle_doc_envoyes           boolean,  -- Mutuelle_DocEnvoyés
    mutuelle_recep_certif          boolean,  -- Mutuelle_RecepCertif
    mutuelle_pas_adhesion          boolean,  -- Mutuelle_PasAdhésion
    mutuelle_pas_adhesion_jusquau  date,  -- Mutuelle_PasAdhésionJusquau
    mutuelle_resilie               boolean,  -- Mutuelle_Résilié
    mutuelle_resilie_date          date,  -- Mutuelle_RésiliéDate
    modif_date                     timestamp,  -- ModifDate
    modif_op                       bigint,  -- ModifOp
    modif_elem                     varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salarie_mutuelle PRIMARY KEY (id_salarie),
    CONSTRAINT uq_pgt_salarie_mutuelle_auto UNIQUE (id_salarie_mutuelle)
);
CREATE INDEX ix_pgt_salarie_mutuelle_modif_date ON rh.pgt_salarie_mutuelle (modif_date);

CREATE TABLE rh.pgt_salarie_organigramme (
    id_salarie                           bigint,  -- IDSalarie
    idorganigramme                       bigint,  -- idorganigramme
    id_salarie_organigramme              bigint NOT NULL,  -- IDsalarie_organigramme
    date_debut                           date,  -- DateDébut
    date_fin                             date,  -- DateFin
    aff_actif                            boolean,  -- aff_ACTIF
    modif_date                           timestamp,  -- ModifDate
    modif_op                             bigint,  -- ModifOP
    id_ste                               bigint,  -- IdSte
    modif_elem                           varchar(5),  -- ModifELEM
    id_salarieidorganigramme_date_debut  varchar(24),  -- IDSalarieidorganigrammeDateDébut
    CONSTRAINT pk_pgt_salarie_organigramme PRIMARY KEY (id_salarie_organigramme)
);
CREATE INDEX ix_pgt_salarie_organigramme_id_salarie ON rh.pgt_salarie_organigramme (id_salarie);
CREATE INDEX ix_pgt_salarie_organigramme_idorganigramme ON rh.pgt_salarie_organigramme (idorganigramme);
CREATE INDEX ix_pgt_salarie_organigramme_date_debut ON rh.pgt_salarie_organigramme (date_debut);
CREATE INDEX ix_pgt_salarie_organigramme_date_fin ON rh.pgt_salarie_organigramme (date_fin);
CREATE INDEX ix_pgt_salarie_organigramme_aff_actif ON rh.pgt_salarie_organigramme (aff_actif);
CREATE INDEX ix_pgt_salarie_organigramme_modif_date ON rh.pgt_salarie_organigramme (modif_date);
CREATE INDEX ix_pgt_salarie_organigramme_id_ste ON rh.pgt_salarie_organigramme (id_ste);

CREATE TABLE rh.pgt_salarie_part_dpae (
    id_salarie_partenaire     bigint NOT NULL,  -- IDsalarie_partenaire
    id_salarie                bigint,  -- IDSalarie
    id_partenaire             bigint,  -- IDPartenaire
    id_ste                    bigint,  -- IdSte
    modif_date                timestamp,  -- ModifDate
    modif_elem                varchar(5),  -- ModifElem
    modif_op                  bigint,  -- ModifOp
    id_salarie_id_partenaire  varchar(16),  -- IDSalarieIDPartenaire
    CONSTRAINT pk_pgt_salarie_part_dpae PRIMARY KEY (id_salarie_partenaire)
);
CREATE INDEX ix_pgt_salarie_part_dpae_id_salarie ON rh.pgt_salarie_part_dpae (id_salarie);
CREATE INDEX ix_pgt_salarie_part_dpae_id_partenaire ON rh.pgt_salarie_part_dpae (id_partenaire);
CREATE INDEX ix_pgt_salarie_part_dpae_id_ste ON rh.pgt_salarie_part_dpae (id_ste);
CREATE INDEX ix_pgt_salarie_part_dpae_modif_date ON rh.pgt_salarie_part_dpae (modif_date);

CREATE TABLE rh.pgt_salarie_partenaire (
    id_salarie_partenaire     bigint NOT NULL,  -- IDsalarie_partenaire
    id_salarie                bigint,  -- IDSalarie
    id_partenaire             bigint,  -- IDPartenaire
    id_salarie_id_partenaire  varchar(16),  -- IDSalarieIDPartenaire
    code                      text,  -- Code
    login                     text,  -- LOGIN
    mdp                       text,  -- MDP
    modif_date                timestamp,  -- ModifDate
    modif_elem                varchar(5),  -- ModifElem
    modif_op                  bigint,  -- ModifOp
    CONSTRAINT pk_pgt_salarie_partenaire PRIMARY KEY (id_salarie_partenaire)
);
CREATE INDEX ix_pgt_salarie_partenaire_id_salarie ON rh.pgt_salarie_partenaire (id_salarie);
CREATE INDEX ix_pgt_salarie_partenaire_id_partenaire ON rh.pgt_salarie_partenaire (id_partenaire);
CREATE INDEX ix_pgt_salarie_partenaire_code ON rh.pgt_salarie_partenaire (code);
CREATE INDEX ix_pgt_salarie_partenaire_login ON rh.pgt_salarie_partenaire (login);
CREATE INDEX ix_pgt_salarie_partenaire_modif_date ON rh.pgt_salarie_partenaire (modif_date);

CREATE TABLE rh.pgt_salarie_prime (
    id_salarie_prime  bigint NOT NULL,  -- IDsalarie_prime
    id_salarie        bigint,  -- IDSalarie
    mois_salaire      date,  -- MoisSalaire
    id_type_prime     integer,  -- IDTypePrime
    montant           numeric(19,4),  -- Montant
    detai_prime       text,  -- DétaiPrime
    date_crea         timestamp,  -- DateCrea
    op_crea           bigint,  -- OpCrea
    modif_date        timestamp,  -- ModifDate
    modif_op          bigint,  -- ModifOP
    modif_elem        varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_salarie_prime PRIMARY KEY (id_salarie_prime)
);
CREATE INDEX ix_pgt_salarie_prime_id_salarie ON rh.pgt_salarie_prime (id_salarie);
CREATE INDEX ix_pgt_salarie_prime_id_type_prime ON rh.pgt_salarie_prime (id_type_prime);
CREATE INDEX ix_pgt_salarie_prime_modif_date ON rh.pgt_salarie_prime (modif_date);

CREATE TABLE rh.pgt_salarie_progevo (
    id_salarie_prog_evo  bigint NOT NULL,  -- IDsalarie_progEvo
    id_salarie           bigint,  -- IDSalarie
    date                 date,  -- Date
    id_da                bigint,  -- IDDa
    id_agence            bigint,  -- IDAgence
    niveau               smallint,  -- Niveau
    avis                 text,  -- Avis
    axe_travail1         text,  -- AxeTravail1
    axe_travail2         text,  -- AxeTravail2
    cloture              boolean,  -- Cloturé
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOP
    modif_elem           varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_salarie_progevo PRIMARY KEY (id_salarie_prog_evo)
);
CREATE INDEX ix_pgt_salarie_progevo_id_salarie ON rh.pgt_salarie_progevo (id_salarie);
CREATE INDEX ix_pgt_salarie_progevo_modif_date ON rh.pgt_salarie_progevo (modif_date);

CREATE TABLE rh.pgt_salarie_progevo_objectif (
    id_salarie_prog_evo_item  bigint NOT NULL,  -- IDsalarie_progEvo_Item
    id_salarie_prog_evo       bigint,  -- IDsalarie_progEvo
    id_prog_evo_objectifs     bigint,  -- IDProgEvo_Objectifs
    champ_libre               varchar(50),  -- ChampLibre
    note                      smallint,  -- Note
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOP
    modif_elem                varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_salarie_progevo_objectif PRIMARY KEY (id_salarie_prog_evo_item)
);
CREATE INDEX ix_pgt_salarie_progevo_objectif_id_salarie_prog_evo ON rh.pgt_salarie_progevo_objectif (id_salarie_prog_evo);
CREATE INDEX ix_pgt_salarie_progevo_objectif_modif_date ON rh.pgt_salarie_progevo_objectif (modif_date);

CREATE TABLE rh.pgt_salarie_sortie (
    id_salarie_sortie     bigint,  -- IDsalarie_sortie
    id_salarie            bigint NOT NULL,  -- IDSalarie
    id_type_sortie        integer,  -- IDTypeSortie
    date_sortie_demandee  timestamp,  -- DateSortieDemandée
    demandeur_sortie      bigint,  -- DemandeurSortie
    date_sortie_reelle    date,  -- DateSortieRéelle
    info_cpl              text,  -- InfoCpl
    courrier_date_envoi   date,  -- CourrierDateEnvoi
    courrier_num_suivi    varchar(15),  -- CourrierNumSuivi
    courrier_date_recep   date,  -- CourrierDateRecep
    courrier_delai_prev   varchar(10),  -- CourrierDelaiPrev
    stc_date_envoi        date,  -- STCDateEnvoi
    stc_num_suivi         varchar(15),  -- STCNumSuivi
    stc_date_recep        date,  -- STCDateRecep
    stc_retourne_le       date,  -- STCRetourné_le
    mail_objet            text,  -- MailObjet
    mail_contenu          text,  -- MailContenu
    modif_op              bigint,  -- ModifOp
    modif_date            timestamp,  -- ModifDate
    modif_elem            varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salarie_sortie PRIMARY KEY (id_salarie),
    CONSTRAINT uq_pgt_salarie_sortie_auto UNIQUE (id_salarie_sortie)
);
CREATE INDEX ix_pgt_salarie_sortie_id_type_sortie ON rh.pgt_salarie_sortie (id_type_sortie);
CREATE INDEX ix_pgt_salarie_sortie_modif_date ON rh.pgt_salarie_sortie (modif_date);

CREATE TABLE rh.pgt_salarie_suivi (
    id_suivi_auto   bigint,  -- IDsuiviAuto
    id_suivi        bigint NOT NULL,  -- IDsuivi
    id_salarie      bigint,  -- IDSalarie
    type            integer,  -- TYPE
    idorganigramme  bigint,  -- idorganigramme
    id_type_poste   smallint,  -- IdTypePoste
    date_debut      date,  -- DateDEBUT
    date_fin        date,  -- DateFIN
    modif_date      timestamp,  -- ModifDate
    modif_op        bigint,  -- ModifOp
    modif_elem      varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salarie_suivi PRIMARY KEY (id_suivi),
    CONSTRAINT uq_pgt_salarie_suivi_auto UNIQUE (id_suivi_auto)
);
CREATE INDEX ix_pgt_salarie_suivi_id_salarie ON rh.pgt_salarie_suivi (id_salarie);
CREATE INDEX ix_pgt_salarie_suivi_idorganigramme ON rh.pgt_salarie_suivi (idorganigramme);
CREATE INDEX ix_pgt_salarie_suivi_id_type_poste ON rh.pgt_salarie_suivi (id_type_poste);
CREATE INDEX ix_pgt_salarie_suivi_date_debut ON rh.pgt_salarie_suivi (date_debut);
CREATE INDEX ix_pgt_salarie_suivi_date_fin ON rh.pgt_salarie_suivi (date_fin);
CREATE INDEX ix_pgt_salarie_suivi_modif_date ON rh.pgt_salarie_suivi (modif_date);

CREATE TABLE rh.pgt_salarie_suivi_adm (
    id_salarie_suivi_adm_auto  bigint,  -- IDsalarie_suiviADMAuto
    id_salarie_suivi_adm       bigint NOT NULL,  -- IDsalarie_suiviADM
    id_salarie                 bigint,  -- IDSalarie
    op_crea                    bigint,  -- OPCREA
    description                text,  -- DESCRIPTION
    date_crea                  timestamp,  -- DATECREA
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOP
    modif_elem                 varchar(5),  -- ModifELEM
    id_salarie_datecrea        varchar(16),  -- IDSalarieDATECREA
    CONSTRAINT pk_pgt_salarie_suivi_adm PRIMARY KEY (id_salarie_suivi_adm),
    CONSTRAINT uq_pgt_salarie_suivi_adm_auto UNIQUE (id_salarie_suivi_adm_auto)
);
CREATE INDEX ix_pgt_salarie_suivi_adm_id_salarie ON rh.pgt_salarie_suivi_adm (id_salarie);
CREATE INDEX ix_pgt_salarie_suivi_adm_modif_date ON rh.pgt_salarie_suivi_adm (modif_date);

CREATE TABLE rh.pgt_societe (
    id_societe_auto      bigint,  -- IDSociétéAuto
    id_ste               bigint NOT NULL,  -- IdSte
    idorganigramme       bigint,  -- idorganigramme
    id_type_orga         integer,  -- IDTypeOrga
    raison_sociale       text,  -- RaisonSociale
    rs_interne           text,  -- RS_Interne
    forme_juri           text,  -- FORMEJURI
    siret                text,  -- SIRET
    siren                text,  -- SIREN
    rcs                  text,  -- RCS
    date_creation        date,  -- DateCreation
    num_tva              text,  -- NumTVA
    code_ape             varchar(5),  -- code_APE
    capital              numeric(19,4),  -- CAPITAL
    iban                 text,  -- IBAN
    bic                  text,  -- BIC
    adresse1             text,  -- ADRESSE1
    adresse2             text,  -- ADRESSE2
    cp                   varchar(5),  -- CP
    ville                text,  -- VILLE
    tel                  text,  -- TEL
    mail                 text,  -- MAIL
    url                  text,  -- URL
    logo                 bytea,  -- LOGO
    guimmick             bytea,  -- GUIMMICK
    cachet_cial          bytea,  -- CachetCial
    gerant_paraphe       bytea,  -- GerantParaphe
    gerant_signature     bytea,  -- GerantSignature
    gerant_nom           varchar(50),  -- GerantNom
    gerant_type          varchar(20),  -- GerantType
    id_gerant            bigint,  -- IdGérant
    secteur              text,  -- Secteur
    num_orias            varchar(10),  -- NumOrias
    is_actif             boolean,  -- IsActif
    modif_op             bigint,  -- ModifOP
    modif_date           timestamp,  -- ModifDate
    modif_elem           varchar(5),  -- ModifELEM
    id_ste_id_type_orga  varchar(12),  -- IdSteIDTypeOrga
    CONSTRAINT pk_pgt_societe PRIMARY KEY (id_ste),
    CONSTRAINT uq_pgt_societe_auto UNIQUE (id_societe_auto)
);
CREATE INDEX ix_pgt_societe_idorganigramme ON rh.pgt_societe (idorganigramme);
CREATE INDEX ix_pgt_societe_id_type_orga ON rh.pgt_societe (id_type_orga);
CREATE INDEX ix_pgt_societe_siret ON rh.pgt_societe (siret);
CREATE INDEX ix_pgt_societe_id_gerant ON rh.pgt_societe (id_gerant);
CREATE INDEX ix_pgt_societe_modif_date ON rh.pgt_societe (modif_date);

CREATE TABLE rh.pgt_societe_doc_courtage (
    id_societe_doc_courtage  bigint NOT NULL,  -- IDsociete_docCourtage
    id_salarie               bigint,  -- IDSalarie
    id_distrib               bigint,  -- idDistrib
    id_doc_courtage          bigint,  -- IDdocCourtage
    id_groupe_operateur      bigint,  -- IDGroupeOpérateur
    date_edition             timestamp,  -- DATE_Edition
    recu                     boolean,  -- RECU
    recu_date                timestamp,  -- RECUDATE
    secteur                  text,  -- Secteur
    nom_ctt_signe            text,  -- NomCttSigné
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOP
    modif_elem               varchar(5),  -- ModifELEM
    id_salarie_date_edition  varchar(16),  -- IDSalarieDATE_Edition
    CONSTRAINT pk_pgt_societe_doc_courtage PRIMARY KEY (id_societe_doc_courtage)
);
CREATE INDEX ix_pgt_societe_doc_courtage_id_salarie ON rh.pgt_societe_doc_courtage (id_salarie);
CREATE INDEX ix_pgt_societe_doc_courtage_id_distrib ON rh.pgt_societe_doc_courtage (id_distrib);
CREATE INDEX ix_pgt_societe_doc_courtage_id_doc_courtage ON rh.pgt_societe_doc_courtage (id_doc_courtage);
CREATE INDEX ix_pgt_societe_doc_courtage_modif_date ON rh.pgt_societe_doc_courtage (modif_date);

CREATE TABLE rh.pgt_societe_formjuri (
    id_societe_form_juri_auto  bigint NOT NULL,  -- IDsociete_FormJuriAuto
    id_societe_form_juri       integer,  -- IDsociete_FormJuri
    lib_form_juri              varchar(50),  -- LibFormJuri
    modif_date                 timestamp,  -- ModifDate
    modif_elem                 varchar(5),  -- ModifELEM
    modif_op                   bigint,  -- ModifOP
    CONSTRAINT pk_pgt_societe_formjuri PRIMARY KEY (id_societe_form_juri_auto)
);
CREATE INDEX ix_pgt_societe_formjuri_modif_date ON rh.pgt_societe_formjuri (modif_date);

CREATE TABLE rh.pgt_type_absence (
    id_type_absence_auto  bigint,  -- IDTypeAbsenceAuto
    id_type_absence       integer NOT NULL,  -- IDTypeAbsence
    lib_absence           text,  -- Lib_Absence
    modif_date            timestamp,  -- ModifDate
    modif_op              bigint,  -- ModifOp
    modif_elem            varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_absence PRIMARY KEY (id_type_absence),
    CONSTRAINT uq_pgt_type_absence_auto UNIQUE (id_type_absence_auto)
);
CREATE INDEX ix_pgt_type_absence_modif_date ON rh.pgt_type_absence (modif_date);

CREATE TABLE rh.pgt_type_adf_item (
    id_type_adf_item  bigint NOT NULL,  -- IDTypeADF_Item
    lib_item          varchar(50),  -- LibItem
    ordre_affichage   smallint,  -- OrdreAffichage
    is_actif          boolean,  -- IsActif
    modif_date        timestamp,  -- ModifDate
    modif_op          bigint,  -- ModifOp
    modif_elem        varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_adf_item PRIMARY KEY (id_type_adf_item)
);
CREATE INDEX ix_pgt_type_adf_item_modif_date ON rh.pgt_type_adf_item (modif_date);

CREATE TABLE rh.pgt_type_ctt_travail (
    id_type_ctt_travail  bigint,  -- IDTypeCttTravail
    id_type_ctt          integer NOT NULL,  -- IDTypeCtt
    intitule             text,  -- Intitulé
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_ctt_travail PRIMARY KEY (id_type_ctt),
    CONSTRAINT uq_pgt_type_ctt_travail_auto UNIQUE (id_type_ctt_travail)
);
CREATE INDEX ix_pgt_type_ctt_travail_modif_date ON rh.pgt_type_ctt_travail (modif_date);

CREATE TABLE rh.pgt_type_doc_distributeur (
    id_type_doc_distributeur  bigint NOT NULL,  -- IDTypeDocDistributeur
    lib_doc                   varchar(50),  -- LibDoc
    obligatoire_dem           boolean,  -- ObligatoireDem
    afaire_signer             boolean,  -- AfaireSigner
    rappel_annuel             smallint,  -- RappelAnnuel
    id_doc_courtage           bigint,  -- IDdocCourtage
    CONSTRAINT pk_pgt_type_doc_distributeur PRIMARY KEY (id_type_doc_distributeur)
);
CREATE INDEX ix_pgt_type_doc_distributeur_id_doc_courtage ON rh.pgt_type_doc_distributeur (id_doc_courtage);

CREATE TABLE rh.pgt_type_droit_acces (
    id_type_droit_acces_auto  bigint,  -- IDTypeDroitAccèsAuto
    id_type_droit_acces       integer NOT NULL,  -- IDTypeDroitAccès
    lib_droit                 varchar(50),  -- Lib_Droit
    code_interne              varchar(15),  -- CodeInterne
    adm                       boolean,  -- ADM
    fdv                       boolean,  -- FDV
    description               text,  -- Description
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    categorie                 varchar(15),  -- Catégorie
    CONSTRAINT pk_pgt_type_droit_acces PRIMARY KEY (id_type_droit_acces),
    CONSTRAINT uq_pgt_type_droit_acces_auto UNIQUE (id_type_droit_acces_auto)
);
CREATE INDEX ix_pgt_type_droit_acces_modif_date ON rh.pgt_type_droit_acces (modif_date);
CREATE INDEX ix_pgt_type_droit_acces_categorie ON rh.pgt_type_droit_acces (categorie);

CREATE TABLE rh.pgt_type_horaire_travail (
    id_type_horaire_travail  bigint,  -- IDTypeHoraireTravail
    id_type_horaire          integer NOT NULL,  -- IDTypeHoraire
    lib_horaire              varchar(50),  -- Lib_Horaire
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_horaire_travail PRIMARY KEY (id_type_horaire),
    CONSTRAINT uq_pgt_type_horaire_travail_auto UNIQUE (id_type_horaire_travail)
);
CREATE INDEX ix_pgt_type_horaire_travail_modif_date ON rh.pgt_type_horaire_travail (modif_date);

CREATE TABLE rh.pgt_type_niveau_orga (
    id_type_niveau_orga_auto  bigint,  -- IDTypeNiveauOrgaAuto
    id_type_niveau_orga       integer NOT NULL,  -- IDTypeNiveauOrga
    lib_niveau                varchar(20),  -- Lib_Niveau
    type                      varchar(5),  -- Type
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_niveau_orga PRIMARY KEY (id_type_niveau_orga),
    CONSTRAINT uq_pgt_type_niveau_orga_auto UNIQUE (id_type_niveau_orga_auto)
);
CREATE INDEX ix_pgt_type_niveau_orga_type ON rh.pgt_type_niveau_orga (type);
CREATE INDEX ix_pgt_type_niveau_orga_modif_date ON rh.pgt_type_niveau_orga (modif_date);

CREATE TABLE rh.pgt_type_operation_livret (
    id_type_operation_livret_auto  bigint,  -- IdTypeOperationLivretAuto
    id_type_operation_livret       integer NOT NULL,  -- IDTypeOperationLivret
    lib_opeation                   varchar(50),  -- LibOpéation
    modif_date                     timestamp,  -- ModifDate
    modif_op                       bigint,  -- ModifOp
    modif_elem                     varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_operation_livret PRIMARY KEY (id_type_operation_livret),
    CONSTRAINT uq_pgt_type_operation_livret_auto UNIQUE (id_type_operation_livret_auto)
);
CREATE INDEX ix_pgt_type_operation_livret_modif_date ON rh.pgt_type_operation_livret (modif_date);

CREATE TABLE rh.pgt_type_orga (
    id_type_orga_auto  bigint,  -- IDTypeOrgaAuto
    id_type_orga       integer NOT NULL,  -- IDTypeOrga
    lib                varchar(50),  -- Lib
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOp
    modif_elem         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_orga PRIMARY KEY (id_type_orga),
    CONSTRAINT uq_pgt_type_orga_auto UNIQUE (id_type_orga_auto)
);
CREATE INDEX ix_pgt_type_orga_modif_date ON rh.pgt_type_orga (modif_date);

CREATE TABLE rh.pgt_type_poste (
    id_type_poste_auto  bigint,  -- IDTypePosteAuto
    id_type_poste       smallint NOT NULL,  -- IdTypePoste
    lib_poste           text,  -- Lib_Poste
    categorie           varchar(15),  -- Catégorie
    modif_op            bigint,  -- ModifOP
    modif_date          timestamp,  -- ModifDate
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_type_poste PRIMARY KEY (id_type_poste),
    CONSTRAINT uq_pgt_type_poste_auto UNIQUE (id_type_poste_auto)
);
CREATE INDEX ix_pgt_type_poste_lib_poste ON rh.pgt_type_poste (lib_poste);
CREATE INDEX ix_pgt_type_poste_categorie ON rh.pgt_type_poste (categorie);
CREATE INDEX ix_pgt_type_poste_modif_date ON rh.pgt_type_poste (modif_date);

CREATE TABLE rh.pgt_typeprime (
    id_type_prime_auto  bigint,  -- IDTypePrimeAuto
    id_type_prime       integer NOT NULL,  -- IDTypePrime
    lib_prime           varchar(50),  -- LibPrime
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_typeprime PRIMARY KEY (id_type_prime),
    CONSTRAINT uq_pgt_typeprime_auto UNIQUE (id_type_prime_auto)
);
CREATE INDEX ix_pgt_typeprime_modif_date ON rh.pgt_typeprime (modif_date);

CREATE TABLE rh.pgt_type_produit (
    id_type_produit_auto  bigint,  -- IDTypeProduitAuto
    id_type_produit       bigint NOT NULL,  -- IDTypeProduit
    lib                   varchar(50),  -- Lib
    logo                  bytea,  -- LOGO
    type                  varchar(5),  -- Type
    modif_date            timestamp,  -- ModifDate
    modif_op              bigint,  -- ModifOp
    modif_elem            varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_produit PRIMARY KEY (id_type_produit),
    CONSTRAINT uq_pgt_type_produit_auto UNIQUE (id_type_produit_auto)
);
CREATE INDEX ix_pgt_type_produit_type ON rh.pgt_type_produit (type);
CREATE INDEX ix_pgt_type_produit_modif_date ON rh.pgt_type_produit (modif_date);

CREATE TABLE rh.pgt_type_produit_partenaire (
    id_type_produit_partenaire  bigint NOT NULL,  -- IDTypeProduit_Partenaire
    id_type_produit             bigint,  -- IDTypeProduit
    id_partenaire               bigint,  -- IDPartenaire
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOp
    modif_elem                  varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_produit_partenaire PRIMARY KEY (id_type_produit_partenaire)
);
CREATE INDEX ix_pgt_type_produit_partenaire_id_type_produit ON rh.pgt_type_produit_partenaire (id_type_produit);
CREATE INDEX ix_pgt_type_produit_partenaire_id_partenaire ON rh.pgt_type_produit_partenaire (id_partenaire);
CREATE INDEX ix_pgt_type_produit_partenaire_modif_date ON rh.pgt_type_produit_partenaire (modif_date);

CREATE TABLE rh.pgt_type_sortie_salarie (
    id_type_sortie_salarie  bigint,  -- IDTypeSortieSalarie
    id_type_sortie          integer NOT NULL,  -- IDTypeSortie
    lib_sortie              varchar(30),  -- Lib_Sortie
    modif_date              timestamp,  -- ModifDate
    modif_op                bigint,  -- ModifOp
    modif_elem              varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_sortie_salarie PRIMARY KEY (id_type_sortie),
    CONSTRAINT uq_pgt_type_sortie_salarie_auto UNIQUE (id_type_sortie_salarie)
);
CREATE INDEX ix_pgt_type_sortie_salarie_modif_date ON rh.pgt_type_sortie_salarie (modif_date);
