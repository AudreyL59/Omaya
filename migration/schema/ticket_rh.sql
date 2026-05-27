CREATE SCHEMA IF NOT EXISTS ticket_rh;


CREATE TABLE ticket_rh.pgt_tk_cde_exo_cash (
    id_tk_cde_exo_cash_auto  bigint NOT NULL,  -- IDTK_CdeExoCashAuto
    id_tk_liste              bigint,  -- IDTK_Liste
    id_tk_cde_exo_cash       bigint,  -- IDTK_CdeExoCash
    id_salarie               bigint,  -- IDSalarie
    date_commande            timestamp,  -- DateCommande
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    commande_validee         boolean,  -- CommandeValidée
    date_validation          timestamp,  -- DateValidation
    ope_validation           bigint,  -- OpéValidation
    adresse_livraison        text,  -- AdresseLivraison
    CONSTRAINT pk_pgt_tk_cde_exo_cash PRIMARY KEY (id_tk_cde_exo_cash_auto)
);
CREATE INDEX ix_pgt_tk_cde_exo_cash_id_tk_liste ON ticket_rh.pgt_tk_cde_exo_cash (id_tk_liste);
CREATE INDEX ix_pgt_tk_cde_exo_cash_id_tk_cde_exo_cash ON ticket_rh.pgt_tk_cde_exo_cash (id_tk_cde_exo_cash);
CREATE INDEX ix_pgt_tk_cde_exo_cash_id_salarie ON ticket_rh.pgt_tk_cde_exo_cash (id_salarie);
CREATE INDEX ix_pgt_tk_cde_exo_cash_modif_date ON ticket_rh.pgt_tk_cde_exo_cash (modif_date);

CREATE TABLE ticket_rh.pgt_tk_cde_exo_cash_envoi (
    id_tk_cde_exo_cash_envoi_auto  bigint,  -- IDTK_CdeExoCashEnvoiAuto
    id_tk_cde_exo_cash             bigint,  -- IDTK_CdeExoCash
    id_tk_liste                    bigint,  -- IDTK_Liste
    modif_date                     timestamp,  -- ModifDate
    modif_op                       bigint,  -- ModifOp
    date_envoi                     date,  -- dateEnvoi
    modif_elem                     varchar(5),  -- ModifElem
    num_suivi                      varchar(50),  -- NumSuivi
    id_tk_cde_exo_cash_envoi       bigint NOT NULL,  -- IDTK_CdeExoCashEnvoi
    transporteur                   varchar(50),  -- Transporteur
    adresse_livraison              text,  -- AdresseLivraison
    CONSTRAINT pk_pgt_tk_cde_exo_cash_envoi PRIMARY KEY (id_tk_cde_exo_cash_envoi),
    CONSTRAINT uq_pgt_tk_cde_exo_cash_envoi_auto UNIQUE (id_tk_cde_exo_cash_envoi_auto)
);
CREATE INDEX ix_pgt_tk_cde_exo_cash_envoi_id_tk_cde_exo_cash ON ticket_rh.pgt_tk_cde_exo_cash_envoi (id_tk_cde_exo_cash);
CREATE INDEX ix_pgt_tk_cde_exo_cash_envoi_id_tk_liste ON ticket_rh.pgt_tk_cde_exo_cash_envoi (id_tk_liste);
CREATE INDEX ix_pgt_tk_cde_exo_cash_envoi_modif_date ON ticket_rh.pgt_tk_cde_exo_cash_envoi (modif_date);

CREATE TABLE ticket_rh.pgt_tk_cde_exo_cash_lot (
    id_tk_cde_exo_cash_lot_auto  bigint,  -- IDTK_CdeExoCashLotAuto
    id_tk_cde_exo_cash_lot       bigint NOT NULL,  -- IDTK_CdeExoCashLot
    id_tk_cde_exo_cash           bigint,  -- IDTK_CdeExoCash
    id_tk_liste                  bigint,  -- IDTK_Liste
    id_exo_cash_lot              bigint,  -- IDExoCashLot
    qte                          integer,  -- Qté
    num_suivi                    varchar(50),  -- NumSuivi
    montant_paye                 numeric(19,4),  -- MontantPayé
    modif_op                     bigint,  -- ModifOp
    modif_date                   timestamp,  -- ModifDate
    modif_elem                   varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_cde_exo_cash_lot PRIMARY KEY (id_tk_cde_exo_cash_lot),
    CONSTRAINT uq_pgt_tk_cde_exo_cash_lot_auto UNIQUE (id_tk_cde_exo_cash_lot_auto)
);
CREATE INDEX ix_pgt_tk_cde_exo_cash_lot_id_tk_cde_exo_cash ON ticket_rh.pgt_tk_cde_exo_cash_lot (id_tk_cde_exo_cash);
CREATE INDEX ix_pgt_tk_cde_exo_cash_lot_id_tk_liste ON ticket_rh.pgt_tk_cde_exo_cash_lot (id_tk_liste);
CREATE INDEX ix_pgt_tk_cde_exo_cash_lot_id_exo_cash_lot ON ticket_rh.pgt_tk_cde_exo_cash_lot (id_exo_cash_lot);
CREATE INDEX ix_pgt_tk_cde_exo_cash_lot_modif_date ON ticket_rh.pgt_tk_cde_exo_cash_lot (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demande_att_exo_cash (
    id_tk_demande_att_exo_cash_auto  bigint,  -- IDTk_DemandeAttExoCashAuto
    id_tk_liste                      bigint,  -- IDTK_Liste
    id_tk_demande_att_exo_cash       bigint NOT NULL,  -- IDTk_DemandeAttExoCash
    id_salarie                       bigint,  -- IDSalarie
    montant_ec                       numeric(19,4),  -- MontantEC
    info_attribution                 text,  -- InfoAttribution
    modif_date                       timestamp,  -- ModifDate
    modif_op                         bigint,  -- ModifOp
    modif_elem                       varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_demande_att_exo_cash PRIMARY KEY (id_tk_demande_att_exo_cash),
    CONSTRAINT uq_pgt_tk_demande_att_exo_cash_auto UNIQUE (id_tk_demande_att_exo_cash_auto)
);
CREATE INDEX ix_pgt_tk_demande_att_exo_cash_id_tk_liste ON ticket_rh.pgt_tk_demande_att_exo_cash (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_att_exo_cash_id_salarie ON ticket_rh.pgt_tk_demande_att_exo_cash (id_salarie);
CREATE INDEX ix_pgt_tk_demande_att_exo_cash_modif_date ON ticket_rh.pgt_tk_demande_att_exo_cash (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demande_conges (
    id_tk_demande_conges       bigint NOT NULL,  -- IDTK_DemandeCongés
    id_tk_liste                bigint,  -- IDTK_Liste
    modif_date                 timestamp,  -- ModifDate
    modif_elem                 varchar(5),  -- ModifELEM
    modif_op                   bigint,  -- ModifOP
    id_salarie                 bigint,  -- IDSalarie
    type_conges                text,  -- TypeCongés
    periode_conges             varchar(10),  -- PériodeCongés
    date_debut                 date,  -- DateDébut
    date_fin                   date,  -- DateFin
    signature_demandeur        bytea,  -- SignatureDemandeur
    motifs                     text,  -- Motifs
    id_tk_demande_conges_auto  bigint,  -- IDTK_DemandeCongésAuto
    signature_resp             bytea,  -- SignatureResp
    id_type_absence            integer,  -- IDTypeAbsence
    CONSTRAINT pk_pgt_tk_demande_conges PRIMARY KEY (id_tk_demande_conges),
    CONSTRAINT uq_pgt_tk_demande_conges_auto UNIQUE (id_tk_demande_conges_auto)
);
CREATE INDEX ix_pgt_tk_demande_conges_id_tk_liste ON ticket_rh.pgt_tk_demande_conges (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_conges_modif_date ON ticket_rh.pgt_tk_demande_conges (modif_date);
CREATE INDEX ix_pgt_tk_demande_conges_id_salarie ON ticket_rh.pgt_tk_demande_conges (id_salarie);
CREATE INDEX ix_pgt_tk_demande_conges_date_debut ON ticket_rh.pgt_tk_demande_conges (date_debut);
CREATE INDEX ix_pgt_tk_demande_conges_date_fin ON ticket_rh.pgt_tk_demande_conges (date_fin);
CREATE INDEX ix_pgt_tk_demande_conges_id_type_absence ON ticket_rh.pgt_tk_demande_conges (id_type_absence);

CREATE TABLE ticket_rh.pgt_tk_demande_ctt_w (
    i_ddoc_rhedit              bigint,  -- IDdocRHEDIT
    idorganigramme             bigint,  -- idorganigramme
    i_ddemande_contrat_w       bigint NOT NULL,  -- IDdemandeContratW
    contenu                    bytea,  -- Contenu
    id_salarie                 bigint,  -- IDSalarie
    contrat_genere             boolean,  -- contratGénéré
    contrat_valide             boolean,  -- contratValidé
    id_da                      bigint,  -- idDA
    contrat_signe              boolean,  -- contratSigné
    datesignature              timestamp,  -- datesignature
    contenu_validation         text,  -- ContenuValidation
    contrat_annul              boolean,  -- contratAnnul
    signature                  bytea,  -- Signature
    paraphe                    bytea,  -- paraphe
    lu_app                     bytea,  -- luApp
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOP
    modif_elem                 varchar(5),  -- ModifELEM
    photo_salarie              bytea,  -- PhotoSalarié
    titre_contrat              text,  -- TitreContrat
    type_ctt_w                 text,  -- TypeCttW
    id_tk_liste                bigint,  -- IDTK_Liste
    i_ddemande_contrat_w_auto  bigint,  -- IDdemandeContratWAuto
    CONSTRAINT pk_pgt_tk_demande_ctt_w PRIMARY KEY (i_ddemande_contrat_w),
    CONSTRAINT uq_pgt_tk_demande_ctt_w_auto UNIQUE (i_ddemande_contrat_w_auto)
);
CREATE INDEX ix_pgt_tk_demande_ctt_w_i_ddoc_rhedit ON ticket_rh.pgt_tk_demande_ctt_w (i_ddoc_rhedit);
CREATE INDEX ix_pgt_tk_demande_ctt_w_idorganigramme ON ticket_rh.pgt_tk_demande_ctt_w (idorganigramme);
CREATE INDEX ix_pgt_tk_demande_ctt_w_id_salarie ON ticket_rh.pgt_tk_demande_ctt_w (id_salarie);
CREATE INDEX ix_pgt_tk_demande_ctt_w_contrat_genere ON ticket_rh.pgt_tk_demande_ctt_w (contrat_genere);
CREATE INDEX ix_pgt_tk_demande_ctt_w_contrat_valide ON ticket_rh.pgt_tk_demande_ctt_w (contrat_valide);
CREATE INDEX ix_pgt_tk_demande_ctt_w_id_da ON ticket_rh.pgt_tk_demande_ctt_w (id_da);
CREATE INDEX ix_pgt_tk_demande_ctt_w_contrat_signe ON ticket_rh.pgt_tk_demande_ctt_w (contrat_signe);
CREATE INDEX ix_pgt_tk_demande_ctt_w_modif_date ON ticket_rh.pgt_tk_demande_ctt_w (modif_date);
CREATE INDEX ix_pgt_tk_demande_ctt_w_id_tk_liste ON ticket_rh.pgt_tk_demande_ctt_w (id_tk_liste);

CREATE TABLE ticket_rh.pgt_tk_demandecttw_doc (
    id_tk_demande_ctt_w_doc  bigint NOT NULL,  -- IDTk_DemandeCttW_Doc
    i_ddemande_contrat_w     bigint,  -- IDdemandeContratW
    id_tk_liste              bigint,  -- IDTK_Liste
    type_doc                 varchar(50),  -- TypeDoc
    nom_fichier              varchar(50),  -- NomFichier
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOP
    modif_elem               varchar(5),  -- ModifELEM
    doc_present              boolean,  -- DocPresent
    CONSTRAINT pk_pgt_tk_demandecttw_doc PRIMARY KEY (id_tk_demande_ctt_w_doc)
);
CREATE INDEX ix_pgt_tk_demandecttw_doc_i_ddemande_contrat_w ON ticket_rh.pgt_tk_demandecttw_doc (i_ddemande_contrat_w);
CREATE INDEX ix_pgt_tk_demandecttw_doc_id_tk_liste ON ticket_rh.pgt_tk_demandecttw_doc (id_tk_liste);
CREATE INDEX ix_pgt_tk_demandecttw_doc_modif_date ON ticket_rh.pgt_tk_demandecttw_doc (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demande_mutuelle (
    id_tk_demande_mutuelle_auto  bigint,  -- IDTK_DemandeMutuelleAuto
    id_tk_demande_mutuelle       bigint NOT NULL,  -- IDTK_DemandeMutuelle
    id_tk_liste                  bigint,  -- IDTK_Liste
    id_salarie                   bigint,  -- IDSalarie
    demande_affiliation          boolean,  -- DemandeAffiliation
    demande_affiliation_date     date,  -- DemandeAffiliationDate
    info_cplt                    text,  -- InfoCplt
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOp
    modif_elem                   varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_demande_mutuelle PRIMARY KEY (id_tk_demande_mutuelle),
    CONSTRAINT uq_pgt_tk_demande_mutuelle_auto UNIQUE (id_tk_demande_mutuelle_auto)
);
CREATE INDEX ix_pgt_tk_demande_mutuelle_id_tk_liste ON ticket_rh.pgt_tk_demande_mutuelle (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_mutuelle_id_salarie ON ticket_rh.pgt_tk_demande_mutuelle (id_salarie);
CREATE INDEX ix_pgt_tk_demande_mutuelle_modif_date ON ticket_rh.pgt_tk_demande_mutuelle (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demande_mutuelle_fic (
    id_tk_demande_mutuelle_fic  bigint NOT NULL,  -- IDTK_DemandeMutuelle_FIC
    id_tk_demande_mutuelle      bigint,  -- IDTK_DemandeMutuelle
    id_tk_liste                 bigint,  -- IDTK_Liste
    chemin_fic                  varchar(50),  -- CheminFic
    nom_fichier                 text,  -- NomFichier
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOp
    modif_elem                  varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tk_demande_mutuelle_fic PRIMARY KEY (id_tk_demande_mutuelle_fic)
);
CREATE INDEX ix_pgt_tk_demande_mutuelle_fic_id_tk_demande_mutuelle ON ticket_rh.pgt_tk_demande_mutuelle_fic (id_tk_demande_mutuelle);
CREATE INDEX ix_pgt_tk_demande_mutuelle_fic_id_tk_liste ON ticket_rh.pgt_tk_demande_mutuelle_fic (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_mutuelle_fic_modif_date ON ticket_rh.pgt_tk_demande_mutuelle_fic (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demandesignpv_photo (
    id_tk_demande_sign_pv_photo  bigint NOT NULL,  -- IDTK_DemandeSignPV_Photo
    i_ddemande_sign_ulease_auto  bigint,  -- IDdemandeSignUleaseAuto
    id_type_capacite_photo       bigint,  -- IDTypeCapacite_Photo
    photo                        bytea,  -- Photo
    note_etat                    smallint,  -- NoteEtat
    date_photo                   timestamp,  -- DatePhoto
    op_photo                     bigint,  -- OpPhoto
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOP
    modif_elem                   varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demandesignpv_photo PRIMARY KEY (id_tk_demande_sign_pv_photo)
);
CREATE INDEX ix_pgt_tk_demandesignpv_photo_i_ddemande_sign_ulease_auto ON ticket_rh.pgt_tk_demandesignpv_photo (i_ddemande_sign_ulease_auto);
CREATE INDEX ix_pgt_tk_demandesignpv_photo_id_type_capacite_photo ON ticket_rh.pgt_tk_demandesignpv_photo (id_type_capacite_photo);
CREATE INDEX ix_pgt_tk_demandesignpv_photo_modif_date ON ticket_rh.pgt_tk_demandesignpv_photo (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demande_sign_pv_ulease (
    i_ddemande_sign_pv_ulease_auto  bigint,  -- IDdemandeSignPVUleaseAuto
    i_ddemande_sign_pv_ulease       bigint NOT NULL,  -- IDdemandeSignPVUlease
    id_tk_liste                     bigint,  -- IDTK_Liste
    idorganigramme                  bigint,  -- idorganigramme
    id_salarie_ulease               bigint,  -- IDSalarie_Ulease
    id_salarie                      bigint,  -- IDSalarie
    id_da                           bigint,  -- idDA
    id_pc                           bigint,  -- IdPC
    titre_contrat                   text,  -- TitreContrat
    contrat_genere                  boolean,  -- contratGénéré
    contrat_valide                  boolean,  -- contratValidé
    contrat_signe                   boolean,  -- contratSigné
    contrat_annul                   boolean,  -- contratAnnul
    datesignature                   timestamp,  -- datesignature
    contenu_validation              text,  -- ContenuValidation
    photo_salarie                   bytea,  -- PhotoSalarié
    signature                       bytea,  -- Signature
    paraphe                         bytea,  -- paraphe
    lu_app                          bytea,  -- luApp
    observations                    text,  -- Observations
    modif_date                      timestamp,  -- ModifDate
    modif_op                        bigint,  -- ModifOP
    modif_elem                      varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_sign_pv_ulease PRIMARY KEY (i_ddemande_sign_pv_ulease),
    CONSTRAINT uq_pgt_tk_demande_sign_pv_ulease_auto UNIQUE (i_ddemande_sign_pv_ulease_auto)
);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_id_tk_liste ON ticket_rh.pgt_tk_demande_sign_pv_ulease (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_idorganigramme ON ticket_rh.pgt_tk_demande_sign_pv_ulease (idorganigramme);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_id_salarie_ulease ON ticket_rh.pgt_tk_demande_sign_pv_ulease (id_salarie_ulease);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_id_salarie ON ticket_rh.pgt_tk_demande_sign_pv_ulease (id_salarie);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_id_da ON ticket_rh.pgt_tk_demande_sign_pv_ulease (id_da);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_contrat_genere ON ticket_rh.pgt_tk_demande_sign_pv_ulease (contrat_genere);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_contrat_valide ON ticket_rh.pgt_tk_demande_sign_pv_ulease (contrat_valide);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_contrat_signe ON ticket_rh.pgt_tk_demande_sign_pv_ulease (contrat_signe);
CREATE INDEX ix_pgt_tk_demande_sign_pv_ulease_modif_date ON ticket_rh.pgt_tk_demande_sign_pv_ulease (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demande_sign_ulease (
    i_ddemande_sign_ulease_auto  bigint,  -- IDdemandeSignUleaseAuto
    i_ddemande_sign_ulease       bigint NOT NULL,  -- IDdemandeSignUlease
    id_tk_liste                  bigint,  -- IDTK_Liste
    idorganigramme               bigint,  -- idorganigramme
    id_salarie_ulease            bigint,  -- IDSalarie_Ulease
    contenu                      bytea,  -- Contenu
    id_salarie                   bigint,  -- IDSalarie
    id_da                        bigint,  -- idDA
    id_pc                        bigint,  -- IdPC
    type_ctt_w                   text,  -- TypeCttW
    titre_contrat                text,  -- TitreContrat
    contrat_genere               boolean,  -- contratGénéré
    contrat_valide               boolean,  -- contratValidé
    contrat_signe                boolean,  -- contratSigné
    contrat_annul                boolean,  -- contratAnnul
    datesignature                timestamp,  -- datesignature
    contenu_validation           text,  -- ContenuValidation
    photo_salarie                bytea,  -- PhotoSalarié
    signature                    bytea,  -- Signature
    paraphe                      bytea,  -- paraphe
    lu_app                       bytea,  -- luApp
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOP
    modif_elem                   varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_sign_ulease PRIMARY KEY (i_ddemande_sign_ulease),
    CONSTRAINT uq_pgt_tk_demande_sign_ulease_auto UNIQUE (i_ddemande_sign_ulease_auto)
);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_id_tk_liste ON ticket_rh.pgt_tk_demande_sign_ulease (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_idorganigramme ON ticket_rh.pgt_tk_demande_sign_ulease (idorganigramme);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_id_salarie_ulease ON ticket_rh.pgt_tk_demande_sign_ulease (id_salarie_ulease);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_id_salarie ON ticket_rh.pgt_tk_demande_sign_ulease (id_salarie);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_id_da ON ticket_rh.pgt_tk_demande_sign_ulease (id_da);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_contrat_genere ON ticket_rh.pgt_tk_demande_sign_ulease (contrat_genere);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_contrat_valide ON ticket_rh.pgt_tk_demande_sign_ulease (contrat_valide);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_contrat_signe ON ticket_rh.pgt_tk_demande_sign_ulease (contrat_signe);
CREATE INDEX ix_pgt_tk_demande_sign_ulease_modif_date ON ticket_rh.pgt_tk_demande_sign_ulease (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demande_sortie_rh (
    id_tk_demande_sortie_rh       bigint NOT NULL,  -- IDTK_DemandeSortieRH
    type_sortie                   varchar(20),  -- TypeSortie
    id_salarie                    bigint,  -- IDSalarie
    id_tk_liste                   bigint,  -- IDTK_Liste
    info_cplt                     text,  -- InfoCplt
    modif_op                      bigint,  -- ModifOP
    modif_date                    timestamp,  -- ModifDate
    modif_elem                    varchar(5),  -- ModifELEM
    doc_sortie                    boolean,  -- DocSortie
    id_tk_demande_sortie_rh_auto  bigint,  -- IDTK_DemandeSortieRHAuto
    CONSTRAINT pk_pgt_tk_demande_sortie_rh PRIMARY KEY (id_tk_demande_sortie_rh),
    CONSTRAINT uq_pgt_tk_demande_sortie_rh_auto UNIQUE (id_tk_demande_sortie_rh_auto)
);
CREATE INDEX ix_pgt_tk_demande_sortie_rh_id_salarie ON ticket_rh.pgt_tk_demande_sortie_rh (id_salarie);
CREATE INDEX ix_pgt_tk_demande_sortie_rh_id_tk_liste ON ticket_rh.pgt_tk_demande_sortie_rh (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_sortie_rh_modif_date ON ticket_rh.pgt_tk_demande_sortie_rh (modif_date);

CREATE TABLE ticket_rh.pgt_tk_demande_sos_ju (
    id_tk_demande_sos_ju_auto  bigint,  -- IDTK_DemandeSOS_JUAuto
    id_tk_demande_sos_ju       bigint NOT NULL,  -- IDTK_DemandeSOS_JU
    id_tk_liste                bigint,  -- IDTK_Liste
    id_tk_type_sos_ju          bigint,  -- IDTK_TypeSOS_JU
    id_elem                    bigint,  -- IdElem
    ref_demande                text,  -- RefDemande
    descriptif                 text,  -- Descriptif
    modif_op                   bigint,  -- ModifOP
    modif_date                 timestamp,  -- ModifDate
    modif_elem                 varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_demande_sos_ju PRIMARY KEY (id_tk_demande_sos_ju),
    CONSTRAINT uq_pgt_tk_demande_sos_ju_auto UNIQUE (id_tk_demande_sos_ju_auto)
);
CREATE INDEX ix_pgt_tk_demande_sos_ju_id_tk_liste ON ticket_rh.pgt_tk_demande_sos_ju (id_tk_liste);
CREATE INDEX ix_pgt_tk_demande_sos_ju_id_tk_type_sos_ju ON ticket_rh.pgt_tk_demande_sos_ju (id_tk_type_sos_ju);
CREATE INDEX ix_pgt_tk_demande_sos_ju_modif_date ON ticket_rh.pgt_tk_demande_sos_ju (modif_date);

CREATE TABLE ticket_rh.pgt_tk_type_sos_ju (
    id_tk_type_sos_ju_auto  bigint,  -- IDTK_TypeSOS_JUAuto
    id_tk_type_sos_ju       bigint NOT NULL,  -- IDTK_TypeSOS_JU
    lib_type_sos            varchar(50),  -- Lib_TypeSos
    type_form               varchar(15),  -- TypeForm
    modif_op                bigint,  -- ModifOP
    modif_date              timestamp,  -- ModifDate
    modif_elem              varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_type_sos_ju PRIMARY KEY (id_tk_type_sos_ju),
    CONSTRAINT uq_pgt_tk_type_sos_ju_auto UNIQUE (id_tk_type_sos_ju_auto)
);
CREATE INDEX ix_pgt_tk_type_sos_ju_modif_date ON ticket_rh.pgt_tk_type_sos_ju (modif_date);
