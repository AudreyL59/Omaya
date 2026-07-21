CREATE SCHEMA IF NOT EXISTS ulease;


CREATE TABLE ulease.pgt_carteattribution (
    id_carte_attribution_auto  bigint NOT NULL,  -- IDCarteAttributionAuto
    id_carte_attribution       bigint,  -- IDCarteAttribution
    id_carte_carburant         bigint,  -- IDCarteCarburant
    id_conducteur              bigint,  -- IDConducteur
    du                         date,  -- Du
    au                         date,  -- Au
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOp
    modif_elem                 varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_carteattribution PRIMARY KEY (id_carte_attribution_auto)
);
CREATE INDEX ix_pgt_carteattribution_id_carte_carburant ON ulease.pgt_carteattribution (id_carte_carburant);
CREATE INDEX ix_pgt_carteattribution_id_conducteur ON ulease.pgt_carteattribution (id_conducteur);
CREATE INDEX ix_pgt_carteattribution_modif_date ON ulease.pgt_carteattribution (modif_date);

CREATE TABLE ulease.pgt_cartecalculatt (
    id_carte_calcul_att_auto  bigint NOT NULL,  -- IDCarteCalculAttAuto
    id_carte_calcul_att       bigint,  -- IDCarteCalculAtt
    id_carte_attribution      bigint,  -- IDCarteAttribution
    id_conducteur             bigint,  -- IDConducteur
    id_carte_carburant        bigint,  -- IDCarteCarburant
    id_type_poste             bigint,  -- IDTypePoste
    calcul_prod               boolean,  -- CalculProd
    id_organigramme           bigint,  -- IdOrganigramme
    nb_place                  smallint,  -- nbPlace
    nb_prod_tot               smallint,  -- nbProdTot
    nb_jours_prod             smallint,  -- nbJoursProd
    moy_prod                  numeric,  -- MoyProd
    montant_detecte           numeric(19,4),  -- MontantDétecté
    montant_attribue          numeric(19,4),  -- MontantAttribué
    montant_carb              numeric(19,4),  -- MontantCarb
    montant_peage             numeric(19,4),  -- MontantPéage
    montant_total             numeric(19,4),  -- MontantTotal
    difference                numeric(19,4),  -- Différence
    montant_valide            numeric(19,4),  -- MontantValidé
    mois                      smallint,  -- Mois
    annee                     smallint,  -- Année
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_cartecalculatt PRIMARY KEY (id_carte_calcul_att_auto)
);
CREATE INDEX ix_pgt_cartecalculatt_id_carte_attribution ON ulease.pgt_cartecalculatt (id_carte_attribution);
CREATE INDEX ix_pgt_cartecalculatt_id_conducteur ON ulease.pgt_cartecalculatt (id_conducteur);
CREATE INDEX ix_pgt_cartecalculatt_id_carte_carburant ON ulease.pgt_cartecalculatt (id_carte_carburant);
CREATE INDEX ix_pgt_cartecalculatt_modif_date ON ulease.pgt_cartecalculatt (modif_date);

CREATE TABLE ulease.pgt_cartecarbrelevefournisseur (
    id_carte_carb_releve_fournisseur_auto  bigint NOT NULL,  -- IDCarteCarbReleveFournisseurAuto
    id_carte_carb_releve_fournisseur       bigint,  -- IDCarteCarbReleveFournisseur
    id_facturation                         varchar(50),  -- IdFacturation
    id_carte_fournisseur                   bigint,  -- IDCarteFournisseur
    id_carte_carburant                     bigint,  -- IDCarteCarburant
    id_type_releve_fournisseur             bigint,  -- IDTypeReleveFournisseur
    date                                   date,  -- Date
    heure                                  time,  -- Heure
    lieu                                   text,  -- Lieu
    montant_ht                             numeric(19,4),  -- MontantHT
    montant_ttc                            numeric(19,4),  -- MontantTTC
    modif_date                             timestamp,  -- ModifDate
    modif_op                               bigint,  -- ModifOp
    modif_elem                             varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_cartecarbrelevefournisseur PRIMARY KEY (id_carte_carb_releve_fournisseur_auto)
);
CREATE INDEX ix_pgt_cartecarbrelevefournisseur_id_facturation ON ulease.pgt_cartecarbrelevefournisseur (id_facturation);
CREATE INDEX ix_pgt_cartecarbrelevefournisseur_id_carte_fournisseur ON ulease.pgt_cartecarbrelevefournisseur (id_carte_fournisseur);
CREATE INDEX ix_pgt_cartecarbrelevefournisseur_id_carte_carburant ON ulease.pgt_cartecarbrelevefournisseur (id_carte_carburant);
CREATE INDEX ix_pgt_cartecarbrelevefournisseur_id_type_releve_fournisseur ON ulease.pgt_cartecarbrelevefournisseur (id_type_releve_fournisseur);
CREATE INDEX ix_pgt_cartecarbrelevefournisseur_modif_date ON ulease.pgt_cartecarbrelevefournisseur (modif_date);

CREATE TABLE ulease.pgt_cartecarburant (
    id_carte_carburant       bigint,  -- IDCarteCarburant
    num_carte                varchar(50),  -- NumCarte
    id_carte_fournisseur     bigint,  -- IDCarteFournisseur
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    is_actif                 boolean,  -- IsActif
    code_carte               varchar(5),  -- CodeCarte
    id_carte_carburant_auto  bigint NOT NULL,  -- IDCarteCarburantAuto
    CONSTRAINT pk_pgt_cartecarburant PRIMARY KEY (id_carte_carburant_auto)
);
CREATE INDEX ix_pgt_cartecarburant_id_carte_fournisseur ON ulease.pgt_cartecarburant (id_carte_fournisseur);
CREATE INDEX ix_pgt_cartecarburant_modif_date ON ulease.pgt_cartecarburant (modif_date);

CREATE TABLE ulease.pgt_cartefournisseur (
    id_carte_fournisseur       bigint,  -- IDCarteFournisseur
    nom_fournisseur            varchar(50),  -- NomFournisseur
    modif_date                 timestamp,  -- ModifDate
    modif_elem                 varchar(5),  -- ModifElem
    modif_op                   bigint,  -- ModifOp
    logo                       bytea,  -- Logo
    id_carte_fournisseur_auto  bigint NOT NULL,  -- IDCarteFournisseurAuto
    CONSTRAINT pk_pgt_cartefournisseur PRIMARY KEY (id_carte_fournisseur_auto)
);
CREATE INDEX ix_pgt_cartefournisseur_modif_date ON ulease.pgt_cartefournisseur (modif_date);

CREATE TABLE ulease.pgt_conducteur (
    id_conducteur       bigint NOT NULL,  -- IDconducteur
    nom_conducteur      varchar(30),  -- NomConducteur
    prenom_conducteur   varchar(20),  -- PrenomConducteur
    date_naiss          date,  -- DateNaiss
    num_permis          varchar(25),  -- numPermis
    type_permis         varchar(3),  -- TypePermis
    id_ste              bigint,  -- idSte
    tel                 varchar(15),  -- TEL
    mobile              varchar(15),  -- Mobile
    adresse1            text,  -- ADRESSE1
    adresse2            text,  -- ADRESSE2
    cp                  varchar(5),  -- CP
    ville               text,  -- VILLE
    pays                varchar(25),  -- PAYS
    nom_marital         varchar(30),  -- NomMarital
    sexe_conducteur     smallint,  -- SexeConducteur
    photo_conducteur    bytea,  -- photoConducteur
    lieu_naiss          varchar(25),  -- LieuNaiss
    date_obtention      date,  -- DateObtention
    login               varchar(50),  -- Login
    mdp_user            varchar(50),  -- MdpUser
    dep_naiss           smallint,  -- DepNaiss
    id_salarie          bigint,  -- IDSalarie
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOp
    modif_elem          varchar(5),  -- ModifElem
    id_conducteur_auto  bigint,  -- IDconducteurAuto
    CONSTRAINT pk_pgt_conducteur PRIMARY KEY (id_conducteur),
    CONSTRAINT uq_pgt_conducteur_auto UNIQUE (id_conducteur_auto)
);
CREATE INDEX ix_pgt_conducteur_modif_date ON ulease.pgt_conducteur (modif_date);

CREATE TABLE ulease.pgt_doc_ulease (
    id_doc_ulease  bigint NOT NULL,  -- IDdocUlease
    id_type_doc    bigint,  -- IDTypeDoc
    titre          varchar(255),  -- Titre
    info_cpl       varchar(50),  -- InfoCpl
    contenu        bytea,  -- Contenu
    datecrea       timestamp,  -- Datecrea
    doc_actif      boolean,  -- DocActif
    prioritaire    boolean,  -- Prioritaire
    id_ste         bigint,  -- IdSte
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOp
    modif_elem     varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_doc_ulease PRIMARY KEY (id_doc_ulease)
);
CREATE INDEX ix_pgt_doc_ulease_id_type_doc ON ulease.pgt_doc_ulease (id_type_doc);
CREATE INDEX ix_pgt_doc_ulease_id_ste ON ulease.pgt_doc_ulease (id_ste);
CREATE INDEX ix_pgt_doc_ulease_modif_date ON ulease.pgt_doc_ulease (modif_date);

CREATE TABLE ulease.pgt_doc_ulease_type (
    id_type_doc_auto  bigint,  -- IDTypeDocAuto
    id_type_doc       bigint NOT NULL,  -- IDTypeDoc
    lib_type          text,  -- Lib_Type
    modif_op          bigint,  -- ModifOP
    modif_date        timestamp,  -- ModifDate
    modif_elem        varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_doc_ulease_type PRIMARY KEY (id_type_doc),
    CONSTRAINT uq_pgt_doc_ulease_type_auto UNIQUE (id_type_doc_auto)
);
CREATE INDEX ix_pgt_doc_ulease_type_lib_type ON ulease.pgt_doc_ulease_type (lib_type);
CREATE INDEX ix_pgt_doc_ulease_type_modif_date ON ulease.pgt_doc_ulease_type (modif_date);

CREATE TABLE ulease.pgt_typecapacite_photo (
    id_type_capacite_photo_auto  bigint NOT NULL,  -- IDTypeCapacite_PhotoAuto
    id_type_capacite_photo       bigint,  -- IDTypeCapacite_Photo
    id_vehicule_type_capacite    bigint,  -- IDVehicule_TypeCapacité
    lib_photo                    text,  -- LibPhoto
    photo                        bytea,  -- Photo
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOp
    modif_elem                   varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_typecapacite_photo PRIMARY KEY (id_type_capacite_photo_auto)
);
CREATE INDEX ix_pgt_typecapacite_photo_id_vehicule_type_capacite ON ulease.pgt_typecapacite_photo (id_vehicule_type_capacite);
CREATE INDEX ix_pgt_typecapacite_photo_lib_photo ON ulease.pgt_typecapacite_photo (lib_photo);
CREATE INDEX ix_pgt_typecapacite_photo_modif_date ON ulease.pgt_typecapacite_photo (modif_date);

CREATE TABLE ulease.pgt_typerelevefournisseur (
    id_type_releve_fournisseur       bigint,  -- IDTypeReleveFournisseur
    lib_type                         text,  -- Lib_Type
    categorie                        varchar(50),  -- Catégorie
    modif_date                       timestamp,  -- ModifDate
    modif_op                         bigint,  -- ModifOp
    modif_elem                       varchar(5),  -- ModifElem
    id_type_releve_fournisseur_auto  bigint NOT NULL,  -- IDTypeReleveFournisseurAuto
    CONSTRAINT pk_pgt_typerelevefournisseur PRIMARY KEY (id_type_releve_fournisseur_auto)
);
CREATE INDEX ix_pgt_typerelevefournisseur_lib_type ON ulease.pgt_typerelevefournisseur (lib_type);
CREATE INDEX ix_pgt_typerelevefournisseur_modif_date ON ulease.pgt_typerelevefournisseur (modif_date);

CREATE TABLE ulease.pgt_vehicule_accident (
    id_vehicule_acc_auto         bigint,  -- IDvehiculeAccAuto
    id_vehicule_acc              bigint NOT NULL,  -- IDvehiculeAcc
    id_vehicule                  bigint,  -- IDvehicule
    vehicule_acc_date            timestamp,  -- vehiculeAcc_Date
    id_vehicule_pc               bigint,  -- IDvehiculePC
    resp                         smallint,  -- Resp
    prix_rep                     numeric(19,4),  -- PrixRep
    prix_fran                    numeric(19,4),  -- PrixFran
    reparable                    boolean,  -- Reparable
    deb_rep                      date,  -- DebRep
    fin_rep                      date,  -- FinRep
    repare                       boolean,  -- Reparé
    desc_                        text,  -- Desc
    modif_op                     bigint,  -- ModifOp
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifElem
    optim_cle_comp_vehic_i_dveh  varchar(16),  -- OptimCleComp_vehic_IDveh
    CONSTRAINT pk_pgt_vehicule_accident PRIMARY KEY (id_vehicule_acc),
    CONSTRAINT uq_pgt_vehicule_accident_auto UNIQUE (id_vehicule_acc_auto)
);
CREATE INDEX ix_pgt_vehicule_accident_id_vehicule ON ulease.pgt_vehicule_accident (id_vehicule);
CREATE INDEX ix_pgt_vehicule_accident_id_vehicule_pc ON ulease.pgt_vehicule_accident (id_vehicule_pc);
CREATE INDEX ix_pgt_vehicule_accident_resp ON ulease.pgt_vehicule_accident (resp);
CREATE INDEX ix_pgt_vehicule_accident_reparable ON ulease.pgt_vehicule_accident (reparable);
CREATE INDEX ix_pgt_vehicule_accident_repare ON ulease.pgt_vehicule_accident (repare);
CREATE INDEX ix_pgt_vehicule_accident_modif_date ON ulease.pgt_vehicule_accident (modif_date);

CREATE TABLE ulease.pgt_vehicule_amende (
    id_vehicule_pv_auto                bigint,  -- IDvehiculePVAuto
    id_vehicule_pv                     bigint NOT NULL,  -- IDvehiculePV
    id_vehicule                        bigint,  -- IDvehicule
    vehicule_pv_date                   timestamp,  -- vehiculePV_DATE
    id_vehicule_pc                     bigint,  -- IDvehiculePC
    montant                            numeric(19,4),  -- Montant
    comment                            text,  -- Comment
    paye_employeur                     boolean,  -- payeEmployeur
    paye_employeur_date                date,  -- payeEmployeur_DATE
    prel_salarie                       boolean,  -- prelSalarie
    prel_salarie_date                  varchar(50),  -- prelSalarie_DATE
    num_pv                             varchar(50),  -- numPV
    frais                              numeric(19,4),  -- frais
    nb_pts                             integer,  -- nbPts
    optim_cle_comp_vehic_i_dveh_vehic  varchar(21),  -- OptimCleComp_vehic_IDveh_vehic
    modif_op                           bigint,  -- ModifOp
    modif_date                         timestamp,  -- ModifDate
    modif_elem                         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_vehicule_amende PRIMARY KEY (id_vehicule_pv),
    CONSTRAINT uq_pgt_vehicule_amende_auto UNIQUE (id_vehicule_pv_auto)
);
CREATE INDEX ix_pgt_vehicule_amende_id_vehicule ON ulease.pgt_vehicule_amende (id_vehicule);
CREATE INDEX ix_pgt_vehicule_amende_vehicule_pv_date ON ulease.pgt_vehicule_amende (vehicule_pv_date);
CREATE INDEX ix_pgt_vehicule_amende_id_vehicule_pc ON ulease.pgt_vehicule_amende (id_vehicule_pc);
CREATE INDEX ix_pgt_vehicule_amende_paye_employeur ON ulease.pgt_vehicule_amende (paye_employeur);
CREATE INDEX ix_pgt_vehicule_amende_prel_salarie ON ulease.pgt_vehicule_amende (prel_salarie);
CREATE INDEX ix_pgt_vehicule_amende_modif_date ON ulease.pgt_vehicule_amende (modif_date);

CREATE TABLE ulease.pgt_vehicule_conducteur (
    id_vehicule_pc        bigint NOT NULL,  -- IDvehiculePC
    id_vehicule           bigint,  -- IDvehicule
    id_conducteur         bigint,  -- IDConducteur
    perception_date       date,  -- PerceptionDate
    restitution_date      date,  -- RestitutionDate
    conv_dispo            boolean,  -- ConvDispo
    fiche_enlev           boolean,  -- FicheEnlev
    permis_cnd            boolean,  -- PermisCnd
    info_vehicule         text,  -- InfoVehicule
    k_mdepart             integer,  -- KMdépart
    cg_conducteur         boolean,  -- CG_Conducteur
    cg_originale_dossier  boolean,  -- CG_originale_dossier
    c_vet_vignette        boolean,  -- CVetVignette
    fiche_rest            boolean,  -- FicheRest
    modif_op              bigint,  -- ModifOp
    modif_date            timestamp,  -- ModifDate
    modif_elem            varchar(5),  -- ModifElem
    temporaire            boolean,  -- Temporaire
    perception_heure      time,  -- PerceptionHeure
    restitution_heure     time,  -- RestitutionHeure
    id_ste                bigint,  -- IDSte
    id_vehicule_pc_auto   bigint,  -- IDvehiculePCAuto
    CONSTRAINT pk_pgt_vehicule_conducteur PRIMARY KEY (id_vehicule_pc),
    CONSTRAINT uq_pgt_vehicule_conducteur_auto UNIQUE (id_vehicule_pc_auto)
);
CREATE INDEX ix_pgt_vehicule_conducteur_id_vehicule ON ulease.pgt_vehicule_conducteur (id_vehicule);
CREATE INDEX ix_pgt_vehicule_conducteur_id_conducteur ON ulease.pgt_vehicule_conducteur (id_conducteur);
CREATE INDEX ix_pgt_vehicule_conducteur_modif_date ON ulease.pgt_vehicule_conducteur (modif_date);

CREATE TABLE ulease.pgt_vehicule_entretien (
    id_vehicule_entretien       bigint NOT NULL,  -- IDvehicule_entretien
    id_vehicule                 bigint,  -- IDvehicule
    type_entretien              smallint,  -- Type_Entretien
    realise_le                  date,  -- RéaliséLe
    montant_ht                  numeric(19,4),  -- MontantHT
    montant_ttc                 numeric(19,4),  -- MontantTTC
    c_rentretien                varchar(50),  -- CRentretien
    modif_op                    bigint,  -- ModifOp
    modif_date                  timestamp,  -- ModifDate
    modif_elem                  varchar(5),  -- ModifElem
    id_vehicule_entretien_auto  bigint,  -- IDvehicule_entretienAuto
    CONSTRAINT pk_pgt_vehicule_entretien PRIMARY KEY (id_vehicule_entretien),
    CONSTRAINT uq_pgt_vehicule_entretien_auto UNIQUE (id_vehicule_entretien_auto)
);
CREATE INDEX ix_pgt_vehicule_entretien_id_vehicule ON ulease.pgt_vehicule_entretien (id_vehicule);
CREATE INDEX ix_pgt_vehicule_entretien_modif_date ON ulease.pgt_vehicule_entretien (modif_date);

CREATE TABLE ulease.pgt_vehicule_etat (
    id_vehicule_etat  bigint NOT NULL,  -- IDvehiculeEtat
    lib_etat          varchar(50),  -- LibEtat
    logo              bytea,  -- LOGO
    modif_op          bigint,  -- ModifOp
    modif_date        timestamp,  -- ModifDate
    modif_elem        varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_vehicule_etat PRIMARY KEY (id_vehicule_etat)
);
CREATE INDEX ix_pgt_vehicule_etat_lib_etat ON ulease.pgt_vehicule_etat (lib_etat);
CREATE INDEX ix_pgt_vehicule_etat_modif_date ON ulease.pgt_vehicule_etat (modif_date);

CREATE TABLE ulease.pgt_vehicule_fiche (
    id_vehicule_marque         bigint,  -- IDvehiculeMarque
    id_vehicule                bigint NOT NULL,  -- IDvehicule
    modele                     varchar(50),  -- MODELE
    immat                      varchar(20),  -- IMMAT
    forfait_km                 integer,  -- FORFAITKM
    date_deb                   date,  -- DATEDEB
    date_fin                   date,  -- DATEFIN
    carte_grise                boolean,  -- CarteGrise
    info_vehicule              text,  -- InfoVehicule
    k_mdepart                  integer,  -- KMdépart
    km_actuel                  integer,  -- KMActuel
    date_releve                date,  -- DateReleve
    id_vehicule_etat           bigint,  -- IDvehiculeEtat
    chevaux_fiscaux            integer,  -- ChevauxFiscaux
    modif_op                   bigint,  -- ModifOp
    modif_date                 timestamp,  -- ModifDate
    modif_elem                 varchar(5),  -- ModifElem
    km_mensuel                 integer,  -- KMMENSUEL
    id_ste_proprio             bigint,  -- IdSte_Proprio
    lien_carte_grise           varchar(15),  -- LienCarteGrise
    achat_loc                  varchar(20),  -- Achat_Loc
    date_mise_circulation      date,  -- DateMiseCirculation
    id_ste_reseau              bigint,  -- IdSte_Reseau
    alerte_rel                 boolean,  -- ALERTEREL
    id_vehicule_type_capacite  bigint,  -- IDVehicule_TypeCapacité
    id_vehicule_auto           bigint,  -- IDvehiculeAuto
    CONSTRAINT pk_pgt_vehicule_fiche PRIMARY KEY (id_vehicule),
    CONSTRAINT uq_pgt_vehicule_fiche_auto UNIQUE (id_vehicule_auto)
);
CREATE INDEX ix_pgt_vehicule_fiche_id_vehicule_marque ON ulease.pgt_vehicule_fiche (id_vehicule_marque);
CREATE INDEX ix_pgt_vehicule_fiche_immat ON ulease.pgt_vehicule_fiche (immat);
CREATE INDEX ix_pgt_vehicule_fiche_date_deb ON ulease.pgt_vehicule_fiche (date_deb);
CREATE INDEX ix_pgt_vehicule_fiche_date_releve ON ulease.pgt_vehicule_fiche (date_releve);
CREATE INDEX ix_pgt_vehicule_fiche_id_vehicule_etat ON ulease.pgt_vehicule_fiche (id_vehicule_etat);
CREATE INDEX ix_pgt_vehicule_fiche_modif_date ON ulease.pgt_vehicule_fiche (modif_date);
CREATE INDEX ix_pgt_vehicule_fiche_id_ste_proprio ON ulease.pgt_vehicule_fiche (id_ste_proprio);
CREATE INDEX ix_pgt_vehicule_fiche_id_vehicule_type_capacite ON ulease.pgt_vehicule_fiche (id_vehicule_type_capacite);

CREATE TABLE ulease.pgt_vehicule_marque (
    id_vehicule_marque       bigint NOT NULL,  -- IDvehiculeMarque
    nom                      varchar(50),  -- NOM
    logo                     bytea,  -- LOGO
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    id_vehicule_marque_auto  bigint,  -- IDvehiculeMarqueAuto
    CONSTRAINT pk_pgt_vehicule_marque PRIMARY KEY (id_vehicule_marque),
    CONSTRAINT uq_pgt_vehicule_marque_auto UNIQUE (id_vehicule_marque_auto)
);
CREATE INDEX ix_pgt_vehicule_marque_nom ON ulease.pgt_vehicule_marque (nom);
CREATE INDEX ix_pgt_vehicule_marque_modif_date ON ulease.pgt_vehicule_marque (modif_date);

-- ulease.pgt_vehicule_pv : obsolete (remplacee par pgt_vehicule_amende).
-- Retiree du mapping et de la sync ; drop en base via
-- migration/patches/drop_pgt_vehicule_pv.sql (a appliquer manuellement).

CREATE TABLE ulease.pgt_vehicule_releve (
    id_vehicule_releve                   bigint NOT NULL,  -- IDvehiculeReleve
    id_vehicule                          bigint,  -- IDvehicule
    km                                   integer,  -- KM
    op_releve                            bigint,  -- OP_Relève
    id_vehicule_pc                       bigint,  -- IDvehiculePC
    km_restant                           integer,  -- KmRestant
    commentaire                          text,  -- Commentaire
    km_parcouru                          integer,  -- KmParcouru
    alerte                               boolean,  -- ALERTE
    modif_op                             bigint,  -- ModifOp
    modif_date                           timestamp,  -- ModifDate
    date_releve                          date,  -- DateReleve
    modif_elem                           varchar(5),  -- ModifElem
    id_vehicule_releve_auto              bigint,  -- IDvehiculeReleveAuto
    optim_cle_comp_vehic_i_dveh_vehic    varchar(21),  -- OptimCleComp_vehic_IDveh_vehic
    optim_cle_comp_vehic_i_dveh_vehic_1  varchar(21),  -- OptimCleComp_vehic_IDveh_vehic_1
    CONSTRAINT pk_pgt_vehicule_releve PRIMARY KEY (id_vehicule_releve),
    CONSTRAINT uq_pgt_vehicule_releve_auto UNIQUE (id_vehicule_releve_auto)
);
CREATE INDEX ix_pgt_vehicule_releve_id_vehicule ON ulease.pgt_vehicule_releve (id_vehicule);
CREATE INDEX ix_pgt_vehicule_releve_op_releve ON ulease.pgt_vehicule_releve (op_releve);
CREATE INDEX ix_pgt_vehicule_releve_id_vehicule_pc ON ulease.pgt_vehicule_releve (id_vehicule_pc);
CREATE INDEX ix_pgt_vehicule_releve_alerte ON ulease.pgt_vehicule_releve (alerte);
CREATE INDEX ix_pgt_vehicule_releve_modif_date ON ulease.pgt_vehicule_releve (modif_date);
CREATE INDEX ix_pgt_vehicule_releve_date_releve ON ulease.pgt_vehicule_releve (date_releve);

CREATE TABLE ulease.pgt_vehicule_typecapacite (
    id_vehicule_type_capacite       bigint,  -- IDVehicule_TypeCapacité
    lib_type                        varchar(5),  -- Lib_Type
    nb_place                        smallint,  -- nbPlace
    modif_date                      timestamp,  -- ModifDate
    modif_op                        bigint,  -- ModifOp
    modif_elem                      varchar(5),  -- ModifElem
    id_vehicule_type_capacite_auto  bigint NOT NULL,  -- IDVehicule_TypeCapacitéAuto
    CONSTRAINT pk_pgt_vehicule_typecapacite PRIMARY KEY (id_vehicule_type_capacite_auto)
);
CREATE INDEX ix_pgt_vehicule_typecapacite_lib_type ON ulease.pgt_vehicule_typecapacite (lib_type);
CREATE INDEX ix_pgt_vehicule_typecapacite_modif_date ON ulease.pgt_vehicule_typecapacite (modif_date);
