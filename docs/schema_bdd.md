# Schéma des bases de données HFSQL

## Connexions

| Nom logique | BDD HFSQL | Thème |
|---|---|---|
| adv | Bdd_Omaya_ADV | Contrats/ventes par partenaire |
| divers | Bdd_Omaya_Divers | Messagerie, challenges, SMS, IT, pointage |
| recrutement | Bdd_Omaya_Recrutement | CV, annonces, recrutement |
| rh | Bdd_Omaya_RH | Salariés, droits, absences, mutuelles |
| scool | Bdd_Omaya_Scool | Formations, bulletins |
| ticket | Bdd_Omaya_Ticket | Tickets base |
| ticket_bo | Bdd_Omaya_Ticket_BO | Tickets back-office |
| ticket_dpae | Bdd_Omaya_Ticket_DPAE | Tickets DPAE |
| ticket_rh | Bdd_Omaya_Ticket_RH | Tickets RH |
| ulease | ulease | Flotte véhicules, carburant |

## Bdd_Omaya_ADV

Pattern par partenaire : {PREFIX}_contrat, {PREFIX}_etatContrat, {PREFIX}_histoAttrCtt, {PREFIX}_histoEtatCtt, {PREFIX}_produit, {PREFIX}_Remun

Préfixes : ENI, GEP, IAG, OEN, OHM, PRO, SFR, STR, TLC, VAL

Tables spécifiques :
- AgendaCommercial, AgendaCommercial_Catégorie, agendacommercial_origine, AgendaCommercial_Source
- baremePoint, BS_Envoi, client, ConvSujet
- ENI_contrat_compteur, ENI_contrat_Option
- GEP (pas de Remun)
- GroupeOpérateur, GroupeOpérateur_Partenaire, GroupeRem, GroupeRemTab, GroupeRemX, GroupeRemY
- importautosuivi, incidentCall
- OEN_contrat_compteur, OEN_contrat_Option, OEN_Contrat_Remun, OEN_histoEtatCttOEN
- OHM_agenda, OHM_agendaHisto, OHM_contrat_Financeur, OHM_contrat_panier, OHM_financeur, OHM_installateur, OHM_Installation, OHM_InstallationHisto, OHM_Leads, OHM_LeadsTypeIntall, OHM_StatutInstallation, OHM_StatutRDV, OHM_StatutRdvTech, OHM_TypeIntallClient
- Partenaire
- SFR_Cluster, SFR_ClusterObjectif, SFR_ClusterPériode, SFR_Contrat_Remun, SFR_histoEtatCttSFR, SFR_OffresProvad, SFR_StatutRDV
- statventes
- TDB_Qualité, TDB_QualitéContrat
- TypeEtatContrat, TypeProdDec

## Bdd_Omaya_Divers

- ChallengeEvenement, ChallengeGagnantsLotsCasinos, ChallengeLotsCasino
- Commande, Commande_facture
- CommunesFrance
- CompteurCoopt
- Conversation, ConversationIntervenant, ConversationLue, ConversationMessage
- couleursSTC
- CvSuivi, cvtheque
- demandeExtracIOS, demandeExtracVendeur
- DerogationOrga
- dialogue* (dialoguedest, dialoguehisto, dialoguelu, dialoguemsg, dialoguepj, dialogues, dialoguestatut, dialoguetheme)
- emoticone
- ExoCash* (ExoCashFamilleLot, ExoCashLot, ExoCashLotHistoStock)
- FeuillePointe, FeuillePointePointage, FeuillePointePorte, FeuillePointePortehisto, FeuillePointeRue
- HistoAnimation, HistoSMS
- IdentifiantPush
- InfoExoNew
- listeScanner, ListeSynchro
- logconnexion
- notificationpush
- parcIT, parcIT_Partenaire, parcITGPS, parcITPerception, parcITPerceptionResp, parcITRéparation
- PodiumMois, PodiumType, PodiumTypePart, PodiumTypePartOption, PodiumTypeProd, PodiumVendeur, PodiumVendeurPart
- Process, ProcessDroit, ProcessFichier
- ProgEvo_Objectifs
- smsanimation, SmsAnimation_Dest, SmsAnimation_Orga, smsanimation_orgadest, SmsAnimation_OrgaPeriode, smsanimation_regleenvoi
- suiviProjet, suiviProjet_Comment, SuiviProjet_Etiquette, suiviProjet_Opé
- SuiviTicketCall
- TacheIT, TacheIT_Fichiers, TacheIT_Planning, TacheITRecurrence
- TypeNiveauOrga, TypeOrga, TypeSociété, TypeStatut, TypeTache
- UUID_connexion

## Bdd_Omaya_Recrutement

- AgendaCatégorie, AgendaEvénement
- annuaire
- CvAnnonceur, CvLieuRdv, CvPoste, CvSource, CvStatut, CvSuivi, cvtheque, cvthequeTemporaire
- GroupeOpérateur_Partenaire
- MailRefusRH, mails_RH_CV
- PortailPartenaire
- prevRecrut, prevRecrutEtat
- SalonVisio, TypeSalonVisio

## Bdd_Omaya_RH

- absence
- DerogationOrga
- Doc_Distrib, docCourtage, docRH, docRHTYPE
- mutuelle
- NoteFrais, NoteFraisType
- organigramme
- ProfilDroitAccès
- salarie, salarie_ADF, salarie_ADF_Item, salarie_avance, salarie_coordonnées, salarie_decl_presence, salarie_decl_production, salarie_docRH, salarie_docUlease, salarie_droitAccès, salarie_embauche, salarie_infotbx, salarie_Livret, salarie_mutuelle, salarie_organigramme, salarie_part_DPAE, salarie_partenaire, salarie_prime, salarie_progevo, salarie_progevo_objectif, salarie_sortie, salarie_suivi, salarie_suiviADM
- societe, societe_docCourtage, societe_formjuri
- TypeAbsence, TypeADF_Item, TypeCttTravail, TypeDocDistributeur, TypeDroitAccès, TypeHoraireTravail, TypeNiveauOrga, TypeOperationLivret, TypeOrga, TypePoste, typeprime, TypeProduit, TypeProduit_Partenaire, TypeSociété, TypeSortieSalarie

## Bdd_Omaya_Scool

- Bulletin_Mention
- Formateur, Formation, Formation_AxeTravail, Formation_barèmeNote, Formation_Bulletin, Formation_Evenement, Formation_PrevRecrut, Formation_programme, Formation_salarié
- FormModèle, FormModèle_Programme

## Bdd_Omaya_Ticket

- TK_Call, TK_Call_Panier, TK_CallSFR
- TK_DemandeCttCourtage, TK_DemandeDocDistrib
- tk_demandesignpv_photo
- TK_Histo, TK_Liste
- TK_ServiceOrganigramme
- TK_Statut, TK_TypeDemande

## Bdd_Omaya_Ticket_BO

- TK_Call, TK_Call_Panier
- TK_CallSFR, TK_CallSFR_Panier, TK_CallSFR_RetKO, TK_CallSFR_RetRacc, TK_CallSFR_RetRDVTech, TK_CallSFR_RetVenteADD, tk_callsfr_typeanomalie
- TK_Demande* (Avance, CartePRO, CodeVendeur, CttCourtage, DocDistrib, DPAE_Distrib, DPAE_DistribPhoto, EnvoiTablette, Facturation, FacturationDistrib, Fourniture, Resa, SOS_BO)
- tk_demandecodevendeur_fichier
- TK_DPAE_DocDemat_Distrib
- TK_RetourRdvTechFIBRE
- TK_Type* (Commande, Resa, ResaSSFam, SOS_BO)

## Bdd_Omaya_Ticket_DPAE

- TK_DemandeDPAE, TK_DemandeDPAEPhoto, TK_DemandeDPAEPhoto_Temp
- TK_DPAE_DocDemat
- TK_TypePhotoDPAE

## Bdd_Omaya_Ticket_RH

- TK_CdeExoCash, TK_CdeExoCashEnvoi, TK_CdeExoCashLot
- Tk_DemandeAttExoCash
- TK_DemandeConges, TK_DemandeCttW, tk_demandecttw_doc
- TK_DemandeMutuelle
- tk_demandesignpv_photo, TK_DemandeSignPVUlease, TK_DemandeSignUlease
- TK_DemandeSortieRH, TK_DemandeSOS_JU
- TK_TypeSOS_JU

## ulease

- carte* (carteattribution, cartecalculatt, cartecarbrelevefournisseur, cartecarburant, cartefournisseur)
- conducteur
- docUlease, docUleaseTYPE
- typecapacite_photo, typerelevefournisseur
- vehicule_* (acc, Accident, amende, Conducteur, entretien, Etat, Fiche, Marque, pv, Releve, typecapacite)
