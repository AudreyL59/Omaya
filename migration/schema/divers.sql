CREATE SCHEMA IF NOT EXISTS divers;


CREATE TABLE divers.pgt_challenge_evenement (
    id_challenge_evenement_auto  bigint,  -- IDChallengeEvenementAuto
    id_challenge_evenement       bigint NOT NULL,  -- IDChallengeEvenement
    libelle                      varchar(50),  -- Libellé
    description                  text,  -- DESCRIPTION
    date_debut                   date,  -- DateDébut
    heure_debut                  time,  -- HeureDebut
    date_fin                     date,  -- DateFin
    heure_fin                    time,  -- HeureFin
    permanent                    boolean,  -- Permanent
    type_evenement               boolean,  -- TypeEvenement
    type_challenge               smallint,  -- TypeChallenge
    type_scenario                smallint,  -- TypeScenario
    nb_b_sa_faire                smallint,  -- NbBSàFaire
    nb_tour_max                  smallint,  -- nbTourMax
    type_bs                      smallint,  -- TypeBS
    test                         boolean,  -- Test
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOP
    modif_elem                   varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_challenge_evenement PRIMARY KEY (id_challenge_evenement),
    CONSTRAINT uq_pgt_challenge_evenement_auto UNIQUE (id_challenge_evenement_auto)
);
CREATE INDEX ix_pgt_challenge_evenement_libelle ON divers.pgt_challenge_evenement (libelle);
CREATE INDEX ix_pgt_challenge_evenement_date_debut ON divers.pgt_challenge_evenement (date_debut);
CREATE INDEX ix_pgt_challenge_evenement_date_fin ON divers.pgt_challenge_evenement (date_fin);
CREATE INDEX ix_pgt_challenge_evenement_modif_date ON divers.pgt_challenge_evenement (modif_date);

CREATE TABLE divers.pgt_challenge_gagnants_lots_casinos (
    id_challenge_gagnants_lots_casinos  bigint NOT NULL,  -- IDChallengeGagnantsLotsCasinos
    id_challenge                        bigint,  -- IDChallenge
    id_salarie                          bigint,  -- IDSalarie
    jour_signature                      date,  -- JourSignature
    tour_valide                         boolean,  -- TourValidé
    date_validation                     timestamp,  -- DateValidation
    tour_joue                           boolean,  -- TourJoué
    date_gain                           timestamp,  -- DateGain
    id_challenge_lots_casino            bigint,  -- IDChallengeLotsCasino
    num_bs_concerne                     text,  -- NumBSConcerné
    modif_date                          timestamp,  -- ModifDate
    modif_op                            bigint,  -- ModifOp
    modif_elem                          varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_challenge_gagnants_lots_casinos PRIMARY KEY (id_challenge_gagnants_lots_casinos)
);
CREATE INDEX ix_pgt_challenge_gagnants_lots_casinos_id_challenge ON divers.pgt_challenge_gagnants_lots_casinos (id_challenge);
CREATE INDEX ix_pgt_challenge_gagnants_lots_casinos_id_salarie ON divers.pgt_challenge_gagnants_lots_casinos (id_salarie);
CREATE INDEX ix_pgt_challenge_gagnants_lots_casinos_id_challenge_lots_casino ON divers.pgt_challenge_gagnants_lots_casinos (id_challenge_lots_casino);
CREATE INDEX ix_pgt_challenge_gagnants_lots_casinos_modif_date ON divers.pgt_challenge_gagnants_lots_casinos (modif_date);

CREATE TABLE divers.pgt_challenge_lots_casino (
    id_challenge_lots_casino  bigint NOT NULL,  -- IDChallengeLotsCasino
    id_challenge              bigint,  -- IDChallenge
    categorie                 smallint,  -- Catégorie
    libelle                   text,  -- Libellé
    en_ligne                  boolean,  -- enLigne
    image_lot                 bytea,  -- ImageLot
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOp
    modif_elem                varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_challenge_lots_casino PRIMARY KEY (id_challenge_lots_casino)
);
CREATE INDEX ix_pgt_challenge_lots_casino_id_challenge ON divers.pgt_challenge_lots_casino (id_challenge);
CREATE INDEX ix_pgt_challenge_lots_casino_libelle ON divers.pgt_challenge_lots_casino (libelle);
CREATE INDEX ix_pgt_challenge_lots_casino_modif_date ON divers.pgt_challenge_lots_casino (modif_date);

CREATE TABLE divers.pgt_commande (
    id_commande_auto  bigint,  -- IDCommandeAuto
    id_commande       bigint NOT NULL,  -- IDCommande
    date_achat        date,  -- DateAchat
    ope_achat         bigint,  -- OpéAchat
    num_commande      varchar(50),  -- NumCommande
    montant_ttc       numeric(19,4),  -- MontantTTC
    enseigne          varchar(25),  -- Enseigne
    description       text,  -- DESCRIPTION
    mode_paiement     varchar(5),  -- ModePaiement
    bene_service      boolean,  -- BénéService
    bene_id           bigint,  -- BénéID
    modif_date        timestamp,  -- ModifDate
    modif_op          bigint,  -- ModifOP
    modif_elem        varchar(5),  -- ModifELEM
    id_ste            bigint,  -- IdSte
    CONSTRAINT pk_pgt_commande PRIMARY KEY (id_commande),
    CONSTRAINT uq_pgt_commande_auto UNIQUE (id_commande_auto)
);
CREATE INDEX ix_pgt_commande_modif_date ON divers.pgt_commande (modif_date);
CREATE INDEX ix_pgt_commande_id_ste ON divers.pgt_commande (id_ste);

CREATE TABLE divers.pgt_commande_facture (
    id_commande_facture_auto  bigint,  -- IDCommande_factureAuto
    id_commande_facture       bigint NOT NULL,  -- IDCommande_facture
    id_commande               bigint,  -- IDCommande
    date_ajout                timestamp,  -- DateAjout
    montant_ttc               numeric(19,4),  -- MontantTTC
    nom_fic                   varchar(255),  -- nom_Fic (etendu : noms longs)
    contenu                   bytea,  -- Contenu binaire du fichier (pdf/jpg/...)
    modif_date                timestamp,  -- ModifDate
    modif_op                  bigint,  -- ModifOP
    modif_elem                varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_commande_facture PRIMARY KEY (id_commande_facture),
    CONSTRAINT uq_pgt_commande_facture_auto UNIQUE (id_commande_facture_auto)
);
CREATE INDEX ix_pgt_commande_facture_id_commande ON divers.pgt_commande_facture (id_commande);
CREATE INDEX ix_pgt_commande_facture_modif_date ON divers.pgt_commande_facture (modif_date);

CREATE TABLE divers.pgt_communes_france (
    id_communes_france               bigint NOT NULL,  -- IDCommunesFrance
    code_commune                     varchar(5),  -- CodeCommune
    code_postal                      varchar(5),  -- CodePostal
    nom_ville                        varchar(50),  -- NomVille
    departement                      varchar(2),  -- Departement
    latitude_deg                     double precision,  -- latitude_deg
    longitude_deg                    double precision,  -- longitude_deg
    modif_date                       timestamp,  -- ModifDate
    modif_op                         bigint,  -- ModifOp
    modif_elem                       varchar(5),  -- ModifElem
    code_pays                        varchar(2),  -- CodePays
    favorite                         boolean,  -- Favorite
    code_pays_code_commune           varchar(7),  -- CodePaysCodeCommune
    code_pays_code_postal_nom_ville  varchar(57),  -- CodePaysCodePostalNomVille
    CONSTRAINT pk_pgt_communes_france PRIMARY KEY (id_communes_france)
);
CREATE INDEX ix_pgt_communes_france_code_commune ON divers.pgt_communes_france (code_commune);
CREATE INDEX ix_pgt_communes_france_code_postal ON divers.pgt_communes_france (code_postal);
CREATE INDEX ix_pgt_communes_france_departement ON divers.pgt_communes_france (departement);
CREATE INDEX ix_pgt_communes_france_latitude_deg ON divers.pgt_communes_france (latitude_deg);
CREATE INDEX ix_pgt_communes_france_longitude_deg ON divers.pgt_communes_france (longitude_deg);
CREATE INDEX ix_pgt_communes_france_modif_date ON divers.pgt_communes_france (modif_date);
CREATE INDEX ix_pgt_communes_france_code_pays ON divers.pgt_communes_france (code_pays);

CREATE TABLE divers.pgt_compteur_coopt (
    id_compteur_coopt  bigint NOT NULL,  -- IDCompteurCoopt
    id_challenge       bigint,  -- IDChallenge
    objectif           integer,  -- objectif
    objectif_atteint   boolean,  -- objectifAtteint
    id_coopteur        bigint,  -- IDCOOPTEUR
    id_cvtheque        bigint,  -- IDcvtheque
    msg_intranet       text,  -- MsgIntranet
    date_validation    timestamp,  -- DateValidation
    lot_a_gagner       text,  -- LotAGagner
    en_ligne           boolean,  -- enLigne
    date_activation    timestamp,  -- DateActivation
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOp
    modif_elem         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_compteur_coopt PRIMARY KEY (id_compteur_coopt)
);
CREATE INDEX ix_pgt_compteur_coopt_id_challenge ON divers.pgt_compteur_coopt (id_challenge);
CREATE INDEX ix_pgt_compteur_coopt_id_coopteur ON divers.pgt_compteur_coopt (id_coopteur);
CREATE INDEX ix_pgt_compteur_coopt_id_cvtheque ON divers.pgt_compteur_coopt (id_cvtheque);
CREATE INDEX ix_pgt_compteur_coopt_modif_date ON divers.pgt_compteur_coopt (modif_date);

CREATE TABLE divers.pgt_couleurs_stc (
    id_couleurs_stc  bigint NOT NULL,  -- IDcouleursSTC
    mois             integer,  -- Mois
    couleur1_r       integer,  -- Couleur1_R
    couleur1_v       integer,  -- Couleur1_V
    couleur1_b       integer,  -- Couleur1_B
    couleur2_r       integer,  -- Couleur2_R
    couleur2_v       integer,  -- Couleur2_V
    couleur2_b       integer,  -- Couleur2_B
    modif_date       timestamp,  -- ModifDate
    modif_op         bigint,  -- ModifOp
    modif_elem       varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_couleurs_stc PRIMARY KEY (id_couleurs_stc)
);
CREATE INDEX ix_pgt_couleurs_stc_mois ON divers.pgt_couleurs_stc (mois);
CREATE INDEX ix_pgt_couleurs_stc_modif_date ON divers.pgt_couleurs_stc (modif_date);

CREATE TABLE divers.pgt_dialoguedest (
    id_dialogue_dest  bigint NOT NULL,  -- IDDialogueDEST
    id_dialogues      bigint,  -- IDDialogues
    dest_ope          bigint,  -- Dest_Opé
    dest_orga         bigint,  -- Dest_Orga
    modif_date        timestamp,  -- ModifDate
    modif_op          bigint,  -- ModifOp
    modif_elem        varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_dialoguedest PRIMARY KEY (id_dialogue_dest)
);
CREATE INDEX ix_pgt_dialoguedest_id_dialogues ON divers.pgt_dialoguedest (id_dialogues);
CREATE INDEX ix_pgt_dialoguedest_modif_date ON divers.pgt_dialoguedest (modif_date);

CREATE TABLE divers.pgt_dialoguehisto (
    id_dialogue_histo   bigint NOT NULL,  -- IDDialogueHisto
    id_dialogues        bigint,  -- IDDialogues
    id_dialogue_statut  bigint,  -- IDDialogueStatut
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOp
    modif_elem          varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_dialoguehisto PRIMARY KEY (id_dialogue_histo)
);
CREATE INDEX ix_pgt_dialoguehisto_id_dialogues ON divers.pgt_dialoguehisto (id_dialogues);
CREATE INDEX ix_pgt_dialoguehisto_id_dialogue_statut ON divers.pgt_dialoguehisto (id_dialogue_statut);
CREATE INDEX ix_pgt_dialoguehisto_modif_date ON divers.pgt_dialoguehisto (modif_date);

CREATE TABLE divers.pgt_dialoguelu (
    id_dialogue_lu  bigint NOT NULL,  -- IDDialogueLu
    id_dialogues    bigint,  -- IDDialogues
    id_salarie      bigint,  -- IDSalarie
    date_lecture    timestamp,  -- DateLecture
    modif_date      timestamp,  -- ModifDate
    modif_op        bigint,  -- ModifOp
    modif_elem      varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_dialoguelu PRIMARY KEY (id_dialogue_lu)
);
CREATE INDEX ix_pgt_dialoguelu_id_dialogues ON divers.pgt_dialoguelu (id_dialogues);
CREATE INDEX ix_pgt_dialoguelu_id_salarie ON divers.pgt_dialoguelu (id_salarie);
CREATE INDEX ix_pgt_dialoguelu_modif_date ON divers.pgt_dialoguelu (modif_date);

CREATE TABLE divers.pgt_dialoguemsg (
    id_dialogue_msg      bigint NOT NULL,  -- IDDialogueMSG
    id_dialogues         bigint,  -- IDDialogues
    contenu              text,  -- Contenu
    date_heure_creation  timestamp,  -- DateHeureCreation
    expediteur           bigint,  -- Expéditeur
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_dialoguemsg PRIMARY KEY (id_dialogue_msg)
);
CREATE INDEX ix_pgt_dialoguemsg_id_dialogues ON divers.pgt_dialoguemsg (id_dialogues);
CREATE INDEX ix_pgt_dialoguemsg_modif_date ON divers.pgt_dialoguemsg (modif_date);

CREATE TABLE divers.pgt_emoticone (
    id_emoticone  bigint NOT NULL,  -- IDemoticone
    emoji         text,  -- emoji
    modif_date    timestamp,  -- ModifDate
    modif_op      bigint,  -- ModifOp
    modif_elem    varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_emoticone PRIMARY KEY (id_emoticone)
);
CREATE INDEX ix_pgt_emoticone_modif_date ON divers.pgt_emoticone (modif_date);

CREATE TABLE divers.pgt_exo_cash_famille_lot (
    id_exo_cash_famille_lot_auto  bigint,  -- IDExoCashFamilleLotAuto
    id_exo_cash_famille_lot       bigint NOT NULL,  -- IDExoCashFamilleLot
    lib_famille_lot               varchar(50),  -- LibFamilleLot
    icone                         bytea,  -- Icone
    modif_date                    timestamp,  -- ModifDate
    modif_op                      bigint,  -- ModifOp
    modif_elem                    varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_exo_cash_famille_lot PRIMARY KEY (id_exo_cash_famille_lot),
    CONSTRAINT uq_pgt_exo_cash_famille_lot_auto UNIQUE (id_exo_cash_famille_lot_auto)
);
CREATE INDEX ix_pgt_exo_cash_famille_lot_modif_date ON divers.pgt_exo_cash_famille_lot (modif_date);

CREATE TABLE divers.pgt_exo_cash_lot (
    id_exo_cash_lot_auto     bigint,  -- IDExoCashLotAuto
    id_exo_cash_lot          bigint NOT NULL,  -- IDExoCashLot
    id_exo_cash_famille_lot  bigint,  -- IDExoCashFamilleLot
    marque                   varchar(25),  -- Marque
    lib_lot                  varchar(50),  -- LibLot
    description              text,  -- Description
    montant                  numeric(19,4),  -- Montant
    categorie                smallint,  -- Catégorie
    photo1                   bytea,  -- Photo1
    photo2                   bytea,  -- Photo2
    photo3                   bytea,  -- Photo3
    stock                    integer,  -- Stock
    en_solde                 boolean,  -- EnSolde
    montant_solde            numeric(19,4),  -- MontantSolde
    solde_deb                timestamp,  -- SoldeDeb
    solde_fin                timestamp,  -- SoldeFin
    sur_commande             boolean,  -- SurCommande
    is_actif                 boolean,  -- IsActif
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_exo_cash_lot PRIMARY KEY (id_exo_cash_lot),
    CONSTRAINT uq_pgt_exo_cash_lot_auto UNIQUE (id_exo_cash_lot_auto)
);
CREATE INDEX ix_pgt_exo_cash_lot_id_exo_cash_famille_lot ON divers.pgt_exo_cash_lot (id_exo_cash_famille_lot);
CREATE INDEX ix_pgt_exo_cash_lot_modif_date ON divers.pgt_exo_cash_lot (modif_date);

CREATE TABLE divers.pgt_exo_cash_lot_histo_stock (
    id_exo_cash_lot_histo_stock  bigint NOT NULL,  -- IDExoCashLotHistoStock
    id_exo_cash_lot              bigint,  -- IDExoCashLot
    date_histo                   timestamp,  -- dateHisto
    ope_crea                     bigint,  -- OpéCrea
    qte                          integer,  -- Qté
    id_tk_liste                  bigint,  -- IDTK_Liste
    modif_date                   timestamp,  -- ModifDate
    modif_op                     bigint,  -- ModifOp
    modif_elem                   varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_exo_cash_lot_histo_stock PRIMARY KEY (id_exo_cash_lot_histo_stock)
);
CREATE INDEX ix_pgt_exo_cash_lot_histo_stock_id_exo_cash_lot ON divers.pgt_exo_cash_lot_histo_stock (id_exo_cash_lot);
CREATE INDEX ix_pgt_exo_cash_lot_histo_stock_id_tk_liste ON divers.pgt_exo_cash_lot_histo_stock (id_tk_liste);
CREATE INDEX ix_pgt_exo_cash_lot_histo_stock_modif_date ON divers.pgt_exo_cash_lot_histo_stock (modif_date);

CREATE TABLE divers.pgt_feuille_pointe (
    id_feuille_pointe   bigint NOT NULL,  -- IDFeuillePointe
    id_communes_france  bigint,  -- IDCommunesFrance
    id_salarie          bigint,  -- IDSalarie
    date                date,  -- Date
    date_crea           timestamp,  -- DateCrea
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOp
    modif_elem          varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_feuille_pointe PRIMARY KEY (id_feuille_pointe)
);
CREATE INDEX ix_pgt_feuille_pointe_id_communes_france ON divers.pgt_feuille_pointe (id_communes_france);
CREATE INDEX ix_pgt_feuille_pointe_id_salarie ON divers.pgt_feuille_pointe (id_salarie);
CREATE INDEX ix_pgt_feuille_pointe_modif_date ON divers.pgt_feuille_pointe (modif_date);

CREATE TABLE divers.pgt_feuille_pointe_pointage (
    id_feuille_pointe_pointage  bigint,  -- IDFeuillePointePointage
    id_pointage                 smallint NOT NULL,  -- IdPointage
    type_pointage               varchar(50),  -- TypePointage
    icone                       bytea,  -- Icone
    car                         varchar(5),  -- Car
    is_actif                    boolean,  -- IsActif
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOp
    modif_elem                  varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_feuille_pointe_pointage PRIMARY KEY (id_pointage),
    CONSTRAINT uq_pgt_feuille_pointe_pointage_auto UNIQUE (id_feuille_pointe_pointage)
);
CREATE INDEX ix_pgt_feuille_pointe_pointage_modif_date ON divers.pgt_feuille_pointe_pointage (modif_date);

CREATE TABLE divers.pgt_feuille_pointe_porte (
    id_feuille_pointe_porte  bigint NOT NULL,  -- IDFeuillePointePorte
    id_feuille_pointe_rue    bigint,  -- IDFeuillePointeRue
    id_feuille_pointe        bigint,  -- IDFeuillePointe
    num_porte                varchar(10),  -- NumPorte
    cplt_porte               varchar(20),  -- CpltPorte
    pointage                 smallint,  -- Pointage
    datecrea                 timestamp,  -- Datecrea
    info_cplt                text,  -- InfoCplt
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_feuille_pointe_porte PRIMARY KEY (id_feuille_pointe_porte)
);
CREATE INDEX ix_pgt_feuille_pointe_porte_id_feuille_pointe_rue ON divers.pgt_feuille_pointe_porte (id_feuille_pointe_rue);
CREATE INDEX ix_pgt_feuille_pointe_porte_id_feuille_pointe ON divers.pgt_feuille_pointe_porte (id_feuille_pointe);
CREATE INDEX ix_pgt_feuille_pointe_porte_modif_date ON divers.pgt_feuille_pointe_porte (modif_date);

CREATE TABLE divers.pgt_feuille_pointe_portehisto (
    id_feuille_pointe_porte_histo  bigint NOT NULL,  -- IDFeuillePointePorteHisto
    id_feuille_pointe_porte        bigint,  -- IDFeuillePointePorte
    pointage                       smallint,  -- Pointage
    datecrea                       timestamp,  -- Datecrea
    modif_date                     timestamp,  -- ModifDate
    modif_op                       bigint,  -- ModifOp
    modif_elem                     varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_feuille_pointe_portehisto PRIMARY KEY (id_feuille_pointe_porte_histo)
);
CREATE INDEX ix_pgt_feuille_pointe_portehisto_id_feuille_pointe_porte ON divers.pgt_feuille_pointe_portehisto (id_feuille_pointe_porte);
CREATE INDEX ix_pgt_feuille_pointe_portehisto_modif_date ON divers.pgt_feuille_pointe_portehisto (modif_date);

CREATE TABLE divers.pgt_feuille_pointe_rue (
    id_feuille_pointe_rue  bigint NOT NULL,  -- IDFeuillePointeRue
    id_feuille_pointe      bigint,  -- IDFeuillePointe
    nom_rue                text,  -- NomRue
    date_crea              timestamp,  -- DateCrea
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOp
    modif_elem             varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_feuille_pointe_rue PRIMARY KEY (id_feuille_pointe_rue)
);
CREATE INDEX ix_pgt_feuille_pointe_rue_id_feuille_pointe ON divers.pgt_feuille_pointe_rue (id_feuille_pointe);
CREATE INDEX ix_pgt_feuille_pointe_rue_modif_date ON divers.pgt_feuille_pointe_rue (modif_date);

CREATE TABLE divers.pgt_histo_animation (
    id_histo_animation  bigint NOT NULL,  -- IDHistoAnimation
    code_animation      varchar(50),  -- CodeAnimation
    date_envoi_sms      date,  -- DateEnvoiSMS
    datecrea            timestamp,  -- Datecrea
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOp
    modif_elem          varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_histo_animation PRIMARY KEY (id_histo_animation)
);
CREATE INDEX ix_pgt_histo_animation_modif_date ON divers.pgt_histo_animation (modif_date);

CREATE TABLE divers.pgt_histo_sms (
    id_histo_sms    bigint NOT NULL,  -- IDHistoSMS
    id_message      varchar(50),  -- IdMessage
    date_envoi      timestamp,  -- dateEnvoi
    destinataire    varchar(15),  -- Destinataire
    fichier         text,  -- Fichier
    rubrique        text,  -- Rubrique
    id_elem         bigint,  -- IdElem
    contenu_envoye  text,  -- ContenuEnvoyé
    type_sms        varchar(7),  -- TypeSMS
    nb_sms          smallint,  -- nbSMS
    statut          varchar(15),  -- Statut
    operateur       varchar(10),  -- Opérateur
    datecrea        timestamp,  -- Datecrea
    ope_envoi       bigint,  -- OpéEnvoi
    cout            integer,  -- Cout
    devise          varchar(7),  -- Devise
    modif_date      timestamp,  -- ModifDate
    modif_op        bigint,  -- ModifOp
    modif_elem      varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_histo_sms PRIMARY KEY (id_histo_sms)
);
CREATE INDEX ix_pgt_histo_sms_modif_date ON divers.pgt_histo_sms (modif_date);

CREATE TABLE divers.pgt_identifiant_push (
    id_identifiant_push               bigint NOT NULL,  -- IDIdentifiantPush
    identifiant_service               varchar(256),  -- IdentifiantService
    type_service                      smallint,  -- TypeService
    id_salarie                        bigint,  -- IDSalarie
    info_perso                        text,  -- InfoPerso
    identifiant_service_type_service  varchar(259),  -- IdentifiantServiceTypeService
    modif_date                        timestamp,  -- ModifDate
    id_salarie_type_service           varchar(9),  -- IDSalarieTypeService
    CONSTRAINT pk_pgt_identifiant_push PRIMARY KEY (id_identifiant_push)
);
CREATE INDEX ix_pgt_identifiant_push_type_service ON divers.pgt_identifiant_push (type_service);
CREATE INDEX ix_pgt_identifiant_push_id_salarie ON divers.pgt_identifiant_push (id_salarie);
CREATE INDEX ix_pgt_identifiant_push_modif_date ON divers.pgt_identifiant_push (modif_date);

CREATE TABLE divers.pgt_info_exo_new (
    id_info_exo_new  bigint NOT NULL,  -- IDInfoExoNew
    date_jour        date,  -- DateJour
    contenu_info     text,  -- ContenuInfo
    modif_date       timestamp,  -- ModifDate
    modif_op         bigint,  -- ModifOP
    modif_elem       varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_info_exo_new PRIMARY KEY (id_info_exo_new)
);
CREATE INDEX ix_pgt_info_exo_new_date_jour ON divers.pgt_info_exo_new (date_jour);
CREATE INDEX ix_pgt_info_exo_new_modif_date ON divers.pgt_info_exo_new (modif_date);

CREATE TABLE divers.pgt_liste_scanner (
    id_liste_scanner  bigint,  -- IDlisteScanner
    nom_reel          varchar(50) NOT NULL,  -- NomReel
    nom_affiche       varchar(50),  -- NomAffiché
    CONSTRAINT pk_pgt_liste_scanner PRIMARY KEY (nom_reel),
    CONSTRAINT uq_pgt_liste_scanner_auto UNIQUE (id_liste_scanner)
);

CREATE TABLE divers.pgt_logconnexion (
    id_logconnexion  bigint NOT NULL,  -- IDlogconnexion
    date             date,  -- DATE
    heure            time,  -- Heure
    ip               varchar(20),  -- IP
    type             varchar(50),  -- Type
    detail           text,  -- Détail
    login            varchar(50),  -- LOGIN
    nom              varchar(40),  -- Nom
    support          varchar(30),  -- Support
    s_ite            varchar(50),  -- SIte
    modif_date       timestamp,  -- ModifDate
    modif_op         bigint,  -- ModifOP
    modif_elem       varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_logconnexion PRIMARY KEY (id_logconnexion)
);
CREATE INDEX ix_pgt_logconnexion_modif_date ON divers.pgt_logconnexion (modif_date);

CREATE TABLE divers.pgt_notificationpush (
    id_notification_push  bigint NOT NULL,  -- IDNotificationPush
    id_salarie            bigint,  -- IDSalarie
    message_notif         varchar(50),  -- MessageNotif
    contenu_notif         varchar(50),  -- ContenuNotif
    titre_notif           varchar(50),  -- TitreNotif
    modif_date            timestamp,  -- ModifDate
    modif_op              bigint,  -- ModifOp
    modif_elem            varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_notificationpush PRIMARY KEY (id_notification_push)
);
CREATE INDEX ix_pgt_notificationpush_id_salarie ON divers.pgt_notificationpush (id_salarie);
CREATE INDEX ix_pgt_notificationpush_modif_date ON divers.pgt_notificationpush (modif_date);

CREATE TABLE divers.pgt_parc_it (
    id_parc_it_auto     bigint,  -- IDparcITAuto
    id_parc_it          bigint NOT NULL,  -- IDparcIT
    num_serie           text,  -- NumSerie
    imei                varchar(50),  -- IMEI
    uuid                text,  -- UUID
    adresse_mac         text,  -- AdresseMac
    marque              varchar(25),  -- Marque
    modele              varchar(25),  -- Modèle
    idorganigramme      bigint,  -- idorganigramme
    id_responsable      bigint,  -- idResponsable
    date_crea           timestamp,  -- DateCrea
    ope_crea            bigint,  -- OpéCrea
    statut              varchar(20),  -- Statut
    type_mat            varchar(25),  -- TypeMat
    id_miradore         integer,  -- IdMiradore
    date_crea_miradore  timestamp,  -- DateCreaMiradore
    info_interne        text,  -- Info_Interne
    archive             boolean,  -- Archivé
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_parc_it PRIMARY KEY (id_parc_it),
    CONSTRAINT uq_pgt_parc_it_auto UNIQUE (id_parc_it_auto)
);
CREATE INDEX ix_pgt_parc_it_marque ON divers.pgt_parc_it (marque);
CREATE INDEX ix_pgt_parc_it_modele ON divers.pgt_parc_it (modele);
CREATE INDEX ix_pgt_parc_it_idorganigramme ON divers.pgt_parc_it (idorganigramme);
CREATE INDEX ix_pgt_parc_it_id_responsable ON divers.pgt_parc_it (id_responsable);
CREATE INDEX ix_pgt_parc_it_modif_date ON divers.pgt_parc_it (modif_date);

CREATE TABLE divers.pgt_parc_it_partenaire (
    id_parc_it_partenaire  bigint NOT NULL,  -- IDparcIT_Partenaire
    id_partenaire          bigint,  -- IDPartenaire
    id_parc_it             bigint,  -- IDparcIT
    uuid                   text,  -- UUID
    login                  text,  -- Login
    mdp                    text,  -- MDP
    nom                    text,  -- Nom
    prenom                 text,  -- Prenom
    du                     date,  -- DU
    au                     date,  -- AU
    is_actif               boolean,  -- IsActif
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOp
    modif_elem             varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_parc_it_partenaire PRIMARY KEY (id_parc_it_partenaire)
);
CREATE INDEX ix_pgt_parc_it_partenaire_id_partenaire ON divers.pgt_parc_it_partenaire (id_partenaire);
CREATE INDEX ix_pgt_parc_it_partenaire_id_parc_it ON divers.pgt_parc_it_partenaire (id_parc_it);
CREATE INDEX ix_pgt_parc_it_partenaire_login ON divers.pgt_parc_it_partenaire (login);
CREATE INDEX ix_pgt_parc_it_partenaire_modif_date ON divers.pgt_parc_it_partenaire (modif_date);

CREATE TABLE divers.pgt_parc_itgps (
    id_parc_itgps_auto  bigint,  -- IDparcITGPSAuto
    id_parc_itgps       bigint NOT NULL,  -- IDparcITGPS
    id_parc_it          bigint,  -- IDparcIT
    latitude_deg        double precision,  -- latitude_deg
    longitude_deg       double precision,  -- longitude_deg
    date_releve         date,  -- DateReleve
    heure_releve        time,  -- HeureReleve
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_parc_itgps PRIMARY KEY (id_parc_itgps),
    CONSTRAINT uq_pgt_parc_itgps_auto UNIQUE (id_parc_itgps_auto)
);
CREATE INDEX ix_pgt_parc_itgps_id_parc_it ON divers.pgt_parc_itgps (id_parc_it);
CREATE INDEX ix_pgt_parc_itgps_latitude_deg ON divers.pgt_parc_itgps (latitude_deg);
CREATE INDEX ix_pgt_parc_itgps_date_releve ON divers.pgt_parc_itgps (date_releve);
CREATE INDEX ix_pgt_parc_itgps_modif_date ON divers.pgt_parc_itgps (modif_date);

CREATE TABLE divers.pgt_parc_it_perception (
    id_parc_it_perception_auto  bigint,  -- IDparcITPerceptionAuto
    id_parc_it_perception       bigint NOT NULL,  -- IDparcITPerception
    id_parc_it                  bigint,  -- IDparcIT
    id_salarie                  bigint,  -- IDSalarie
    date_perception             date,  -- DatePerception
    date_restitution            date,  -- DateRestitution
    etat_perception             varchar(20),  -- EtatPerception
    etat_restitution            varchar(20),  -- EtatRestitution
    info_etat_cplt              text,  -- InfoEtatCplt
    restituee                   boolean,  -- Restituée
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOP
    modif_elem                  varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_parc_it_perception PRIMARY KEY (id_parc_it_perception),
    CONSTRAINT uq_pgt_parc_it_perception_auto UNIQUE (id_parc_it_perception_auto)
);
CREATE INDEX ix_pgt_parc_it_perception_id_parc_it ON divers.pgt_parc_it_perception (id_parc_it);
CREATE INDEX ix_pgt_parc_it_perception_id_salarie ON divers.pgt_parc_it_perception (id_salarie);
CREATE INDEX ix_pgt_parc_it_perception_modif_date ON divers.pgt_parc_it_perception (modif_date);

CREATE TABLE divers.pgt_parc_it_perception_resp (
    id_parc_it_perception_auto  bigint,  -- IDparcITPerceptionAuto
    id_parc_it_perception       bigint NOT NULL,  -- IDparcITPerception
    id_parc_it                  bigint,  -- IDparcIT
    id_salarie                  bigint,  -- IDSalarie
    date_perception             date,  -- DatePerception
    date_restitution            date,  -- DateRestitution
    etat_perception             varchar(20),  -- EtatPerception
    etat_restitution            varchar(20),  -- EtatRestitution
    info_etat_cplt              text,  -- InfoEtatCplt
    restituee                   boolean,  -- Restituée
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOP
    modif_elem                  varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_parc_it_perception_resp PRIMARY KEY (id_parc_it_perception),
    CONSTRAINT uq_pgt_parc_it_perception_resp_auto UNIQUE (id_parc_it_perception_auto)
);
CREATE INDEX ix_pgt_parc_it_perception_resp_id_parc_it ON divers.pgt_parc_it_perception_resp (id_parc_it);
CREATE INDEX ix_pgt_parc_it_perception_resp_id_salarie ON divers.pgt_parc_it_perception_resp (id_salarie);
CREATE INDEX ix_pgt_parc_it_perception_resp_modif_date ON divers.pgt_parc_it_perception_resp (modif_date);

CREATE TABLE divers.pgt_parc_it_reparation (
    id_parc_it_reparation_auto  bigint,  -- IDparcITRéparationAuto
    id_parc_it_reparation       bigint NOT NULL,  -- IDparcITRéparation
    id_parc_it                  bigint,  -- IDparcIT
    date_reparation             date,  -- dateRéparation
    type_rep                    varchar(50),  -- TypeRép
    tps_rep                     time,  -- TpsRép
    montant_piece               numeric(19,4),  -- MontantPièce
    modif_op                    bigint,  -- ModifOP
    modif_date                  timestamp,  -- ModifDate
    modif_elem                  varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_parc_it_reparation PRIMARY KEY (id_parc_it_reparation),
    CONSTRAINT uq_pgt_parc_it_reparation_auto UNIQUE (id_parc_it_reparation_auto)
);
CREATE INDEX ix_pgt_parc_it_reparation_id_parc_it ON divers.pgt_parc_it_reparation (id_parc_it);
CREATE INDEX ix_pgt_parc_it_reparation_modif_date ON divers.pgt_parc_it_reparation (modif_date);

CREATE TABLE divers.pgt_podium_mois (
    id_podium_mois  bigint NOT NULL,  -- IDPodiumMois
    mois            integer,  -- Mois
    annee           varchar(50),  -- Année
    id_podium_type  bigint,  -- IDPodiumType
    score_visible   boolean,  -- ScoreVisible
    modif_date      timestamp,  -- ModifDate
    modif_op        bigint,  -- ModifOp
    modif_elem      varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_podium_mois PRIMARY KEY (id_podium_mois)
);
CREATE INDEX ix_pgt_podium_mois_mois ON divers.pgt_podium_mois (mois);
CREATE INDEX ix_pgt_podium_mois_id_podium_type ON divers.pgt_podium_mois (id_podium_type);
CREATE INDEX ix_pgt_podium_mois_modif_date ON divers.pgt_podium_mois (modif_date);

CREATE TABLE divers.pgt_podium_type (
    id_podium_type   bigint NOT NULL,  -- IDPodiumType
    lib_podium_type  varchar(50),  -- LibPodiumType
    lib_court        varchar(30),  -- LibCourt
    prod_groupe      boolean,  -- ProdGroupe
    qualite          boolean,  -- Qualité
    espoir           boolean,  -- Espoir
    is_actif         boolean,  -- IsActif
    modif_date       timestamp,  -- ModifDate
    modif_op         bigint,  -- ModifOp
    modif_elem       varchar(5),  -- ModifElem
    ordre_affichage  smallint,  -- OrdreAffichage
    CONSTRAINT pk_pgt_podium_type PRIMARY KEY (id_podium_type)
);
CREATE INDEX ix_pgt_podium_type_modif_date ON divers.pgt_podium_type (modif_date);

CREATE TABLE divers.pgt_podium_type_part_option (
    id_podium_type_part_option  bigint,  -- IDPodiumTypePartOption
    lib_option_vente            varchar(20) NOT NULL,  -- LibOptionVente
    prefixe_bdd                 varchar(5),  -- PréfixeBDD
    description                 text,  -- Description
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOp
    modif_elem                  varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_podium_type_part_option PRIMARY KEY (lib_option_vente),
    CONSTRAINT uq_pgt_podium_type_part_option_auto UNIQUE (id_podium_type_part_option)
);
CREATE INDEX ix_pgt_podium_type_part_option_prefixe_bdd ON divers.pgt_podium_type_part_option (prefixe_bdd);
CREATE INDEX ix_pgt_podium_type_part_option_modif_date ON divers.pgt_podium_type_part_option (modif_date);

CREATE TABLE divers.pgt_podium_type_prod (
    id_podium_type_prod  bigint,  -- IDPodiumTypeProd
    lib_type_prod        varchar(10) NOT NULL,  -- LibTypeProd
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_podium_type_prod PRIMARY KEY (lib_type_prod),
    CONSTRAINT uq_pgt_podium_type_prod_auto UNIQUE (id_podium_type_prod)
);
CREATE INDEX ix_pgt_podium_type_prod_modif_date ON divers.pgt_podium_type_prod (modif_date);

CREATE TABLE divers.pgt_podium_vendeur (
    id_podium_vendeur  bigint NOT NULL,  -- IDPodiumVendeur
    id_podium_type     bigint,  -- IDPodiumType
    date_jour          date,  -- DateJour
    id_salarie         bigint,  -- IDSalarie
    id_equipe          bigint,  -- IdEquipe
    distributeur       boolean,  -- Distributeur
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOp
    modif_elem         varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_podium_vendeur PRIMARY KEY (id_podium_vendeur)
);
CREATE INDEX ix_pgt_podium_vendeur_id_podium_type ON divers.pgt_podium_vendeur (id_podium_type);
CREATE INDEX ix_pgt_podium_vendeur_date_jour ON divers.pgt_podium_vendeur (date_jour);
CREATE INDEX ix_pgt_podium_vendeur_id_salarie ON divers.pgt_podium_vendeur (id_salarie);
CREATE INDEX ix_pgt_podium_vendeur_modif_date ON divers.pgt_podium_vendeur (modif_date);

CREATE TABLE divers.pgt_podium_vendeur_part (
    id_podium_vendeur_part  bigint NOT NULL,  -- IDPodiumVendeurPart
    id_podium_type_part     bigint,  -- IDPodiumTypePart
    id_podium_vendeur       bigint,  -- IDPodiumVendeur
    prefixe_bdd             varchar(5),  -- PréfixeBDD
    qte_brut                smallint,  -- QtéBrut
    qte_hors_rejet          smallint,  -- QtéHorsRejet
    qte_paye                smallint,  -- QtéPayé
    modif_date              timestamp,  -- ModifDate
    modif_op                bigint,  -- ModifOp
    modif_elem              varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_podium_vendeur_part PRIMARY KEY (id_podium_vendeur_part)
);
CREATE INDEX ix_pgt_podium_vendeur_part_id_podium_type_part ON divers.pgt_podium_vendeur_part (id_podium_type_part);
CREATE INDEX ix_pgt_podium_vendeur_part_id_podium_vendeur ON divers.pgt_podium_vendeur_part (id_podium_vendeur);
CREATE INDEX ix_pgt_podium_vendeur_part_prefixe_bdd ON divers.pgt_podium_vendeur_part (prefixe_bdd);
CREATE INDEX ix_pgt_podium_vendeur_part_modif_date ON divers.pgt_podium_vendeur_part (modif_date);

CREATE TABLE divers.pgt_process (
    id_process      bigint NOT NULL,  -- IDProcess
    service         varchar(5),  -- Service
    titre           text,  -- Titre
    mots_cles       text,  -- MotsClés
    date_crea       timestamp,  -- DateCrea
    derniere_modif  timestamp,  -- DernièreModif
    ope_crea        bigint,  -- OpéCrea
    ope_modif       bigint,  -- OpéModif
    diagramme       bytea,  -- Diagramme
    modif_date      timestamp,  -- ModifDate
    modif_op        bigint,  -- ModifOp
    modif_elem      varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_process PRIMARY KEY (id_process)
);
CREATE INDEX ix_pgt_process_service ON divers.pgt_process (service);
CREATE INDEX ix_pgt_process_mots_cles ON divers.pgt_process (mots_cles);
CREATE INDEX ix_pgt_process_modif_date ON divers.pgt_process (modif_date);

CREATE TABLE divers.pgt_process_droit (
    id_process_droit  bigint NOT NULL,  -- IDProcessDroit
    id_process        bigint,  -- IDProcess
    id_salarie        bigint,  -- IDSalarie
    type_profil       varchar(10),  -- TypeProfil
    id_ste            bigint,  -- IdSte
    droit_actif       boolean,  -- DroitActif
    modif_date        timestamp,  -- ModifDate
    modif_op          bigint,  -- ModifOp
    modif_elem        varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_process_droit PRIMARY KEY (id_process_droit)
);
CREATE INDEX ix_pgt_process_droit_id_process ON divers.pgt_process_droit (id_process);
CREATE INDEX ix_pgt_process_droit_id_salarie ON divers.pgt_process_droit (id_salarie);
CREATE INDEX ix_pgt_process_droit_id_ste ON divers.pgt_process_droit (id_ste);
CREATE INDEX ix_pgt_process_droit_modif_date ON divers.pgt_process_droit (modif_date);

CREATE TABLE divers.pgt_process_fichier (
    id_process_fichier  bigint NOT NULL,  -- IDProcessFichier
    id_process          bigint,  -- IDProcess
    titre               text,  -- Titre
    date_crea           timestamp,  -- DateCrea
    derniere_modif      timestamp,  -- DernièreModif
    ope_crea            bigint,  -- OpéCrea
    ope_modif           bigint,  -- OpéModif
    contenu_fichier     bytea,  -- ContenuFichier
    extension           varchar(10),  -- Extension
    taille_fic          bigint,  -- TailleFic
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOp
    modif_elem          varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_process_fichier PRIMARY KEY (id_process_fichier)
);
CREATE INDEX ix_pgt_process_fichier_id_process ON divers.pgt_process_fichier (id_process);
CREATE INDEX ix_pgt_process_fichier_extension ON divers.pgt_process_fichier (extension);
CREATE INDEX ix_pgt_process_fichier_modif_date ON divers.pgt_process_fichier (modif_date);

CREATE TABLE divers.pgt_productionextractionjob (
    id_production_extraction_job  bigint NOT NULL,  -- IDProductionExtractionJob
    id_salarie_user               bigint,  -- IDSalarieUser
    datecrea                      timestamp,  -- Datecrea
    date_debut_trait              timestamp,  -- DateDebutTrait
    date_fin_trait                timestamp,  -- DateFinTrait
    params_json                   text,  -- ParamsJSON
    statut                        varchar(10),  -- Statut
    progression_pct               smallint,  -- ProgressionPct
    progression_msg               varchar(100),  -- ProgressionMsg
    nb_lignes                     integer,  -- NbLignes
    duree_s                       integer,  -- DureeS
    path_resultat                 varchar(255),  -- PathResultat
    message_erreur                text,  -- MessageErreur
    titre                         varchar(200),  -- Titre
    priority                      smallint,  -- Priority
    modif_date                    timestamp,  -- ModifDate
    modif_op                      bigint,  -- ModifOp
    modif_elem                    varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_productionextractionjob PRIMARY KEY (id_production_extraction_job)
);
CREATE INDEX ix_pgt_productionextractionjob_id_salarie_user ON divers.pgt_productionextractionjob (id_salarie_user);
CREATE INDEX ix_pgt_productionextractionjob_statut ON divers.pgt_productionextractionjob (statut);
CREATE INDEX ix_pgt_productionextractionjob_modif_date ON divers.pgt_productionextractionjob (modif_date);

CREATE TABLE divers.pgt_prog_evo_objectifs (
    id_prog_evo_objectifs  bigint NOT NULL,  -- IDProgEvo_Objectifs
    type_categorie         varchar(50),  -- TypeCatégorie
    lib_objectif           varchar(50),  -- LibObjectif
    nb_bouton              smallint,  -- nbBouton
    lib_bouton             text,  -- LibBouton
    champ_libre            boolean,  -- ChampLibre
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOp
    modif_elem             varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_prog_evo_objectifs PRIMARY KEY (id_prog_evo_objectifs)
);
CREATE INDEX ix_pgt_prog_evo_objectifs_modif_date ON divers.pgt_prog_evo_objectifs (modif_date);

CREATE TABLE divers.pgt_smsanimation (
    id_sms_animation  bigint,  -- IDSmsAnimation
    type_sms          varchar(50) NOT NULL,  -- TypeSMS
    liste_num_staff   text,  -- ListeNumStaff
    is_actif          boolean,  -- IsActif
    CONSTRAINT pk_pgt_smsanimation PRIMARY KEY (type_sms),
    CONSTRAINT uq_pgt_smsanimation_auto UNIQUE (id_sms_animation)
);

CREATE TABLE divers.pgt_smsanimation_orgadest (
    id_sms_animation_orga_dest  bigint NOT NULL,  -- IDSmsAnimation_OrgaDest
    idorganigramme              bigint,  -- idorganigramme
    anim_code                   text,  -- AnimCode
    du                          date,  -- DU
    au                          date,  -- AU
    is_actif                    boolean,  -- IsActif
    modif_date                  timestamp,  -- ModifDate
    modif_op                    bigint,  -- ModifOp
    modif_elem                  varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_smsanimation_orgadest PRIMARY KEY (id_sms_animation_orga_dest)
);
CREATE INDEX ix_pgt_smsanimation_orgadest_idorganigramme ON divers.pgt_smsanimation_orgadest (idorganigramme);
CREATE INDEX ix_pgt_smsanimation_orgadest_modif_date ON divers.pgt_smsanimation_orgadest (modif_date);

CREATE TABLE divers.pgt_sms_animation_orga_periode (
    id_sms_animation_orga  bigint NOT NULL,  -- IDSmsAnimation_Orga
    type                   varchar(20),  -- Type
    idorganigramme         bigint,  -- idorganigramme
    is_actif               boolean,  -- IsActif
    du                     date,  -- DU
    au                     date,  -- AU
    code_animation         varchar(50),  -- CodeAnimation
    modif_date             timestamp,  -- ModifDate
    modif_op               bigint,  -- ModifOp
    modif_elem             varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_sms_animation_orga_periode PRIMARY KEY (id_sms_animation_orga)
);
CREATE INDEX ix_pgt_sms_animation_orga_periode_idorganigramme ON divers.pgt_sms_animation_orga_periode (idorganigramme);
CREATE INDEX ix_pgt_sms_animation_orga_periode_modif_date ON divers.pgt_sms_animation_orga_periode (modif_date);

CREATE TABLE divers.pgt_smsanimation_regleenvoi (
    id_sms_animation_regle_envoi  bigint NOT NULL,  -- IDSmsAnimation_RegleEnvoi
    type_sms                      varchar(50),  -- TypeSMS
    code_animation                varchar(50),  -- CodeAnimation
    texte_sms                     text,  -- TexteSMS
    heure_envoi                   time,  -- HeureEnvoi
    ordre                         smallint,  -- Ordre
    sms_groupe                    boolean,  -- SMSGroupé
    partenaire                    text,  -- Partenaire
    heure_debut                   time,  -- HeureDebut
    heure_fin                     time,  -- HeureFin
    prod_groupe                   smallint,  -- ProdGroupe
    periode_calcul                smallint,  -- PériodeCalcul
    nb_bs_min                     smallint,  -- NbBSMin
    is_actif                      boolean,  -- IsActif
    modif_date                    timestamp,  -- ModifDate
    modif_op                      bigint,  -- ModifOp
    modif_elem                    varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_smsanimation_regleenvoi PRIMARY KEY (id_sms_animation_regle_envoi)
);
CREATE INDEX ix_pgt_smsanimation_regleenvoi_type_sms ON divers.pgt_smsanimation_regleenvoi (type_sms);
CREATE INDEX ix_pgt_smsanimation_regleenvoi_modif_date ON divers.pgt_smsanimation_regleenvoi (modif_date);

CREATE TABLE divers.pgt_suivi_projet (
    id_suivi_projet_auto       bigint,  -- IDsuiviProjetAuto
    id_suivi_projet            bigint NOT NULL,  -- IDsuiviProjet
    id_type_tache              smallint,  -- IDTypeTache
    element                    varchar(50),  -- Element
    id_suivi_projet_etiquette  bigint,  -- IDSuiviProjet_Etiquette
    description                text,  -- Description
    id_parent                  bigint,  -- IdPARENT
    op_crea                    bigint,  -- OPCREA
    couleur                    integer,  -- Couleur
    cloturee                   boolean,  -- Cloturée
    modif_date                 timestamp,  -- ModifDate
    modif_op                   bigint,  -- ModifOp
    modif_elem                 varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_suivi_projet PRIMARY KEY (id_suivi_projet),
    CONSTRAINT uq_pgt_suivi_projet_auto UNIQUE (id_suivi_projet_auto)
);
CREATE INDEX ix_pgt_suivi_projet_id_type_tache ON divers.pgt_suivi_projet (id_type_tache);
CREATE INDEX ix_pgt_suivi_projet_id_parent ON divers.pgt_suivi_projet (id_parent);
CREATE INDEX ix_pgt_suivi_projet_modif_date ON divers.pgt_suivi_projet (modif_date);

CREATE TABLE divers.pgt_suivi_projet_comment (
    id_suivi_projet_comment  bigint NOT NULL,  -- IDsuiviProjet_Comment
    id_suivi_projet          bigint,  -- IDsuiviProjet
    id_salarie               bigint,  -- IDSalarie
    id_projet                bigint,  -- IDProjet
    commentaire              text,  -- commentaire
    nom_fichier              text,  -- NomFichier
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOp
    modif_elem               varchar(5),  -- ModifElem
    datecrea                 timestamp,  -- Datecrea
    CONSTRAINT pk_pgt_suivi_projet_comment PRIMARY KEY (id_suivi_projet_comment)
);
CREATE INDEX ix_pgt_suivi_projet_comment_id_suivi_projet ON divers.pgt_suivi_projet_comment (id_suivi_projet);
CREATE INDEX ix_pgt_suivi_projet_comment_id_salarie ON divers.pgt_suivi_projet_comment (id_salarie);
CREATE INDEX ix_pgt_suivi_projet_comment_id_projet ON divers.pgt_suivi_projet_comment (id_projet);
CREATE INDEX ix_pgt_suivi_projet_comment_modif_date ON divers.pgt_suivi_projet_comment (modif_date);

CREATE TABLE divers.pgt_suivi_projet_etiquette (
    id_suivi_projet_etiquette_auto  bigint,  -- IDSuiviProjet_EtiquetteAuto
    id_suivi_projet_etiquette       bigint NOT NULL,  -- IDSuiviProjet_Etiquette
    lib_etiquette                   varchar(50),  -- LibEtiquette
    id_suivi_projet                 bigint,  -- IDsuiviProjet
    couleur                         integer,  -- Couleur
    modif_date                      timestamp,  -- ModifDate
    modif_op                        bigint,  -- ModifOp
    modif_elem                      varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_suivi_projet_etiquette PRIMARY KEY (id_suivi_projet_etiquette),
    CONSTRAINT uq_pgt_suivi_projet_etiquette_auto UNIQUE (id_suivi_projet_etiquette_auto)
);
CREATE INDEX ix_pgt_suivi_projet_etiquette_id_suivi_projet ON divers.pgt_suivi_projet_etiquette (id_suivi_projet);
CREATE INDEX ix_pgt_suivi_projet_etiquette_modif_date ON divers.pgt_suivi_projet_etiquette (modif_date);

CREATE TABLE divers.pgt_suivi_projet_ope (
    id_suivi_projet_ope  bigint NOT NULL,  -- IDsuiviProjet_Opé
    id_suivi_projet      bigint,  -- IDsuiviProjet
    id_salarie           bigint,  -- IDSalarie
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOp
    modif_elem           varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_suivi_projet_ope PRIMARY KEY (id_suivi_projet_ope)
);
CREATE INDEX ix_pgt_suivi_projet_ope_id_suivi_projet ON divers.pgt_suivi_projet_ope (id_suivi_projet);
CREATE INDEX ix_pgt_suivi_projet_ope_id_salarie ON divers.pgt_suivi_projet_ope (id_salarie);
CREATE INDEX ix_pgt_suivi_projet_ope_modif_date ON divers.pgt_suivi_projet_ope (modif_date);

CREATE TABLE divers.pgt_suivi_ticket_call (
    id_suivi_ticket_call  bigint,  -- IDSuiviTicketCall
    type_call             varchar(5) NOT NULL,  -- TypeCall
    id_encours            text,  -- IdEncours
    id_appel_en_cours     text,  -- IdAppelEnCours
    der_modif             timestamp,  -- DerModif
    CONSTRAINT pk_pgt_suivi_ticket_call PRIMARY KEY (type_call),
    CONSTRAINT uq_pgt_suivi_ticket_call_auto UNIQUE (id_suivi_ticket_call)
);

CREATE TABLE divers.pgt_tache_it (
    id_tache_it        bigint NOT NULL,  -- IDTacheIT
    id_suivi_projet    bigint,  -- IDsuiviProjet
    id_type_tache      smallint,  -- IDTypeTache
    conf               varchar(50),  -- Conf
    op_crea            bigint,  -- OPCREA
    titre              varchar(255),  -- Titre
    contenu            text,  -- Contenu
    datecrea           timestamp,  -- Datecrea
    version            varchar(20),  -- Version
    detail_resolution  text,  -- DétailResolution
    terminee           boolean,  -- Terminée
    terminee_date      timestamp,  -- TerminéeDate
    modif_date         timestamp,  -- ModifDate
    ope_traitement     bigint,  -- OpéTraitement
    modif_op           bigint,  -- ModifOP
    modif_elem         varchar(5),  -- ModifELEM
    id_type_statut     smallint,  -- IDTypeStatut
    id_dialogues       bigint,  -- IDDialogues
    CONSTRAINT pk_pgt_tache_it PRIMARY KEY (id_tache_it)
);
CREATE INDEX ix_pgt_tache_it_id_suivi_projet ON divers.pgt_tache_it (id_suivi_projet);
CREATE INDEX ix_pgt_tache_it_id_type_tache ON divers.pgt_tache_it (id_type_tache);
CREATE INDEX ix_pgt_tache_it_conf ON divers.pgt_tache_it (conf);
CREATE INDEX ix_pgt_tache_it_modif_date ON divers.pgt_tache_it (modif_date);
CREATE INDEX ix_pgt_tache_it_ope_traitement ON divers.pgt_tache_it (ope_traitement);
CREATE INDEX ix_pgt_tache_it_id_type_statut ON divers.pgt_tache_it (id_type_statut);
CREATE INDEX ix_pgt_tache_it_id_dialogues ON divers.pgt_tache_it (id_dialogues);

CREATE TABLE divers.pgt_tache_it_fichiers (
    id_tache_it_fichiers  bigint NOT NULL,  -- IDTacheIT_Fichiers
    id_tache_it           bigint,  -- IDTacheIT
    nom_fichier           text,  -- NomFichier
    taille_fic            bigint,  -- TailleFic
    modif_date            timestamp,  -- ModifDate
    modif_op              bigint,  -- ModifOp
    modif_elem            varchar(5),  -- ModifElem
    CONSTRAINT pk_pgt_tache_it_fichiers PRIMARY KEY (id_tache_it_fichiers)
);
CREATE INDEX ix_pgt_tache_it_fichiers_id_tache_it ON divers.pgt_tache_it_fichiers (id_tache_it);
CREATE INDEX ix_pgt_tache_it_fichiers_modif_date ON divers.pgt_tache_it_fichiers (modif_date);

CREATE TABLE divers.pgt_tache_it_planning (
    id_tache_it_planning_auto  bigint,  -- IDTacheIT_PlanningAuto
    id_tache_it_planning       bigint NOT NULL,  -- IDTacheIT_Planning
    id_tache_it                bigint,  -- IDTacheIT
    id_salarie                 bigint,  -- IDSalarie
    date_debut                 timestamp,  -- DateDébut
    date_fin                   timestamp,  -- DateFin
    op_crea                    bigint,  -- OPCrea
    datecrea                   timestamp,  -- Datecrea
    modif_op                   bigint,  -- ModifOP
    modif_date                 timestamp,  -- ModifDate
    modif_elem                 varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tache_it_planning PRIMARY KEY (id_tache_it_planning),
    CONSTRAINT uq_pgt_tache_it_planning_auto UNIQUE (id_tache_it_planning_auto)
);
CREATE INDEX ix_pgt_tache_it_planning_id_tache_it ON divers.pgt_tache_it_planning (id_tache_it);
CREATE INDEX ix_pgt_tache_it_planning_id_salarie ON divers.pgt_tache_it_planning (id_salarie);
CREATE INDEX ix_pgt_tache_it_planning_date_debut ON divers.pgt_tache_it_planning (date_debut);
CREATE INDEX ix_pgt_tache_it_planning_modif_date ON divers.pgt_tache_it_planning (modif_date);

CREATE TABLE divers.pgt_tache_it_recurrence (
    id_tache_it_recurrence  bigint NOT NULL,  -- IDTacheITRecurrence
    id_tache_it             bigint,  -- IDTacheIT
    op_crea                 bigint,  -- OPCREA
    datecrea                timestamp,  -- Datecrea
    version                 varchar(20),  -- Version
    conf                    varchar(50),  -- Conf
    support                 varchar(30),  -- Support
    modif_date              timestamp,  -- ModifDate
    modif_op                bigint,  -- ModifOP
    modif_elem              varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tache_it_recurrence PRIMARY KEY (id_tache_it_recurrence)
);
CREATE INDEX ix_pgt_tache_it_recurrence_id_tache_it ON divers.pgt_tache_it_recurrence (id_tache_it);
CREATE INDEX ix_pgt_tache_it_recurrence_conf ON divers.pgt_tache_it_recurrence (conf);
CREATE INDEX ix_pgt_tache_it_recurrence_modif_date ON divers.pgt_tache_it_recurrence (modif_date);

CREATE TABLE divers.pgt_type_statut (
    id_type_statut_auto  bigint,  -- IDTypeStatutAuto
    id_type_statut       smallint NOT NULL,  -- IDTypeStatut
    lib_statut           varchar(30),  -- Lib_Statut
    couleur_statut       integer,  -- CouleurStatut
    ordre_affichage      smallint,  -- OrdreAffichage
    modif_date           timestamp,  -- ModifDate
    modif_op             bigint,  -- ModifOP
    modif_elem           varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_type_statut PRIMARY KEY (id_type_statut),
    CONSTRAINT uq_pgt_type_statut_auto UNIQUE (id_type_statut_auto)
);
CREATE INDEX ix_pgt_type_statut_modif_date ON divers.pgt_type_statut (modif_date);

CREATE TABLE divers.pgt_type_tache (
    id_type_tache_auto  bigint,  -- IDTypeTacheAuto
    id_type_tache       smallint NOT NULL,  -- IDTypeTache
    lib_tache           varchar(50),  -- Lib_Tache
    couleur_tache       integer,  -- CouleurTache
    ordre_affichage     smallint,  -- OrdreAffichage
    modif_date          timestamp,  -- ModifDate
    modif_op            bigint,  -- ModifOP
    modif_elem          varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_type_tache PRIMARY KEY (id_type_tache),
    CONSTRAINT uq_pgt_type_tache_auto UNIQUE (id_type_tache_auto)
);
CREATE INDEX ix_pgt_type_tache_modif_date ON divers.pgt_type_tache (modif_date);

CREATE TABLE divers.pgt_uuid_connexion (
    id_uuid_connexion_auto  bigint,  -- IDUUID_connexionAuto
    id_salarie              bigint NOT NULL,  -- IDSalarie
    id_uuid_connexion       varchar(64),  -- IDUUID_connexion
    CONSTRAINT pk_pgt_uuid_connexion PRIMARY KEY (id_salarie),
    CONSTRAINT uq_pgt_uuid_connexion_auto UNIQUE (id_uuid_connexion_auto)
);
