-- Patch idempotent pour ajouter pgt_cvsuivi + pgt_prev_recrut au schema
-- recrutement (necessaire pour le module Fen_AgendaDetail).
--
-- Application :
--   psql -h <host> -U erp_user -d erp_db -f migration/patches/add_cv_suivi_prev_recrut.sql

CREATE TABLE IF NOT EXISTS recrutement.pgt_cvsuivi (
    id_cv_suivi_auto                                     bigint,
    id_cv_suivi                                          bigint NOT NULL,
    id_cvtheque                                          bigint,
    datecrea                                             timestamp,
    op_crea                                              bigint,
    id_cv_statut                                         bigint,
    type_elem                                            varchar(10),
    id_elem                                              bigint,
    observation                                          text,
    modif_date                                           timestamp,
    modif_op                                             bigint,
    modif_elem                                           varchar(5),
    id_cvtheque_datecrea_id_cv_statut_type_elem_id_elem  varchar(42),
    CONSTRAINT pk_pgt_cvsuivi PRIMARY KEY (id_cv_suivi),
    CONSTRAINT uq_pgt_cv_suivi_auto UNIQUE (id_cv_suivi_auto)
);
CREATE INDEX IF NOT EXISTS ix_pgt_cv_suivi_id_cvtheque
    ON recrutement.pgt_cvsuivi (id_cvtheque);
CREATE INDEX IF NOT EXISTS ix_pgt_cv_suivi_id_cv_statut
    ON recrutement.pgt_cvsuivi (id_cv_statut);
CREATE INDEX IF NOT EXISTS ix_pgt_cv_suivi_modif_date
    ON recrutement.pgt_cvsuivi (modif_date);

CREATE TABLE IF NOT EXISTS recrutement.pgt_prev_recrut (
    id_prevision_recrut_auto  bigint,
    id_prevision_recrut       bigint NOT NULL,
    id_cv_lieu_rdv            bigint,
    id_prev_recrut_etat       bigint,
    idorganigramme            bigint,
    id_recruteur              bigint,
    date_debut                date,
    date_fin                  date,
    date_session              date,
    date_butoire              date,
    potentiel_accueil         integer,
    nb_prod                   integer,
    coopt_s_moins_1           integer,
    coopt_j_moins_2           integer,
    sourcing_s_moins_1        integer,
    sourcing_j_moins_2        integer,
    taille_session            integer,
    obj_coopt                 integer,
    obj_sourcing              integer,
    nb_coopt_mini             integer,
    nb_sourcing_mini          integer,
    id_communes_france        bigint,
    commentaire               text,
    modif_date                timestamp,
    modif_op                  bigint,
    modif_elem                varchar(5),
    CONSTRAINT pk_pgt_prev_recrut PRIMARY KEY (id_prevision_recrut),
    CONSTRAINT uq_pgt_prev_recrut_auto UNIQUE (id_prevision_recrut_auto)
);
CREATE INDEX IF NOT EXISTS ix_pgt_prev_recrut_id_cv_lieu_rdv
    ON recrutement.pgt_prev_recrut (id_cv_lieu_rdv);
CREATE INDEX IF NOT EXISTS ix_pgt_prev_recrut_id_prev_recrut_etat
    ON recrutement.pgt_prev_recrut (id_prev_recrut_etat);
CREATE INDEX IF NOT EXISTS ix_pgt_prev_recrut_idorganigramme
    ON recrutement.pgt_prev_recrut (idorganigramme);
CREATE INDEX IF NOT EXISTS ix_pgt_prev_recrut_id_recruteur
    ON recrutement.pgt_prev_recrut (id_recruteur);
CREATE INDEX IF NOT EXISTS ix_pgt_prev_recrut_date_session
    ON recrutement.pgt_prev_recrut (date_session);
CREATE INDEX IF NOT EXISTS ix_pgt_prev_recrut_modif_date
    ON recrutement.pgt_prev_recrut (modif_date);
