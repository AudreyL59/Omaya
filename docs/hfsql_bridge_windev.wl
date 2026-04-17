// =============================================================
// HFSQLBridge - Exécutable WinDev à compiler
// Projet : "Exécutable Windows" (sans fenêtre)
// =============================================================
// Usage en ligne de commande :
//   hfsql_bridge.exe <serveur:port> <user> <pwd> <filepwd> <database> <requete_sql> <fichier_sortie>
//
// Écrit le résultat JSON dans <fichier_sortie> :
//   Succès : {"ok": true, "rows": [{...}, {...}], "count": 2}
//   Erreur : {"ok": false, "error": "message d'erreur"}
// =============================================================

// Code d'initialisation du projet (onglet "Code du projet" > "Initialisation")

sServeur		est une chaîne	= LigneCommande(1)
sUser			est une chaîne	= LigneCommande(2)
sPwd			est une chaîne	= LigneCommande(3)
sFilePwd		est une chaîne	= LigneCommande(4)
sDatabase		est une chaîne	= LigneCommande(5)
sSQL			est une chaîne	= LigneCommande(6)
sFichierSortie	est une chaîne	= LigneCommande(7)
sNomConnexion	est une chaîne	= LigneCommande(8)

// Vérifier les paramètres
si sServeur = "" ou sSQL = "" ou sFichierSortie = "" alors
	si sFichierSortie <> "" alors
		fSauveTexte(sFichierSortie, "{""ok"":false,""error"":""Paramètres manquants""}")
	fin
	FinProgramme()
fin

// Mot de passe des fichiers
si sFilePwd <> "" alors
	HPasse("*", sFilePwd)
fin

// Connexion — utilise le nom de connexion de l'analyse si fourni
si sNomConnexion = "" alors
	sNomConnexion = "MaConnexion"
fin

HDécritConnexion(sNomConnexion, sUser, sPwd, sServeur, sDatabase, hAccèsHFClientServeur)

si pas HOuvreConnexion(sNomConnexion) alors
	sErr est une chaîne = Remplace(HErreurInfo(), """", "\""")
	sErr = Remplace(sErr, RC, " ")
	fSauveTexte(sFichierSortie, "{""ok"":false,""error"":""" + sErr + """}")
	FinProgramme()
fin

// Importer la description des fichiers depuis le serveur
sListeFichiers est une chaîne = HListeFichier(sNomConnexion)
pour toute chaîne sFichier de sListeFichiers séparée par RC
	si sFichier <> "" alors
		HDéclareExterne(sFichier, sNomConnexion)
	fin
fin

// Exécuter la requête
MaRequête est une Source de Données
si pas HExécuteRequêteSQL(MaRequête, sNomConnexion, hRequêteSansCorrection, sSQL) alors
	sErr2 est une chaîne = Remplace(HErreurInfo(), """", "\""")
	sErr2 = Remplace(sErr2, RC, " ")
	fSauveTexte(sFichierSortie, "{""ok"":false,""error"":""" + sErr2 + """}")
	HFermeConnexion(sNomConnexion)
	FinProgramme()
fin

// Récupérer les rubriques : noms simples + détail pour les types
sListeRubSimple est une chaîne = HListeRubrique(MaRequête)
sListeRubDetail est une chaîne = HListeRubrique(MaRequête, hLstDétail)

// Construire un tableau associatif nom -> type
tabTypes est un tableau associatif de chaînes
pour toute chaîne sLigneRub de sListeRubDetail séparée par RC
	si sLigneRub = "" alors continuer
	sN est une chaîne = ExtraitChaîne(sLigneRub, 1, TAB)
	sT est une chaîne = ExtraitChaîne(sLigneRub, 3, TAB)
	si sN <> "" alors
		tabTypes[sN] = sT
	fin
fin

// Lister les champs binaires
tabBinaires est un tableau de chaînes
pour toute chaîne sNomRub de sListeRubSimple séparée par RC
	si sNomRub = "" alors continuer
	si tabTypes[sNomRub] = "16" ou tabTypes[sNomRub] = "19" ou tabTypes[sNomRub] = "23" alors
		tabBinaires.Ajoute(sNomRub)
	fin
fin

// Construire le JSON
sJSON		est une chaîne	= "{""ok"":true,""rows"":["
nCount		est un entier	= 0

HLitPremier(MaRequête)
tantque pas HEnDehors(MaRequête)
	si nCount > 0 alors
		sJSON += ","
	fin

	// JSON de base via HEnregistrementVersJSON (gère les champs normaux)
	sRowJSON est une chaîne = HEnregistrementVersJSON(MaRequête)

	// Ajouter les champs binaires en Base64
	pour tout sChampBin de tabBinaires
		QUAND EXCEPTION DANS
			bufVal est un Buffer = {MaRequête, sChampBin}
			si bufVal <> "" alors
				sB64 est une chaîne = Encode(bufVal, encodeBASE64)
				// Trouver la position du dernier } pour injecter avant
				nPos est un entier = Taille(sRowJSON)
				// Remonter pour trouver le } du sous-objet
				tantque nPos > 0 et sRowJSON[[nPos]] <> "}"
					nPos--
				fin
				si nPos > 1 alors
					// Remonter encore un } (il y a 2 niveaux : {_SOURCE:{...}})
					nPos2 est un entier = nPos - 1
					tantque nPos2 > 0 et sRowJSON[[nPos2]] <> "}"
						nPos2--
					fin
					si nPos2 > 0 alors
						sRowJSON = sRowJSON[[1 À nPos2-1]] + ",""" + sChampBin + """:""" + sB64 + """" + sRowJSON[[nPos2 À]]
					fin
				fin
			fin
		FAIRE
			// Ignorer si erreur
		FIN
	fin

	sJSON += sRowJSON
	nCount++
	HLitSuivant(MaRequête)
fin

sJSON += "],""count"":" + nCount + "}"

fSauveTexte(sFichierSortie, sJSON)
HFermeConnexion(sNomConnexion)
