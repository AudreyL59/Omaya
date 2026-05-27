CREATE SCHEMA IF NOT EXISTS adv;


CREATE TABLE adv.pgt_agenda_commercial (
    id_agenda_commercial_auto       bigint,  -- IDAgendaCommercialAuto
    id_agenda_commercial            bigint  NOT NULL,  -- IDAgendaCommercial
    id_salarie                      bigint,  -- IDSalarie
    id_agenda_commercial_categorie  integer,  -- IDAgendaCommercial_Catégorie
    id_agenda_commercial_origine    integer,  -- IDAgendaCommercial_Origine
    id_agenda_commercial_source     integer,  -- IDAgendaCommercial_Source
    motif_statut                    text,  -- MotifStatut
    titre                           text,  -- Titre
    contenu                         text,  -- Contenu
    info_compl                      text,  -- InfoCompl
    date_debut                      timestamp,  -- DateDébut
    date_fin                        timestamp,  -- DateFin
    id_tk_liste                     bigint,  -- IDTK_Liste
    op_crea                         bigint,  -- OPCrea
    datecrea                        timestamp,  -- Datecrea
    modif_op                        bigint,  -- ModifOP
    modif_date                      timestamp,  -- ModifDate
    modif_elem                      varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_agenda_commercial PRIMARY KEY (id_agenda_commercial),
    CONSTRAINT uq_pgt_agenda_commercial_auto UNIQUE (id_agenda_commercial_auto)
);
CREATE INDEX ix_pgt_agenda_commercial_id_salarie ON adv.pgt_agenda_commercial (id_salarie);
CREATE INDEX ix_pgt_agenda_commercial_id_agenda_commercial_categorie ON adv.pgt_agenda_commercial (id_agenda_commercial_categorie);
CREATE INDEX ix_pgt_agenda_commercial_id_agenda_commercial_origine ON adv.pgt_agenda_commercial (id_agenda_commercial_origine);
CREATE INDEX ix_pgt_agenda_commercial_id_agenda_commercial_source ON adv.pgt_agenda_commercial (id_agenda_commercial_source);
CREATE INDEX ix_pgt_agenda_commercial_date_debut ON adv.pgt_agenda_commercial (date_debut);
CREATE INDEX ix_pgt_agenda_commercial_id_tk_liste ON adv.pgt_agenda_commercial (id_tk_liste);
CREATE INDEX ix_pgt_agenda_commercial_modif_date ON adv.pgt_agenda_commercial (modif_date);

CREATE TABLE adv.pgt_agenda_commercial_categorie (
    id_agenda_commercial_categorie_auto  bigint,  -- IDAgendaCommercial_CatégorieAuto
    id_agenda_commercial_categorie       integer  NOT NULL,  -- IDAgendaCommercial_Catégorie
    lib_categorie                        text,  -- Lib_Catégorie
    couleur                              integer,  -- Couleur
    id_cv_statut                         bigint,  -- IdCvStatut
    modif_date                           timestamp,  -- ModifDate
    modif_op                             bigint,  -- ModifOP
    modif_elem                           varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_agenda_commercial_categorie PRIMARY KEY (id_agenda_commercial_categorie),
    CONSTRAINT uq_pgt_agenda_commercial_categorie_auto UNIQUE (id_agenda_commercial_categorie_auto)
);
CREATE INDEX ix_pgt_agenda_commercial_categorie_id_cv_statut ON adv.pgt_agenda_commercial_categorie (id_cv_statut);
CREATE INDEX ix_pgt_agenda_commercial_categorie_modif_date ON adv.pgt_agenda_commercial_categorie (modif_date);

CREATE TABLE adv.pgt_client (
    i_dclient_auto  bigint,  -- IDclientAuto
    i_dclient       bigint  NOT NULL,  -- IDclient
    civilite        smallint,  -- Civilité
    nom             text,  -- NOM
    prenom          text,  -- PRENOM
    date_naiss      date,  -- DATENAISS
    loca_proprio    smallint,  -- LOCA_PROPRIO
    adr_bat         boolean,  -- ADRBAT
    adresse1        text,  -- ADRESSE1
    adresse2        text,  -- ADRESSE2
    cp              varchar(5),  -- CP
    ville           text,  -- VILLE
    pays            text,  -- PAYS
    tel             varchar(15),  -- TEL
    gsm             varchar(15),  -- GSM
    mail            text,  -- MAIL
    date_saisie     timestamp,  -- DateSAISIE
    op_saisie       bigint,  -- OPSAISIE
    info_interne    text,  -- InfoInterne
    latitude_deg    double precision,  -- latitude_deg
    longitude_deg   double precision,  -- longitude_deg
    opt_partenaire  boolean,  -- Opt_Partenaire
    modif_op        bigint,  -- ModifOP
    modif_date      timestamp,  -- ModifDate
    modif_elem      varchar(5),  -- ModifELEM
    tel_gsm1        varchar(30),  -- TELGSM1
    CONSTRAINT pk_pgt_client PRIMARY KEY (i_dclient),
    CONSTRAINT uq_pgt_client_auto UNIQUE (i_dclient_auto)
);
CREATE INDEX ix_pgt_client_tel ON adv.pgt_client (tel);
CREATE INDEX ix_pgt_client_gsm ON adv.pgt_client (gsm);
CREATE INDEX ix_pgt_client_date_saisie ON adv.pgt_client (date_saisie);
CREATE INDEX ix_pgt_client_op_saisie ON adv.pgt_client (op_saisie);
CREATE INDEX ix_pgt_client_latitude_deg ON adv.pgt_client (latitude_deg);
CREATE INDEX ix_pgt_client_modif_date ON adv.pgt_client (modif_date);

CREATE TABLE adv.pgt_eni_contrat (
    i_dcontrat_auto   bigint,  -- IDcontratAuto
    i_dcontrat        bigint  NOT NULL,  -- IDcontrat
    id_sales_force    varchar(25),  -- IDSalesForce
    i_dclient         bigint,  -- IDclient
    id_salarie        bigint,  -- IDSalarie
    id_ste            bigint,  -- IdSte
    num_bs            text,  -- NumBS
    i_dproduit        integer,  -- IDproduit
    i_detat_contrat   integer,  -- IDetatContrat
    date_signature    date,  -- DateSignature
    gaz_car_declaree  integer,  -- GazCarDeclaree
    gaz_car_relevee   integer,  -- GazCarRelevée
    elec_puissance    smallint,  -- ElecPuissance
    gaz_actif         boolean,  -- GazActif
    elec_actif        boolean,  -- ElecActif
    info_partagee     text,  -- InfoPartagée
    info_interne      text,  -- InfoInterne
    mois_p            date,  -- MoisP
    op_saisie         bigint,  -- OPSAISIE
    date_saisie       timestamp,  -- DateSAISIE
    non_call          boolean,  -- NonCALL
    nb_points         double precision,  -- nbPoints
    code_enr          text,  -- CodeENR
    notation          numeric,  -- Notation
    notation_info     text,  -- NotationInfo
    modif_op          bigint,  -- ModifOP
    modif_date        timestamp,  -- ModifDate
    modif_elem        varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_eni_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_eni_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_eni_contrat_i_dclient ON adv.pgt_eni_contrat (i_dclient);
CREATE INDEX ix_pgt_eni_contrat_id_salarie ON adv.pgt_eni_contrat (id_salarie);
CREATE INDEX ix_pgt_eni_contrat_id_ste ON adv.pgt_eni_contrat (id_ste);
CREATE INDEX ix_pgt_eni_contrat_num_bs ON adv.pgt_eni_contrat (num_bs);
CREATE INDEX ix_pgt_eni_contrat_i_dproduit ON adv.pgt_eni_contrat (i_dproduit);
CREATE INDEX ix_pgt_eni_contrat_i_detat_contrat ON adv.pgt_eni_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_eni_contrat_date_signature ON adv.pgt_eni_contrat (date_signature);
CREATE INDEX ix_pgt_eni_contrat_op_saisie ON adv.pgt_eni_contrat (op_saisie);
CREATE INDEX ix_pgt_eni_contrat_date_saisie ON adv.pgt_eni_contrat (date_saisie);
CREATE INDEX ix_pgt_eni_contrat_modif_date ON adv.pgt_eni_contrat (modif_date);

CREATE TABLE adv.pgt_eni_contrat_compteur (
    i_dcontrat_compteur     bigint  NOT NULL,  -- IDcontratCompteur
    i_dcontrat              bigint,  -- IDcontrat
    type_releve             varchar(10),  -- TypeRelève
    releve                  integer,  -- Relève
    modif_op                bigint,  -- ModifOP
    modif_date              timestamp,  -- ModifDate
    modif_elem              varchar(5),  -- ModifELEM
    i_dcontrat_type_releve  varchar(18),  -- IDcontratTypeRelève
    CONSTRAINT pk_pgt_eni_contrat_compteur PRIMARY KEY (i_dcontrat_compteur)
);
CREATE INDEX ix_pgt_eni_contrat_compteur_i_dcontrat ON adv.pgt_eni_contrat_compteur (i_dcontrat);
CREATE INDEX ix_pgt_eni_contrat_compteur_type_releve ON adv.pgt_eni_contrat_compteur (type_releve);
CREATE INDEX ix_pgt_eni_contrat_compteur_modif_date ON adv.pgt_eni_contrat_compteur (modif_date);

CREATE TABLE adv.pgt_eni_contrat_option (
    i_dcontrat_option_auto      bigint,  -- IDcontratOptionAuto
    i_dcontrat                  bigint  NOT NULL,  -- IDcontrat
    num_bs                      text,  -- NumBS
    opt_mail                    boolean,  -- OPT_Mail
    opt_index_gaz               boolean,  -- OPT_IndexGaz
    opt_entretien               boolean,  -- OPT_Entretien
    opt_entretien_etat          integer,  -- OPT_Entretien_Etat
    opt_delai_retra             boolean,  -- OPT_DelaiRetra
    opt_index_elec              boolean,  -- OPT_IndexElec
    opt_hp_hc                   boolean,  -- OPT_HP_HC
    opt_energie_verte_gaz       boolean,  -- OPT_EnergieVerteGaz
    opt_energie_verte_elec      boolean,  -- OPT_EnergieVerteElec
    opt_deja_client_eni         boolean,  -- OPT_DejaClientENI
    opt_reforestation           boolean,  -- OPT_Reforestation
    opt_optin_commercial        boolean,  -- OPT_optinCommercial
    opt_e_facture               boolean,  -- OPT_eFacture
    opt_e_communication         boolean,  -- OPT_eCommunication
    opt_pdc                     boolean,  -- OPT_PDC
    opt_accept_com_parte        boolean,  -- OPT_AcceptComParte
    opt_consent_consult_distri  boolean,  -- OPT_ConsentConsultDistri
    opt_protection              boolean,  -- OPT_Protection
    modif_op                    bigint,  -- ModifOP
    modif_date                  timestamp,  -- ModifDate
    modif_elem                  varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_eni_contrat_option PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_eni_contrat_option_auto UNIQUE (i_dcontrat_option_auto)
);
CREATE INDEX ix_pgt_eni_contrat_option_num_bs ON adv.pgt_eni_contrat_option (num_bs);
CREATE INDEX ix_pgt_eni_contrat_option_opt_entretien ON adv.pgt_eni_contrat_option (opt_entretien);
CREATE INDEX ix_pgt_eni_contrat_option_opt_entretien_etat ON adv.pgt_eni_contrat_option (opt_entretien_etat);
CREATE INDEX ix_pgt_eni_contrat_option_modif_date ON adv.pgt_eni_contrat_option (modif_date);

CREATE TABLE adv.pgt_eni_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_eni_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_eni_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_eni_etat_contrat_id_type_etat ON adv.pgt_eni_etat_contrat (id_type_etat);
CREATE INDEX ix_pgt_eni_etat_contrat_lib_etat ON adv.pgt_eni_etat_contrat (lib_etat);
CREATE INDEX ix_pgt_eni_etat_contrat_lib_etat_vend ON adv.pgt_eni_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_eni_etat_contrat_categorie ON adv.pgt_eni_etat_contrat (categorie);
CREATE INDEX ix_pgt_eni_etat_contrat_modif_date ON adv.pgt_eni_etat_contrat (modif_date);

CREATE TABLE adv.pgt_eni_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_eni_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_eni_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_eni_histo_attr_ctt_i_dcontrat ON adv.pgt_eni_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_eni_histo_attr_ctt_num ON adv.pgt_eni_histo_attr_ctt (num);
CREATE INDEX ix_pgt_eni_histo_attr_ctt_op_saisie ON adv.pgt_eni_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_eni_histo_attr_ctt_date ON adv.pgt_eni_histo_attr_ctt (date);
CREATE INDEX ix_pgt_eni_histo_attr_ctt_modif_date ON adv.pgt_eni_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_eni_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_eni_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_eni_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_eni_histo_etat_ctt_i_dcontrat ON adv.pgt_eni_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_eni_histo_etat_ctt_op_saisie ON adv.pgt_eni_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_eni_histo_etat_ctt_date ON adv.pgt_eni_histo_etat_ctt (date);
CREATE INDEX ix_pgt_eni_histo_etat_ctt_modif_date ON adv.pgt_eni_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_eni_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_eni_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_eni_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_eni_produit_lib_produit ON adv.pgt_eni_produit (lib_produit);
CREATE INDEX ix_pgt_eni_produit_prefixe_bdd ON adv.pgt_eni_produit (prefixe_bdd);
CREATE INDEX ix_pgt_eni_produit_famille ON adv.pgt_eni_produit (famille);
CREATE INDEX ix_pgt_eni_produit_sous_fam ON adv.pgt_eni_produit (sous_fam);
CREATE INDEX ix_pgt_eni_produit_pro_actif ON adv.pgt_eni_produit (pro_actif);
CREATE INDEX ix_pgt_eni_produit_id_type_prod_dec ON adv.pgt_eni_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_eni_produit_modif_date ON adv.pgt_eni_produit (modif_date);

CREATE TABLE adv.pgt_eni_remun (
    id_remun_auto                            bigint,  -- IDRemunAuto
    id_remun                                 bigint  NOT NULL,  -- IDRemun
    famille                                  varchar(10),  -- FAMILLE
    ss_fam                                   varchar(10),  -- SSFAM
    val_min                                  integer,  -- val_MIN
    val_max                                  integer,  -- val_MAX
    rem_active                               boolean,  -- Rem_Active
    date_activation                          date,  -- DateActivation
    date_desactivation                       date,  -- DateDésactivation
    modif_op                                 bigint,  -- ModifOP
    modif_date                               timestamp,  -- ModifDate
    modif_elem                               varchar(5),  -- ModifELEM
    optim_cle_comp_ssfam_rem_a_famil_date_a  varchar(29),  -- OptimCleComp_SSFAM_Rem_A_FAMIL_DateA
    nb_points                                double precision,  -- nbPoints
    CONSTRAINT pk_pgt_eni_remun PRIMARY KEY (id_remun),
    CONSTRAINT uq_pgt_eni_remun_auto UNIQUE (id_remun_auto)
);
CREATE INDEX ix_pgt_eni_remun_famille ON adv.pgt_eni_remun (famille);
CREATE INDEX ix_pgt_eni_remun_ss_fam ON adv.pgt_eni_remun (ss_fam);
CREATE INDEX ix_pgt_eni_remun_modif_date ON adv.pgt_eni_remun (modif_date);

CREATE TABLE adv.pgt_etat_call_ret (
    id_etat_call_ret_auto  bigint,  -- IDEtatCallRetAuto
    id_etat_call_ret       smallint  NOT NULL,  -- IDEtatCallRet
    lib_etat               varchar(50),  -- LibEtat
    mots_cles              text,  -- MotsClés
    id_etat_rdv_tech       bigint,  -- IdEtatRdvTech
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOp
    modif_elem             varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_etat_call_ret PRIMARY KEY (id_etat_call_ret),
    CONSTRAINT uq_pgt_etat_call_ret_auto UNIQUE (id_etat_call_ret_auto)
);
CREATE INDEX ix_pgt_etat_call_ret_mots_cles ON adv.pgt_etat_call_ret (mots_cles);
CREATE INDEX ix_pgt_etat_call_ret_modif_date ON adv.pgt_etat_call_ret (modif_date);

CREATE TABLE adv.pgt_gep_contrat (
    i_dcontrat_auto  bigint,  -- IDcontratAuto
    i_dcontrat       bigint  NOT NULL,  -- IDcontrat
    i_dclient        bigint,  -- IDclient
    id_salarie       bigint,  -- IDSalarie
    id_ste           bigint,  -- IdSte
    num_bs           text,  -- NumBS
    i_dproduit       integer,  -- IDproduit
    i_detat_contrat  integer,  -- IDetatContrat
    date_signature   date,  -- DateSignature
    info_partagee    text,  -- InfoPartagée
    info_interne     text,  -- InfoInterne
    mois_p           date,  -- MoisP
    op_saisie        bigint,  -- OPSAISIE
    date_saisie      timestamp,  -- DateSAISIE
    non_call         boolean,  -- NonCALL
    nb_points        double precision,  -- nbPoints
    code_enr         text,  -- CodeENR
    mode_paiement    boolean,  -- ModePaiement
    pack             smallint,  -- Pack
    duree_ab         smallint,  -- DuréeAb
    rib_fourni       boolean,  -- RIB_Fourni
    notation         numeric,  -- Notation
    notation_info    text,  -- NotationInfo
    modif_op         bigint,  -- ModifOp
    modif_date       timestamp,  -- ModifDate
    modif_elem       varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_gep_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_gep_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_gep_contrat_i_dclient ON adv.pgt_gep_contrat (i_dclient);
CREATE INDEX ix_pgt_gep_contrat_id_salarie ON adv.pgt_gep_contrat (id_salarie);
CREATE INDEX ix_pgt_gep_contrat_id_ste ON adv.pgt_gep_contrat (id_ste);
CREATE INDEX ix_pgt_gep_contrat_num_bs ON adv.pgt_gep_contrat (num_bs);
CREATE INDEX ix_pgt_gep_contrat_i_dproduit ON adv.pgt_gep_contrat (i_dproduit);
CREATE INDEX ix_pgt_gep_contrat_i_detat_contrat ON adv.pgt_gep_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_gep_contrat_date_signature ON adv.pgt_gep_contrat (date_signature);
CREATE INDEX ix_pgt_gep_contrat_op_saisie ON adv.pgt_gep_contrat (op_saisie);
CREATE INDEX ix_pgt_gep_contrat_date_saisie ON adv.pgt_gep_contrat (date_saisie);
CREATE INDEX ix_pgt_gep_contrat_modif_date ON adv.pgt_gep_contrat (modif_date);

CREATE TABLE adv.pgt_gep_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_gep_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_gep_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_gep_etat_contrat_id_type_etat ON adv.pgt_gep_etat_contrat (id_type_etat);
CREATE INDEX ix_pgt_gep_etat_contrat_lib_etat ON adv.pgt_gep_etat_contrat (lib_etat);
CREATE INDEX ix_pgt_gep_etat_contrat_lib_etat_vend ON adv.pgt_gep_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_gep_etat_contrat_categorie ON adv.pgt_gep_etat_contrat (categorie);
CREATE INDEX ix_pgt_gep_etat_contrat_modif_date ON adv.pgt_gep_etat_contrat (modif_date);

CREATE TABLE adv.pgt_gep_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_gep_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_gep_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_gep_histo_attr_ctt_i_dcontrat ON adv.pgt_gep_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_gep_histo_attr_ctt_num ON adv.pgt_gep_histo_attr_ctt (num);
CREATE INDEX ix_pgt_gep_histo_attr_ctt_op_saisie ON adv.pgt_gep_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_gep_histo_attr_ctt_date ON adv.pgt_gep_histo_attr_ctt (date);
CREATE INDEX ix_pgt_gep_histo_attr_ctt_modif_date ON adv.pgt_gep_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_gep_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_gep_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_gep_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_gep_histo_etat_ctt_i_dcontrat ON adv.pgt_gep_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_gep_histo_etat_ctt_op_saisie ON adv.pgt_gep_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_gep_histo_etat_ctt_date ON adv.pgt_gep_histo_etat_ctt (date);
CREATE INDEX ix_pgt_gep_histo_etat_ctt_modif_date ON adv.pgt_gep_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_gep_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_gep_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_gep_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_gep_produit_lib_produit ON adv.pgt_gep_produit (lib_produit);
CREATE INDEX ix_pgt_gep_produit_prefixe_bdd ON adv.pgt_gep_produit (prefixe_bdd);
CREATE INDEX ix_pgt_gep_produit_famille ON adv.pgt_gep_produit (famille);
CREATE INDEX ix_pgt_gep_produit_sous_fam ON adv.pgt_gep_produit (sous_fam);
CREATE INDEX ix_pgt_gep_produit_pro_actif ON adv.pgt_gep_produit (pro_actif);
CREATE INDEX ix_pgt_gep_produit_id_type_prod_dec ON adv.pgt_gep_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_gep_produit_modif_date ON adv.pgt_gep_produit (modif_date);

CREATE TABLE adv.pgt_groupe_operateur (
    id_groupe_operateur  bigint  NOT NULL,  -- IDGroupeOpérateur
    lib_groupe           varchar(50),  -- LibGroupe
    description          text,  -- Description
    logo                 bytea,  -- Logo
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_groupe_operateur PRIMARY KEY (id_groupe_operateur)
);
CREATE INDEX ix_pgt_groupe_operateur_modif_date ON adv.pgt_groupe_operateur (modif_date);

CREATE TABLE adv.pgt_groupe_operateur_partenaire (
    id_groupe_operateur_partenaire  bigint  NOT NULL,  -- IDGroupeOpérateur_Partenaire
    id_groupe_operateur             bigint,  -- IDGroupeOpérateur
    id_partenaire                   bigint,  -- IDPartenaire
    i_dproduit                      integer,  -- IDproduit
    date_deb                        date,  -- DateDeb
    date_fin                        date,  -- DateFin
    is_actif                        boolean,  -- IsActif
    modif_date                      timestamp,  -- ModifDate
    modif_op                        bigint,  -- ModifOp
    modif_elem                      varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_groupe_operateur_partenaire PRIMARY KEY (id_groupe_operateur_partenaire)
);
CREATE INDEX ix_pgt_groupe_operateur_partenaire_id_groupe_operateur ON adv.pgt_groupe_operateur_partenaire (id_groupe_operateur);
CREATE INDEX ix_pgt_groupe_operateur_partenaire_id_partenaire ON adv.pgt_groupe_operateur_partenaire (id_partenaire);
CREATE INDEX ix_pgt_groupe_operateur_partenaire_i_dproduit ON adv.pgt_groupe_operateur_partenaire (i_dproduit);
CREATE INDEX ix_pgt_groupe_operateur_partenaire_modif_date ON adv.pgt_groupe_operateur_partenaire (modif_date);

CREATE TABLE adv.pgt_groupe_rem (
    id_groupe_rem        bigint  NOT NULL,  -- IDGroupeRem
    id_distrib           bigint,  -- idDistrib
    id_groupe_operateur  bigint,  -- IDGroupeOpérateur
    lib_groupe           varchar(50),  -- LibGroupe
    nb_col               smallint,  -- nbCol
    nb_ligne             smallint,  -- nbLigne
    ordre                smallint,  -- Ordre
    date_deb             date,  -- DateDeb
    date_fin             date,  -- DateFin
    is_actif             boolean,  -- IsActif
    famille              bigint,  -- Famille
    ss_fam               varchar(15),  -- SsFam
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_groupe_rem PRIMARY KEY (id_groupe_rem)
);
CREATE INDEX ix_pgt_groupe_rem_id_distrib ON adv.pgt_groupe_rem (id_distrib);
CREATE INDEX ix_pgt_groupe_rem_id_groupe_operateur ON adv.pgt_groupe_rem (id_groupe_operateur);
CREATE INDEX ix_pgt_groupe_rem_famille ON adv.pgt_groupe_rem (famille);
CREATE INDEX ix_pgt_groupe_rem_ss_fam ON adv.pgt_groupe_rem (ss_fam);
CREATE INDEX ix_pgt_groupe_rem_modif_date ON adv.pgt_groupe_rem (modif_date);

CREATE TABLE adv.pgt_groupe_rem_tab (
    id_groupe_rem_tab  bigint  NOT NULL,  -- IDGroupeRemTab
    id_groupe_rem      bigint,  -- IDGroupeRem
    id_groupe_rem_x    bigint,  -- IDGroupeRemX
    id_groupe_rem_y    bigint,  -- IDGroupeRemY
    montant            numeric(19,4),  -- Montant
    date_deb           date,  -- DateDeb
    date_fin           date,  -- DateFin
    is_actif           boolean,  -- IsActif
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOp
    modif_elem         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_groupe_rem_tab PRIMARY KEY (id_groupe_rem_tab)
);
CREATE INDEX ix_pgt_groupe_rem_tab_id_groupe_rem ON adv.pgt_groupe_rem_tab (id_groupe_rem);
CREATE INDEX ix_pgt_groupe_rem_tab_id_groupe_rem_x ON adv.pgt_groupe_rem_tab (id_groupe_rem_x);
CREATE INDEX ix_pgt_groupe_rem_tab_id_groupe_rem_y ON adv.pgt_groupe_rem_tab (id_groupe_rem_y);
CREATE INDEX ix_pgt_groupe_rem_tab_modif_date ON adv.pgt_groupe_rem_tab (modif_date);

CREATE TABLE adv.pgt_groupe_rem_x (
    id_groupe_rem_x  bigint  NOT NULL,  -- IDGroupeRemX
    id_groupe_rem    bigint,  -- IDGroupeRem
    lib              varchar(100),  -- Lib
    code_interne     varchar(15),  -- CodeInterne
    date_deb         date,  -- DateDeb
    date_fin         date,  -- DateFin
    is_actif         boolean,  -- IsActif
    ordre            smallint,  -- Ordre
    modif_date       timestamp,  -- ModifDate
    modif_op         bigint,  -- ModifOp
    modif_elem       varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_groupe_rem_x PRIMARY KEY (id_groupe_rem_x)
);
CREATE INDEX ix_pgt_groupe_rem_x_id_groupe_rem ON adv.pgt_groupe_rem_x (id_groupe_rem);
CREATE INDEX ix_pgt_groupe_rem_x_modif_date ON adv.pgt_groupe_rem_x (modif_date);

CREATE TABLE adv.pgt_groupe_rem_y (
    id_groupe_rem_y  bigint  NOT NULL,  -- IDGroupeRemY
    id_groupe_rem    bigint,  -- IDGroupeRem
    lib              varchar(100),  -- Lib
    code_interne     varchar(15),  -- CodeInterne
    date_deb         date,  -- DateDeb
    date_fin         date,  -- DateFin
    is_actif         boolean,  -- IsActif
    ordre            smallint,  -- Ordre
    modif_date       timestamp,  -- ModifDate
    modif_op         bigint,  -- ModifOp
    modif_elem       varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_groupe_rem_y PRIMARY KEY (id_groupe_rem_y)
);
CREATE INDEX ix_pgt_groupe_rem_y_id_groupe_rem ON adv.pgt_groupe_rem_y (id_groupe_rem);
CREATE INDEX ix_pgt_groupe_rem_y_modif_date ON adv.pgt_groupe_rem_y (modif_date);

CREATE TABLE adv.pgt_iag_contrat (
    i_dcontrat_auto  bigint,  -- IDcontratAuto
    i_dcontrat       bigint  NOT NULL,  -- IDcontrat
    i_dclient        bigint,  -- IDclient
    id_salarie       bigint,  -- IDSalarie
    id_ste           bigint,  -- IdSte
    num_bs           text,  -- NumBS
    i_dproduit       integer,  -- IDproduit
    i_detat_contrat  integer,  -- IDetatContrat
    date_signature   date,  -- DateSignature
    info_partagee    text,  -- InfoPartagée
    info_interne     text,  -- InfoInterne
    mois_p           date,  -- MoisP
    op_saisie        bigint,  -- OPSAISIE
    date_saisie      timestamp,  -- DateSAISIE
    non_call         boolean,  -- NonCALL
    nb_points        double precision,  -- nbPoints
    code_enr         text,  -- CodeENR
    notation         numeric,  -- Notation
    notation_info    text,  -- NotationInfo
    modif_op         bigint,  -- ModifOP
    modif_date       timestamp,  -- ModifDate
    modif_elem       varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_iag_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_iag_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_iag_contrat_i_dclient ON adv.pgt_iag_contrat (i_dclient);
CREATE INDEX ix_pgt_iag_contrat_id_salarie ON adv.pgt_iag_contrat (id_salarie);
CREATE INDEX ix_pgt_iag_contrat_id_ste ON adv.pgt_iag_contrat (id_ste);
CREATE INDEX ix_pgt_iag_contrat_num_bs ON adv.pgt_iag_contrat (num_bs);
CREATE INDEX ix_pgt_iag_contrat_i_dproduit ON adv.pgt_iag_contrat (i_dproduit);
CREATE INDEX ix_pgt_iag_contrat_i_detat_contrat ON adv.pgt_iag_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_iag_contrat_date_signature ON adv.pgt_iag_contrat (date_signature);
CREATE INDEX ix_pgt_iag_contrat_op_saisie ON adv.pgt_iag_contrat (op_saisie);
CREATE INDEX ix_pgt_iag_contrat_date_saisie ON adv.pgt_iag_contrat (date_saisie);
CREATE INDEX ix_pgt_iag_contrat_modif_date ON adv.pgt_iag_contrat (modif_date);

CREATE TABLE adv.pgt_iag_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_iag_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_iag_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_iag_etat_contrat_id_type_etat ON adv.pgt_iag_etat_contrat (id_type_etat);
CREATE INDEX ix_pgt_iag_etat_contrat_lib_etat ON adv.pgt_iag_etat_contrat (lib_etat);
CREATE INDEX ix_pgt_iag_etat_contrat_lib_etat_vend ON adv.pgt_iag_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_iag_etat_contrat_categorie ON adv.pgt_iag_etat_contrat (categorie);
CREATE INDEX ix_pgt_iag_etat_contrat_modif_date ON adv.pgt_iag_etat_contrat (modif_date);

CREATE TABLE adv.pgt_iag_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_iag_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_iag_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_iag_histo_attr_ctt_i_dcontrat ON adv.pgt_iag_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_iag_histo_attr_ctt_num ON adv.pgt_iag_histo_attr_ctt (num);
CREATE INDEX ix_pgt_iag_histo_attr_ctt_op_saisie ON adv.pgt_iag_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_iag_histo_attr_ctt_date ON adv.pgt_iag_histo_attr_ctt (date);
CREATE INDEX ix_pgt_iag_histo_attr_ctt_modif_date ON adv.pgt_iag_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_iag_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_iag_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_iag_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_iag_histo_etat_ctt_i_dcontrat ON adv.pgt_iag_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_iag_histo_etat_ctt_op_saisie ON adv.pgt_iag_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_iag_histo_etat_ctt_date ON adv.pgt_iag_histo_etat_ctt (date);
CREATE INDEX ix_pgt_iag_histo_etat_ctt_modif_date ON adv.pgt_iag_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_iag_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_iag_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_iag_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_iag_produit_lib_produit ON adv.pgt_iag_produit (lib_produit);
CREATE INDEX ix_pgt_iag_produit_prefixe_bdd ON adv.pgt_iag_produit (prefixe_bdd);
CREATE INDEX ix_pgt_iag_produit_famille ON adv.pgt_iag_produit (famille);
CREATE INDEX ix_pgt_iag_produit_sous_fam ON adv.pgt_iag_produit (sous_fam);
CREATE INDEX ix_pgt_iag_produit_pro_actif ON adv.pgt_iag_produit (pro_actif);
CREATE INDEX ix_pgt_iag_produit_id_type_prod_dec ON adv.pgt_iag_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_iag_produit_modif_date ON adv.pgt_iag_produit (modif_date);

CREATE TABLE adv.pgt_iag_remun (
    id_remun_auto  bigint,  -- IDRemunAuto
    id_remun       bigint  NOT NULL,  -- IDRemun
    i_dproduit     integer,  -- IDproduit
    type_vente     smallint,  -- TypeVente
    date_debut     date,  -- DateDébut
    date_fin       date,  -- DateFin
    montant        numeric(19,4),  -- Montant
    nb_points      double precision,  -- nbPoints
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_iag_remun PRIMARY KEY (id_remun),
    CONSTRAINT uq_pgt_iag_remun_auto UNIQUE (id_remun_auto)
);
CREATE INDEX ix_pgt_iag_remun_i_dproduit ON adv.pgt_iag_remun (i_dproduit);
CREATE INDEX ix_pgt_iag_remun_date_debut ON adv.pgt_iag_remun (date_debut);
CREATE INDEX ix_pgt_iag_remun_modif_date ON adv.pgt_iag_remun (modif_date);

CREATE TABLE adv.pgt_importautosuivi (
    id_import_auto_suivi  bigint  NOT NULL,  -- IDImportAutoSuivi
    type                  varchar(20),  -- Type
    dateimport            date,  -- Dateimport
    total                 integer,  -- Total
    avancement            integer,  -- Avancement
    modif_date            timestamp,  -- ModifDate
    CONSTRAINT pk_pgt_importautosuivi PRIMARY KEY (id_import_auto_suivi)
);
CREATE INDEX ix_pgt_importautosuivi_type ON adv.pgt_importautosuivi (type);
CREATE INDEX ix_pgt_importautosuivi_modif_date ON adv.pgt_importautosuivi (modif_date);

CREATE TABLE adv.pgt_incident_call (
    i_dincident_call_auto  bigint,  -- IDincidentCallAuto
    i_dincident_call       bigint  NOT NULL,  -- IDincidentCall
    date_debut             timestamp,  -- DateDEBUT
    date_fin               timestamp,  -- DateFIN
    commentaire            text,  -- commentaire
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOP
    modif_elem             varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_incident_call PRIMARY KEY (i_dincident_call),
    CONSTRAINT uq_pgt_incident_call_auto UNIQUE (i_dincident_call_auto)
);
CREATE INDEX ix_pgt_incident_call_date_debut ON adv.pgt_incident_call (date_debut);
CREATE INDEX ix_pgt_incident_call_date_fin ON adv.pgt_incident_call (date_fin);
CREATE INDEX ix_pgt_incident_call_modif_date ON adv.pgt_incident_call (modif_date);

CREATE TABLE adv.pgt_oen_contrat (
    i_dcontrat_auto   bigint,  -- IDcontratAuto
    i_dcontrat        bigint  NOT NULL,  -- IDcontrat
    id_sales_force    varchar(25),  -- IDSalesForce
    i_dclient         bigint,  -- IDclient
    id_salarie        bigint,  -- IDSalarie
    id_ste            bigint,  -- IdSte
    num_bs            text,  -- NumBS
    ref_client        text,  -- RefClient
    i_dproduit        integer,  -- IDproduit
    i_detat_contrat   integer,  -- IDetatContrat
    id_etat_oen       bigint,  -- IdEtatOEN
    date_signature    date,  -- DateSignature
    date_activation   timestamp,  -- DateActivation
    gaz_car_declaree  integer,  -- GazCarDeclaree
    gaz_car_relevee   integer,  -- GazCarRelevée
    elec_puissance    smallint,  -- ElecPuissance
    is_dual           boolean,  -- IsDual
    info_partagee     text,  -- InfoPartagée
    info_interne      text,  -- InfoInterne
    mois_p            date,  -- MoisP
    op_saisie         bigint,  -- OPSAISIE
    date_saisie       timestamp,  -- DateSAISIE
    non_call          boolean,  -- NonCALL
    nb_points         double precision,  -- nbPoints
    code_enr          text,  -- CodeENR
    notation          numeric,  -- Notation
    notation_info     text,  -- NotationInfo
    modif_op          bigint,  -- ModifOP
    modif_date        timestamp,  -- ModifDate
    modif_elem        varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_oen_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_oen_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_oen_contrat_i_dclient ON adv.pgt_oen_contrat (i_dclient);
CREATE INDEX ix_pgt_oen_contrat_id_salarie ON adv.pgt_oen_contrat (id_salarie);
CREATE INDEX ix_pgt_oen_contrat_id_ste ON adv.pgt_oen_contrat (id_ste);
CREATE INDEX ix_pgt_oen_contrat_num_bs ON adv.pgt_oen_contrat (num_bs);
CREATE INDEX ix_pgt_oen_contrat_i_dproduit ON adv.pgt_oen_contrat (i_dproduit);
CREATE INDEX ix_pgt_oen_contrat_i_detat_contrat ON adv.pgt_oen_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_oen_contrat_id_etat_oen ON adv.pgt_oen_contrat (id_etat_oen);
CREATE INDEX ix_pgt_oen_contrat_date_signature ON adv.pgt_oen_contrat (date_signature);
CREATE INDEX ix_pgt_oen_contrat_op_saisie ON adv.pgt_oen_contrat (op_saisie);
CREATE INDEX ix_pgt_oen_contrat_date_saisie ON adv.pgt_oen_contrat (date_saisie);
CREATE INDEX ix_pgt_oen_contrat_modif_date ON adv.pgt_oen_contrat (modif_date);

CREATE TABLE adv.pgt_oen_contrat_compteur (
    i_dcontrat_compteur     bigint  NOT NULL,  -- IDcontratCompteur
    i_dcontrat              bigint,  -- IDcontrat
    type_releve             varchar(10),  -- TypeRelève
    releve                  integer,  -- Relève
    modif_op                bigint,  -- ModifOP
    modif_date              timestamp,  -- ModifDate
    modif_elem              varchar(5),  -- ModifELEM
    i_dcontrat_type_releve  varchar(18),  -- IDcontratTypeRelève
    CONSTRAINT pk_pgt_oen_contrat_compteur PRIMARY KEY (i_dcontrat_compteur)
);
CREATE INDEX ix_pgt_oen_contrat_compteur_i_dcontrat ON adv.pgt_oen_contrat_compteur (i_dcontrat);
CREATE INDEX ix_pgt_oen_contrat_compteur_type_releve ON adv.pgt_oen_contrat_compteur (type_releve);
CREATE INDEX ix_pgt_oen_contrat_compteur_modif_date ON adv.pgt_oen_contrat_compteur (modif_date);

CREATE TABLE adv.pgt_oen_contrat_option (
    i_dcontrat_option_auto      bigint,  -- IDcontratOptionAuto
    i_dcontrat                  bigint  NOT NULL,  -- IDcontrat
    num_bs                      text,  -- NumBS
    opt_mail                    boolean,  -- OPT_Mail
    opt_index_gaz               boolean,  -- OPT_IndexGaz
    opt_entretien               boolean,  -- OPT_Entretien
    opt_entretien_etat          integer,  -- OPT_Entretien_Etat
    opt_delai_retra             boolean,  -- OPT_DelaiRetra
    opt_index_elec              boolean,  -- OPT_IndexElec
    opt_hp_hc                   boolean,  -- OPT_HP_HC
    opt_energie_verte_gaz       boolean,  -- OPT_EnergieVerteGaz
    opt_energie_verte_elec      boolean,  -- OPT_EnergieVerteElec
    opt_deja_client_eni         boolean,  -- OPT_DejaClientENI
    opt_reforestation           boolean,  -- OPT_Reforestation
    opt_optin_commercial        boolean,  -- OPT_optinCommercial
    opt_e_facture               boolean,  -- OPT_eFacture
    opt_e_communication         boolean,  -- OPT_eCommunication
    opt_pdc                     boolean,  -- OPT_PDC
    opt_accept_com_parte        boolean,  -- OPT_AcceptComParte
    opt_consent_consult_distri  boolean,  -- OPT_ConsentConsultDistri
    opt_protection              boolean,  -- OPT_Protection
    modif_op                    bigint,  -- ModifOP
    modif_date                  timestamp,  -- ModifDate
    modif_elem                  varchar(5),  -- ModifELEM
    opt_vte_add_part            text,  -- OPT_VteAdd_Part
    CONSTRAINT pk_pgt_oen_contrat_option PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_oen_contrat_option_auto UNIQUE (i_dcontrat_option_auto)
);
CREATE INDEX ix_pgt_oen_contrat_option_num_bs ON adv.pgt_oen_contrat_option (num_bs);
CREATE INDEX ix_pgt_oen_contrat_option_opt_entretien ON adv.pgt_oen_contrat_option (opt_entretien);
CREATE INDEX ix_pgt_oen_contrat_option_opt_entretien_etat ON adv.pgt_oen_contrat_option (opt_entretien_etat);
CREATE INDEX ix_pgt_oen_contrat_option_modif_date ON adv.pgt_oen_contrat_option (modif_date);

CREATE TABLE adv.pgt_oen_contrat_remun (
    id_oen_contrat_remun_auto  bigint,  -- IDOEN_Contrat_RemunAuto
    id_oen_contrat_remun       bigint  NOT NULL,  -- IDOEN_Contrat_Remun
    i_dcontrat                 bigint,  -- IDcontrat
    num                        varchar(25),  -- NUM
    type_rem                   varchar(15),  -- TypeRem
    lib_option                 text,  -- Lib_Option
    validation                 boolean,  -- Validation
    va_mois_p                  varchar(7),  -- Va_MoisP
    va_montant                 numeric(19,4),  -- Va_Montant
    va_statut                  text,  -- Va_Statut
    va_motif                   text,  -- Va_Motif
    raccordement               boolean,  -- Raccordement
    ra_mois_p                  varchar(7),  -- Ra_MoisP
    ra_montant                 numeric(19,4),  -- Ra_Montant
    ra_statut                  text,  -- Ra_Statut
    ra_motif                   text,  -- Ra_Motif
    distri_paye_va             boolean,  -- Distri_PayéVa
    distri_paye_ra             boolean,  -- Distri_PayéRa
    modif_date                 timestamp,  -- ModifDATE
    modif_op                   bigint,  -- ModifOP
    modif_elem                 varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_oen_contrat_remun PRIMARY KEY (id_oen_contrat_remun),
    CONSTRAINT uq_pgt_oen_contrat_remun_auto UNIQUE (id_oen_contrat_remun_auto)
);
CREATE INDEX ix_pgt_oen_contrat_remun_i_dcontrat ON adv.pgt_oen_contrat_remun (i_dcontrat);
CREATE INDEX ix_pgt_oen_contrat_remun_num ON adv.pgt_oen_contrat_remun (num);
CREATE INDEX ix_pgt_oen_contrat_remun_modif_date ON adv.pgt_oen_contrat_remun (modif_date);

CREATE TABLE adv.pgt_oen_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_oen_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_oen_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_oen_etat_contrat_id_type_etat ON adv.pgt_oen_etat_contrat (id_type_etat);
CREATE INDEX ix_pgt_oen_etat_contrat_lib_etat ON adv.pgt_oen_etat_contrat (lib_etat);
CREATE INDEX ix_pgt_oen_etat_contrat_lib_etat_vend ON adv.pgt_oen_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_oen_etat_contrat_categorie ON adv.pgt_oen_etat_contrat (categorie);
CREATE INDEX ix_pgt_oen_etat_contrat_modif_date ON adv.pgt_oen_etat_contrat (modif_date);

CREATE TABLE adv.pgt_oen_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_oen_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_oen_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_oen_histo_attr_ctt_i_dcontrat ON adv.pgt_oen_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_oen_histo_attr_ctt_num ON adv.pgt_oen_histo_attr_ctt (num);
CREATE INDEX ix_pgt_oen_histo_attr_ctt_op_saisie ON adv.pgt_oen_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_oen_histo_attr_ctt_date ON adv.pgt_oen_histo_attr_ctt (date);
CREATE INDEX ix_pgt_oen_histo_attr_ctt_modif_date ON adv.pgt_oen_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_oen_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_oen_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_oen_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_oen_histo_etat_ctt_i_dcontrat ON adv.pgt_oen_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_oen_histo_etat_ctt_op_saisie ON adv.pgt_oen_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_oen_histo_etat_ctt_date ON adv.pgt_oen_histo_etat_ctt (date);
CREATE INDEX ix_pgt_oen_histo_etat_ctt_modif_date ON adv.pgt_oen_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_oen_histo_etat_ctt_oen (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_oen_histo_etat_ctt_oen PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_oen_histo_etat_ctt_oen_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_oen_histo_etat_ctt_oen_i_dcontrat ON adv.pgt_oen_histo_etat_ctt_oen (i_dcontrat);
CREATE INDEX ix_pgt_oen_histo_etat_ctt_oen_op_saisie ON adv.pgt_oen_histo_etat_ctt_oen (op_saisie);
CREATE INDEX ix_pgt_oen_histo_etat_ctt_oen_date ON adv.pgt_oen_histo_etat_ctt_oen (date);
CREATE INDEX ix_pgt_oen_histo_etat_ctt_oen_modif_date ON adv.pgt_oen_histo_etat_ctt_oen (modif_date);

CREATE TABLE adv.pgt_oen_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_oen_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_oen_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_oen_produit_lib_produit ON adv.pgt_oen_produit (lib_produit);
CREATE INDEX ix_pgt_oen_produit_prefixe_bdd ON adv.pgt_oen_produit (prefixe_bdd);
CREATE INDEX ix_pgt_oen_produit_famille ON adv.pgt_oen_produit (famille);
CREATE INDEX ix_pgt_oen_produit_sous_fam ON adv.pgt_oen_produit (sous_fam);
CREATE INDEX ix_pgt_oen_produit_pro_actif ON adv.pgt_oen_produit (pro_actif);
CREATE INDEX ix_pgt_oen_produit_id_type_prod_dec ON adv.pgt_oen_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_oen_produit_modif_date ON adv.pgt_oen_produit (modif_date);

CREATE TABLE adv.pgt_partenaire (
    id_partenaire   bigint,  -- IDPartenaire
    lib_partenaire  text,  -- Lib_Partenaire
    prefixe_bdd     text  NOT NULL,  -- PréfixeBDD
    logo            bytea,  -- LOGO
    date_debut      date,  -- DateDEBUT
    date_fin        date,  -- DateFIN
    is_actif        boolean,  -- IsActif
    couleur_r       smallint,  -- Couleur_R
    couleur_v       smallint,  -- Couleur_V
    couleur_b       smallint,  -- Couleur_B
    tk_call         boolean,  -- TkCall
    modif_date      timestamp,  -- ModifDate
    modif_op        smallint,  -- ModifOp
    modif_elem      text,  -- ModifElem
    CONSTRAINT pk_pgt_partenaire PRIMARY KEY (prefixe_bdd),
    CONSTRAINT uq_pgt_partenaire_auto UNIQUE (id_partenaire)
);
CREATE INDEX ix_pgt_partenaire_date_debut ON adv.pgt_partenaire (date_debut);
CREATE INDEX ix_pgt_partenaire_date_fin ON adv.pgt_partenaire (date_fin);
CREATE INDEX ix_pgt_partenaire_modif_date ON adv.pgt_partenaire (modif_date);

CREATE TABLE adv.pgt_pro_contrat (
    i_dcontrat_auto  bigint,  -- IDcontratAuto
    i_dcontrat       bigint  NOT NULL,  -- IDcontrat
    i_dclient        bigint,  -- IDclient
    id_salarie       bigint,  -- IDSalarie
    id_ste           bigint,  -- IdSte
    num_bs           text,  -- NumBS
    i_dproduit       integer,  -- IDproduit
    i_detat_contrat  integer,  -- IDetatContrat
    date_signature   date,  -- DateSignature
    date_resil       date,  -- DateRésil
    date_prem        date,  -- DatePrem
    info_partagee    text,  -- InfoPartagée
    info_interne     text,  -- InfoInterne
    mois_p           date,  -- MoisP
    op_saisie        bigint,  -- OPSAISIE
    date_saisie      timestamp,  -- DateSAISIE
    non_call         boolean,  -- NonCALL
    nb_points        double precision,  -- nbPoints
    code_enr         text,  -- CodeENR
    notation         numeric,  -- Notation
    notation_info    text,  -- NotationInfo
    modif_op         bigint,  -- ModifOP
    modif_date       timestamp,  -- ModifDate
    modif_elem       varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_pro_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_pro_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_pro_contrat_i_dclient ON adv.pgt_pro_contrat (i_dclient);
CREATE INDEX ix_pgt_pro_contrat_id_salarie ON adv.pgt_pro_contrat (id_salarie);
CREATE INDEX ix_pgt_pro_contrat_id_ste ON adv.pgt_pro_contrat (id_ste);
CREATE INDEX ix_pgt_pro_contrat_num_bs ON adv.pgt_pro_contrat (num_bs);
CREATE INDEX ix_pgt_pro_contrat_i_dproduit ON adv.pgt_pro_contrat (i_dproduit);
CREATE INDEX ix_pgt_pro_contrat_i_detat_contrat ON adv.pgt_pro_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_pro_contrat_date_signature ON adv.pgt_pro_contrat (date_signature);
CREATE INDEX ix_pgt_pro_contrat_op_saisie ON adv.pgt_pro_contrat (op_saisie);
CREATE INDEX ix_pgt_pro_contrat_date_saisie ON adv.pgt_pro_contrat (date_saisie);
CREATE INDEX ix_pgt_pro_contrat_modif_date ON adv.pgt_pro_contrat (modif_date);

CREATE TABLE adv.pgt_pro_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_pro_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_pro_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_pro_etat_contrat_id_type_etat ON adv.pgt_pro_etat_contrat (id_type_etat);
CREATE INDEX ix_pgt_pro_etat_contrat_lib_etat ON adv.pgt_pro_etat_contrat (lib_etat);
CREATE INDEX ix_pgt_pro_etat_contrat_lib_etat_vend ON adv.pgt_pro_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_pro_etat_contrat_categorie ON adv.pgt_pro_etat_contrat (categorie);
CREATE INDEX ix_pgt_pro_etat_contrat_modif_date ON adv.pgt_pro_etat_contrat (modif_date);

CREATE TABLE adv.pgt_pro_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_pro_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_pro_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_pro_histo_attr_ctt_i_dcontrat ON adv.pgt_pro_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_pro_histo_attr_ctt_num ON adv.pgt_pro_histo_attr_ctt (num);
CREATE INDEX ix_pgt_pro_histo_attr_ctt_op_saisie ON adv.pgt_pro_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_pro_histo_attr_ctt_date ON adv.pgt_pro_histo_attr_ctt (date);
CREATE INDEX ix_pgt_pro_histo_attr_ctt_modif_date ON adv.pgt_pro_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_pro_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_pro_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_pro_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_pro_histo_etat_ctt_i_dcontrat ON adv.pgt_pro_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_pro_histo_etat_ctt_op_saisie ON adv.pgt_pro_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_pro_histo_etat_ctt_date ON adv.pgt_pro_histo_etat_ctt (date);
CREATE INDEX ix_pgt_pro_histo_etat_ctt_modif_date ON adv.pgt_pro_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_pro_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_pro_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_pro_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_pro_produit_lib_produit ON adv.pgt_pro_produit (lib_produit);
CREATE INDEX ix_pgt_pro_produit_prefixe_bdd ON adv.pgt_pro_produit (prefixe_bdd);
CREATE INDEX ix_pgt_pro_produit_famille ON adv.pgt_pro_produit (famille);
CREATE INDEX ix_pgt_pro_produit_sous_fam ON adv.pgt_pro_produit (sous_fam);
CREATE INDEX ix_pgt_pro_produit_pro_actif ON adv.pgt_pro_produit (pro_actif);
CREATE INDEX ix_pgt_pro_produit_id_type_prod_dec ON adv.pgt_pro_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_pro_produit_modif_date ON adv.pgt_pro_produit (modif_date);

CREATE TABLE adv.pgt_pro_remun (
    id_remun_auto  bigint,  -- IDRemunAuto
    id_remun       bigint  NOT NULL,  -- IDRemun
    i_dproduit     integer,  -- IDproduit
    type_vente     smallint,  -- TypeVente
    date_debut     date,  -- DateDébut
    date_fin       date,  -- DateFin
    montant        numeric(19,4),  -- Montant
    nb_points      double precision,  -- nbPoints
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_pro_remun PRIMARY KEY (id_remun),
    CONSTRAINT uq_pgt_pro_remun_auto UNIQUE (id_remun_auto)
);
CREATE INDEX ix_pgt_pro_remun_i_dproduit ON adv.pgt_pro_remun (i_dproduit);
CREATE INDEX ix_pgt_pro_remun_date_debut ON adv.pgt_pro_remun (date_debut);
CREATE INDEX ix_pgt_pro_remun_modif_date ON adv.pgt_pro_remun (modif_date);

CREATE TABLE adv.pgt_sfr_cluster (
    id_sfr_cluster_auto  bigint,  -- IDSFR_ClusterAuto
    id_sfr_cluster       bigint  NOT NULL,  -- IDSFR_Cluster
    region               varchar(20),  -- Région
    code_vad             varchar(5),  -- CodeVAD
    nom_cluster          text,  -- NomCluster
    mail_bo              text,  -- MailBo
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOP
    modif_elem           varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_cluster PRIMARY KEY (id_sfr_cluster),
    CONSTRAINT uq_pgt_sfr_cluster_auto UNIQUE (id_sfr_cluster_auto)
);
CREATE INDEX ix_pgt_sfr_cluster_code_vad ON adv.pgt_sfr_cluster (code_vad);
CREATE INDEX ix_pgt_sfr_cluster_modif_date ON adv.pgt_sfr_cluster (modif_date);

CREATE TABLE adv.pgt_sfr_cluster_objectif (
    id_sfr_cluster_objectif  bigint,  -- IDSFR_ClusterObjectif
    obj_mois                 smallint,  -- ObjMois
    obj_annee                smallint,  -- ObjAnnée
    code_vad                 varchar(5),  -- CodeVAD
    id_resp                  bigint,  -- IDResp
    obj_ctt                  integer,  -- ObjCtt
    nb_ctt_brut              integer,  -- NbCttBrut
    nb_racc_sfr              smallint,  -- nbRaccSFR
    nb_fib_hors_att          integer,  -- nbFibHorsAtt
    nb_s1                    integer,  -- nbS1
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
);
CREATE INDEX ix_pgt_sfr_cluster_objectif_code_vad ON adv.pgt_sfr_cluster_objectif (code_vad);
CREATE INDEX ix_pgt_sfr_cluster_objectif_modif_date ON adv.pgt_sfr_cluster_objectif (modif_date);

CREATE TABLE adv.pgt_sfr_cluster_periode (
    id_sfr_cluster_periode  bigint  NOT NULL,  -- IDSFR_ClusterPériode
    id_sfr_cluster          bigint,  -- IDSFR_Cluster
    du                      date,  -- DU
    au                      date,  -- AU
    objectif_vv             integer,  -- ObjectifVV
    modif_date              timestamp,  -- ModifDate
    modif_op                bigint,  -- ModifOP
    modif_elem              varchar(5),  -- ModifELEM
    id_sfr_cluster_duau     varchar(24),  -- IDSFR_ClusterDUAU
    CONSTRAINT pk_pgt_sfr_cluster_periode PRIMARY KEY (id_sfr_cluster_periode)
);
CREATE INDEX ix_pgt_sfr_cluster_periode_id_sfr_cluster ON adv.pgt_sfr_cluster_periode (id_sfr_cluster);
CREATE INDEX ix_pgt_sfr_cluster_periode_modif_date ON adv.pgt_sfr_cluster_periode (modif_date);

CREATE TABLE adv.pgt_sfr_contrat (
    i_dcontrat_auto     bigint,  -- IDcontratAuto
    i_dcontrat          bigint  NOT NULL,  -- IDcontrat
    i_dclient           bigint,  -- IDclient
    id_salarie          bigint,  -- IDSalarie
    id_ste              bigint,  -- IdSte
    num_bs              text,  -- NumBS
    date_signature      date,  -- DateSignature
    date_validation     date,  -- DateValidation
    date_racc_activ     date,  -- DateRaccActiv
    portabilite         boolean,  -- Portabilité
    date_portabilite    date,  -- DatePortabilité
    date_rdv_tech       date,  -- DateRDVTech
    periode_rdv_tech    smallint,  -- PériodeRDVTech
    date_resil          date,  -- DateRésil
    id_sfr_cluster      bigint,  -- IDSFR_Cluster
    id_sfr_statut_rdv   bigint,  -- IdSFR_StatutRDV
    i_detat_contrat     integer,  -- IDetatContrat
    i_detat_sfr         integer,  -- IDetatSFR
    technologie         smallint,  -- Technologie
    i_dproduit          integer,  -- IDproduit
    self_install        boolean,  -- SelfInstall
    type_vente          smallint,  -- TypeVente
    offre_speciale      boolean,  -- OffreSpeciale
    box8                boolean,  -- Box8
    box8_verif          boolean,  -- Box8Vérif
    option_dec          boolean,  -- OptionDec
    option_verif        boolean,  -- OptionVérif
    mois_p_option       date,  -- MoisP_Option
    motif_annulation    text,  -- MotifAnnulation
    info_vente_sfr      text,  -- InfoVenteSFR
    info_interne        text,  -- InfoInterne
    op_saisie           bigint,  -- OPSAISIE
    date_saisie         timestamp,  -- DateSAISIE
    mois_p_va           date,  -- MoisP_Va
    nb_pts_payes_va     double precision,  -- nbPtsPayés_Va
    mois_p_ra           date,  -- MoisP_Ra
    nb_pts_payes_ra     double precision,  -- nbPtsPayés_Ra
    paye_va_distri      boolean,  -- PayeVaDistri
    mois_p_va_distri    date,  -- MoisP_VaDistri
    paye_ra_distri      boolean,  -- PayeRaDistri
    mois_p_ra_distri    date,  -- MoisP_RaDistri
    internet_garanti    boolean,  -- InternetGaranti
    mail_bo_envoye      boolean,  -- MailBoEnvoyé
    mail_bo_date_envoi  date,  -- MailBoDateEnvoi
    non_call            boolean,  -- NonCALL
    remise              boolean,  -- Remise
    booster_active      boolean,  -- BoosterActivé
    nb_points           double precision,  -- nbPoints
    import_j            boolean,  -- ImportJ
    hors_cible          boolean,  -- HorsCible
    notation            numeric,  -- Notation
    notation_info       text,  -- NotationInfo
    id_etat_call_ret    smallint,  -- IDEtatCallRet
    obs_call_ret        text,  -- ObsCallRet
    id_contrat_ret      bigint,  -- IDContratRET
    mob_propo_vend      boolean,  -- MobPropoVend
    intervention_vend   boolean,  -- InterventionVend
    issu_tk_diff        boolean,  -- IssuTkDiff
    rep_app_sfr         boolean,  -- RepAppSFR
    parcours_chaine     boolean,  -- ParcoursChainé
    parcours_degroupes  boolean,  -- ParcoursDégroupés
    prise_existante     boolean,  -- PriseExistante
    num_prise_sfr       varchar(25),  -- NumPrise_SFR
    prise_saisie        boolean,  -- PriseSaisie
    num_prise_vend      varchar(25),  -- NumPrise_Vend
    activ_control       text,  -- ActivControl
    processing_state    text,  -- ProcessingState
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_sfr_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_sfr_contrat_i_dclient ON adv.pgt_sfr_contrat (i_dclient);
CREATE INDEX ix_pgt_sfr_contrat_id_salarie ON adv.pgt_sfr_contrat (id_salarie);
CREATE INDEX ix_pgt_sfr_contrat_id_ste ON adv.pgt_sfr_contrat (id_ste);
CREATE INDEX ix_pgt_sfr_contrat_num_bs ON adv.pgt_sfr_contrat (num_bs);
CREATE INDEX ix_pgt_sfr_contrat_date_signature ON adv.pgt_sfr_contrat (date_signature);
CREATE INDEX ix_pgt_sfr_contrat_id_sfr_cluster ON adv.pgt_sfr_contrat (id_sfr_cluster);
CREATE INDEX ix_pgt_sfr_contrat_i_detat_contrat ON adv.pgt_sfr_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_sfr_contrat_i_detat_sfr ON adv.pgt_sfr_contrat (i_detat_sfr);
CREATE INDEX ix_pgt_sfr_contrat_i_dproduit ON adv.pgt_sfr_contrat (i_dproduit);
CREATE INDEX ix_pgt_sfr_contrat_op_saisie ON adv.pgt_sfr_contrat (op_saisie);
CREATE INDEX ix_pgt_sfr_contrat_date_saisie ON adv.pgt_sfr_contrat (date_saisie);
CREATE INDEX ix_pgt_sfr_contrat_id_etat_call_ret ON adv.pgt_sfr_contrat (id_etat_call_ret);
CREATE INDEX ix_pgt_sfr_contrat_id_contrat_ret ON adv.pgt_sfr_contrat (id_contrat_ret);
CREATE INDEX ix_pgt_sfr_contrat_modif_date ON adv.pgt_sfr_contrat (modif_date);

CREATE TABLE adv.pgt_sfr_contrat_remun (
    id_sfr_contrat_remun_auto  bigint,  -- IDSFR_Contrat_RemunAuto
    id_sfr_contrat_remun       bigint  NOT NULL,  -- IDSFR_Contrat_Remun
    i_dcontrat                 bigint,  -- IDcontrat
    num                        varchar(25),  -- NUM
    type_rem                   varchar(15),  -- TypeRem
    lib_option                 text,  -- Lib_Option
    validation                 boolean,  -- Validation
    va_mois_p                  varchar(7),  -- Va_MoisP
    va_montant                 numeric(19,4),  -- Va_Montant
    va_statut                  text,  -- Va_Statut
    va_motif                   text,  -- Va_Motif
    raccordement               boolean,  -- Raccordement
    ra_mois_p                  varchar(7),  -- Ra_MoisP
    ra_montant                 numeric(19,4),  -- Ra_Montant
    ra_statut                  text,  -- Ra_Statut
    ra_motif                   text,  -- Ra_Motif
    distri_paye_va             boolean,  -- Distri_PayéVa
    distri_paye_ra             boolean,  -- Distri_PayéRa
    modif_date                 timestamp,  -- ModifDATE
    modif_op                   bigint,  -- ModifOP
    modif_elem                 varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_contrat_remun PRIMARY KEY (id_sfr_contrat_remun),
    CONSTRAINT uq_pgt_sfr_contrat_remun_auto UNIQUE (id_sfr_contrat_remun_auto)
);
CREATE INDEX ix_pgt_sfr_contrat_remun_i_dcontrat ON adv.pgt_sfr_contrat_remun (i_dcontrat);
CREATE INDEX ix_pgt_sfr_contrat_remun_num ON adv.pgt_sfr_contrat_remun (num);
CREATE INDEX ix_pgt_sfr_contrat_remun_modif_date ON adv.pgt_sfr_contrat_remun (modif_date);

CREATE TABLE adv.pgt_sfr_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_sfr_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_sfr_etat_contrat_id_type_etat ON adv.pgt_sfr_etat_contrat (id_type_etat);
CREATE INDEX ix_pgt_sfr_etat_contrat_lib_etat ON adv.pgt_sfr_etat_contrat (lib_etat);
CREATE INDEX ix_pgt_sfr_etat_contrat_lib_etat_vend ON adv.pgt_sfr_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_sfr_etat_contrat_categorie ON adv.pgt_sfr_etat_contrat (categorie);
CREATE INDEX ix_pgt_sfr_etat_contrat_modif_date ON adv.pgt_sfr_etat_contrat (modif_date);

CREATE TABLE adv.pgt_sfr_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_sfr_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_sfr_histo_attr_ctt_i_dcontrat ON adv.pgt_sfr_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_sfr_histo_attr_ctt_num ON adv.pgt_sfr_histo_attr_ctt (num);
CREATE INDEX ix_pgt_sfr_histo_attr_ctt_op_saisie ON adv.pgt_sfr_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_sfr_histo_attr_ctt_date ON adv.pgt_sfr_histo_attr_ctt (date);
CREATE INDEX ix_pgt_sfr_histo_attr_ctt_modif_date ON adv.pgt_sfr_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_sfr_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_sfr_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_sfr_histo_etat_ctt_i_dcontrat ON adv.pgt_sfr_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_sfr_histo_etat_ctt_op_saisie ON adv.pgt_sfr_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_sfr_histo_etat_ctt_date ON adv.pgt_sfr_histo_etat_ctt (date);
CREATE INDEX ix_pgt_sfr_histo_etat_ctt_modif_date ON adv.pgt_sfr_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_sfr_histo_etat_ctt_sfr (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_histo_etat_ctt_sfr PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_sfr_histo_etat_ctt_sfr_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_sfr_histo_etat_ctt_sfr_i_dcontrat ON adv.pgt_sfr_histo_etat_ctt_sfr (i_dcontrat);
CREATE INDEX ix_pgt_sfr_histo_etat_ctt_sfr_op_saisie ON adv.pgt_sfr_histo_etat_ctt_sfr (op_saisie);
CREATE INDEX ix_pgt_sfr_histo_etat_ctt_sfr_date ON adv.pgt_sfr_histo_etat_ctt_sfr (date);
CREATE INDEX ix_pgt_sfr_histo_etat_ctt_sfr_modif_date ON adv.pgt_sfr_histo_etat_ctt_sfr (modif_date);

CREATE TABLE adv.pgt_sfr_offres_provad (
    id_offres_sfr_auto  bigint,  -- IDOffres_SFRAuto
    id_offres_sfr       bigint  NOT NULL,  -- IDOffres_SFR
    type                varchar(8),  -- Type
    lib_offre           varchar(50),  -- Lib_Offre
    debit_down          varchar(20),  -- DebitDown
    debit_up            varchar(20),  -- DebitUp
    prix_offre          numeric(19,4),  -- PrixOffre
    recurrence          varchar(10),  -- Recurrence
    prix_pro_ttc        text,  -- PrixProTTC
    engagement          text,  -- Engagement
    en_promo            boolean,  -- EnPromo
    info_promo          text,  -- InfoPromo
    service_inclus      text,  -- ServiceInclus
    i_dproduit          integer,  -- IDproduit
    online              boolean,  -- Online
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_offres_provad PRIMARY KEY (id_offres_sfr),
    CONSTRAINT uq_pgt_sfr_offres_provad_auto UNIQUE (id_offres_sfr_auto)
);
CREATE INDEX ix_pgt_sfr_offres_provad_type ON adv.pgt_sfr_offres_provad (type);
CREATE INDEX ix_pgt_sfr_offres_provad_lib_offre ON adv.pgt_sfr_offres_provad (lib_offre);
CREATE INDEX ix_pgt_sfr_offres_provad_i_dproduit ON adv.pgt_sfr_offres_provad (i_dproduit);
CREATE INDEX ix_pgt_sfr_offres_provad_modif_date ON adv.pgt_sfr_offres_provad (modif_date);

CREATE TABLE adv.pgt_sfr_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_sfr_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_sfr_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_sfr_produit_lib_produit ON adv.pgt_sfr_produit (lib_produit);
CREATE INDEX ix_pgt_sfr_produit_prefixe_bdd ON adv.pgt_sfr_produit (prefixe_bdd);
CREATE INDEX ix_pgt_sfr_produit_famille ON adv.pgt_sfr_produit (famille);
CREATE INDEX ix_pgt_sfr_produit_sous_fam ON adv.pgt_sfr_produit (sous_fam);
CREATE INDEX ix_pgt_sfr_produit_pro_actif ON adv.pgt_sfr_produit (pro_actif);
CREATE INDEX ix_pgt_sfr_produit_id_type_prod_dec ON adv.pgt_sfr_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_sfr_produit_modif_date ON adv.pgt_sfr_produit (modif_date);

CREATE TABLE adv.pgt_sfr_remun (
    id_sfr_remun_auto  bigint,  -- IDSFR_RemunAuto
    id_sfr_remun       bigint  NOT NULL,  -- IDSFR_Remun
    categorie          varchar(15),  -- Catégorie
    i_dproduit         integer,  -- IDproduit
    type_vente         smallint,  -- TypeVente
    date_debut         date,  -- DateDébut
    date_fin           date,  -- DateFin
    montant_va         numeric(19,4),  -- MontantVa
    montant_va_remise  numeric(19,4),  -- MontantVa_Remise
    montant_ra         numeric(19,4),  -- MontantRa
    montant_ra_remise  numeric(19,4),  -- MontantRa_Remise
    prime_volumique    numeric(19,4),  -- PrimeVolumique
    abonnement_tv      numeric(19,4),  -- Abonnement_TV
    type_repart_rem    smallint,  -- TypeRépartRem
    modif_op           bigint,  -- ModifOP
    modif_date         timestamp,  -- ModifDate
    modif_elem         varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_sfr_remun PRIMARY KEY (id_sfr_remun),
    CONSTRAINT uq_pgt_sfr_remun_auto UNIQUE (id_sfr_remun_auto)
);
CREATE INDEX ix_pgt_sfr_remun_categorie ON adv.pgt_sfr_remun (categorie);
CREATE INDEX ix_pgt_sfr_remun_i_dproduit ON adv.pgt_sfr_remun (i_dproduit);
CREATE INDEX ix_pgt_sfr_remun_date_debut ON adv.pgt_sfr_remun (date_debut);
CREATE INDEX ix_pgt_sfr_remun_modif_date ON adv.pgt_sfr_remun (modif_date);

CREATE TABLE adv.pgt_sfr_statut_rdv (
    id_sfr_statut_rdv_auto  bigint,  -- IdSFR_StatutRDVAuto
    id_sfr_statut_rdv       bigint  NOT NULL,  -- IdSFR_StatutRDV
    lib_statut              varchar(50),  -- LibStatut
    couleur_r               smallint,  -- Couleur_R
    couleur_v               smallint,  -- Couleur_V
    couleur_b               smallint,  -- Couleur_B
    modif_date              timestamp,  -- ModifDate
    modif_op                bigint,  -- ModifOp
    modif_elem              varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_sfr_statut_rdv PRIMARY KEY (id_sfr_statut_rdv),
    CONSTRAINT uq_pgt_sfr_statut_rdv_auto UNIQUE (id_sfr_statut_rdv_auto)
);
CREATE INDEX ix_pgt_sfr_statut_rdv_modif_date ON adv.pgt_sfr_statut_rdv (modif_date);

CREATE TABLE adv.pgt_statventes (
    id_stat_ventes                                              bigint  NOT NULL,  -- IDStatVentes
    annee                                                       smallint,  -- Année
    num_sem                                                     smallint,  -- NumSem
    date_deb                                                    date,  -- DateDeb
    date_fin                                                    date,  -- DateFin
    id_salarie                                                  bigint,  -- IDSalarie
    id_organigramme                                             bigint,  -- IDOrganigramme
    annee_num_sem_id_organigramme                               varchar(11),  -- AnnéeNumSemIDOrganigramme
    annee_num_sem_id_salarie_id_organigramme                    varchar(19),  -- AnnéeNumSemIDSalarieIDOrganigramme
    annee_num_sem_id_salarie_id_organigramme_date_deb_date_fin  varchar(35),  -- AnnéeNumSemIDSalarieIDOrganigrammeDateDebDateFin
    nb_fixe_brut_hors_tk                                        integer,  -- nbFixeBrutHorsTK
    nb_fixe_cq                                                  integer,  -- nbFixeCQ
    nb_prem_brut                                                integer,  -- nbPremBrut
    nb_fixe_cq2                                                 integer,  -- nbFixeCQ2
    nb_fixe_cq1                                                 integer,  -- nbFixeCQ1
    nb_fixe_hors_attente_sfr                                    integer,  -- nbFixeHorsAttenteSFR
    nb_racc_sfr                                                 integer,  -- nbRaccSFR
    nb_racc_vend                                                integer,  -- nbRaccVend
    nb_fixe_hors_attente_vend                                   integer,  -- nbFixeHorsAttenteVend
    nb_fixe_resil                                               integer,  -- nbFixeRésil
    nb_fixe_cq_brut                                             integer,  -- nbFixeCQBrut
    nb_fixe_dg_brut                                             integer,  -- nbFixeDGBrut
    nb_fixe_cq_porta                                            integer,  -- nbFixeCQPorta
    nb_fixe_cq_racc                                             integer,  -- nbFixeCqRacc
    nb_fixe_cq_resil30j                                         integer,  -- nbFixeCqResil30j
    nb_prise_saisie                                             integer,  -- nbPriseSaisie
    nb_prise_existante                                          integer,  -- nbPriseExistante
    nb_mob_brut_hors_tk                                         integer,  -- nbMobBrutHorsTK
    nb_forfait_sup                                              integer,  -- nbForfaitSup
    nb_mob_hors_attente                                         integer,  -- nbMobHorsAttente
    nb_mob_active                                               integer,  -- nbMobActivé
    nb_pc                                                       integer,  -- nbPC
    nb4_p                                                       integer,  -- nb4P
    nb_mob_cq_active                                            integer,  -- nbMobCqActive
    nb_mob_cq_resil30j                                          integer,  -- nbMobCqResil30j
    note_tot                                                    double precision,  -- NoteTot
    nb_ctt_note                                                 integer,  -- nbCttNoté
    nb_coopt                                                    integer,  -- nbCoopt
    modif_date                                                  timestamp,  -- ModifDate
    modif_op                                                    bigint,  -- ModifOp
    modif_elem                                                  varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_statventes PRIMARY KEY (id_stat_ventes)
);
CREATE INDEX ix_pgt_statventes_id_salarie ON adv.pgt_statventes (id_salarie);
CREATE INDEX ix_pgt_statventes_modif_date ON adv.pgt_statventes (modif_date);

CREATE TABLE adv.pgt_str_contrat (
    i_dcontrat_auto  bigint,  -- IDcontratAuto
    i_dcontrat       bigint  NOT NULL,  -- IDcontrat
    i_dclient        bigint,  -- IDclient
    id_salarie       bigint,  -- IDSalarie
    id_ste           bigint,  -- IdSte
    num_bs           text,  -- NumBS
    i_dproduit       integer,  -- IDproduit
    i_detat_contrat  integer,  -- IDetatContrat
    date_signature   date,  -- DateSignature
    info_partagee    text,  -- InfoPartagée
    info_interne     text,  -- InfoInterne
    mois_p           date,  -- MoisP
    op_saisie        bigint,  -- OPSAISIE
    date_saisie      timestamp,  -- DateSAISIE
    non_call         boolean,  -- NonCALL
    nb_points        double precision,  -- nbPoints
    code_enr         text,  -- CodeENR
    opt_mandat       boolean,  -- Opt_Mandat
    notation         numeric,  -- Notation
    notation_info    text,  -- NotationInfo
    modif_op         bigint,  -- ModifOp
    modif_date       timestamp,  -- ModifDate
    modif_elem       varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_str_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_str_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_str_contrat_i_dclient ON adv.pgt_str_contrat (i_dclient);
CREATE INDEX ix_pgt_str_contrat_id_salarie ON adv.pgt_str_contrat (id_salarie);
CREATE INDEX ix_pgt_str_contrat_id_ste ON adv.pgt_str_contrat (id_ste);
CREATE INDEX ix_pgt_str_contrat_num_bs ON adv.pgt_str_contrat (num_bs);
CREATE INDEX ix_pgt_str_contrat_i_dproduit ON adv.pgt_str_contrat (i_dproduit);
CREATE INDEX ix_pgt_str_contrat_i_detat_contrat ON adv.pgt_str_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_str_contrat_date_signature ON adv.pgt_str_contrat (date_signature);
CREATE INDEX ix_pgt_str_contrat_op_saisie ON adv.pgt_str_contrat (op_saisie);
CREATE INDEX ix_pgt_str_contrat_date_saisie ON adv.pgt_str_contrat (date_saisie);
CREATE INDEX ix_pgt_str_contrat_modif_date ON adv.pgt_str_contrat (modif_date);

CREATE TABLE adv.pgt_str_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_str_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_str_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_str_etat_contrat_id_type_etat ON adv.pgt_str_etat_contrat (id_type_etat);
CREATE INDEX ix_pgt_str_etat_contrat_lib_etat ON adv.pgt_str_etat_contrat (lib_etat);
CREATE INDEX ix_pgt_str_etat_contrat_lib_etat_vend ON adv.pgt_str_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_str_etat_contrat_categorie ON adv.pgt_str_etat_contrat (categorie);
CREATE INDEX ix_pgt_str_etat_contrat_modif_date ON adv.pgt_str_etat_contrat (modif_date);

CREATE TABLE adv.pgt_str_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_str_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_str_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_str_histo_attr_ctt_i_dcontrat ON adv.pgt_str_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_str_histo_attr_ctt_num ON adv.pgt_str_histo_attr_ctt (num);
CREATE INDEX ix_pgt_str_histo_attr_ctt_op_saisie ON adv.pgt_str_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_str_histo_attr_ctt_date ON adv.pgt_str_histo_attr_ctt (date);
CREATE INDEX ix_pgt_str_histo_attr_ctt_modif_date ON adv.pgt_str_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_str_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_str_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_str_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_str_histo_etat_ctt_i_dcontrat ON adv.pgt_str_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_str_histo_etat_ctt_op_saisie ON adv.pgt_str_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_str_histo_etat_ctt_date ON adv.pgt_str_histo_etat_ctt (date);
CREATE INDEX ix_pgt_str_histo_etat_ctt_modif_date ON adv.pgt_str_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_str_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_str_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_str_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_str_produit_lib_produit ON adv.pgt_str_produit (lib_produit);
CREATE INDEX ix_pgt_str_produit_prefixe_bdd ON adv.pgt_str_produit (prefixe_bdd);
CREATE INDEX ix_pgt_str_produit_famille ON adv.pgt_str_produit (famille);
CREATE INDEX ix_pgt_str_produit_sous_fam ON adv.pgt_str_produit (sous_fam);
CREATE INDEX ix_pgt_str_produit_pro_actif ON adv.pgt_str_produit (pro_actif);
CREATE INDEX ix_pgt_str_produit_id_type_prod_dec ON adv.pgt_str_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_str_produit_modif_date ON adv.pgt_str_produit (modif_date);

CREATE TABLE adv.pgt_str_remun (
    id_remun_auto  bigint,  -- IDRemunAuto
    id_remun       bigint  NOT NULL,  -- IDRemun
    i_dproduit     integer,  -- IDproduit
    type_vente     smallint,  -- TypeVente
    date_debut     date,  -- DateDébut
    date_fin       date,  -- DateFin
    montant        numeric(19,4),  -- Montant
    nb_points      double precision,  -- nbPoints
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_str_remun PRIMARY KEY (id_remun),
    CONSTRAINT uq_pgt_str_remun_auto UNIQUE (id_remun_auto)
);
CREATE INDEX ix_pgt_str_remun_i_dproduit ON adv.pgt_str_remun (i_dproduit);
CREATE INDEX ix_pgt_str_remun_date_debut ON adv.pgt_str_remun (date_debut);
CREATE INDEX ix_pgt_str_remun_modif_date ON adv.pgt_str_remun (modif_date);

CREATE TABLE adv.pgt_tdb_qualite (
    id_tdb_qualite  bigint  NOT NULL,  -- IDTDB_Qualité
    date            date,  -- Date
    id_salarie      bigint,  -- IDSalarie
    en_ligne        boolean,  -- EnLigne
    modif_op        bigint,  -- ModifOp
    modif_date      timestamp,  -- ModifDate
    modif_elem      varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tdb_qualite PRIMARY KEY (id_tdb_qualite)
);
CREATE INDEX ix_pgt_tdb_qualite_id_salarie ON adv.pgt_tdb_qualite (id_salarie);
CREATE INDEX ix_pgt_tdb_qualite_modif_date ON adv.pgt_tdb_qualite (modif_date);

CREATE TABLE adv.pgt_tdb_qualite_contrat (
    id_tdb_qualite_contrat  bigint  NOT NULL,  -- IDTDB_QualitéContrat
    id_tdb_qualite          bigint,  -- IDTDB_Qualité
    i_dcontrat              bigint,  -- IDcontrat
    part                    varchar(4),  -- Part
    i_detat_contrat         integer,  -- IDetatContrat
    modif_date              timestamp,  -- ModifDate
    modif_op                bigint,  -- ModifOp
    modif_elem              varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tdb_qualite_contrat PRIMARY KEY (id_tdb_qualite_contrat)
);
CREATE INDEX ix_pgt_tdb_qualite_contrat_id_tdb_qualite ON adv.pgt_tdb_qualite_contrat (id_tdb_qualite);
CREATE INDEX ix_pgt_tdb_qualite_contrat_i_dcontrat ON adv.pgt_tdb_qualite_contrat (i_dcontrat);
CREATE INDEX ix_pgt_tdb_qualite_contrat_i_detat_contrat ON adv.pgt_tdb_qualite_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_tdb_qualite_contrat_modif_date ON adv.pgt_tdb_qualite_contrat (modif_date);

CREATE TABLE adv.pgt_tlc_contrat (
    i_dcontrat_auto  bigint,  -- IDcontratAuto
    i_dcontrat       bigint  NOT NULL,  -- IDcontrat
    i_dclient        bigint,  -- IDclient
    id_salarie       bigint,  -- IDSalarie
    id_ste           bigint,  -- IdSte
    num_bs           text,  -- NumBS
    i_dproduit       integer,  -- IDproduit
    i_detat_contrat  integer,  -- IDetatContrat
    date_signature   date,  -- DateSignature
    info_partagee    text,  -- InfoPartagée
    info_interne     text,  -- InfoInterne
    mois_p           date,  -- MoisP
    op_saisie        bigint,  -- OPSAISIE
    date_saisie      timestamp,  -- DateSAISIE
    non_call         boolean,  -- NonCALL
    nb_points        double precision,  -- nbPoints
    code_enr         text,  -- CodeENR
    notation         numeric,  -- Notation
    notation_info    text,  -- NotationInfo
    modif_op         bigint,  -- ModifOP
    modif_date       timestamp,  -- ModifDate
    modif_elem       varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tlc_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_tlc_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_tlc_contrat_i_dclient ON adv.pgt_tlc_contrat (i_dclient);
CREATE INDEX ix_pgt_tlc_contrat_id_salarie ON adv.pgt_tlc_contrat (id_salarie);
CREATE INDEX ix_pgt_tlc_contrat_id_ste ON adv.pgt_tlc_contrat (id_ste);
CREATE INDEX ix_pgt_tlc_contrat_num_bs ON adv.pgt_tlc_contrat (num_bs);
CREATE INDEX ix_pgt_tlc_contrat_i_dproduit ON adv.pgt_tlc_contrat (i_dproduit);
CREATE INDEX ix_pgt_tlc_contrat_i_detat_contrat ON adv.pgt_tlc_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_tlc_contrat_date_signature ON adv.pgt_tlc_contrat (date_signature);
CREATE INDEX ix_pgt_tlc_contrat_op_saisie ON adv.pgt_tlc_contrat (op_saisie);
CREATE INDEX ix_pgt_tlc_contrat_date_saisie ON adv.pgt_tlc_contrat (date_saisie);
CREATE INDEX ix_pgt_tlc_contrat_modif_date ON adv.pgt_tlc_contrat (modif_date);

CREATE TABLE adv.pgt_tlc_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tlc_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_tlc_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_tlc_etat_contrat_lib_etat_vend ON adv.pgt_tlc_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_tlc_etat_contrat_categorie ON adv.pgt_tlc_etat_contrat (categorie);
CREATE INDEX ix_pgt_tlc_etat_contrat_modif_date ON adv.pgt_tlc_etat_contrat (modif_date);

CREATE TABLE adv.pgt_tlc_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tlc_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_tlc_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_tlc_histo_attr_ctt_i_dcontrat ON adv.pgt_tlc_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_tlc_histo_attr_ctt_num ON adv.pgt_tlc_histo_attr_ctt (num);
CREATE INDEX ix_pgt_tlc_histo_attr_ctt_op_saisie ON adv.pgt_tlc_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_tlc_histo_attr_ctt_date ON adv.pgt_tlc_histo_attr_ctt (date);
CREATE INDEX ix_pgt_tlc_histo_attr_ctt_modif_date ON adv.pgt_tlc_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_tlc_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tlc_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_tlc_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_tlc_histo_etat_ctt_i_dcontrat ON adv.pgt_tlc_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_tlc_histo_etat_ctt_op_saisie ON adv.pgt_tlc_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_tlc_histo_etat_ctt_date ON adv.pgt_tlc_histo_etat_ctt (date);
CREATE INDEX ix_pgt_tlc_histo_etat_ctt_modif_date ON adv.pgt_tlc_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_tlc_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_tlc_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_tlc_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_tlc_produit_lib_produit ON adv.pgt_tlc_produit (lib_produit);
CREATE INDEX ix_pgt_tlc_produit_prefixe_bdd ON adv.pgt_tlc_produit (prefixe_bdd);
CREATE INDEX ix_pgt_tlc_produit_famille ON adv.pgt_tlc_produit (famille);
CREATE INDEX ix_pgt_tlc_produit_sous_fam ON adv.pgt_tlc_produit (sous_fam);
CREATE INDEX ix_pgt_tlc_produit_pro_actif ON adv.pgt_tlc_produit (pro_actif);
CREATE INDEX ix_pgt_tlc_produit_id_type_prod_dec ON adv.pgt_tlc_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_tlc_produit_modif_date ON adv.pgt_tlc_produit (modif_date);

CREATE TABLE adv.pgt_tlc_remun (
    id_remun_auto  bigint,  -- IDRemunAuto
    id_remun       bigint  NOT NULL,  -- IDRemun
    i_dproduit     integer,  -- IDproduit
    type_vente     smallint,  -- TypeVente
    date_debut     date,  -- DateDébut
    date_fin       date,  -- DateFin
    montant        numeric(19,4),  -- Montant
    nb_points      double precision,  -- nbPoints
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tlc_remun PRIMARY KEY (id_remun),
    CONSTRAINT uq_pgt_tlc_remun_auto UNIQUE (id_remun_auto)
);
CREATE INDEX ix_pgt_tlc_remun_i_dproduit ON adv.pgt_tlc_remun (i_dproduit);
CREATE INDEX ix_pgt_tlc_remun_date_debut ON adv.pgt_tlc_remun (date_debut);
CREATE INDEX ix_pgt_tlc_remun_modif_date ON adv.pgt_tlc_remun (modif_date);

CREATE TABLE adv.pgt_type_etat_contrat (
    id_type_etat_contrat_auto  bigint,  -- IDTypeEtatContratAuto
    id_type_etat               smallint  NOT NULL,  -- IDTypeEtat
    lib_type                   varchar(20),  -- LibType
    couleur_r                  smallint,  -- Couleur_R
    couleur_v                  smallint,  -- Couleur_V
    couleur_b                  smallint,  -- Couleur_B
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOp
    modif_elem                 varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_etat_contrat PRIMARY KEY (id_type_etat),
    CONSTRAINT uq_pgt_type_etat_contrat_auto UNIQUE (id_type_etat_contrat_auto)
);
CREATE INDEX ix_pgt_type_etat_contrat_modif_date ON adv.pgt_type_etat_contrat (modif_date);

CREATE TABLE adv.pgt_type_prod_dec (
    id_type_prod_dec_auto       bigint,  -- IDTypeProdDecAuto
    id_type_prod_dec            bigint  NOT NULL,  -- IdTypeProdDec
    lib_type_prod_dec           varchar(20),  -- LibTypeProdDec
    prod_actif                  boolean,  -- ProdActif
    prefixe_bdd                 varchar(5),  -- PréfixeBDD
    a_comptabilise_dans_tot_bs  boolean,  -- AComptabiliséDansTotBS
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOp
    modif_elem                  varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_prod_dec PRIMARY KEY (id_type_prod_dec),
    CONSTRAINT uq_pgt_type_prod_dec_auto UNIQUE (id_type_prod_dec_auto)
);
CREATE INDEX ix_pgt_type_prod_dec_lib_type_prod_dec ON adv.pgt_type_prod_dec (lib_type_prod_dec);
CREATE INDEX ix_pgt_type_prod_dec_prod_actif ON adv.pgt_type_prod_dec (prod_actif);
CREATE INDEX ix_pgt_type_prod_dec_prefixe_bdd ON adv.pgt_type_prod_dec (prefixe_bdd);
CREATE INDEX ix_pgt_type_prod_dec_modif_date ON adv.pgt_type_prod_dec (modif_date);

CREATE TABLE adv.pgt_val_contrat (
    i_dcontrat_auto   bigint,  -- IDcontratAuto
    i_dcontrat        bigint  NOT NULL,  -- IDcontrat
    i_dclient         bigint,  -- IDclient
    id_salarie        bigint,  -- IDSalarie
    id_ste            bigint,  -- IdSte
    num_bs            text,  -- NumBS
    num_bs_associe    text,  -- NumBSAssocié
    i_dproduit        integer,  -- IDproduit
    i_detat_contrat   integer,  -- IDetatContrat
    date_signature    date,  -- DateSignature
    info_partagee     text,  -- InfoPartagée
    info_interne      text,  -- InfoInterne
    mois_p            date,  -- MoisP
    op_saisie         bigint,  -- OPSAISIE
    date_saisie       timestamp,  -- DateSAISIE
    non_call          boolean,  -- NonCALL
    nb_points         double precision,  -- nbPoints
    code_enr          text,  -- CodeENR
    format_numerique  boolean,  -- FormatNumérique
    notation          numeric,  -- Notation
    notation_info     text,  -- NotationInfo
    modif_op          bigint,  -- ModifOp
    modif_date        timestamp,  -- ModifDate
    modif_elem        varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_val_contrat PRIMARY KEY (i_dcontrat),
    CONSTRAINT uq_pgt_val_contrat_auto UNIQUE (i_dcontrat_auto)
);
CREATE INDEX ix_pgt_val_contrat_i_dclient ON adv.pgt_val_contrat (i_dclient);
CREATE INDEX ix_pgt_val_contrat_id_salarie ON adv.pgt_val_contrat (id_salarie);
CREATE INDEX ix_pgt_val_contrat_id_ste ON adv.pgt_val_contrat (id_ste);
CREATE INDEX ix_pgt_val_contrat_num_bs ON adv.pgt_val_contrat (num_bs);
CREATE INDEX ix_pgt_val_contrat_num_bs_associe ON adv.pgt_val_contrat (num_bs_associe);
CREATE INDEX ix_pgt_val_contrat_i_dproduit ON adv.pgt_val_contrat (i_dproduit);
CREATE INDEX ix_pgt_val_contrat_i_detat_contrat ON adv.pgt_val_contrat (i_detat_contrat);
CREATE INDEX ix_pgt_val_contrat_date_signature ON adv.pgt_val_contrat (date_signature);
CREATE INDEX ix_pgt_val_contrat_op_saisie ON adv.pgt_val_contrat (op_saisie);
CREATE INDEX ix_pgt_val_contrat_date_saisie ON adv.pgt_val_contrat (date_saisie);
CREATE INDEX ix_pgt_val_contrat_modif_date ON adv.pgt_val_contrat (modif_date);

CREATE TABLE adv.pgt_val_etat_contrat (
    i_detat_auto   bigint,  -- IDetatAuto
    i_detat        integer  NOT NULL,  -- IDetat
    id_type_etat   smallint,  -- IDTypeEtat
    lib_etat       text,  -- Lib_Etat
    lib_etat_vend  text,  -- Lib_EtatVend
    categorie      varchar(10),  -- Catégorie
    modif_date     timestamp,  -- ModifDate
    modif_op       bigint,  -- ModifOP
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_val_etat_contrat PRIMARY KEY (i_detat),
    CONSTRAINT uq_pgt_val_etat_contrat_auto UNIQUE (i_detat_auto)
);
CREATE INDEX ix_pgt_val_etat_contrat_id_type_etat ON adv.pgt_val_etat_contrat (id_type_etat);
CREATE INDEX ix_pgt_val_etat_contrat_lib_etat ON adv.pgt_val_etat_contrat (lib_etat);
CREATE INDEX ix_pgt_val_etat_contrat_lib_etat_vend ON adv.pgt_val_etat_contrat (lib_etat_vend);
CREATE INDEX ix_pgt_val_etat_contrat_categorie ON adv.pgt_val_etat_contrat (categorie);
CREATE INDEX ix_pgt_val_etat_contrat_modif_date ON adv.pgt_val_etat_contrat (modif_date);

CREATE TABLE adv.pgt_val_histo_attr_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    type_ctt       varchar(20),  -- TypeCtt
    i_dcontrat     bigint,  -- IDcontrat
    num            varchar(25),  -- NUM
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    vendeur_old    bigint,  -- VendeurOld
    vendeur_new    bigint,  -- VendeurNew
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_val_histo_attr_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_val_histo_attr_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_val_histo_attr_ctt_i_dcontrat ON adv.pgt_val_histo_attr_ctt (i_dcontrat);
CREATE INDEX ix_pgt_val_histo_attr_ctt_num ON adv.pgt_val_histo_attr_ctt (num);
CREATE INDEX ix_pgt_val_histo_attr_ctt_op_saisie ON adv.pgt_val_histo_attr_ctt (op_saisie);
CREATE INDEX ix_pgt_val_histo_attr_ctt_date ON adv.pgt_val_histo_attr_ctt (date);
CREATE INDEX ix_pgt_val_histo_attr_ctt_modif_date ON adv.pgt_val_histo_attr_ctt (modif_date);

CREATE TABLE adv.pgt_val_histo_etat_ctt (
    id_histo_auto  bigint,  -- idHistoAuto
    id_histo       bigint  NOT NULL,  -- idHisto
    i_dcontrat     bigint,  -- IDcontrat
    op_saisie      bigint,  -- OPSAISIE
    date           timestamp,  -- DATE
    old_etat       bigint,  -- OLD_etat
    new_etat       bigint,  -- NEW_etat
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    date_paiement  varchar(7),  -- DATEPAIEMENT
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_val_histo_etat_ctt PRIMARY KEY (id_histo),
    CONSTRAINT uq_pgt_val_histo_etat_ctt_auto UNIQUE (id_histo_auto)
);
CREATE INDEX ix_pgt_val_histo_etat_ctt_i_dcontrat ON adv.pgt_val_histo_etat_ctt (i_dcontrat);
CREATE INDEX ix_pgt_val_histo_etat_ctt_op_saisie ON adv.pgt_val_histo_etat_ctt (op_saisie);
CREATE INDEX ix_pgt_val_histo_etat_ctt_date ON adv.pgt_val_histo_etat_ctt (date);
CREATE INDEX ix_pgt_val_histo_etat_ctt_modif_date ON adv.pgt_val_histo_etat_ctt (modif_date);

CREATE TABLE adv.pgt_val_produit (
    i_dproduit_auto              bigint,  -- IDproduitAuto
    i_dproduit                   integer  NOT NULL,  -- IDproduit
    lib_produit                  text,  -- Lib_produit
    prefixe_bdd                  varchar(5),  -- PréfixeBDD
    famille                      varchar(10),  -- Famille
    sous_fam                     varchar(10),  -- SousFAM
    pro_actif                    smallint,  -- pro_ACTIF
    logo                         bytea,  -- Logo
    id_type_prod_dec             bigint,  -- IdTypeProdDec
    categorie                    smallint,  -- Catégorie
    modif_op                     bigint,  -- ModifOP
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifELEM
    optim_cle_comp_i_dpro_famil  varchar(14),  -- OptimCleComp_IDpro_FAMIL
    CONSTRAINT pk_pgt_val_produit PRIMARY KEY (i_dproduit),
    CONSTRAINT uq_pgt_val_produit_auto UNIQUE (i_dproduit_auto)
);
CREATE INDEX ix_pgt_val_produit_lib_produit ON adv.pgt_val_produit (lib_produit);
CREATE INDEX ix_pgt_val_produit_prefixe_bdd ON adv.pgt_val_produit (prefixe_bdd);
CREATE INDEX ix_pgt_val_produit_famille ON adv.pgt_val_produit (famille);
CREATE INDEX ix_pgt_val_produit_sous_fam ON adv.pgt_val_produit (sous_fam);
CREATE INDEX ix_pgt_val_produit_pro_actif ON adv.pgt_val_produit (pro_actif);
CREATE INDEX ix_pgt_val_produit_id_type_prod_dec ON adv.pgt_val_produit (id_type_prod_dec);
CREATE INDEX ix_pgt_val_produit_modif_date ON adv.pgt_val_produit (modif_date);

CREATE TABLE adv.pgt_val_remun (
    id_remun_auto  bigint,  -- IDRemunAuto
    id_remun       bigint  NOT NULL,  -- IDRemun
    i_dproduit     integer,  -- IDproduit
    type_vente     smallint,  -- TypeVente
    date_debut     date,  -- DateDébut
    date_fin       date,  -- DateFin
    montant        numeric(19,4),  -- Montant
    nb_points      double precision,  -- nbPoints
    modif_op       bigint,  -- ModifOP
    modif_date     timestamp,  -- ModifDate
    modif_elem     varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_val_remun PRIMARY KEY (id_remun),
    CONSTRAINT uq_pgt_val_remun_auto UNIQUE (id_remun_auto)
);
CREATE INDEX ix_pgt_val_remun_i_dproduit ON adv.pgt_val_remun (i_dproduit);
CREATE INDEX ix_pgt_val_remun_date_debut ON adv.pgt_val_remun (date_debut);
CREATE INDEX ix_pgt_val_remun_modif_date ON adv.pgt_val_remun (modif_date);
