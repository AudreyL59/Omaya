CREATE SCHEMA IF NOT EXISTS ticket;


CREATE TABLE ticket.pgt_tk_histo (
    id_tk_histo_auto  bigint,  -- IDTK_HistoAuto
    id_tk_histo       bigint  NOT NULL,  -- IDTK_Histo
    id_tk_liste       bigint,  -- IDTK_Liste
    operateur         bigint,  -- operateur
    date_histo        timestamp,  -- dateHisto
    id_tk_statut      bigint,  -- IDTK_Statut
    modif_date        timestamp,  -- ModifDate
    modif_elem        varchar(5),  -- ModifELEM
    modif_op          bigint,  -- ModifOP
    CONSTRAINT pk_pgt_tk_histo PRIMARY KEY (id_tk_histo),
    CONSTRAINT uq_pgt_tk_histo_auto UNIQUE (id_tk_histo_auto)
);
CREATE INDEX ix_pgt_tk_histo_id_tk_liste ON ticket.pgt_tk_histo (id_tk_liste);
CREATE INDEX ix_pgt_tk_histo_operateur ON ticket.pgt_tk_histo (operateur);
CREATE INDEX ix_pgt_tk_histo_id_tk_statut ON ticket.pgt_tk_histo (id_tk_statut);
CREATE INDEX ix_pgt_tk_histo_modif_date ON ticket.pgt_tk_histo (modif_date);

CREATE TABLE ticket.pgt_tk_liste (
    id_tk_liste             bigint  NOT NULL,  -- IDTK_Liste
    date_crea               timestamp,  -- DATECREA
    op_crea                 bigint,  -- OPCREA
    service                 varchar(5),  -- Service
    id_tk_type_demande      bigint,  -- IDTK_TypeDemande
    id_tk_statut            bigint,  -- IDTK_Statut
    date_report             date,  -- DateReport
    cloturee                boolean,  -- Cloturée
    date_cloture            timestamp,  -- DateCloture
    modif_date              timestamp,  -- ModifDate
    modif_elem              varchar(5),  -- ModifELEM
    modif_op                bigint,  -- ModifOP
    modification            boolean,  -- modification
    new_comment             boolean,  -- NewComment
    id_modif                bigint,  -- idModif
    type_modif              varchar(50),  -- TypeModif
    op_modif                bigint,  -- opModif
    op_comment              bigint,  -- opComment
    op_dest                 bigint,  -- OPDEST
    id_tk_liste_auto        bigint,  -- IDTK_ListeAuto
    op_traitement_staff     bigint,  -- OpTraitementStaff
    ordre_traitement_staff  smallint,  -- OrdreTraitementStaff
    CONSTRAINT pk_pgt_tk_liste PRIMARY KEY (id_tk_liste),
    CONSTRAINT uq_pgt_tk_liste_auto UNIQUE (id_tk_liste_auto)
);
CREATE INDEX ix_pgt_tk_liste_op_crea ON ticket.pgt_tk_liste (op_crea);
CREATE INDEX ix_pgt_tk_liste_service ON ticket.pgt_tk_liste (service);
CREATE INDEX ix_pgt_tk_liste_id_tk_type_demande ON ticket.pgt_tk_liste (id_tk_type_demande);
CREATE INDEX ix_pgt_tk_liste_id_tk_statut ON ticket.pgt_tk_liste (id_tk_statut);
CREATE INDEX ix_pgt_tk_liste_modif_date ON ticket.pgt_tk_liste (modif_date);
CREATE INDEX ix_pgt_tk_liste_op_dest ON ticket.pgt_tk_liste (op_dest);

CREATE TABLE ticket.pgt_tk_service_organigramme (
    id_tk_service_organigramme  bigint  NOT NULL,  -- IDTK_ServiceOrganigramme
    service                     varchar(5),  -- Service
    idorganigramme              bigint,  -- idorganigramme
    modif_date                  timestamp,  -- ModifDate
    CONSTRAINT pk_pgt_tk_service_organigramme PRIMARY KEY (id_tk_service_organigramme)
);
CREATE INDEX ix_pgt_tk_service_organigramme_service ON ticket.pgt_tk_service_organigramme (service);
CREATE INDEX ix_pgt_tk_service_organigramme_idorganigramme ON ticket.pgt_tk_service_organigramme (idorganigramme);
CREATE INDEX ix_pgt_tk_service_organigramme_modif_date ON ticket.pgt_tk_service_organigramme (modif_date);

CREATE TABLE ticket.pgt_tk_statut (
    id_tk_statut_auto  bigint,  -- IDTK_StatutAuto
    id_tk_statut       bigint  NOT NULL,  -- IDTK_Statut
    lib_statut         varchar(30),  -- Lib_Statut
    modif_date         timestamp,  -- ModifDate
    modif_op           bigint,  -- ModifOP
    modif_elem         varchar(5),  -- ModifELEM
    CONSTRAINT pk_pgt_tk_statut PRIMARY KEY (id_tk_statut),
    CONSTRAINT uq_pgt_tk_statut_auto UNIQUE (id_tk_statut_auto)
);
CREATE INDEX ix_pgt_tk_statut_modif_date ON ticket.pgt_tk_statut (modif_date);

CREATE TABLE ticket.pgt_tk_type_demande (
    id_tk_type_demande       bigint  NOT NULL,  -- IDTK_TypeDemande
    service                  varchar(5),  -- Service
    lib_type_demande         text,  -- Lib_TypeDemande
    modif_date               timestamp,  -- ModifDate
    modif_op                 bigint,  -- ModifOP
    modif_elem               varchar(5),  -- ModifELEM
    icone                    bytea,  -- icone
    id_tk_type_demande_auto  bigint,  -- IDTK_TypeDemandeAuto
    droit_acces              varchar(10),  -- DroitAccès
    droit_acces_vend         varchar(10),  -- DroitAccèsVend
    CONSTRAINT pk_pgt_tk_type_demande PRIMARY KEY (id_tk_type_demande),
    CONSTRAINT uq_pgt_tk_type_demande_auto UNIQUE (id_tk_type_demande_auto)
);
CREATE INDEX ix_pgt_tk_type_demande_service ON ticket.pgt_tk_type_demande (service);
CREATE INDEX ix_pgt_tk_type_demande_modif_date ON ticket.pgt_tk_type_demande (modif_date);
