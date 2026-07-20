CREATE SCHEMA IF NOT EXISTS ticket_bo;


CREATE TABLE ticket_bo.pgt_tk_call (
    id_tk_call_auto           bigint,  -- IDtk_CallAuto
    id_tk_call                bigint NOT NULL,  -- IDtk_Call
    id_tk_liste               bigint,  -- IDTK_Liste
    id_salarie                bigint,  -- IDSalarie
    id_client                 bigint,  -- IDclient
    civilite_client           smallint,  -- CivilitéClient
    nom_client                text,  -- NomClient
    nom_marital_client        text,  -- NomMaritalClient
    prenom_client             text,  -- PrenomClient
    date_naiss                date,  -- DATENAISS
    dep_naiss                 smallint,  -- DEPNAISS
    adresse1                  text,  -- ADRESSE1
    adresse2                  text,  -- ADRESSE2
    cp                        varchar(5),  -- CP
    ville                     text,  -- VILLE
    adr_mail                  text,  -- adrMail
    mobile1                   varchar(10),  -- Mobile1
    type_logement             smallint,  -- TypeLogement
    client_pro                boolean,  -- ClientPro
    client_rs                 varchar(50),  -- ClientRS
    client_siret              varchar(50),  -- ClientSiret
    appel_en_cours            boolean,  -- AppelEnCours
    date_h_appel              timestamp,  -- DateH_Appel
    ope_appel                 bigint,  -- OpéAppel
    ref_appel                 text,  -- RefAppel
    motif_annulation          text,  -- MotifAnnulation
    date_deb_prise_en_charge  timestamp,  -- DateDeb_PriseEnCharge
    date_fin_prise_en_charge  timestamp,  -- DateFin_PriseEnCharge
    intervention_vend         boolean,  -- InterventionVend
    info_vente                text,  -- InfoVente
    code_valid                varchar(6),  -- CodeValid
    opt_rappel                boolean,  -- Opt_Rappel
    opt_partenaire            boolean,  -- Opt_Partenaire
    modif_op                  bigint,  -- ModifOP
    modif_date                timestamp,  -- ModifDate
    modif_elem                varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_call PRIMARY KEY (id_tk_call),
    CONSTRAINT uq_pgt_tk_call_auto UNIQUE (id_tk_call_auto)
);
CREATE INDEX ix_pgt_tk_call_id_tk_liste ON ticket_bo.pgt_tk_call (id_tk_liste);
CREATE INDEX ix_pgt_tk_call_id_salarie ON ticket_bo.pgt_tk_call (id_salarie);
CREATE INDEX ix_pgt_tk_call_id_client ON ticket_bo.pgt_tk_call (id_client);
CREATE INDEX ix_pgt_tk_call_appel_en_cours ON ticket_bo.pgt_tk_call (appel_en_cours);
CREATE INDEX ix_pgt_tk_call_modif_date ON ticket_bo.pgt_tk_call (modif_date);

CREATE TABLE ticket_bo.pgt_tk_call_panier (
    id_tk_call_panier           bigint NOT NULL,  -- IDTK_Call_Panier
    id_tk_call                  bigint,  -- IDtk_Call
    id_tk_liste                 bigint,  -- IDTK_Liste
    partenaire                  varchar(5),  -- Partenaire
    id_produit                  integer,  -- IDproduit
    num_bs                      text,  -- NumBS
    opt_energie_verte_elec      boolean,  -- OPT_EnergieVerteElec
    opt_reforestation           boolean,  -- OPT_Reforestation
    opt_energie_verte_gaz       boolean,  -- OPT_EnergieVerteGaz
    opt_mail                    boolean,  -- OPT_Mail
    opt_e_facture               boolean,  -- OPT_eFacture
    opt_e_communication         boolean,  -- OPT_eCommunication
    opt_optin_commercial        boolean,  -- OPT_optinCommercial
    opt_mandat                  boolean,  -- Opt_Mandat
    opt_consent_consult_distri  boolean,  -- OPT_ConsentConsultDistri
    opt_accept_com_parte        boolean,  -- OPT_AcceptComParte
    opt_maintenance             boolean,  -- Opt_Maintenance
    format_numerique            boolean,  -- FormatNumérique
    motif_annulation            text,  -- MotifAnnulation
    statut_prod                 smallint,  -- StatutProd
    nb_pers_foyer               smallint,  -- NBPersFoyer
    sit_pro                     text,  -- SitPro
    rfr                         numeric(19,4),  -- RFR
    date_entree                 date,  -- DateEntrée
    annee_construction          smallint,  -- AnnéeConstruction
    annee_installation          smallint,  -- AnnéeInstallation
    supercie                    smallint,  -- Supercie
    autre_install               boolean,  -- AutreInstall
    autre_installation          text,  -- AutreInstallation
    chauffage_appoint           boolean,  -- ChauffageAppoint
    isolation_combles           boolean,  -- IsolationCombles
    montant_mens_elec           numeric(19,4),  -- MontantMensELEC
    montant_mens_gaz            numeric(19,4),  -- MontantMensGAZ
    chauffage_alternantif       smallint,  -- ChauffageAlternantif
    type_chauff_alter           text,  -- TypeChauffAlter
    observations                text,  -- Observations
    num_date_saisie             timestamp,  -- Num_DateSaisie
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOp
    modif_elem                  varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_call_panier PRIMARY KEY (id_tk_call_panier)
);
CREATE INDEX ix_pgt_tk_call_panier_id_tk_call ON ticket_bo.pgt_tk_call_panier (id_tk_call);
CREATE INDEX ix_pgt_tk_call_panier_id_tk_liste ON ticket_bo.pgt_tk_call_panier (id_tk_liste);
CREATE INDEX ix_pgt_tk_call_panier_id_produit ON ticket_bo.pgt_tk_call_panier (id_produit);
CREATE INDEX ix_pgt_tk_call_panier_num_bs ON ticket_bo.pgt_tk_call_panier (num_bs);
CREATE INDEX ix_pgt_tk_call_panier_modif_date ON ticket_bo.pgt_tk_call_panier (modif_date);

CREATE TABLE ticket_bo.pgt_tk_call_sfr (
    id_tk_call_sfr_auto           bigint,  -- IDtk_CallSFRAuto
    id_tk_call_sfr                bigint NOT NULL,  -- IDtk_CallSFR
    id_tk_liste                   bigint,  -- IDTK_Liste
    id_offres_sfr                 bigint,  -- IDOffres_SFR
    id_salarie                    bigint,  -- IDSalarie
    civilite_client               smallint,  -- CivilitéClient
    nom_client                    text,  -- NomClient
    nom_marital_client            text,  -- NomMaritalClient
    prenom_client                 text,  -- PrenomClient
    date_naiss                    date,  -- DATENAISS
    dep_naiss                     smallint,  -- DEPNAISS
    adresse1                      text,  -- ADRESSE1
    adresse2                      text,  -- ADRESSE2
    cp                            varchar(5),  -- CP
    ville                         text,  -- VILLE
    adr_mail                      text,  -- adrMail
    mobile1                       varchar(10),  -- Mobile1
    mobile2                       varchar(10),  -- Mobile2
    type_logement                 smallint,  -- TypeLogement
    client_pro                    boolean,  -- ClientPro
    client_rs                     varchar(50),  -- ClientRS
    client_siret                  varchar(50),  -- ClientSiret
    test_eligibilite              bytea,  -- TestEligibilité
    appel_en_cours                boolean,  -- AppelEnCours
    date_h_appel                  timestamp,  -- DateH_Appel
    ope_appel                     bigint,  -- OpéAppel
    ref_appel                     text,  -- RefAppel
    motif_annulation              text,  -- MotifAnnulation
    date_deb_prise_en_charge      timestamp,  -- DateDeb_PriseEnCharge
    date_fin_prise_en_charge      timestamp,  -- DateFin_PriseEnCharge
    info_vente                    text,  -- InfoVente
    mob_propo_vend                boolean,  -- MobPropoVend
    intervention_vend             boolean,  -- InterventionVend
    code_valid                    varchar(6),  -- CodeValid
    opt_rappel                    boolean,  -- Opt_Rappel
    opt_partenaire                boolean,  -- Opt_Partenaire
    anomalie_mobile               boolean,  -- AnomalieMobile
    id_tk_call_sfr_type_anomalie  bigint,  -- IDTK_CallSFR_TypeAnomalie
    id_tk_liste_ref_anomalie      bigint,  -- IDTK_ListeRefAnomalie
    info_cplt_anomalie            text,  -- InfoCpltAnomalie
    ticket_diff                   boolean,  -- TicketDiff
    kbis                          varchar(50),  -- KBIS
    modif_date                    timestamp,  -- ModifDate
    modif_op                      bigint,  -- ModifOP
    modif_elem                    varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_call_sfr PRIMARY KEY (id_tk_call_sfr),
    CONSTRAINT uq_pgt_tk_call_sfr_auto UNIQUE (id_tk_call_sfr_auto)
);
CREATE INDEX ix_pgt_tk_call_sfr_id_tk_liste ON ticket_bo.pgt_tk_call_sfr (id_tk_liste);
CREATE INDEX ix_pgt_tk_call_sfr_id_offres_sfr ON ticket_bo.pgt_tk_call_sfr (id_offres_sfr);
CREATE INDEX ix_pgt_tk_call_sfr_id_salarie ON ticket_bo.pgt_tk_call_sfr (id_salarie);
CREATE INDEX ix_pgt_tk_call_sfr_appel_en_cours ON ticket_bo.pgt_tk_call_sfr (appel_en_cours);
CREATE INDEX ix_pgt_tk_call_sfr_id_tk_call_sfr_type_anomalie ON ticket_bo.pgt_tk_call_sfr (id_tk_call_sfr_type_anomalie);
CREATE INDEX ix_pgt_tk_call_sfr_modif_date ON ticket_bo.pgt_tk_call_sfr (modif_date);

CREATE TABLE ticket_bo.pgt_tk_call_sfr_panier (
    id_tk_call_sfr              bigint,  -- IDtk_CallSFR
    id_tk_liste                 bigint,  -- IDTK_Liste
    num                         varchar(25),  -- NUM
    id_offres_sfr               bigint,  -- IDOffres_SFR
    opt_tv                      boolean,  -- Opt_TV
    type                        varchar(8),  -- Type
    portabilite                 boolean,  -- portabilité
    num_portabilite             varchar(10),  -- NumPortabilité
    num_prise_rio               text,  -- NumPrise_RIO
    type_vente                  smallint,  -- TypeVente
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOP
    modif_elem                  varchar(5),  -- ModifELEM
    test_eligibilite            bytea,  -- TestEligibilité
    motif_annulation            text,  -- MotifAnnulation
    id_tk_call_sfr_panier       bigint NOT NULL,  -- IDTK_CallSFR_Panier
    statut_prod                 smallint,  -- StatutProd
    id_tk_call_sfr_panier_auto  bigint,  -- IDTK_CallSFR_PanierAuto
    num_date_saisie             timestamp,  -- Num_DateSaisie
    num_prise_optique           text,  -- NumPrise_Optique
    opt_choisies                text,  -- OptChoisies
    CONSTRAINT pk_pgt_tk_call_sfr_panier PRIMARY KEY (id_tk_call_sfr_panier),
    CONSTRAINT uq_pgt_tk_call_sfr_panier_auto UNIQUE (id_tk_call_sfr_panier_auto)
);
CREATE INDEX ix_pgt_tk_call_sfr_panier_id_tk_call_sfr ON ticket_bo.pgt_tk_call_sfr_panier (id_tk_call_sfr);
CREATE INDEX ix_pgt_tk_call_sfr_panier_id_tk_liste ON ticket_bo.pgt_tk_call_sfr_panier (id_tk_liste);
CREATE INDEX ix_pgt_tk_call_sfr_panier_num ON ticket_bo.pgt_tk_call_sfr_panier (num);
CREATE INDEX ix_pgt_tk_call_sfr_panier_id_offres_sfr ON ticket_bo.pgt_tk_call_sfr_panier (id_offres_sfr);
CREATE INDEX ix_pgt_tk_call_sfr_panier_type ON ticket_bo.pgt_tk_call_sfr_panier (type);
CREATE INDEX ix_pgt_tk_call_sfr_panier_modif_date ON ticket_bo.pgt_tk_call_sfr_panier (modif_date);

CREATE TABLE ticket_bo.pgt_tk_call_sfr_ret_ko (
    id_tk_call_sfr_ret_racc  bigint NOT NULL,  -- IDTK_CallSFR_RetRacc
    id_tk_liste              bigint,  -- IDTK_Liste
    id_contrat               bigint,  -- IDcontrat
    ope_traitement           bigint,  -- OpéTraitement
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_call_sfr_ret_ko PRIMARY KEY (id_tk_call_sfr_ret_racc)
);
CREATE INDEX ix_pgt_tk_call_sfr_ret_ko_id_tk_liste ON ticket_bo.pgt_tk_call_sfr_ret_ko (id_tk_liste);
CREATE INDEX ix_pgt_tk_call_sfr_ret_ko_id_contrat ON ticket_bo.pgt_tk_call_sfr_ret_ko (id_contrat);
CREATE INDEX ix_pgt_tk_call_sfr_ret_ko_ope_traitement ON ticket_bo.pgt_tk_call_sfr_ret_ko (ope_traitement);
CREATE INDEX ix_pgt_tk_call_sfr_ret_ko_modif_date ON ticket_bo.pgt_tk_call_sfr_ret_ko (modif_date);

CREATE TABLE ticket_bo.pgt_tk_call_sfr_ret_racc (
    id_tk_call_sfr_ret_racc  bigint NOT NULL,  -- IDTK_CallSFR_RetRacc
    id_tk_liste              bigint,  -- IDTK_Liste
    id_contrat               bigint,  -- IDcontrat
    id_etat_call_ret         smallint,  -- IDEtatCallRet
    info_clpt                text,  -- InfoClpt
    ope_traitement           bigint,  -- OpéTraitement
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_call_sfr_ret_racc PRIMARY KEY (id_tk_call_sfr_ret_racc)
);
CREATE INDEX ix_pgt_tk_call_sfr_ret_racc_id_tk_liste ON ticket_bo.pgt_tk_call_sfr_ret_racc (id_tk_liste);
CREATE INDEX ix_pgt_tk_call_sfr_ret_racc_id_contrat ON ticket_bo.pgt_tk_call_sfr_ret_racc (id_contrat);
CREATE INDEX ix_pgt_tk_call_sfr_ret_racc_id_etat_call_ret ON ticket_bo.pgt_tk_call_sfr_ret_racc (id_etat_call_ret);
CREATE INDEX ix_pgt_tk_call_sfr_ret_racc_ope_traitement ON ticket_bo.pgt_tk_call_sfr_ret_racc (ope_traitement);
CREATE INDEX ix_pgt_tk_call_sfr_ret_racc_modif_date ON ticket_bo.pgt_tk_call_sfr_ret_racc (modif_date);

CREATE TABLE ticket_bo.pgt_tk_call_sfr_ret_rdv_tech (
    id_tk_call_sfr_ret_rdv_tech  bigint NOT NULL,  -- IDTK_CallSFR_RetRDVTech
    id_tk_liste                  bigint,  -- IDTK_Liste
    id_contrat                   bigint,  -- IDcontrat
    nouvelle_date_rdv            date,  -- NouvelleDateRDV
    info_complementaire          text,  -- InfoComplémentaire
    id_sfr_statut_rdv            bigint,  -- IdSFR_StatutRDV
    ope_traitement               bigint,  -- OpéTraitement
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOp
    modif_elem                   varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_call_sfr_ret_rdv_tech PRIMARY KEY (id_tk_call_sfr_ret_rdv_tech)
);
CREATE INDEX ix_pgt_tk_call_sfr_ret_rdv_tech_id_tk_liste ON ticket_bo.pgt_tk_call_sfr_ret_rdv_tech (id_tk_liste);
CREATE INDEX ix_pgt_tk_call_sfr_ret_rdv_tech_id_contrat ON ticket_bo.pgt_tk_call_sfr_ret_rdv_tech (id_contrat);
CREATE INDEX ix_pgt_tk_call_sfr_ret_rdv_tech_ope_traitement ON ticket_bo.pgt_tk_call_sfr_ret_rdv_tech (ope_traitement);
CREATE INDEX ix_pgt_tk_call_sfr_ret_rdv_tech_modif_date ON ticket_bo.pgt_tk_call_sfr_ret_rdv_tech (modif_date);

CREATE TABLE ticket_bo.pgt_tk_call_sfr_ret_vente_add (
    id_tk_call_sfr_ret_vente_add  bigint NOT NULL,  -- IDTK_CallSFR_RetVenteADD
    id_tk_liste                   bigint,  -- IDTK_Liste
    id_contrat                    bigint,  -- IDcontrat
    num_bs                        text,  -- NumBS
    type                          varchar(5),  -- Type
    modif_date                    timestamp,  -- ModifDate
    modif_op                      bigint,  -- ModifOp
    modif_elem                    varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_call_sfr_ret_vente_add PRIMARY KEY (id_tk_call_sfr_ret_vente_add)
);
CREATE INDEX ix_pgt_tk_call_sfr_ret_vente_add_id_tk_liste ON ticket_bo.pgt_tk_call_sfr_ret_vente_add (id_tk_liste);
CREATE INDEX ix_pgt_tk_call_sfr_ret_vente_add_id_contrat ON ticket_bo.pgt_tk_call_sfr_ret_vente_add (id_contrat);
CREATE INDEX ix_pgt_tk_call_sfr_ret_vente_add_num_bs ON ticket_bo.pgt_tk_call_sfr_ret_vente_add (num_bs);
CREATE INDEX ix_pgt_tk_call_sfr_ret_vente_add_type ON ticket_bo.pgt_tk_call_sfr_ret_vente_add (type);
CREATE INDEX ix_pgt_tk_call_sfr_ret_vente_add_modif_date ON ticket_bo.pgt_tk_call_sfr_ret_vente_add (modif_date);

CREATE TABLE ticket_bo.pgt_tk_callsfr_typeanomalie (
    id_tk_call_sfr_type_anomalie  bigint NOT NULL,  -- IDTK_CallSFR_TypeAnomalie
    lib_type_anomalie             text,  -- LibTypeAnomalie
    modif_date                    timestamp,  -- ModifDate
    modif_op                      bigint,  -- ModifOP
    modif_elem                    varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_callsfr_typeanomalie PRIMARY KEY (id_tk_call_sfr_type_anomalie)
);
CREATE INDEX ix_pgt_tk_callsfr_typeanomalie_modif_date ON ticket_bo.pgt_tk_callsfr_typeanomalie (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_avance (
    id_tk_demande_avance_auto  bigint,  -- IDTK_DemandeAvanceAuto
    id_tk_demande_avance       bigint NOT NULL,  -- IDTK_DemandeAvance
    id_tk_liste                bigint,  -- IDTK_Liste
    beneficiaire               bigint,  -- Bénéficiaire
    montant                    numeric(19,4),  -- Montant
    preuve_virement            bytea,  -- PreuveVirement
    demande_validee            boolean,  -- DemandeValidée
    date_paiement              varchar(7),  -- DATEPAIEMENT
    modif_op                   bigint,  -- ModifOP
    modif_date                 timestamp,  -- ModifDate
    modif_elem                 varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_avance PRIMARY KEY (id_tk_demande_avance),
    CONSTRAINT uq_pgt_tk_demande_avance_auto UNIQUE (id_tk_demande_avance_auto)
);
CREATE INDEX ix_pgt_tk_demande_avance_id_tk_liste ON ticket_bo.pgt_tk_demande_avance (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_avance_beneficiaire ON ticket_bo.pgt_tk_demande_avance (beneficiaire);
CREATE INDEX ix_pgt_tk_demande_avance_modif_date ON ticket_bo.pgt_tk_demande_avance (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_carte_pro (
    id_tk_demande_carte_pro_auto  bigint,  -- IDTK_DemandeCartePROAuto
    id_tk_demande_carte_pro       bigint NOT NULL,  -- IDTK_DemandeCartePRO
    id_tk_liste                   bigint,  -- IDTK_Liste
    id_salarie                    bigint,  -- IDSalarie
    photo                         bytea,  -- PHOTO
    op_crea                       bigint,  -- OPCrea
    date_crea                     timestamp,  -- dateCrea
    num_suivi                     varchar(50),  -- NumSuivi
    modif_date                    timestamp,  -- ModifDate
    modif_elem                    varchar(5),  -- ModifELEM
    modif_op                      bigint,  -- ModifOP
    CONSTRAINT pk_pgt_tk_demande_carte_pro PRIMARY KEY (id_tk_demande_carte_pro),
    CONSTRAINT uq_pgt_tk_demande_carte_pro_auto UNIQUE (id_tk_demande_carte_pro_auto)
);
CREATE INDEX ix_pgt_tk_demande_carte_pro_id_tk_liste ON ticket_bo.pgt_tk_demande_carte_pro (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_carte_pro_id_salarie ON ticket_bo.pgt_tk_demande_carte_pro (id_salarie);
CREATE INDEX ix_pgt_tk_demande_carte_pro_modif_date ON ticket_bo.pgt_tk_demande_carte_pro (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_code_vendeur (
    id_tk_demande_code_vendeur  bigint NOT NULL,  -- IDTK_DemandeCodeVendeur
    id_tk_liste                 bigint,  -- IDTK_Liste
    type_ori                    varchar(5),  -- TypeOri
    id_elem                     bigint,  -- IDElem
    id_partenaire               bigint,  -- IDPartenaire
    id_salarie_id_partenaire    varchar(16),  -- IDSalarieIDPartenaire
    code                        text,  -- Code
    login                       text,  -- LOGIN
    mdp                         text,  -- MDP
    modif_date                  timestamp,  -- ModifDate
    modif_elem                  varchar(5),  -- ModifElem
    modif_op                    bigint,  -- ModifOp
    CONSTRAINT pk_pgt_tk_demande_code_vendeur PRIMARY KEY (id_tk_demande_code_vendeur)
);
CREATE INDEX ix_pgt_tk_demande_code_vendeur_id_tk_liste ON ticket_bo.pgt_tk_demande_code_vendeur (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_code_vendeur_id_elem ON ticket_bo.pgt_tk_demande_code_vendeur (id_elem);
CREATE INDEX ix_pgt_tk_demande_code_vendeur_id_partenaire ON ticket_bo.pgt_tk_demande_code_vendeur (id_partenaire);
CREATE INDEX ix_pgt_tk_demande_code_vendeur_code ON ticket_bo.pgt_tk_demande_code_vendeur (code);
CREATE INDEX ix_pgt_tk_demande_code_vendeur_login ON ticket_bo.pgt_tk_demande_code_vendeur (login);
CREATE INDEX ix_pgt_tk_demande_code_vendeur_modif_date ON ticket_bo.pgt_tk_demande_code_vendeur (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demandecodevendeur_fichier (
    id_tk_demande_code_vendeur_fichier  bigint NOT NULL,  -- IDTK_DemandeCodeVendeur_Fichier
    id_tk_demande_code_vendeur          bigint,  -- IDTK_DemandeCodeVendeur
    id_tk_liste                         bigint,  -- IDTK_Liste
    lien_fichier                        text,  -- LienFichier
    modif_date                          timestamp,  -- ModifDate
    modif_op                            bigint,  -- ModifOP
    modif_elem                          varchar(5),  -- ModifELEM
    nom_fichier                         text,  -- NomFichier
    CONSTRAINT pk_pgt_tk_demandecodevendeur_fichier PRIMARY KEY (id_tk_demande_code_vendeur_fichier)
);
CREATE INDEX ix_pgt_tk_demandecodevendeur_fichier_id_tk_demande_code_vendeur ON ticket_bo.pgt_tk_demandecodevendeur_fichier (id_tk_demande_code_vendeur);
CREATE INDEX ix_pgt_tk_demandecodevendeur_fichier_id_tk_liste ON ticket_bo.pgt_tk_demandecodevendeur_fichier (id_tk_liste);
CREATE INDEX ix_pgt_tk_demandecodevendeur_fichier_modif_date ON ticket_bo.pgt_tk_demandecodevendeur_fichier (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_ctt_courtage (
    id_demande_contrat_w_auto  bigint,  -- IDdemandeContratWAuto
    id_demande_contrat_w       bigint NOT NULL,  -- IDdemandeContratW
    id_tk_liste                bigint,  -- IDTK_Liste
    idorganigramme             bigint,  -- idorganigramme
    id_societe_doc_courtage    bigint,  -- IDsociete_docCourtage
    id_salarie                 bigint,  -- IDSalarie
    contenu                    bytea,  -- Contenu
    id_distrib                 bigint,  -- idDistrib
    titre_contrat              text,  -- TitreContrat
    contrat_genere             boolean,  -- contratGénéré
    contrat_valide             boolean,  -- contratValidé
    contrat_signe              boolean,  -- contratSigné
    contrat_annul              boolean,  -- contratAnnul
    datesignature              timestamp,  -- datesignature
    contenu_validation         text,  -- ContenuValidation
    photo_salarie              bytea,  -- PhotoSalarié
    signature                  bytea,  -- Signature
    paraphe                    bytea,  -- paraphe
    lu_app                     bytea,  -- luApp
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOP
    modif_elem                 varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_ctt_courtage PRIMARY KEY (id_demande_contrat_w),
    CONSTRAINT uq_pgt_tk_demande_ctt_courtage_auto UNIQUE (id_demande_contrat_w_auto)
);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_id_tk_liste ON ticket_bo.pgt_tk_demande_ctt_courtage (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_idorganigramme ON ticket_bo.pgt_tk_demande_ctt_courtage (idorganigramme);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_id_societe_doc_courtage ON ticket_bo.pgt_tk_demande_ctt_courtage (id_societe_doc_courtage);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_id_salarie ON ticket_bo.pgt_tk_demande_ctt_courtage (id_salarie);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_id_distrib ON ticket_bo.pgt_tk_demande_ctt_courtage (id_distrib);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_contrat_genere ON ticket_bo.pgt_tk_demande_ctt_courtage (contrat_genere);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_contrat_valide ON ticket_bo.pgt_tk_demande_ctt_courtage (contrat_valide);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_contrat_signe ON ticket_bo.pgt_tk_demande_ctt_courtage (contrat_signe);
CREATE INDEX ix_pgt_tk_demande_ctt_courtage_modif_date ON ticket_bo.pgt_tk_demande_ctt_courtage (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_doc_distrib (
    id_tk_demande_doc_distrib  bigint NOT NULL,  -- IDTK_DemandeDocDistrib
    id_tk_liste                bigint,  -- IDTK_Liste
    id_doc_distrib             bigint,  -- IDDoc_Distrib
    lien_fichier               text,  -- LienFichier
    motif_refus                text,  -- MotifRefus
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOp
    modif_elem                 varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_demande_doc_distrib PRIMARY KEY (id_tk_demande_doc_distrib)
);
CREATE INDEX ix_pgt_tk_demande_doc_distrib_id_tk_liste ON ticket_bo.pgt_tk_demande_doc_distrib (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_doc_distrib_id_doc_distrib ON ticket_bo.pgt_tk_demande_doc_distrib (id_doc_distrib);
CREATE INDEX ix_pgt_tk_demande_doc_distrib_modif_date ON ticket_bo.pgt_tk_demande_doc_distrib (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_dpae_distrib (
    id_tk_demande_dpae_distrib_auto  bigint,  -- IDTK_DemandeDPAE_DistribAuto
    id_tk_demande_dpae_distrib       bigint NOT NULL,  -- IDTK_DemandeDPAE_Distrib
    id_tk_liste                      bigint,  -- IDTK_Liste
    op_crea                          bigint,  -- OPCrea
    date_crea                        timestamp,  -- dateCrea
    civilite                         smallint,  -- Civilité
    nom                              text,  -- NOM
    nom_marital                      text,  -- NOM_MARITAL
    prenom                           text,  -- PRENOM
    num_ss                           text,  -- NUMSS
    dnaiss                           date,  -- DNAISS
    lnaiss                           text,  -- LNAISS
    dep_naiss                        integer,  -- DEPNAISS
    num_cin                          text,  -- NUMCIN
    adresse1                         text,  -- ADRESSE1
    cp                               varchar(5),  -- Cp
    ville                            text,  -- VILLE
    gsm                              text,  -- GSM
    mail                             text,  -- MAIL
    id_ste                           bigint,  -- IdSte
    idorganigramme                   bigint,  -- idorganigramme
    date_debut                       date,  -- DateDébut
    raison_sociale                   text,  -- RaisonSociale
    siret                            text,  -- SIRET
    adresse_siege                    text,  -- AdresseSiege
    cp_siege                         varchar(5),  -- CPSiege
    v_ille_siege                     text,  -- VIlleSiege
    num_tva                          text,  -- NumTVA
    doc_orias                        boolean,  -- DocOrias
    modif_op                         bigint,  -- ModifOP
    modif_date                       timestamp,  -- ModifDate
    modif_elem                       varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_dpae_distrib PRIMARY KEY (id_tk_demande_dpae_distrib),
    CONSTRAINT uq_pgt_tk_demande_dpae_distrib_auto UNIQUE (id_tk_demande_dpae_distrib_auto)
);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_id_tk_liste ON ticket_bo.pgt_tk_demande_dpae_distrib (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_id_ste ON ticket_bo.pgt_tk_demande_dpae_distrib (id_ste);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_idorganigramme ON ticket_bo.pgt_tk_demande_dpae_distrib (idorganigramme);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_date_debut ON ticket_bo.pgt_tk_demande_dpae_distrib (date_debut);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_siret ON ticket_bo.pgt_tk_demande_dpae_distrib (siret);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_modif_date ON ticket_bo.pgt_tk_demande_dpae_distrib (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_dpae_distrib_photo (
    id_tk_demande_dpae_photo_auto  bigint,  -- IDTK_DemandeDPAEPhotoAuto
    id_tk_demande_dpae_photo       bigint NOT NULL,  -- IDTK_DemandeDPAEPhoto
    id_tk_demande_dpae             bigint,  -- IDTK_DemandeDPAE
    id_tk_type_photo_dpae          bigint,  -- IDTK_TypePhotoDPAE
    id_tk_liste                    bigint,  -- IDTK_Liste
    op_crea                        bigint,  -- OPCrea
    date_crea                      timestamp,  -- dateCrea
    nom                            text,  -- NOM
    photo                          bytea,  -- PHOTO
    doc_pdf                        bytea,  -- DocPDF
    nom_fichier                    varchar(50),  -- NomFichier
    modif_date                     timestamp,  -- ModifDate
    modif_elem                     varchar(5),  -- ModifELEM
    modif_op                       bigint,  -- ModifOP
    CONSTRAINT pk_pgt_tk_demande_dpae_distrib_photo PRIMARY KEY (id_tk_demande_dpae_photo),
    CONSTRAINT uq_pgt_tk_demande_dpae_distrib_photo_auto UNIQUE (id_tk_demande_dpae_photo_auto)
);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_photo_id_tk_demande_dpae ON ticket_bo.pgt_tk_demande_dpae_distrib_photo (id_tk_demande_dpae);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_photo_id_tk_type_photo_dpae ON ticket_bo.pgt_tk_demande_dpae_distrib_photo (id_tk_type_photo_dpae);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_photo_id_tk_liste ON ticket_bo.pgt_tk_demande_dpae_distrib_photo (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_dpae_distrib_photo_modif_date ON ticket_bo.pgt_tk_demande_dpae_distrib_photo (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_envoi_tablette (
    id_tk_demande_envoi_tablette_auto  bigint,  -- IDTK_DemandeEnvoiTabletteAuto
    id_tk_demande_envoi_tablette       bigint NOT NULL,  -- IDTK_DemandeEnvoiTablette
    id_tk_demande_fourniture           bigint,  -- IDTK_DemandeFourniture
    id_parc_it                         bigint,  -- IDparcIT
    id_salarie                         bigint,  -- IDSalarie
    date_envoi                         date,  -- dateEnvoi
    modif_date                         timestamp,  -- ModifDate
    modif_op                           bigint,  -- ModifOP
    modif_elem                         varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_envoi_tablette PRIMARY KEY (id_tk_demande_envoi_tablette),
    CONSTRAINT uq_pgt_tk_demande_envoi_tablette_auto UNIQUE (id_tk_demande_envoi_tablette_auto)
);
CREATE INDEX ix_pgt_tk_demande_envoi_tablette_id_tk_demande_fourniture ON ticket_bo.pgt_tk_demande_envoi_tablette (id_tk_demande_fourniture);
CREATE INDEX ix_pgt_tk_demande_envoi_tablette_id_parc_it ON ticket_bo.pgt_tk_demande_envoi_tablette (id_parc_it);
CREATE INDEX ix_pgt_tk_demande_envoi_tablette_id_salarie ON ticket_bo.pgt_tk_demande_envoi_tablette (id_salarie);
CREATE INDEX ix_pgt_tk_demande_envoi_tablette_date_envoi ON ticket_bo.pgt_tk_demande_envoi_tablette (date_envoi);
CREATE INDEX ix_pgt_tk_demande_envoi_tablette_modif_date ON ticket_bo.pgt_tk_demande_envoi_tablette (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_facturation (
    id_commande                        bigint,  -- IDCommande
    id_tk_demande_facturation_distrib  bigint NOT NULL,  -- IDTK_DemandeFacturationDistrib
    id_tk_liste                        bigint,  -- IDTK_Liste
    fic_facture                        text,  -- FicFacture
    fic_preuve_virement                text,  -- FicPreuveVirement
    modif_date                         timestamp,  -- ModifDate
    modif_op                           bigint,  -- ModifOp
    date_paiement                      date,  -- DatePaiement
    modif_elem                         varchar(5),  -- ModifElem
    montant                            numeric(19,4),  -- Montant
    lib_facture                        varchar(50),  -- LibFacture
    descriptif                         text,  -- Descriptif
    date_achat                         date,  -- DateAchat
    num_commande                       varchar(50),  -- NumCommande
    CONSTRAINT pk_pgt_tk_demande_facturation PRIMARY KEY (id_tk_demande_facturation_distrib)
);
CREATE INDEX ix_pgt_tk_demande_facturation_id_commande ON ticket_bo.pgt_tk_demande_facturation (id_commande);
CREATE INDEX ix_pgt_tk_demande_facturation_id_tk_liste ON ticket_bo.pgt_tk_demande_facturation (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_facturation_modif_date ON ticket_bo.pgt_tk_demande_facturation (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_facturation_distrib (
    id_tk_demande_facturation_distrib  bigint NOT NULL,  -- IDTK_DemandeFacturationDistrib
    id_tk_liste                        bigint,  -- IDTK_Liste
    fic_facture                        text,  -- FicFacture
    fic_preuve_virement                text,  -- FicPreuveVirement
    id_gerant                          bigint,  -- IdGérant
    id_ste                             bigint,  -- IdSte
    montant                            numeric(19,4),  -- Montant
    date_virement                      date,  -- DateVirement
    modif_date                         timestamp,  -- ModifDate
    modif_op                           bigint,  -- ModifOp
    modif_elem                         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_demande_facturation_distrib PRIMARY KEY (id_tk_demande_facturation_distrib)
);
CREATE INDEX ix_pgt_tk_demande_facturation_distrib_id_tk_liste ON ticket_bo.pgt_tk_demande_facturation_distrib (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_facturation_distrib_id_gerant ON ticket_bo.pgt_tk_demande_facturation_distrib (id_gerant);
CREATE INDEX ix_pgt_tk_demande_facturation_distrib_id_ste ON ticket_bo.pgt_tk_demande_facturation_distrib (id_ste);
CREATE INDEX ix_pgt_tk_demande_facturation_distrib_modif_date ON ticket_bo.pgt_tk_demande_facturation_distrib (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_fourniture (
    id_tk_demande_fourniture       bigint NOT NULL,  -- IDTK_DemandeFourniture
    id_tk_liste                    bigint,  -- IDTK_Liste
    qte                            integer,  -- Qté
    date_crea                      timestamp,  -- dateCrea
    op_crea                        bigint,  -- OPCrea
    date_envoi                     date,  -- dateEnvoi
    priorite_haute                 boolean,  -- PrioritéHaute
    num_suivi                      varchar(50),  -- NumSuivi
    modif_date                     timestamp,  -- ModifDate
    modif_elem                     varchar(5),  -- ModifELEM
    modif_op                       bigint,  -- ModifOP
    id_tk_type_commande            bigint,  -- IDTK_TypeCommande
    adr_livraison                  text,  -- adrLivraison
    id_tk_demande_fourniture_auto  bigint,  -- IDTK_DemandeFournitureAuto
    CONSTRAINT pk_pgt_tk_demande_fourniture PRIMARY KEY (id_tk_demande_fourniture),
    CONSTRAINT uq_pgt_tk_demande_fourniture_auto UNIQUE (id_tk_demande_fourniture_auto)
);
CREATE INDEX ix_pgt_tk_demande_fourniture_id_tk_liste ON ticket_bo.pgt_tk_demande_fourniture (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_fourniture_modif_date ON ticket_bo.pgt_tk_demande_fourniture (modif_date);
CREATE INDEX ix_pgt_tk_demande_fourniture_id_tk_type_commande ON ticket_bo.pgt_tk_demande_fourniture (id_tk_type_commande);

CREATE TABLE ticket_bo.pgt_tk_demande_resa (
    id_tk_demande_resa_auto  bigint,  -- IDTK_DemandeResaAuto
    id_tk_demande_resa       bigint NOT NULL,  -- IDTK_DemandeResa
    id_tk_liste              bigint,  -- IDTK_Liste
    id_tk_type_resa_ss_fam   integer,  -- IDTK_TypeResaSSFam
    ville_dep                varchar(50),  -- Ville_Dep
    ville_arr                varchar(50),  -- Ville_Arr
    jour_dep                 date,  -- Jour_Dep
    jour_arr                 date,  -- Jour_Arr
    heure_dep                time,  -- Heure_Dep
    heure_arr                time,  -- Heure_Arr
    beneficiaire             bigint,  -- Bénéficiaire
    liste_bene_supp          text,  -- ListeBénéSupp
    info_cplt                text,  -- InfoCplt
    pj                       text,  -- PJ
    ar                       boolean,  -- AR
    jour_r_dep               date,  -- JourR_Dep
    jour_r_arr               date,  -- JourR_Arr
    heure_r_dep              time,  -- HeureR_Dep
    heure_r_arr              time,  -- HeureR_Arr
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOP
    modif_elem               varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_resa PRIMARY KEY (id_tk_demande_resa),
    CONSTRAINT uq_pgt_tk_demande_resa_auto UNIQUE (id_tk_demande_resa_auto)
);
CREATE INDEX ix_pgt_tk_demande_resa_id_tk_liste ON ticket_bo.pgt_tk_demande_resa (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_resa_id_tk_type_resa_ss_fam ON ticket_bo.pgt_tk_demande_resa (id_tk_type_resa_ss_fam);
CREATE INDEX ix_pgt_tk_demande_resa_beneficiaire ON ticket_bo.pgt_tk_demande_resa (beneficiaire);
CREATE INDEX ix_pgt_tk_demande_resa_modif_date ON ticket_bo.pgt_tk_demande_resa (modif_date);

CREATE TABLE ticket_bo.pgt_tk_demande_sos_bo (
    id_tk_demande_sos_bo_auto  bigint,  -- IDTK_DemandeSOS_BOAuto
    id_tk_demande_sos_bo       bigint NOT NULL,  -- IDTK_DemandeSOS_BO
    id_tk_liste                bigint,  -- IDTK_Liste
    beneficiaire               bigint,  -- Bénéficiaire
    id_tk_type_sos_bo          bigint,  -- IDTK_TypeSOS_BO
    ref_a_controler            varchar(50),  -- Ref_A_contrôler
    info_cplt                  text,  -- InfoCplt
    modif_op                   bigint,  -- ModifOP
    modif_date                 timestamp,  -- ModifDate
    modif_elem                 varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_sos_bo PRIMARY KEY (id_tk_demande_sos_bo),
    CONSTRAINT uq_pgt_tk_demande_sos_bo_auto UNIQUE (id_tk_demande_sos_bo_auto)
);
CREATE INDEX ix_pgt_tk_demande_sos_bo_id_tk_liste ON ticket_bo.pgt_tk_demande_sos_bo (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_sos_bo_beneficiaire ON ticket_bo.pgt_tk_demande_sos_bo (beneficiaire);
CREATE INDEX ix_pgt_tk_demande_sos_bo_id_tk_type_sos_bo ON ticket_bo.pgt_tk_demande_sos_bo (id_tk_type_sos_bo);
CREATE INDEX ix_pgt_tk_demande_sos_bo_modif_date ON ticket_bo.pgt_tk_demande_sos_bo (modif_date);

CREATE TABLE ticket_bo.pgt_tk_dpae_doc_demat_distrib (
    id_tk_dpae_doc_demat_distrib_auto  bigint,  -- IDTK_DPAE_DocDemat_DistribAuto
    id_tk_dpae_doc_demat_distrib       bigint NOT NULL,  -- IDTK_DPAE_DocDemat_Distrib
    id_tk_liste                        bigint,  -- IDTK_Liste
    type_doc                           varchar(10),  -- TypeDoc
    id_doc_rh                          bigint,  -- IDdocRH
    date_signature                     date,  -- DateSignature
    num_semaine                        smallint,  -- NumSemaine
    nb_masque_tissu                    integer,  -- nbMasqueTissu
    nb_masque_jetable                  integer,  -- nbMasqueJetable
    nb_visiere                         integer,  -- nbVisiere
    nb_gel_hydro                       integer,  -- nbGelHydro
    nb_lingettes                       integer,  -- nbLingettes
    photo                              bytea,  -- PHOTO
    signature                          bytea,  -- Signature
    lu_app                             bytea,  -- luApp
    id_ste                             bigint,  -- IdSte
    cmu                                boolean,  -- CMU
    mutuelle                           boolean,  -- MUTUELLE
    nom_mutuelle                       text,  -- NomMutuelle
    date_fin_mutuelle                  date,  -- DateFinMutuelle
    contenu                            bytea,  -- Contenu
    modif_op                           bigint,  -- ModifOP
    modif_date                         timestamp,  -- ModifDate
    modif_elem                         varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_dpae_doc_demat_distrib PRIMARY KEY (id_tk_dpae_doc_demat_distrib),
    CONSTRAINT uq_pgt_tk_dpae_doc_demat_distrib_auto UNIQUE (id_tk_dpae_doc_demat_distrib_auto)
);
CREATE INDEX ix_pgt_tk_dpae_doc_demat_distrib_id_tk_liste ON ticket_bo.pgt_tk_dpae_doc_demat_distrib (id_tk_liste);
CREATE INDEX ix_pgt_tk_dpae_doc_demat_distrib_date_signature ON ticket_bo.pgt_tk_dpae_doc_demat_distrib (date_signature);
CREATE INDEX ix_pgt_tk_dpae_doc_demat_distrib_id_ste ON ticket_bo.pgt_tk_dpae_doc_demat_distrib (id_ste);
CREATE INDEX ix_pgt_tk_dpae_doc_demat_distrib_modif_date ON ticket_bo.pgt_tk_dpae_doc_demat_distrib (modif_date);

CREATE TABLE ticket_bo.pgt_tk_retour_rdv_tech_fibre (
    id_tk_retour_rdv_tech_fibre       bigint NOT NULL,  -- IDTK_RetourRdvTechFIBRE
    id_tk_liste                       bigint,  -- IDTK_Liste
    id_contrat                        bigint,  -- IDcontrat
    num_bs                            varchar(50),  -- NumBS
    id_fibre_statut_rdv               bigint,  -- IdFIBRE_StatutRDV
    info_cplt                         text,  -- InfoCplt
    modif_date                        timestamp,  -- ModifDate
    modif_op                          bigint,  -- ModifOP
    modif_elem                        varchar(5),  -- ModifELEM
    id_tk_retour_rdv_tech_fibre_auto  bigint,  -- IDTK_RetourRdvTechFIBREAuto
    CONSTRAINT pk_pgt_tk_retour_rdv_tech_fibre PRIMARY KEY (id_tk_retour_rdv_tech_fibre),
    CONSTRAINT uq_pgt_tk_retour_rdv_tech_fibre_auto UNIQUE (id_tk_retour_rdv_tech_fibre_auto)
);
CREATE INDEX ix_pgt_tk_retour_rdv_tech_fibre_id_tk_liste ON ticket_bo.pgt_tk_retour_rdv_tech_fibre (id_tk_liste);
CREATE INDEX ix_pgt_tk_retour_rdv_tech_fibre_id_contrat ON ticket_bo.pgt_tk_retour_rdv_tech_fibre (id_contrat);
CREATE INDEX ix_pgt_tk_retour_rdv_tech_fibre_modif_date ON ticket_bo.pgt_tk_retour_rdv_tech_fibre (modif_date);

CREATE TABLE ticket_bo.pgt_tk_type_commande (
    id_tk_type_commande_auto  bigint,  -- IDTK_TypeCommandeAuto
    id_tk_type_commande       bigint NOT NULL,  -- IDTK_TypeCommande
    lib_type_bs               varchar(50),  -- LibTypeBS
    modif_date                timestamp,  -- ModifDate
    desactiver                boolean,  -- Desactiver
    modif_op                  bigint,  -- ModifOP
    modif_elem                varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_type_commande PRIMARY KEY (id_tk_type_commande),
    CONSTRAINT uq_pgt_tk_type_commande_auto UNIQUE (id_tk_type_commande_auto)
);
CREATE INDEX ix_pgt_tk_type_commande_modif_date ON ticket_bo.pgt_tk_type_commande (modif_date);

CREATE TABLE ticket_bo.pgt_tk_type_resa (
    id_tk_type_resa_auto  bigint,  -- IDTK_TypeResaAuto
    id_tk_type_resa       integer NOT NULL,  -- IDTK_TypeResa
    lib_type_resa         varchar(50),  -- Lib_TypeResa
    modif_date            timestamp,  -- ModifDate
    modif_op              bigint,  -- ModifOP
    modif_elem            varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_type_resa PRIMARY KEY (id_tk_type_resa),
    CONSTRAINT uq_pgt_tk_type_resa_auto UNIQUE (id_tk_type_resa_auto)
);
CREATE INDEX ix_pgt_tk_type_resa_modif_date ON ticket_bo.pgt_tk_type_resa (modif_date);

CREATE TABLE ticket_bo.pgt_tk_type_resa_ss_fam (
    id_tk_type_resa_ss_fam       integer NOT NULL,  -- IDTK_TypeResaSSFam
    lib_type_resa_ss_fam         varchar(50),  -- Lib_TypeResaSSFam
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOP
    modif_elem                   varchar(5),  -- ModifELEM
    id_tk_type_resa              integer,  -- IDTK_TypeResa
    logo                         bytea,  -- LOGO
    id_tk_type_resa_ss_fam_auto  bigint,  -- IDTK_TypeResaSSFamAuto
    CONSTRAINT pk_pgt_tk_type_resa_ss_fam PRIMARY KEY (id_tk_type_resa_ss_fam),
    CONSTRAINT uq_pgt_tk_type_resa_ss_fam_auto UNIQUE (id_tk_type_resa_ss_fam_auto)
);
CREATE INDEX ix_pgt_tk_type_resa_ss_fam_modif_date ON ticket_bo.pgt_tk_type_resa_ss_fam (modif_date);
CREATE INDEX ix_pgt_tk_type_resa_ss_fam_id_tk_type_resa ON ticket_bo.pgt_tk_type_resa_ss_fam (id_tk_type_resa);

CREATE TABLE ticket_bo.pgt_tk_type_sos_bo (
    id_tk_type_sos_bo       bigint NOT NULL,  -- IDTK_TypeSOS_BO
    lib_type_sos            varchar(50),  -- Lib_TypeSos
    modif_op                bigint,  -- ModifOP
    modif_date              timestamp,  -- ModifDate
    modif_elem              varchar(5),  -- ModifELEM
    id_tk_type_sos_bo_auto  bigint,  -- IDTK_TypeSOS_BOAuto
    CONSTRAINT pk_pgt_tk_type_sos_bo PRIMARY KEY (id_tk_type_sos_bo),
    CONSTRAINT uq_pgt_tk_type_sos_bo_auto UNIQUE (id_tk_type_sos_bo_auto)
);
CREATE INDEX ix_pgt_tk_type_sos_bo_modif_date ON ticket_bo.pgt_tk_type_sos_bo (modif_date);
