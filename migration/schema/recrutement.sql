CREATE SCHEMA IF NOT EXISTS recrutement;


CREATE TABLE recrutement.pgt_agenda_categorie (
    id_agenda_categorie       bigint NOT NULL,  -- IDAgendaCatégorie
    lib_categorie             text,  -- Lib_Catégorie
    couleur_r                 integer,  -- CouleurR
    couleur_v                 integer,  -- CouleurV
    id_cv_statut              bigint,  -- IdCvStatut
    couleur_b                 integer,  -- CouleurB
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOP
    modif_elem                varchar(5),  -- ModifELEM
    id_agenda_categorie_auto  bigint,  -- IDAgendaCatégorieAuto
    CONSTRAINT pk_pgt_agenda_categorie PRIMARY KEY (id_agenda_categorie),
    CONSTRAINT uq_pgt_agenda_categorie_auto UNIQUE (id_agenda_categorie_auto)
);
CREATE INDEX ix_pgt_agenda_categorie_id_cv_statut ON recrutement.pgt_agenda_categorie (id_cv_statut);
CREATE INDEX ix_pgt_agenda_categorie_modif_date ON recrutement.pgt_agenda_categorie (modif_date);

CREATE TABLE recrutement.pgt_agenda_evenement (
    id_salon_visio            bigint,  -- IDSalonVisio
    id_cv_suivi               bigint,  -- IDCvSuivi
    id_tk_liste               bigint,  -- IDTK_Liste
    id_salarie                bigint,  -- IDSalarie
    id_agenda_evenement       bigint NOT NULL,  -- IDAgendaEvénement
    titre                     text,  -- Titre
    contenu                   text,  -- Contenu
    date_debut                timestamp,  -- DateDébut
    date_fin                  timestamp,  -- DateFin
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOP
    id_cv_lieux               bigint,  -- IdCvLieux
    id_categorie              integer,  -- IDCatégorie
    id_prevision_recrut       bigint,  -- IDprevisionRecrut
    modif_elem                varchar(5),  -- ModifELEM
    op_crea                   bigint,  -- OPCrea
    id_agenda_evenement_auto  bigint,  -- IDAgendaEvénementAuto
    datecrea                  timestamp,  -- Datecrea
    motif_statut              text,  -- MotifStatut
    pb_presentation           boolean,  -- Pb_Presentation
    pb_elocution              boolean,  -- Pb_Elocution
    pb_motivation             boolean,  -- Pb_Motivation
    pb_horaires               boolean,  -- Pb_Horaires
    CONSTRAINT pk_pgt_agenda_evenement PRIMARY KEY (id_agenda_evenement),
    CONSTRAINT uq_pgt_agenda_evenement_auto UNIQUE (id_agenda_evenement_auto)
);
CREATE INDEX ix_pgt_agenda_evenement_id_salon_visio ON recrutement.pgt_agenda_evenement (id_salon_visio);
CREATE INDEX ix_pgt_agenda_evenement_id_cv_suivi ON recrutement.pgt_agenda_evenement (id_cv_suivi);
CREATE INDEX ix_pgt_agenda_evenement_id_tk_liste ON recrutement.pgt_agenda_evenement (id_tk_liste);
CREATE INDEX ix_pgt_agenda_evenement_id_salarie ON recrutement.pgt_agenda_evenement (id_salarie);
CREATE INDEX ix_pgt_agenda_evenement_date_debut ON recrutement.pgt_agenda_evenement (date_debut);
CREATE INDEX ix_pgt_agenda_evenement_modif_date ON recrutement.pgt_agenda_evenement (modif_date);
CREATE INDEX ix_pgt_agenda_evenement_id_categorie ON recrutement.pgt_agenda_evenement (id_categorie);
CREATE INDEX ix_pgt_agenda_evenement_id_prevision_recrut ON recrutement.pgt_agenda_evenement (id_prevision_recrut);

CREATE TABLE recrutement.pgt_annuaire (
    id_cv_lieu_rdv                    bigint,  -- IDcvLieuRdv
    id_annuaire                       bigint NOT NULL,  -- IDannuaire
    id_annuaire_auto                  bigint,  -- IDannuaireAuto
    intitule                          text,  -- Intitulé
    detail                            text,  -- Détail
    adresse                           text,  -- Adresse
    telephone1                        varchar(12),  -- Téléphone1
    telephone2                        varchar(12),  -- Téléphone2
    telephone3                        varchar(12),  -- Téléphone3
    mail1                             text,  -- Mail1
    mail2                             text,  -- Mail2
    mail3                             text,  -- Mail3
    mots_cles                         text,  -- MotsClés
    nom_contact1                      text,  -- NomContact1
    nom_contact2                      text,  -- NomContact2
    nom_contact3                      text,  -- NomContact3
    cpl_adr                           text,  -- CplAdr
    modif_date                        timestamp,  -- ModifDate
    modif_elem                        varchar(5),  -- ModifElem
    modif_op                          bigint,  -- ModifOp
    id_communes_france                bigint,  -- IDCommunesFrance
    telephone1_telephone2_telephone3  varchar(36),  -- Téléphone1Téléphone2Téléphone3
    CONSTRAINT pk_pgt_annuaire PRIMARY KEY (id_annuaire),
    CONSTRAINT uq_pgt_annuaire_auto UNIQUE (id_annuaire_auto)
);
CREATE INDEX ix_pgt_annuaire_id_cv_lieu_rdv ON recrutement.pgt_annuaire (id_cv_lieu_rdv);
CREATE INDEX ix_pgt_annuaire_telephone1 ON recrutement.pgt_annuaire (telephone1);
CREATE INDEX ix_pgt_annuaire_telephone2 ON recrutement.pgt_annuaire (telephone2);
CREATE INDEX ix_pgt_annuaire_telephone3 ON recrutement.pgt_annuaire (telephone3);
CREATE INDEX ix_pgt_annuaire_mail1 ON recrutement.pgt_annuaire (mail1);
CREATE INDEX ix_pgt_annuaire_mail2 ON recrutement.pgt_annuaire (mail2);
CREATE INDEX ix_pgt_annuaire_mail3 ON recrutement.pgt_annuaire (mail3);
CREATE INDEX ix_pgt_annuaire_mots_cles ON recrutement.pgt_annuaire (mots_cles);
CREATE INDEX ix_pgt_annuaire_modif_date ON recrutement.pgt_annuaire (modif_date);
CREATE INDEX ix_pgt_annuaire_id_communes_france ON recrutement.pgt_annuaire (id_communes_france);

CREATE TABLE recrutement.pgt_cv_annonceur (
    id_cv_annonceur_auto  bigint,  -- IDCvAnnonceurAuto
    id_cv_annonceur       bigint NOT NULL,  -- IDCvAnnonceur
    lib_annonceur         varchar(50),  -- Lib_Annonceur
    logo                  bytea,  -- Logo
    is_actif              boolean,  -- IsActif
    modif_date            timestamp,  -- ModifDate
    modif_op              bigint,  -- ModifOp
    modif_elem            varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_cv_annonceur PRIMARY KEY (id_cv_annonceur),
    CONSTRAINT uq_pgt_cv_annonceur_auto UNIQUE (id_cv_annonceur_auto)
);
CREATE INDEX ix_pgt_cv_annonceur_lib_annonceur ON recrutement.pgt_cv_annonceur (lib_annonceur);
CREATE INDEX ix_pgt_cv_annonceur_is_actif ON recrutement.pgt_cv_annonceur (is_actif);
CREATE INDEX ix_pgt_cv_annonceur_modif_date ON recrutement.pgt_cv_annonceur (modif_date);

CREATE TABLE recrutement.pgt_cv_lieu_rdv (
    id_cv_lieu_rdv_auto  bigint,  -- IDCvLieuRdvAuto
    id_cv_lieu_rdv       bigint NOT NULL,  -- IDcvLieuRdv
    lib_lieu             varchar(50),  -- Lib_Lieu
    adresse1             text,  -- ADRESSE1
    adresse2             text,  -- ADRESSE2
    id_communes_france   bigint,  -- IDCommunesFrance
    latitude_deg         double precision,  -- latitude_deg
    longitude_deg        double precision,  -- longitude_deg
    is_actif             boolean,  -- IsActif
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_cv_lieu_rdv PRIMARY KEY (id_cv_lieu_rdv),
    CONSTRAINT uq_pgt_cv_lieu_rdv_auto UNIQUE (id_cv_lieu_rdv_auto)
);
CREATE INDEX ix_pgt_cv_lieu_rdv_id_communes_france ON recrutement.pgt_cv_lieu_rdv (id_communes_france);
CREATE INDEX ix_pgt_cv_lieu_rdv_latitude_deg ON recrutement.pgt_cv_lieu_rdv (latitude_deg);
CREATE INDEX ix_pgt_cv_lieu_rdv_longitude_deg ON recrutement.pgt_cv_lieu_rdv (longitude_deg);
CREATE INDEX ix_pgt_cv_lieu_rdv_modif_date ON recrutement.pgt_cv_lieu_rdv (modif_date);

CREATE TABLE recrutement.pgt_cvposte (
    id_cv_poste_auto  bigint,  -- IDCvPosteAuto
    id_cvposte        bigint NOT NULL,  -- IDcvposte
    lib_poste         varchar(30),  -- Lib_Poste
    is_actif          boolean,  -- IsActif
    modif_date        timestamp,  -- ModifDate
    modif_op          bigint,  -- ModifOp
    modif_elem        varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_cvposte PRIMARY KEY (id_cvposte),
    CONSTRAINT uq_pgt_cvposte_auto UNIQUE (id_cv_poste_auto)
);
CREATE INDEX ix_pgt_cvposte_lib_poste ON recrutement.pgt_cvposte (lib_poste);
CREATE INDEX ix_pgt_cvposte_modif_date ON recrutement.pgt_cvposte (modif_date);

CREATE TABLE recrutement.pgt_cv_source (
    id_cv_source_auto  bigint,  -- IDCvSourceAuto
    id_cvsource        bigint NOT NULL,  -- IDcvsource
    lib_source         varchar(30),  -- Lib_Source
    is_actif           boolean,  -- IsActif
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOp
    modif_elem         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_cv_source PRIMARY KEY (id_cvsource),
    CONSTRAINT uq_pgt_cv_source_auto UNIQUE (id_cv_source_auto)
);
CREATE INDEX ix_pgt_cv_source_is_actif ON recrutement.pgt_cv_source (is_actif);
CREATE INDEX ix_pgt_cv_source_modif_date ON recrutement.pgt_cv_source (modif_date);

CREATE TABLE recrutement.pgt_cvstatut (
    id_cv_statut_auto  bigint,  -- IDCvStatutAuto
    id_cv_statut       bigint NOT NULL,  -- IdCvStatut
    lib_statut         varchar(30),  -- LibStatut
    icone              bytea,  -- Icone
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOp
    modif_elem         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_cvstatut PRIMARY KEY (id_cv_statut),
    CONSTRAINT uq_pgt_cvstatut_auto UNIQUE (id_cv_statut_auto)
);
CREATE INDEX ix_pgt_cvstatut_modif_date ON recrutement.pgt_cvstatut (modif_date);

CREATE TABLE recrutement.pgt_cvsuivi (
    id_cv_suivi                                          bigint NOT NULL,  -- IDCvSuivi
    id_cvtheque                                          bigint,  -- IDcvtheque
    datecrea                                             timestamp,  -- Datecrea
    op_crea                                              bigint,  -- OPCREA
    id_cv_statut                                         bigint,  -- IdCvStatut
    type_elem                                            varchar(10),  -- TypeElem
    id_elem                                              bigint,  -- IdElem
    observation                                          text,  -- Observation
    modif_date                                           timestamp,  -- ModifDate
    modif_op                                             bigint,  -- ModifOp
    modif_elem                                           varchar(5),  -- ModifElem
    id_cvtheque_datecrea_id_cv_statut_type_elem_id_elem  varchar(42),  -- IDcvthequeDatecreaIdCvStatutTypeElemIdElem
    CONSTRAINT pk_pgt_cvsuivi PRIMARY KEY (id_cv_suivi)
);
CREATE INDEX ix_pgt_cvsuivi_id_cvtheque ON recrutement.pgt_cvsuivi (id_cvtheque);
CREATE INDEX ix_pgt_cvsuivi_id_cv_statut ON recrutement.pgt_cvsuivi (id_cv_statut);
CREATE INDEX ix_pgt_cvsuivi_modif_date ON recrutement.pgt_cvsuivi (modif_date);

CREATE TABLE recrutement.pgt_cvtheque (
    id_cvtheque_auto    bigint,  -- IDcvthequeAuto
    id_cvtheque         bigint NOT NULL,  -- IDcvtheque
    origine             smallint,  -- Origine
    nom                 text,  -- NOM
    pays                text,  -- PAYS
    prenom              text,  -- PRENOM
    adresse             text,  -- Adresse
    date_naissance      date,  -- DateNaissance
    permis_b            boolean,  -- PermisB
    vehicule            boolean,  -- Véhicule
    mail                text,  -- MAIL
    gsm                 text,  -- GSM
    id_communes_france  bigint,  -- IDCommunesFrance
    fic_cv              text,  -- Fic_CV
    id_cvposte          bigint,  -- IDcvposte
    id_cvsource         bigint,  -- IDcvsource
    id_elem_source      bigint,  -- IdElemSource
    id_ste              bigint,  -- IdSte
    date_saisie         timestamp,  -- DateSAISIE
    ope_saisie          bigint,  -- Opé_SAISIE
    date_reac           timestamp,  -- DateREAC
    ope_reac            bigint,  -- Opé_REAC
    date_rappel         date,  -- DateRappel
    observ              text,  -- OBSERV
    traite_en_cours     boolean,  -- TraiteEnCours
    op_traite           bigint,  -- opTraite
    date_traite         timestamp,  -- DateTraite
    mots_cles           text,  -- MotsClés
    modif_op            bigint,  -- ModifOP
    modif_date          timestamp,  -- ModifDate
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_cvtheque PRIMARY KEY (id_cvtheque),
    CONSTRAINT uq_pgt_cvtheque_auto UNIQUE (id_cvtheque_auto)
);
CREATE INDEX ix_pgt_cvtheque_origine ON recrutement.pgt_cvtheque (origine);
CREATE INDEX ix_pgt_cvtheque_date_naissance ON recrutement.pgt_cvtheque (date_naissance);
CREATE INDEX ix_pgt_cvtheque_permis_b ON recrutement.pgt_cvtheque (permis_b);
CREATE INDEX ix_pgt_cvtheque_vehicule ON recrutement.pgt_cvtheque (vehicule);
CREATE INDEX ix_pgt_cvtheque_gsm ON recrutement.pgt_cvtheque (gsm);
CREATE INDEX ix_pgt_cvtheque_id_communes_france ON recrutement.pgt_cvtheque (id_communes_france);
CREATE INDEX ix_pgt_cvtheque_id_cvposte ON recrutement.pgt_cvtheque (id_cvposte);
CREATE INDEX ix_pgt_cvtheque_id_cvsource ON recrutement.pgt_cvtheque (id_cvsource);
CREATE INDEX ix_pgt_cvtheque_id_elem_source ON recrutement.pgt_cvtheque (id_elem_source);
CREATE INDEX ix_pgt_cvtheque_id_ste ON recrutement.pgt_cvtheque (id_ste);
CREATE INDEX ix_pgt_cvtheque_date_saisie ON recrutement.pgt_cvtheque (date_saisie);
CREATE INDEX ix_pgt_cvtheque_ope_saisie ON recrutement.pgt_cvtheque (ope_saisie);
CREATE INDEX ix_pgt_cvtheque_date_reac ON recrutement.pgt_cvtheque (date_reac);
CREATE INDEX ix_pgt_cvtheque_ope_reac ON recrutement.pgt_cvtheque (ope_reac);
CREATE INDEX ix_pgt_cvtheque_date_rappel ON recrutement.pgt_cvtheque (date_rappel);
CREATE INDEX ix_pgt_cvtheque_modif_date ON recrutement.pgt_cvtheque (modif_date);

CREATE TABLE recrutement.pgt_cvtheque_temporaire (
    id_cvposte          bigint,  -- IDcvposte
    id_cvsource         bigint,  -- IDcvsource
    id_elem_source      bigint,  -- IdElemSource
    adr_mail_rh         text,  -- AdrMailRH
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    id_cvtheque         bigint,  -- IDcvtheque
    nom                 text,  -- NOM
    prenom              text,  -- PRENOM
    pays                text,  -- PAYS
    fic_cv              text,  -- Fic_CV
    mail                text,  -- MAIL
    id_ste              bigint,  -- IdSte
    gsm                 text,  -- GSM
    observ              text,  -- OBSERV
    modif_elem          varchar(5),  -- ModifELEM
    id_cvtheque_auto    bigint NOT NULL,  -- IDcvthequeAuto
    id_communes_france  bigint,  -- IDCommunesFrance
    cp                  varchar(5),  -- CP
    ville               text,  -- VILLE
    lien_cv             text,  -- LienCV
    mail_objet          text,  -- Mail_Objet
    mail_contenu        text,  -- Mail_Contenu
    mail_date           timestamp,  -- Mail_Date
    CONSTRAINT pk_pgt_cvtheque_temporaire PRIMARY KEY (id_cvtheque_auto)
);
CREATE INDEX ix_pgt_cvtheque_temporaire_id_cvposte ON recrutement.pgt_cvtheque_temporaire (id_cvposte);
CREATE INDEX ix_pgt_cvtheque_temporaire_id_cvsource ON recrutement.pgt_cvtheque_temporaire (id_cvsource);
CREATE INDEX ix_pgt_cvtheque_temporaire_id_elem_source ON recrutement.pgt_cvtheque_temporaire (id_elem_source);
CREATE INDEX ix_pgt_cvtheque_temporaire_adr_mail_rh ON recrutement.pgt_cvtheque_temporaire (adr_mail_rh);
CREATE INDEX ix_pgt_cvtheque_temporaire_modif_date ON recrutement.pgt_cvtheque_temporaire (modif_date);
CREATE INDEX ix_pgt_cvtheque_temporaire_id_cvtheque ON recrutement.pgt_cvtheque_temporaire (id_cvtheque);
CREATE INDEX ix_pgt_cvtheque_temporaire_id_ste ON recrutement.pgt_cvtheque_temporaire (id_ste);
CREATE INDEX ix_pgt_cvtheque_temporaire_gsm ON recrutement.pgt_cvtheque_temporaire (gsm);
CREATE INDEX ix_pgt_cvtheque_temporaire_id_communes_france ON recrutement.pgt_cvtheque_temporaire (id_communes_france);

CREATE TABLE recrutement.pgt_mail_refus_rh (
    id_mail_refus_rh     bigint,  -- IDMailRefusRH
    id_agenda_evenement  bigint NOT NULL,  -- IDAgendaEvénement
    date_envoi           timestamp,  -- dateEnvoi
    contenu_mail         text,  -- ContenuMail
    mail_dest            text,  -- MailDest
    CONSTRAINT pk_pgt_mail_refus_rh PRIMARY KEY (id_agenda_evenement),
    CONSTRAINT uq_pgt_mail_refus_rh_auto UNIQUE (id_mail_refus_rh)
);

CREATE TABLE recrutement.pgt_mails_rh_cv (
    srv_entrant     text,  -- Srv_entrant
    num_port        integer,  -- NumPort
    type_srv        varchar(10),  -- TYPE_Srv
    adr_mail_rh     text NOT NULL,  -- AdrMailRH
    mdp             text,  -- MDP
    modif_op        bigint,  -- ModifOP
    modif_date      timestamp,  -- ModifDate
    modif_elem      varchar(5),  -- ModifELEM
    id_ste          bigint,  -- IdSte
    id_cv_poste     bigint,  -- IDCvPoste
    id_mails_rh_cv  bigint,  -- IDmails_RH_CV
    import_externe  boolean,  -- ImportExterne
    is_actif        boolean,  -- IsActif
    CONSTRAINT pk_pgt_mails_rh_cv PRIMARY KEY (adr_mail_rh),
    CONSTRAINT uq_pgt_mails_rh_cv_auto UNIQUE (id_mails_rh_cv)
);
CREATE INDEX ix_pgt_mails_rh_cv_modif_date ON recrutement.pgt_mails_rh_cv (modif_date);
CREATE INDEX ix_pgt_mails_rh_cv_id_ste ON recrutement.pgt_mails_rh_cv (id_ste);
CREATE INDEX ix_pgt_mails_rh_cv_id_cv_poste ON recrutement.pgt_mails_rh_cv (id_cv_poste);

CREATE TABLE recrutement.pgt_portail_partenaire (
    id_portail_partenaire_auto  bigint,  -- IDportailPartenaireAuto
    id_portail_partenaire       bigint NOT NULL,  -- IDportailPartenaire
    id_partenaire               bigint,  -- IDPartenaire
    lien_portail                text,  -- LienPortail
    login                       text,  -- LOGIN
    mdp                         text,  -- MDP
    id_entite                   varchar(20),  -- IdEntité
    mail_contact                text,  -- MailContact
    is_actif                    boolean,  -- IsActif
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOP
    modif_elem                  varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_portail_partenaire PRIMARY KEY (id_portail_partenaire),
    CONSTRAINT uq_pgt_portail_partenaire_auto UNIQUE (id_portail_partenaire_auto)
);
CREATE INDEX ix_pgt_portail_partenaire_id_partenaire ON recrutement.pgt_portail_partenaire (id_partenaire);
CREATE INDEX ix_pgt_portail_partenaire_login ON recrutement.pgt_portail_partenaire (login);
CREATE INDEX ix_pgt_portail_partenaire_id_entite ON recrutement.pgt_portail_partenaire (id_entite);
CREATE INDEX ix_pgt_portail_partenaire_modif_date ON recrutement.pgt_portail_partenaire (modif_date);

CREATE TABLE recrutement.pgt_prev_recrut (
    id_cv_lieu_rdv            bigint,  -- IDcvLieuRdv
    id_prev_recrut_etat       bigint,  -- IDprevRecrutEtat
    id_prevision_recrut       bigint NOT NULL,  -- IDprevisionRecrut
    idorganigramme            bigint,  -- idorganigramme
    date_debut                date,  -- DateDébut
    date_fin                  date,  -- DateFin
    modif_date                timestamp,  -- ModifDate
    modif_elem                varchar(5),  -- ModifElem
    date_session              date,  -- dateSession
    potentiel_accueil         integer,  -- PotentielAccueil
    modif_op                  bigint,  -- ModifOp
    nb_prod                   integer,  -- NBProd
    coopt_smoins1             integer,  -- cooptSmoins1
    coopt_jmoins2             integer,  -- cooptJmoins2
    sourcing_smoins1          integer,  -- SourcingSmoins1
    sourcing_jmoins2          integer,  -- SourcingJmoins2
    taille_session            integer,  -- tailleSession
    obj_coopt                 integer,  -- objCoopt
    obj_sourcing              integer,  -- objSourcing
    date_butoire              date,  -- DateButoire
    commentaire               text,  -- commentaire
    id_communes_france        bigint,  -- IDCommunesFrance
    nb_coopt_mini             integer,  -- NbCooptMini
    nb_sourcing_mini          integer,  -- NbSourcingMini
    id_prevision_recrut_auto  bigint,  -- IDprevisionRecrutAuto
    id_recruteur              bigint,  -- IdRecruteur
    CONSTRAINT pk_pgt_prev_recrut PRIMARY KEY (id_prevision_recrut),
    CONSTRAINT uq_pgt_prev_recrut_auto UNIQUE (id_prevision_recrut_auto)
);
CREATE INDEX ix_pgt_prev_recrut_id_cv_lieu_rdv ON recrutement.pgt_prev_recrut (id_cv_lieu_rdv);
CREATE INDEX ix_pgt_prev_recrut_id_prev_recrut_etat ON recrutement.pgt_prev_recrut (id_prev_recrut_etat);
CREATE INDEX ix_pgt_prev_recrut_idorganigramme ON recrutement.pgt_prev_recrut (idorganigramme);
CREATE INDEX ix_pgt_prev_recrut_date_debut ON recrutement.pgt_prev_recrut (date_debut);
CREATE INDEX ix_pgt_prev_recrut_date_fin ON recrutement.pgt_prev_recrut (date_fin);
CREATE INDEX ix_pgt_prev_recrut_modif_date ON recrutement.pgt_prev_recrut (modif_date);
CREATE INDEX ix_pgt_prev_recrut_date_session ON recrutement.pgt_prev_recrut (date_session);
CREATE INDEX ix_pgt_prev_recrut_date_butoire ON recrutement.pgt_prev_recrut (date_butoire);
CREATE INDEX ix_pgt_prev_recrut_id_communes_france ON recrutement.pgt_prev_recrut (id_communes_france);

CREATE TABLE recrutement.pgt_prev_recrut_etat (
    id_prev_recrut_etat_auto  bigint,  -- IDprevRecrutEtatAuto
    id_prev_recrut_etat       bigint NOT NULL,  -- IDprevRecrutEtat
    lib_etat                  text,  -- Lib_Etat
    contenu_mail              text,  -- ContenuMail
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_prev_recrut_etat PRIMARY KEY (id_prev_recrut_etat),
    CONSTRAINT uq_pgt_prev_recrut_etat_auto UNIQUE (id_prev_recrut_etat_auto)
);
CREATE INDEX ix_pgt_prev_recrut_etat_lib_etat ON recrutement.pgt_prev_recrut_etat (lib_etat);
CREATE INDEX ix_pgt_prev_recrut_etat_modif_date ON recrutement.pgt_prev_recrut_etat (modif_date);

CREATE TABLE recrutement.pgt_salon_visio (
    id_salon_visio_auto  bigint,  -- IDSalonVisioAuto
    id_salon_visio       bigint NOT NULL,  -- IDSalonVisio
    id_salarie           bigint,  -- IDSalarie
    id_type_salon_visio  bigint,  -- IDTypeSalonVisio
    lien_salon           text,  -- LienSalon
    id_salon             text,  -- IdSalon
    mpd_salon            text,  -- MpdSalon
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_salon_visio PRIMARY KEY (id_salon_visio),
    CONSTRAINT uq_pgt_salon_visio_auto UNIQUE (id_salon_visio_auto)
);
CREATE INDEX ix_pgt_salon_visio_id_salarie ON recrutement.pgt_salon_visio (id_salarie);
CREATE INDEX ix_pgt_salon_visio_id_type_salon_visio ON recrutement.pgt_salon_visio (id_type_salon_visio);
CREATE INDEX ix_pgt_salon_visio_modif_date ON recrutement.pgt_salon_visio (modif_date);

CREATE TABLE recrutement.pgt_type_salon_visio (
    id_type_salon_visio_auto  bigint,  -- IDTypeSalonVisioAuto
    id_type_salon_visio       bigint NOT NULL,  -- IDTypeSalonVisio
    lib_salon                 varchar(30),  -- Lib_Salon
    is_actif                  boolean,  -- IsActif
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_type_salon_visio PRIMARY KEY (id_type_salon_visio),
    CONSTRAINT uq_pgt_type_salon_visio_auto UNIQUE (id_type_salon_visio_auto)
);
CREATE INDEX ix_pgt_type_salon_visio_modif_date ON recrutement.pgt_type_salon_visio (modif_date);

CREATE TABLE recrutement.pgt_cv_suivi (
    id_cv_suivi_auto                                     bigint,  -- IDCvSuiviAuto
    id_cv_suivi                                          bigint NOT NULL,  -- IDCvSuivi
    id_cvtheque                                          bigint,  -- IDcvtheque
    datecrea                                             timestamp,  -- Datecrea
    op_crea                                              bigint,  -- OPCREA
    id_cv_statut                                         bigint,  -- IdCvStatut
    type_elem                                            varchar(10),  -- TypeElem
    id_elem                                              bigint,  -- IdElem
    observation                                          text,  -- Observation
    modif_date                                           timestamp,  -- ModifDate
    modif_op                                             bigint,  -- ModifOp
    modif_elem                                           varchar(5),  -- ModifElem
    id_cvtheque_datecrea_id_cv_statut_type_elem_id_elem  varchar(42),  -- IDcvthequeDatecreaIdCvStatutTypeElemIdElem
    CONSTRAINT pk_pgt_cv_suivi PRIMARY KEY (id_cv_suivi),
    CONSTRAINT uq_pgt_cv_suivi_auto UNIQUE (id_cv_suivi_auto)
);
CREATE INDEX ix_pgt_cv_suivi_id_cvtheque ON recrutement.pgt_cv_suivi (id_cvtheque);
CREATE INDEX ix_pgt_cv_suivi_id_cv_statut ON recrutement.pgt_cv_suivi (id_cv_statut);
CREATE INDEX ix_pgt_cv_suivi_modif_date ON recrutement.pgt_cv_suivi (modif_date);

CREATE TABLE recrutement.pgt_prev_recrut (
    id_prevision_recrut_auto  bigint,  -- IDprevisionRecrutAuto
    id_prevision_recrut       bigint NOT NULL,  -- IDprevisionRecrut
    id_cv_lieu_rdv            bigint,  -- IDcvLieuRdv
    id_prev_recrut_etat       bigint,  -- IDprevRecrutEtat
    idorganigramme            bigint,  -- idorganigramme
    id_recruteur              bigint,  -- IdRecruteur
    date_debut                date,  -- DateDébut
    date_fin                  date,  -- DateFin
    date_session              date,  -- dateSession
    date_butoire              date,  -- DateButoire
    potentiel_accueil         integer,  -- PotentielAccueil
    nb_prod                   integer,  -- NBProd
    coopt_s_moins_1           integer,  -- cooptSmoins1
    coopt_j_moins_2           integer,  -- cooptJmoins2
    sourcing_s_moins_1        integer,  -- SourcingSmoins1
    sourcing_j_moins_2        integer,  -- SourcingJmoins2
    taille_session            integer,  -- tailleSession
    obj_coopt                 integer,  -- objCoopt
    obj_sourcing              integer,  -- objSourcing
    nb_coopt_mini             integer,  -- NbCooptMini
    nb_sourcing_mini          integer,  -- NbSourcingMini
    id_communes_france        bigint,  -- IDCommunesFrance
    commentaire               text,  -- commentaire
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_prev_recrut PRIMARY KEY (id_prevision_recrut),
    CONSTRAINT uq_pgt_prev_recrut_auto UNIQUE (id_prevision_recrut_auto)
);
CREATE INDEX ix_pgt_prev_recrut_id_cv_lieu_rdv ON recrutement.pgt_prev_recrut (id_cv_lieu_rdv);
CREATE INDEX ix_pgt_prev_recrut_id_prev_recrut_etat ON recrutement.pgt_prev_recrut (id_prev_recrut_etat);
CREATE INDEX ix_pgt_prev_recrut_idorganigramme ON recrutement.pgt_prev_recrut (idorganigramme);
CREATE INDEX ix_pgt_prev_recrut_id_recruteur ON recrutement.pgt_prev_recrut (id_recruteur);
CREATE INDEX ix_pgt_prev_recrut_date_session ON recrutement.pgt_prev_recrut (date_session);
CREATE INDEX ix_pgt_prev_recrut_modif_date ON recrutement.pgt_prev_recrut (modif_date);
