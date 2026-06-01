// =============================================================================
//  SYNC ENGINE - HFSQL -> PostgreSQL (interne)
//  Squelette WLangage pour le programme de synchro decrit dans SYNC_WINDEV_SPEC.md
//
//  Architecture :
//    - 1 connexion HFSQL Classic/CS vers les fichiers source (existante)
//    - 1 connexion native PostgreSQL vers PG interne (a creer dans l'analyse)
//    - Mapping lu depuis migration/mapping/columns.csv (3816 lignes, 298 tables)
//    - Curseur dans la table sync.sync_control de PG interne
//
//  A coller dans un Set de procedures du projet WinDev.
//  Adapter :
//    - le nom des connexions (cnxHF, cnxPG)
//    - le chemin du CSV (gsCheminCSV)
//    - les parametres de connexion PG (host, port, user, mdp)
// =============================================================================

// ---------- Constantes et globales ----------------------------------------------

CONSTANT
    // Chemin du CSV de mapping. A adapter selon la machine.
    // Sur le poste de dev : D:\Claude\Projet Omaya\migration\mapping\columns.csv
    // Sur le serveur interne (deploiement) : C:\Omaya\migration\mapping\columns.csv (a creer)
    CSV_MAPPING  = "D:\Claude\Projet Omaya\migration\mapping\columns.csv"
    SYNC_SCHEMA  = "sync"
    SYNC_TABLE   = "sync_control"

    // Destinataire du rapport de fin de sync (separer par , pour plusieurs)
    MAIL_DEST = "a.loudieux@exosphere.fr"
END

// MaConnexionPG est l'alias de la connexion PG declaree dans l'analyse WinDev
// (rubrique Connexion -> "MaConnexionPG"). On y refere directement par son
// identifiant, pas via une chaine.

// Structure d'une ligne de mapping (= 1 colonne d'une table)
STColMap is structure
    schema       is string
    hfsql_table  is string
    pg_table     is string
    hfsql_column is string
    pg_column    is string
    pg_type      is string
    is_pk        is boolean   // pk = "1"
END

// Cache du mapping : par cle "schema.hfsql_table" -> tableau de STColMap
gMapping is associative array of array of STColMap

// =============================================================================
//  LOG VERS LE CHAMP "Resume"
// =============================================================================

PROCEDURE INTERNE LogAction(sMessage is string)
    // Horodatage HH:MM:SS + message, 1 ligne par action, append en fin de champ.
    // Le champ "Resume" est un champ de saisie multiligne sur la fenetre courante.
    // (Si tu as garde le nom avec accent dans WinDev, remplace "Resume" par "Résumé".)
    sLigne is string = HeureVersChaine(HeureSys(), "HH:MM:SS") + " - " + sMessage
    IF Resume <> "" THEN
        Resume = Resume + CR
    END
    Resume = Resume + sLigne
    // Rend la main au thread UI pour rafraichir l'affichage pendant la boucle
    Multitask(0)
END

// =============================================================================
//  POINT D'ENTREE
// =============================================================================

PROCEDURE INTERNE SyncAllTables()
    LoadMapping()                      // charge le CSV en memoire 1x
    EnsureSyncControl()                // CREATE sync.sync_control si absent
                                       // (la connexion MaConnexionPG est ouverte
                                       //  automatiquement par WinDev car les
                                       //  fichiers pgt_* sont declares dans
                                       //  l'analyse)

    LogAction("=== Synchronisation HFSQL -> PG demarree (" + gMapping.Occurrence + " tables) ===")

    // Iterer sur toutes les tables connues du mapping
    // Syntaxe : FOR EACH <valeur>, <cle> OF <tableau associatif>
    //   arrCols   = valeur (tableau de STColMap = colonnes de la table)
    //   sTableKey = cle    (chaine "schema.hfsql_table")
    arrCols is array of STColMap
    sTableKey is string
    FOR EACH arrCols, sTableKey OF gMapping
        sSchema is string  = ExtraitChaine(sTableKey, 1, ".")
        sTableHF is string = ExtraitChaine(sTableKey, 2, ".")
        sTablePG is string = arrCols[1].pg_table   // pg_table identique sur toutes les lignes

        WHEN EXCEPTION IN
            SyncOneTable(sSchema, sTableHF, sTablePG)
        DO
            LogAction("ERREUR " + sTableKey + " : " + ExceptionInfo())
            // on continue avec les autres tables
        END
    END

    LogAction("=== Synchronisation terminee ===")

    // Envoi du rapport par mail (le TXT en PJ contient l'historique complet)
    EnvoyerMailResume()
END

// =============================================================================
//  ENVOI MAIL RAPPORT (avec Resume en piece jointe TXT)
// =============================================================================

PROCEDURE INTERNE EnvoyerMailResume()
    // 1. Ecrire le contenu de Resume dans un fichier TXT temporaire
    sNomFichier is string = "sync_resume_" + ...
                            DateVersChaine(DateSys(), "AAAAMMJJ") + "_" + ...
                            HeureVersChaine(HeureSys(), "HHMMSS") + ".txt"
    sCheminTxt is string = fRepTemp() + "\" + sNomFichier
    nFich is int = fOuvre(sCheminTxt, foEcriture + foCreation)
    IF nFich = -1 THEN
        LogAction("[KO] Impossible de creer le fichier TXT : " + ErreurInfo())
    ELSE
        fEcritLigne(nFich, Resume)
        fFerme(nFich)

        // 2. Construction du message + PJ
        MonMessage is Email
        Ajoute(MonMessage.Destinataire, MAIL_DEST)
        MonMessage.Sujet = "Sync HFSQL -> PG terminee - " + ...
                           DateVersChaine(DateSys(), "JJ/MM/AAAA") + " " + ...
                           HeureVersChaine(HeureSys(), "HH:MM:SS")
        MonMessage.Message = "Le rapport detaille de la synchronisation est en piece jointe." + RC + ...
                             "Total tables traitees : " + gMapping.Occurrence

        pj is emailAttache
        pj..Nom     = fExtraitChemin(sCheminTxt, fFichier + fExtension)
        pj..Contenu = fChargeTexte(sCheminTxt)
        Ajoute(MonMessage.Attache, pj)

        // 3. Envoi via la proc globale existante
        WHEN EXCEPTION IN
            envoiMail(MonMessage)
            LogAction("[OK] Rapport envoye a " + MAIL_DEST)
        DO
            LogAction("[KO] Envoi mail : " + ExceptionInfo())
        END

        // (on garde le TXT dans le temp pour audit ; supprimable manuellement)
    END
END

// =============================================================================
//  CHARGEMENT MAPPING (CSV)
// =============================================================================

PROCEDURE INTERNE LoadMapping()
    DeleteAll(gMapping)
    nFich is int = fOpen(CSV_MAPPING, foRead)
    IF nFich = -1 THEN
        Error("Impossible d'ouvrir " + CSV_MAPPING + " : " + ErrorInfo())
        RETURN
    END

    sLigne is string = fReadLine(nFich)  // entete : on saute
    LOOP
        sLigne = fReadLine(nFich)
        IF sLigne = EOT THEN BREAK
        // CSV genere en UTF-8 (Python) -> conversion en ANSI pour matcher
        // les noms de rubriques HFSQL (ex. "Civilité" et non "CivilitÃ©")
        sLigne = Utf8ToAnsi(sLigne)
        sLigne = NoSpace(sLigne)
        IF sLigne = "" THEN CONTINUE

        // CSV simple sans guillemets sur ces colonnes
        // schema,hfsql_table,pg_table,hfsql_column,pg_column,pg_type,pk
        col is STColMap
        col.schema       = ExtractString(sLigne, 1, ",")
        col.hfsql_table  = ExtractString(sLigne, 2, ",")
        col.pg_table     = ExtractString(sLigne, 3, ",")
        col.hfsql_column = ExtractString(sLigne, 4, ",")
        col.pg_column    = ExtractString(sLigne, 5, ",")
        col.pg_type      = ExtractString(sLigne, 6, ",")
        col.is_pk        = (ExtractString(sLigne, 7, ",") = "1")

        sKey is string = col.schema + "." + col.hfsql_table
        // En WLangage, lire gMapping[sKey] sur une cle absente leve une
        // exception. On lit en defensif, on Add, puis on reaffecte (l'ecriture
        // cree l'entree si elle n'existe pas).
        arrCurrent is array of STColMap
        WHEN EXCEPTION IN
            arrCurrent = gMapping[sKey]
        DO
            // 1re ligne pour cette table -> arrCurrent reste vide, c'est OK
        END
        Add(arrCurrent, col)
        gMapping[sKey] = arrCurrent
    END
    fClose(nFich)
END

// =============================================================================
//  CURSEUR sync.sync_control
// =============================================================================

PROCEDURE INTERNE EnsureSyncControl()
    sSQL is string = [
        CREATE SCHEMA IF NOT EXISTS sync;
        CREATE TABLE IF NOT EXISTS sync.sync_control (
            schema_name   text      NOT NULL,
            table_name    text      NOT NULL,
            last_modif    timestamp,
            last_run      timestamp,
            rows_synced   bigint    DEFAULT 0,
            PRIMARY KEY (schema_name, table_name)
        );
    ]
    HExecuteSQLQuery("reqInit", MaConnexionPG, hQueryWithoutCorrection, sSQL)
END

PROCEDURE INTERNE GetLastModif(LOCAL sSchema is string, LOCAL sTable is string) : DateTime
    sSQL is string = "SELECT last_modif FROM sync.sync_control " + ...
                     "WHERE schema_name = '" + sSchema + "' " + ...
                     "  AND table_name = '" + sTable + "';"
    HExecuteSQLQuery("reqLast", MaConnexionPG, hQueryWithoutCorrection, sSQL)
    HReadFirst("reqLast")
    IF HOut("reqLast") THEN
        RESULT 0  // 1er run : full load
    END
    // Indirection : la requete est creee dynamiquement, WinDev ne connait
    // pas sa structure a la compilation -> lecture par {"req.col"}
    RESULT {"reqLast.last_modif"}
END

PROCEDURE INTERNE SetLastModif(LOCAL sSchema is string, LOCAL sTable is string, ...
                      LOCAL dtLastModif is DateTime, LOCAL nRows is int)
    // UPSERT du curseur
    sSQL is string = [
        INSERT INTO sync.sync_control (schema_name, table_name, last_modif, last_run, rows_synced)
        VALUES ('%1', '%2', '%3', current_timestamp, %4)
        ON CONFLICT (schema_name, table_name) DO UPDATE
        SET last_modif = EXCLUDED.last_modif,
            last_run = EXCLUDED.last_run,
            rows_synced = sync.sync_control.rows_synced + EXCLUDED.rows_synced;
    ]
    sSQL = StringBuild(sSQL, sSchema, sTable, DateTimeToString(dtLastModif, "AAAA-MM-JJ HH:MM:SS"), nRows)
    HExecuteSQLQuery("reqMaj", MaConnexionPG, hQueryWithoutCorrection, sSQL)
END

// =============================================================================
//  SYNC D'UNE TABLE
// =============================================================================

PROCEDURE INTERNE SyncOneTable(LOCAL sSchema is string, LOCAL sTableHF is string, ...
                      LOCAL sTablePG is string)
    sKey is string = sSchema + "." + sTableHF
    tabCols is array of STColMap = gMapping[sKey]

    // Trouver la colonne PK (1 seule par table, valide par le mapping)
    sColPK_HF is string = ""
    sColPK_PG is string = ""
    bHasModifDate is boolean = False
    FOR EACH col OF tabCols
        IF col.is_pk THEN
            sColPK_HF = col.hfsql_column
            sColPK_PG = col.pg_column
        END
        IF col.pg_column = "modif_date" THEN
            bHasModifDate = True
        END
    END
    IF sColPK_HF = "" THEN
        Error("Pas de PK dans le mapping pour " + sKey)
        RETURN
    END

    // 2 strategies selon la presence de modif_date
    IF bHasModifDate THEN
        SyncIncremental(sSchema, sTableHF, sTablePG, tabCols, sColPK_HF, sColPK_PG)
    ELSE
        SyncFullReload(sSchema, sTableHF, sTablePG, tabCols, sColPK_HF, sColPK_PG)
    END
END

// -- Strategie incrementale (292 tables avec modif_date) ----------------------

PROCEDURE INTERNE SyncIncremental(LOCAL sSchema, sTableHF, sTablePG is string, ...
                         LOCAL tabCols is array of STColMap, ...
                         LOCAL sColPK_HF, sColPK_PG is string)
    dtCurseur is DateTime = GetLastModif(sSchema, sTableHF)
    dtMax is DateTime = dtCurseur
    nRows is int = 0
    nPos  is int = 0

    // Init jauge pour cette table
    nTotal is int = SafeNbEnr(sTableHF)
    Jauge1..Libellé = sSchema + "." + sTableHF + " (" + nTotal + " lignes)"
    Jauge1..BorneMin = 0
    Jauge1..BorneMax = Max(nTotal, 1)
    Jauge1..Valeur = 0

    // Scan + skip : on parcourt tous les enregistrements et on filtre en WL.
    // (HFilter exigerait que ModifDate soit indexee HFSQL, ce qui n'est pas
    //  le cas par defaut sur les fichiers ERP. Pour les grosses tables, ajouter
    //  un index sur ModifDate + repasser sur HFilter pour gagner en perf.)
    HReadFirst(sTableHF)
    LOOP
        IF HOut(sTableHF) THEN BREAK
        IF {sTableHF + ".ModifDate"} >= dtCurseur THEN
            UpsertRow(sTablePG, tabCols, sTableHF, sColPK_HF, sColPK_PG)
            IF {sTableHF + ".ModifDate"} > dtMax THEN
                dtMax = {sTableHF + ".ModifDate"}
            END
            nRows++
        END
        nPos++
        // Refresh visuel tous les 50 enr pour ne pas saturer le rendu
        IF nPos MODULO 50 = 0 THEN
            Jauge1..Valeur = nPos
            Multitask(0)
        END
        HReadNext(sTableHF)
    END
    Jauge1..Valeur = nTotal

    IF nRows > 0 THEN
        SetLastModif(sSchema, sTableHF, dtMax, nRows)
    END
    LogAction(sSchema + "." + sTableHF + " : " + nRows + " lignes (incremental)")
END

// -- Strategie full-reload (6 tables sans modif_date) --------------------------

PROCEDURE INTERNE SyncFullReload(LOCAL sSchema, sTableHF, sTablePG is string, ...
                        LOCAL tabCols is array of STColMap, ...
                        LOCAL sColPK_HF, sColPK_PG is string)
    // Init jauge pour cette table
    nTotal is int = SafeNbEnr(sTableHF)
    Jauge1..Libellé = sSchema + "." + sTableHF + " (" + nTotal + " lignes, full-reload)"
    Jauge1..BorneMin = 0
    Jauge1..BorneMax = Max(nTotal, 1)
    Jauge1..Valeur = 0

    // Truncate + reload en 1 transaction pour eviter une fenetre vide
    HTransactionStart(MaConnexionPG)
    WHEN EXCEPTION IN
        HExecuteSQLQuery("reqTrunc", MaConnexionPG, hQueryWithoutCorrection, ...
                         "TRUNCATE TABLE " + sSchema + "." + sTablePG + ";")
        nRows is int = 0
        HReadFirst(sTableHF)
        LOOP
            IF HOut(sTableHF) THEN BREAK
            UpsertRow(sTablePG, tabCols, sTableHF, sColPK_HF, sColPK_PG)
            nRows++
            IF nRows MODULO 50 = 0 THEN
                Jauge1..Valeur = nRows
                Multitask(0)
            END
            HReadNext(sTableHF)
        END
        Jauge1..Valeur = nTotal
        HTransactionEnd(MaConnexionPG)
        SetLastModif(sSchema, sTableHF, DateSys() + TimeSys(), nRows)
        LogAction(sSchema + "." + sTableHF + " : " + nRows + " lignes (full-reload)")
    DO
        HTransactionCancel(MaConnexionPG)
        LogAction("ERREUR full-reload " + sTableHF + " : " + ExceptionInfo())
    END
END

// =============================================================================
//  COMPTAGE ENREGISTREMENTS TOLERANT (renvoie 0 sur erreur)
// =============================================================================

PROCEDURE INTERNE SafeNbEnr(LOCAL sFile is string) : int
    nRes is int = 0
    WHEN EXCEPTION IN
        nRes = HNbEnr(sFile)
    DO
        LogAction("[WARN] HNbEnr KO sur " + sFile + " : " + ExceptionInfo() + " (jauge en mode indetermine)")
        nRes = 0
    END
    RESULT nRes
END

// =============================================================================
//  AFFECTATION DATE TOLERANTE
// =============================================================================
// Une rubrique "date" cote HFSQL peut contenir :
//   - une vraie Date vide ("00000000" interne -> "0000-01-01" en PG -> erreur)
//   - un texte mal formate ("24/01/20") -> DateVersChaine plante avec une exception
//   - "0000-01-01" deja en chaine, ou autres surprises
// On encapsule l'affectation dans un WHEN EXCEPTION isole : si quoi que ce
// soit echoue, on ne touche pas a la colonne cible -> reste NULL apres HRAZ.

PROCEDURE INTERNE TryAssignDate(LOCAL sFilePG, sColPG, sFileHF, sColHF is string)
    WHEN EXCEPTION IN
        // Premier filtre brut sur la chaine (sans appeler DateVersChaine qui plante
        // sur l'annee 0000). Si on detecte un marqueur de date vide -> skip.
        sValSrc is string = "" + {sFileHF + "." + sColHF}
        bEmpty is boolean = (sValSrc = "" ...
                          OR sValSrc = "00000000" ...
                          OR sValSrc = "0000-00-00" ...
                          OR sValSrc = "0000-01-01" ...
                          OR sValSrc = "00/00/0000" ...
                          OR sValSrc = "01/01/0000" ...
                          OR Gauche(sValSrc, 4) = "0000")
        IF NOT bEmpty THEN
            {sFilePG + "." + sColPG} = {sFileHF + "." + sColHF}
        END
    DO
        // affectation impossible (texte mal forme, annee invalide...) -> on laisse NULL
    END
END

// =============================================================================
//  UPSERT D'UNE LIGNE (copie record-a-record par indirection)
// =============================================================================

PROCEDURE INTERNE UpsertRow(LOCAL sTablePG is string, ...
                   LOCAL tabCols is array of STColMap, ...
                   LOCAL sTableHF, sColPK_HF, sColPK_PG is string)
    // Tolerance : une ligne corrompue ne doit pas casser toute la sync.
    // L'erreur est loggee dans Resume, on passe a l'enregistrement suivant.
    WHEN EXCEPTION IN
        // Recherche par PK cote PG
        HReadSeekFirst(sTablePG, sColPK_PG, {sTableHF + "." + sColPK_HF})

        bFound is boolean = HFound(sTablePG)
        IF NOT bFound THEN
            HReset(sTablePG)
        END

        // Copie de tous les champs par indirection.
        // Cas special : pour les types date/timestamp/time, HFSQL renvoie
        // "00000000" sur une rubrique vide -> PG refuse en strict. On detecte
        // ET on retombe sur un WHEN EXCEPTION : si l'affectation plante quand
        // meme, on positionne NULL et on continue.
        FOR EACH col OF tabCols
            IF col.pg_type = "date" OR col.pg_type = "timestamp" OR col.pg_type = "time" THEN
                // Delegue a une proc dediee : isole le WHEN EXCEPTION pour ne
                // pas faire planter toute la ligne sur une date pourrie.
                TryAssignDate(sTablePG, col.pg_column, sTableHF, col.hfsql_column)
            ELSE
                {sTablePG + "." + col.pg_column} = {sTableHF + "." + col.hfsql_column}
            END
        END

        IF bFound THEN
            HModify(sTablePG)
        ELSE
            HAdd(sTablePG)
        END

        IF ErrorOccurred THEN
            LogAction("KO " + sTablePG + " PK=" + ...
                      {sTableHF + "." + sColPK_HF} + " : " + HErrorInfo())
        END
    DO
        LogAction("KO " + sTablePG + " PK=" + ...
                  {sTableHF + "." + sColPK_HF} + " : " + ExceptionInfo())
    END
END

// =============================================================================
//  TEST INTERACTIF (a appeler pour le POC)
// =============================================================================

PROCEDURE INTERNE TestSyncOneTable(sSchema is string, sTableHF is string)
    LoadMapping()
    EnsureSyncControl()
    sKey is string = sSchema + "." + sTableHF

    // Lecture defensive : la cle peut etre absente -> exception attrapee
    arrCols is array of STColMap
    bFound is boolean = True
    WHEN EXCEPTION IN
        arrCols = gMapping[sKey]
    DO
        bFound = False
    END
    IF NOT bFound THEN
        Error("Table inconnue dans le mapping : " + sKey)
        RETURN
    END

    sTablePG is string = arrCols[1].pg_table
    SyncOneTable(sSchema, sTableHF, sTablePG)
END

// Exemples d'appel pour le POC :
// (noms HFSQL EXACTS - respecte la casse, c'est sensible)
//   TestSyncOneTable("ticket", "TK_Statut")        // table simple sans memo
//   TestSyncOneTable("rh",     "salarie")          // table a accents
//   TestSyncOneTable("ticket_rh", "<table_a_memo>")  // table a memo binaire (a trouver dans le mapping)
//
// Pour explorer le mapping : ouvre migration/mapping/columns.csv
// Schemas disponibles : adv, divers, recrutement, rh, scool, ticket, ticket_bo,
// ticket_dpae, ticket_rh, ulease
SyncAllTables()
//
//TestSyncOneTable("rh", "salarie_coordonnees")
//TestSyncOneTable("rh", "salarie_embauche")
//TestSyncOneTable("rh", "TypePoste")
//TestSyncOneTable("rh", "salarie_droitAccès")
//TestSyncOneTable("rh", "TypeDroitAccès")
//TestSyncOneTable("rh", "TypeOrga")
//TestSyncOneTable("rh", "TypeOrga")
//TestSyncOneTable("rh", "TypeProduit")
//TestSyncOneTable("rh", "TypeProduit_Partenaire")
//TestSyncOneTable("rh", "TypeSortieSalarie")
//TestSyncOneTable("rh", "TypeHoraireTravail")
//TestSyncOneTable("rh", "TypeAbsence")
//TestSyncOneTable("rh", "societe")
//TestSyncOneTable("rh", "organigramme")
//TestSyncOneTable("recrutement", "CvAnnonceur")
//TestSyncOneTable("recrutement", "CvSource")
//TestSyncOneTable("divers", "communes_france")
//TestSyncOneTable("adv", "Partenaire")