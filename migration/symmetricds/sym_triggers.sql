-- ============================================================
--  SymmetricDS : triggers + overrides de conflit (genere)
--  A appliquer apres sym_config_base.sql sur le noeud 'interne'.
-- ============================================================

-- Tables sym_* dans le schema dedie (cf. currentSchema).
SET search_path TO symmetricds, public;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_agenda_commercial', 'adv', 'pgt_agenda_commercial', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_agenda_commercial', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_agenda_commercial_categorie', 'adv', 'pgt_agenda_commercial_categorie', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_agenda_commercial_categorie', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_agenda_commercial_origine', 'adv', 'pgt_agenda_commercial_origine', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_agenda_commercial_origine', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_agenda_commercial_source', 'adv', 'pgt_agenda_commercial_source', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_agenda_commercial_source', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_bareme_point', 'adv', 'pgt_bareme_point', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_bareme_point', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_client', 'adv', 'pgt_client', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_client', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_eni_contrat', 'adv', 'pgt_eni_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_eni_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_eni_contrat_compteur', 'adv', 'pgt_eni_contrat_compteur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_eni_contrat_compteur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_eni_contrat_option', 'adv', 'pgt_eni_contrat_option', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_eni_contrat_option', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_eni_etat_contrat', 'adv', 'pgt_eni_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_eni_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_eni_histo_attr_ctt', 'adv', 'pgt_eni_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_eni_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_eni_histo_etat_ctt', 'adv', 'pgt_eni_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_eni_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_eni_produit', 'adv', 'pgt_eni_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_eni_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_eni_remun', 'adv', 'pgt_eni_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_eni_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_etat_call_ret', 'adv', 'pgt_etat_call_ret', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_etat_call_ret', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_gep_contrat', 'adv', 'pgt_gep_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_gep_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_gep_etat_contrat', 'adv', 'pgt_gep_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_gep_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_gep_histo_attr_ctt', 'adv', 'pgt_gep_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_gep_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_gep_histo_etat_ctt', 'adv', 'pgt_gep_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_gep_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_gep_produit', 'adv', 'pgt_gep_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_gep_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_groupe_operateur', 'adv', 'pgt_groupe_operateur', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_groupe_operateur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_groupe_operateur_partenaire', 'adv', 'pgt_groupe_operateur_partenaire', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_groupe_operateur_partenaire', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_groupe_rem', 'adv', 'pgt_groupe_rem', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_groupe_rem', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_groupe_rem_tab', 'adv', 'pgt_groupe_rem_tab', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_groupe_rem_tab', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_groupe_rem_x', 'adv', 'pgt_groupe_rem_x', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_groupe_rem_x', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_groupe_rem_y', 'adv', 'pgt_groupe_rem_y', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_groupe_rem_y', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_iag_contrat', 'adv', 'pgt_iag_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_iag_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_iag_etat_contrat', 'adv', 'pgt_iag_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_iag_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_iag_histo_attr_ctt', 'adv', 'pgt_iag_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_iag_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_iag_histo_etat_ctt', 'adv', 'pgt_iag_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_iag_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_iag_produit', 'adv', 'pgt_iag_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_iag_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_iag_remun', 'adv', 'pgt_iag_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_iag_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_importautosuivi', 'adv', 'pgt_importautosuivi', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_importautosuivi', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_incident_call', 'adv', 'pgt_incident_call', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_incident_call', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_contrat', 'adv', 'pgt_oen_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_contrat_compteur', 'adv', 'pgt_oen_contrat_compteur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_contrat_compteur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_contrat_option', 'adv', 'pgt_oen_contrat_option', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_contrat_option', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_contrat_remun', 'adv', 'pgt_oen_contrat_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_contrat_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_etat_contrat', 'adv', 'pgt_oen_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_histo_attr_ctt', 'adv', 'pgt_oen_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_histo_etat_ctt', 'adv', 'pgt_oen_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_histo_etat_ctt_oen', 'adv', 'pgt_oen_histo_etat_ctt_oen', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_histo_etat_ctt_oen', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_oen_produit', 'adv', 'pgt_oen_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_oen_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_partenaire', 'adv', 'pgt_partenaire', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_partenaire', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_pro_contrat', 'adv', 'pgt_pro_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_pro_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_pro_etat_contrat', 'adv', 'pgt_pro_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_pro_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_pro_histo_attr_ctt', 'adv', 'pgt_pro_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_pro_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_pro_histo_etat_ctt', 'adv', 'pgt_pro_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_pro_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_pro_produit', 'adv', 'pgt_pro_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_pro_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_pro_remun', 'adv', 'pgt_pro_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_pro_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_cluster', 'adv', 'pgt_sfr_cluster', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_cluster', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_cluster_objectif', 'adv', 'pgt_sfr_cluster_objectif', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_cluster_objectif', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_cluster_periode', 'adv', 'pgt_sfr_cluster_periode', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_cluster_periode', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_contrat', 'adv', 'pgt_sfr_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_contrat_remun', 'adv', 'pgt_sfr_contrat_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_contrat_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_etat_contrat', 'adv', 'pgt_sfr_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_histo_attr_ctt', 'adv', 'pgt_sfr_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_histo_etat_ctt', 'adv', 'pgt_sfr_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_histo_etat_ctt_sfr', 'adv', 'pgt_sfr_histo_etat_ctt_sfr', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_histo_etat_ctt_sfr', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_offres_provad', 'adv', 'pgt_sfr_offres_provad', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_offres_provad', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_produit', 'adv', 'pgt_sfr_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_remun', 'adv', 'pgt_sfr_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_sfr_statut_rdv', 'adv', 'pgt_sfr_statut_rdv', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_sfr_statut_rdv', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_statventes', 'adv', 'pgt_statventes', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_statventes', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_str_contrat', 'adv', 'pgt_str_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_str_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_str_etat_contrat', 'adv', 'pgt_str_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_str_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_str_histo_attr_ctt', 'adv', 'pgt_str_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_str_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_str_histo_etat_ctt', 'adv', 'pgt_str_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_str_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_str_produit', 'adv', 'pgt_str_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_str_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_str_remun', 'adv', 'pgt_str_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_str_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_tdb_qualite', 'adv', 'pgt_tdb_qualite', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_tdb_qualite', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_tdb_qualite_contrat', 'adv', 'pgt_tdb_qualite_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_tdb_qualite_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_tlc_contrat', 'adv', 'pgt_tlc_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_tlc_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_tlc_etat_contrat', 'adv', 'pgt_tlc_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_tlc_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_tlc_histo_attr_ctt', 'adv', 'pgt_tlc_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_tlc_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_tlc_histo_etat_ctt', 'adv', 'pgt_tlc_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_tlc_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_tlc_produit', 'adv', 'pgt_tlc_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_tlc_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_tlc_remun', 'adv', 'pgt_tlc_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_tlc_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_type_etat_contrat', 'adv', 'pgt_type_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_type_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_type_prod_dec', 'adv', 'pgt_type_prod_dec', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_type_prod_dec', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_val_contrat', 'adv', 'pgt_val_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_val_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_val_etat_contrat', 'adv', 'pgt_val_etat_contrat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_val_etat_contrat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_val_histo_attr_ctt', 'adv', 'pgt_val_histo_attr_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_val_histo_attr_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_val_histo_etat_ctt', 'adv', 'pgt_val_histo_etat_ctt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_val_histo_etat_ctt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_val_produit', 'adv', 'pgt_val_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_val_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('adv_pgt_val_remun', 'adv', 'pgt_val_remun', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('adv_pgt_val_remun', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_challenge_evenement', 'divers', 'pgt_challenge_evenement', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_challenge_evenement', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_challenge_gagnants_lots_casinos', 'divers', 'pgt_challenge_gagnants_lots_casinos', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_challenge_gagnants_lots_casinos', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_challenge_lots_casino', 'divers', 'pgt_challenge_lots_casino', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_challenge_lots_casino', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_commande', 'divers', 'pgt_commande', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_commande', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_commande_facture', 'divers', 'pgt_commande_facture', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_commande_facture', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_communes_france', 'divers', 'pgt_communes_france', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_communes_france', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_compteur_coopt', 'divers', 'pgt_compteur_coopt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_compteur_coopt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_couleurs_stc', 'divers', 'pgt_couleurs_stc', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_couleurs_stc', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_dialoguedest', 'divers', 'pgt_dialoguedest', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_dialoguedest', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_dialoguehisto', 'divers', 'pgt_dialoguehisto', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_dialoguehisto', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_dialoguelu', 'divers', 'pgt_dialoguelu', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_dialoguelu', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_dialoguemsg', 'divers', 'pgt_dialoguemsg', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_dialoguemsg', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_emoticone', 'divers', 'pgt_emoticone', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_emoticone', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_exo_cash_famille_lot', 'divers', 'pgt_exo_cash_famille_lot', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_exo_cash_famille_lot', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_exo_cash_lot', 'divers', 'pgt_exo_cash_lot', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_exo_cash_lot', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_exo_cash_lot_histo_stock', 'divers', 'pgt_exo_cash_lot_histo_stock', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_exo_cash_lot_histo_stock', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe', 'divers', 'pgt_feuille_pointe', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe_pointage', 'divers', 'pgt_feuille_pointe_pointage', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe_pointage', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe_porte', 'divers', 'pgt_feuille_pointe_porte', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe_porte', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe_portehisto', 'divers', 'pgt_feuille_pointe_portehisto', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe_portehisto', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe_rue', 'divers', 'pgt_feuille_pointe_rue', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_feuille_pointe_rue', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_histo_animation', 'divers', 'pgt_histo_animation', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_histo_animation', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_histo_sms', 'divers', 'pgt_histo_sms', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_histo_sms', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_identifiant_push', 'divers', 'pgt_identifiant_push', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_identifiant_push', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_info_exo_new', 'divers', 'pgt_info_exo_new', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_info_exo_new', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_liste_scanner', 'divers', 'pgt_liste_scanner', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_liste_scanner', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;
INSERT INTO sym_conflict (conflict_id, source_node_group_id, target_node_group_id, target_schema_name, target_table_name, detect_type, resolve_type, ping_back, resolve_changes_only, resolve_row_only, create_time, last_update_time) VALUES ('cf_divers_pgt_liste_scanner', 'erp', 'erp', 'divers', 'pgt_liste_scanner', 'USE_PK_DATA', 'FALLBACK', 'SINGLE_ROW', 0, 0, current_timestamp, current_timestamp) ON CONFLICT (conflict_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_logconnexion', 'divers', 'pgt_logconnexion', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_logconnexion', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_notificationpush', 'divers', 'pgt_notificationpush', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_notificationpush', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_parc_it', 'divers', 'pgt_parc_it', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_parc_it', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_parc_it_partenaire', 'divers', 'pgt_parc_it_partenaire', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_parc_it_partenaire', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_parc_itgps', 'divers', 'pgt_parc_itgps', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_parc_itgps', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_parc_it_perception', 'divers', 'pgt_parc_it_perception', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_parc_it_perception', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_parc_it_perception_resp', 'divers', 'pgt_parc_it_perception_resp', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_parc_it_perception_resp', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_parc_it_reparation', 'divers', 'pgt_parc_it_reparation', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_parc_it_reparation', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_podium_mois', 'divers', 'pgt_podium_mois', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_podium_mois', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_podium_type', 'divers', 'pgt_podium_type', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_podium_type', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_podium_type_part_option', 'divers', 'pgt_podium_type_part_option', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_podium_type_part_option', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_podium_type_part', 'divers', 'pgt_podium_type_part', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_podium_type_part', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_podium_type_prod', 'divers', 'pgt_podium_type_prod', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_podium_type_prod', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_podium_vendeur', 'divers', 'pgt_podium_vendeur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_podium_vendeur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_podium_vendeur_part', 'divers', 'pgt_podium_vendeur_part', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_podium_vendeur_part', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_process', 'divers', 'pgt_process', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_process', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_process_droit', 'divers', 'pgt_process_droit', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_process_droit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_process_fichier', 'divers', 'pgt_process_fichier', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_process_fichier', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_productionextractionjob', 'divers', 'pgt_productionextractionjob', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_productionextractionjob', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_prog_evo_objectifs', 'divers', 'pgt_prog_evo_objectifs', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_prog_evo_objectifs', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_smsanimation', 'divers', 'pgt_smsanimation', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_smsanimation', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;
INSERT INTO sym_conflict (conflict_id, source_node_group_id, target_node_group_id, target_schema_name, target_table_name, detect_type, resolve_type, ping_back, resolve_changes_only, resolve_row_only, create_time, last_update_time) VALUES ('cf_divers_pgt_smsanimation', 'erp', 'erp', 'divers', 'pgt_smsanimation', 'USE_PK_DATA', 'FALLBACK', 'SINGLE_ROW', 0, 0, current_timestamp, current_timestamp) ON CONFLICT (conflict_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_smsanimation_orgadest', 'divers', 'pgt_smsanimation_orgadest', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_smsanimation_orgadest', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_sms_animation_orga_periode', 'divers', 'pgt_sms_animation_orga_periode', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_sms_animation_orga_periode', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_smsanimation_regleenvoi', 'divers', 'pgt_smsanimation_regleenvoi', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_smsanimation_regleenvoi', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_suivi_projet', 'divers', 'pgt_suivi_projet', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_suivi_projet', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_suivi_projet_comment', 'divers', 'pgt_suivi_projet_comment', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_suivi_projet_comment', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_suivi_projet_etiquette', 'divers', 'pgt_suivi_projet_etiquette', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_suivi_projet_etiquette', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_suivi_projet_ope', 'divers', 'pgt_suivi_projet_ope', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_suivi_projet_ope', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_suivi_ticket_call', 'divers', 'pgt_suivi_ticket_call', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_suivi_ticket_call', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;
INSERT INTO sym_conflict (conflict_id, source_node_group_id, target_node_group_id, target_schema_name, target_table_name, detect_type, resolve_type, ping_back, resolve_changes_only, resolve_row_only, create_time, last_update_time) VALUES ('cf_divers_pgt_suivi_ticket_call', 'erp', 'erp', 'divers', 'pgt_suivi_ticket_call', 'USE_PK_DATA', 'FALLBACK', 'SINGLE_ROW', 0, 0, current_timestamp, current_timestamp) ON CONFLICT (conflict_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_tache_it', 'divers', 'pgt_tache_it', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_tache_it', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_tache_it_fichiers', 'divers', 'pgt_tache_it_fichiers', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_tache_it_fichiers', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_tache_it_planning', 'divers', 'pgt_tache_it_planning', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_tache_it_planning', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_tache_it_recurrence', 'divers', 'pgt_tache_it_recurrence', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_tache_it_recurrence', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_type_statut', 'divers', 'pgt_type_statut', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_type_statut', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('divers_pgt_type_tache', 'divers', 'pgt_type_tache', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('divers_pgt_type_tache', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_agenda_categorie', 'recrutement', 'pgt_agenda_categorie', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_agenda_categorie', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_agenda_evenement', 'recrutement', 'pgt_agenda_evenement', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_agenda_evenement', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_annuaire', 'recrutement', 'pgt_annuaire', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_annuaire', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_cv_annonceur', 'recrutement', 'pgt_cv_annonceur', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_cv_annonceur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_cv_lieu_rdv', 'recrutement', 'pgt_cv_lieu_rdv', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_cv_lieu_rdv', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_cvposte', 'recrutement', 'pgt_cvposte', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_cvposte', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_cv_source', 'recrutement', 'pgt_cv_source', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_cv_source', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_cvstatut', 'recrutement', 'pgt_cvstatut', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_cvstatut', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_cvsuivi', 'recrutement', 'pgt_cvsuivi', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_cvsuivi', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_cvtheque', 'recrutement', 'pgt_cvtheque', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_cvtheque', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_cvtheque_temporaire', 'recrutement', 'pgt_cvtheque_temporaire', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_cvtheque_temporaire', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_mail_refus_rh', 'recrutement', 'pgt_mail_refus_rh', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_mail_refus_rh', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;
INSERT INTO sym_conflict (conflict_id, source_node_group_id, target_node_group_id, target_schema_name, target_table_name, detect_type, resolve_type, ping_back, resolve_changes_only, resolve_row_only, create_time, last_update_time) VALUES ('cf_recrutement_pgt_mail_refus_rh', 'erp', 'erp', 'recrutement', 'pgt_mail_refus_rh', 'USE_PK_DATA', 'FALLBACK', 'SINGLE_ROW', 0, 0, current_timestamp, current_timestamp) ON CONFLICT (conflict_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_mails_rh_cv', 'recrutement', 'pgt_mails_rh_cv', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_mails_rh_cv', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_portail_partenaire', 'recrutement', 'pgt_portail_partenaire', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_portail_partenaire', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_prev_recrut', 'recrutement', 'pgt_prev_recrut', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_prev_recrut', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_prev_recrut_etat', 'recrutement', 'pgt_prev_recrut_etat', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_prev_recrut_etat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_salon_visio', 'recrutement', 'pgt_salon_visio', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_salon_visio', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('recrutement_pgt_type_salon_visio', 'recrutement', 'pgt_type_salon_visio', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('recrutement_pgt_type_salon_visio', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_absence', 'rh', 'pgt_absence', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_absence', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_derogation_orga', 'rh', 'pgt_derogation_orga', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_derogation_orga', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_doc_distrib', 'rh', 'pgt_doc_distrib', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_doc_distrib', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_doc_courtage', 'rh', 'pgt_doc_courtage', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_doc_courtage', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_doc_rh', 'rh', 'pgt_doc_rh', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_doc_rh', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_doc_rhtype', 'rh', 'pgt_doc_rhtype', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_doc_rhtype', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_mutuelle', 'rh', 'pgt_mutuelle', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_mutuelle', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_note_frais', 'rh', 'pgt_note_frais', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_note_frais', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_note_frais_type', 'rh', 'pgt_note_frais_type', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_note_frais_type', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_organigramme', 'rh', 'pgt_organigramme', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_organigramme', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_profil_droit_acces', 'rh', 'pgt_profil_droit_acces', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_profil_droit_acces', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie', 'rh', 'pgt_salarie', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_adf', 'rh', 'pgt_salarie_adf', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_adf', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_adf_item', 'rh', 'pgt_salarie_adf_item', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_adf_item', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_avance', 'rh', 'pgt_salarie_avance', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_avance', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_coordonnees', 'rh', 'pgt_salarie_coordonnees', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_coordonnees', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_decl_presence', 'rh', 'pgt_salarie_decl_presence', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_decl_presence', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_decl_production', 'rh', 'pgt_salarie_decl_production', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_decl_production', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_doc_rh', 'rh', 'pgt_salarie_doc_rh', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_doc_rh', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_doc_ulease', 'rh', 'pgt_salarie_doc_ulease', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_doc_ulease', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_droit_acces', 'rh', 'pgt_salarie_droit_acces', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_droit_acces', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_embauche', 'rh', 'pgt_salarie_embauche', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_embauche', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_infotbx', 'rh', 'pgt_salarie_infotbx', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_infotbx', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_livret', 'rh', 'pgt_salarie_livret', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_livret', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_mutuelle', 'rh', 'pgt_salarie_mutuelle', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_mutuelle', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_organigramme', 'rh', 'pgt_salarie_organigramme', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_organigramme', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_part_dpae', 'rh', 'pgt_salarie_part_dpae', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_part_dpae', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_partenaire', 'rh', 'pgt_salarie_partenaire', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_partenaire', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_prime', 'rh', 'pgt_salarie_prime', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_prime', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_progevo', 'rh', 'pgt_salarie_progevo', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_progevo', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_progevo_objectif', 'rh', 'pgt_salarie_progevo_objectif', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_progevo_objectif', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_sortie', 'rh', 'pgt_salarie_sortie', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_sortie', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_suivi', 'rh', 'pgt_salarie_suivi', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_suivi', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_salarie_suivi_adm', 'rh', 'pgt_salarie_suivi_adm', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_salarie_suivi_adm', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_societe', 'rh', 'pgt_societe', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_societe', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_societe_doc_courtage', 'rh', 'pgt_societe_doc_courtage', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_societe_doc_courtage', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_societe_formjuri', 'rh', 'pgt_societe_formjuri', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_societe_formjuri', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_absence', 'rh', 'pgt_type_absence', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_absence', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_adf_item', 'rh', 'pgt_type_adf_item', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_adf_item', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_ctt_travail', 'rh', 'pgt_type_ctt_travail', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_ctt_travail', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_doc_distributeur', 'rh', 'pgt_type_doc_distributeur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_doc_distributeur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;
INSERT INTO sym_conflict (conflict_id, source_node_group_id, target_node_group_id, target_schema_name, target_table_name, detect_type, resolve_type, ping_back, resolve_changes_only, resolve_row_only, create_time, last_update_time) VALUES ('cf_rh_pgt_type_doc_distributeur', 'erp', 'erp', 'rh', 'pgt_type_doc_distributeur', 'USE_PK_DATA', 'FALLBACK', 'SINGLE_ROW', 0, 0, current_timestamp, current_timestamp) ON CONFLICT (conflict_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_droit_acces', 'rh', 'pgt_type_droit_acces', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_droit_acces', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_horaire_travail', 'rh', 'pgt_type_horaire_travail', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_horaire_travail', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_niveau_orga', 'rh', 'pgt_type_niveau_orga', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_niveau_orga', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_operation_livret', 'rh', 'pgt_type_operation_livret', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_operation_livret', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_orga', 'rh', 'pgt_type_orga', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_orga', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_poste', 'rh', 'pgt_type_poste', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_poste', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_typeprime', 'rh', 'pgt_typeprime', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_typeprime', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_produit', 'rh', 'pgt_type_produit', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_produit', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_produit_partenaire', 'rh', 'pgt_type_produit_partenaire', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_produit_partenaire', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('rh_pgt_type_sortie_salarie', 'rh', 'pgt_type_sortie_salarie', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('rh_pgt_type_sortie_salarie', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_bulletin_mention', 'scool', 'pgt_bulletin_mention', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_bulletin_mention', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_formateur', 'scool', 'pgt_formateur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_formateur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_formation', 'scool', 'pgt_formation', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_formation', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_formation_bareme_note', 'scool', 'pgt_formation_bareme_note', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_formation_bareme_note', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_formation_bulletin', 'scool', 'pgt_formation_bulletin', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_formation_bulletin', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_formation_evenement', 'scool', 'pgt_formation_evenement', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_formation_evenement', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_formation_prev_recrut', 'scool', 'pgt_formation_prev_recrut', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_formation_prev_recrut', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_formation_programme', 'scool', 'pgt_formation_programme', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_formation_programme', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_formation_salarie', 'scool', 'pgt_formation_salarie', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_formation_salarie', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_form_modele', 'scool', 'pgt_form_modele', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_form_modele', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('scool_pgt_form_modele_programme', 'scool', 'pgt_form_modele_programme', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('scool_pgt_form_modele_programme', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_pgt_tk_histo', 'ticket', 'pgt_tk_histo', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_pgt_tk_histo', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_pgt_tk_liste', 'ticket', 'pgt_tk_liste', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_pgt_tk_liste', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_pgt_tk_service_organigramme', 'ticket', 'pgt_tk_service_organigramme', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_pgt_tk_service_organigramme', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_pgt_tk_statut', 'ticket', 'pgt_tk_statut', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_pgt_tk_statut', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_pgt_tk_type_demande', 'ticket', 'pgt_tk_type_demande', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_pgt_tk_type_demande', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call', 'ticket_bo', 'pgt_tk_call', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_panier', 'ticket_bo', 'pgt_tk_call_panier', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_panier', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr', 'ticket_bo', 'pgt_tk_call_sfr', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_panier', 'ticket_bo', 'pgt_tk_call_sfr_panier', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_panier', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_ret_ko', 'ticket_bo', 'pgt_tk_call_sfr_ret_ko', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_ret_ko', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_ret_racc', 'ticket_bo', 'pgt_tk_call_sfr_ret_racc', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_ret_racc', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_ret_rdv_tech', 'ticket_bo', 'pgt_tk_call_sfr_ret_rdv_tech', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_ret_rdv_tech', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_ret_vente_add', 'ticket_bo', 'pgt_tk_call_sfr_ret_vente_add', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_call_sfr_ret_vente_add', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_callsfr_typeanomalie', 'ticket_bo', 'pgt_tk_callsfr_typeanomalie', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_callsfr_typeanomalie', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_avance', 'ticket_bo', 'pgt_tk_demande_avance', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_avance', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_carte_pro', 'ticket_bo', 'pgt_tk_demande_carte_pro', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_carte_pro', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_code_vendeur', 'ticket_bo', 'pgt_tk_demande_code_vendeur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_code_vendeur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demandecodevendeur_fichier', 'ticket_bo', 'pgt_tk_demandecodevendeur_fichier', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demandecodevendeur_fichier', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_ctt_courtage', 'ticket_bo', 'pgt_tk_demande_ctt_courtage', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_ctt_courtage', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_doc_distrib', 'ticket_bo', 'pgt_tk_demande_doc_distrib', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_doc_distrib', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_dpae_distrib', 'ticket_bo', 'pgt_tk_demande_dpae_distrib', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_dpae_distrib', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_dpae_distrib_photo', 'ticket_bo', 'pgt_tk_demande_dpae_distrib_photo', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_dpae_distrib_photo', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_envoi_tablette', 'ticket_bo', 'pgt_tk_demande_envoi_tablette', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_envoi_tablette', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_facturation', 'ticket_bo', 'pgt_tk_demande_facturation', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_facturation', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_facturation_distrib', 'ticket_bo', 'pgt_tk_demande_facturation_distrib', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_facturation_distrib', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_fourniture', 'ticket_bo', 'pgt_tk_demande_fourniture', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_fourniture', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_resa', 'ticket_bo', 'pgt_tk_demande_resa', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_resa', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_sos_bo', 'ticket_bo', 'pgt_tk_demande_sos_bo', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_demande_sos_bo', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_dpae_doc_demat_distrib', 'ticket_bo', 'pgt_tk_dpae_doc_demat_distrib', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_dpae_doc_demat_distrib', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_retour_rdv_tech_fibre', 'ticket_bo', 'pgt_tk_retour_rdv_tech_fibre', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_retour_rdv_tech_fibre', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_type_commande', 'ticket_bo', 'pgt_tk_type_commande', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_type_commande', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_type_resa', 'ticket_bo', 'pgt_tk_type_resa', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_type_resa', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_type_resa_ss_fam', 'ticket_bo', 'pgt_tk_type_resa_ss_fam', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_type_resa_ss_fam', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_type_sos_bo', 'ticket_bo', 'pgt_tk_type_sos_bo', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_bo_pgt_tk_type_sos_bo', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_demande_dpae', 'ticket_dpae', 'pgt_tk_demande_dpae', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_demande_dpae', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_demande_dpae_photo', 'ticket_dpae', 'pgt_tk_demande_dpae_photo', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_demande_dpae_photo', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_demande_dpae_photo_temp', 'ticket_dpae', 'pgt_tk_demande_dpae_photo_temp', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_demande_dpae_photo_temp', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_dpae_doc_demat', 'ticket_dpae', 'pgt_tk_dpae_doc_demat', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_dpae_doc_demat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_type_photo_dpae', 'ticket_dpae', 'pgt_tk_type_photo_dpae', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_dpae_pgt_tk_type_photo_dpae', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_cde_exo_cash', 'ticket_rh', 'pgt_tk_cde_exo_cash', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_cde_exo_cash', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_cde_exo_cash_envoi', 'ticket_rh', 'pgt_tk_cde_exo_cash_envoi', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_cde_exo_cash_envoi', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_cde_exo_cash_lot', 'ticket_rh', 'pgt_tk_cde_exo_cash_lot', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_cde_exo_cash_lot', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_att_exo_cash', 'ticket_rh', 'pgt_tk_demande_att_exo_cash', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_att_exo_cash', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_conges', 'ticket_rh', 'pgt_tk_demande_conges', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_conges', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_ctt_w', 'ticket_rh', 'pgt_tk_demande_ctt_w', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_ctt_w', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demandecttw_doc', 'ticket_rh', 'pgt_tk_demandecttw_doc', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demandecttw_doc', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_mutuelle', 'ticket_rh', 'pgt_tk_demande_mutuelle', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_mutuelle', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_mutuelle_fic', 'ticket_rh', 'pgt_tk_demande_mutuelle_fic', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_mutuelle_fic', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demandesignpv_photo', 'ticket_rh', 'pgt_tk_demandesignpv_photo', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demandesignpv_photo', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_sign_pv_ulease', 'ticket_rh', 'pgt_tk_demande_sign_pv_ulease', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_sign_pv_ulease', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_sign_ulease', 'ticket_rh', 'pgt_tk_demande_sign_ulease', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_sign_ulease', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_sortie_rh', 'ticket_rh', 'pgt_tk_demande_sortie_rh', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_sortie_rh', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_sos_ju', 'ticket_rh', 'pgt_tk_demande_sos_ju', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_demande_sos_ju', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_type_sos_ju', 'ticket_rh', 'pgt_tk_type_sos_ju', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ticket_rh_pgt_tk_type_sos_ju', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_carteattribution', 'ulease', 'pgt_carteattribution', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_carteattribution', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_cartecalculatt', 'ulease', 'pgt_cartecalculatt', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_cartecalculatt', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_cartecarbrelevefournisseur', 'ulease', 'pgt_cartecarbrelevefournisseur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_cartecarbrelevefournisseur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_cartecarburant', 'ulease', 'pgt_cartecarburant', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_cartecarburant', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_cartefournisseur', 'ulease', 'pgt_cartefournisseur', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_cartefournisseur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_conducteur', 'ulease', 'pgt_conducteur', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_conducteur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_doc_ulease', 'ulease', 'pgt_doc_ulease', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_doc_ulease', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_doc_ulease_type', 'ulease', 'pgt_doc_ulease_type', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_doc_ulease_type', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_typecapacite_photo', 'ulease', 'pgt_typecapacite_photo', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_typecapacite_photo', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_typerelevefournisseur', 'ulease', 'pgt_typerelevefournisseur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_typerelevefournisseur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_accident', 'ulease', 'pgt_vehicule_accident', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_accident', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_amende', 'ulease', 'pgt_vehicule_amende', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_amende', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_conducteur', 'ulease', 'pgt_vehicule_conducteur', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_conducteur', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_entretien', 'ulease', 'pgt_vehicule_entretien', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_entretien', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_etat', 'ulease', 'pgt_vehicule_etat', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_etat', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_fiche', 'ulease', 'pgt_vehicule_fiche', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_fiche', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_marque', 'ulease', 'pgt_vehicule_marque', 'erp_blob', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_marque', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_releve', 'ulease', 'pgt_vehicule_releve', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_releve', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;

INSERT INTO sym_trigger (trigger_id, source_schema_name, source_table_name, channel_id, sync_on_insert, sync_on_update, sync_on_delete, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_typecapacite', 'ulease', 'pgt_vehicule_typecapacite', 'erp_data', 1, 1, 1, current_timestamp, current_timestamp) ON CONFLICT (trigger_id) DO NOTHING;
INSERT INTO sym_trigger_router (trigger_id, router_id, initial_load_order, last_update_time, create_time) VALUES ('ulease_pgt_vehicule_typecapacite', 'erp2erp', 100, current_timestamp, current_timestamp) ON CONFLICT (trigger_id, router_id) DO NOTHING;
