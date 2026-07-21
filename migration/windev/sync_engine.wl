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
    Résumé..Curseur = Taille(Résumé)
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

    // Apres sync : compare le nb d'enregistrements HFSQL vs PG.
    // Si ecart, log un WARN (la table est sous-/sur-syncronisee).
    nDiff is int = CheckCountMismatch(sSchema, sTableHF, sTablePG)
    si nDiff > 0 alors
        Interrupteur1 = 1
        if bHasModifDate then
            SyncIncremental(sSchema, sTableHF, sTablePG, tabCols, sColPK_HF, sColPK_PG)
        else
            SyncFullReload(sSchema, sTableHF, sTablePG, tabCols, sColPK_HF, sColPK_PG)
        end
    fin
    Interrupteur1 = 0
END


// -- Verif coherence HFSQL <-> PG (apres chaque sync) -------------------------
//
// Compte les enregistrements des 2 cotes et log un WARN si difference.
// Ne fait rien si HFSQL ou PG inaccessibles (le log d'erreur principal aura
// deja signale).
procédure interne CheckCountMismatch(local sSchema, sTableHF, sTablePG is string)
    nDiff is int
    when exception in
        nHF		is int		= SafeNbEnr(sTableHF)
        nPG		is int		= -1

        sSQL	is string	= "SELECT COUNT(*) AS n FROM " + sSchema + "." + sTablePG
        HExecuteSQLQuery("reqCount", MaConnexionPG, hQueryWithoutCorrection, sSQL)
        HReadFirst("reqCount")
        if not HOut("reqCount") then
            nPG = {"reqCount.n"}
        end

        if nPG >= 0 and nHF <> nPG then
            nDiff = nHF - nPG
            LogAction("[WARN] " + sSchema + "." + sTableHF + ...
            " : HFSQL=" + nHF + " vs PG=" + nPG + ...
            " (diff=" + nDiff + ")")


        end

    do
        LogAction("[WARN] CheckCount " + sSchema + "." + sTableHF + ...
        " : " + ExceptionInfo())
    end
    renvoyer nDiff
end

// -- Strategie incrementale (292 tables avec modif_date) ----------------------

PROCEDURE INTERNE SyncIncremental(LOCAL sSchema, sTableHF, sTablePG is string, ...
                         LOCAL tabCols is array of STColMap, ...
                         LOCAL sColPK_HF, sColPK_PG is string)
    dtCurseur is DateTime = GetLastModif(sSchema, sTableHF)
    si Interrupteur1 alors dtCurseur = "20180101000000000"
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
//
// COMPORTEMENT : on FORCE toujours une valeur (NULL si supporte par la
// rubrique de l'analyse, sinon date sentinelle 1900-01-01 valide pour PG).
//
// PIEGE 1 : "{file + '.' + col} = Null" N'AFFECTE PAS NULL a la rubrique.
// Ca affecte la VALEUR PAR DEFAUT du type (00000000 pour date, 0 pour
// entier, "" pour string). Pour forcer NULL il FAUT ..NULL = True.
//
// PIEGE 2 : "..NULL = True" est SILENCIEUSEMENT IGNORE si la rubrique de
// l'analyse WinDev n'a PAS la case "Supporte la valeur NULL" cochee. Le
// buffer garde alors sa valeur par defaut ("00000000") -> WinDev serialise
// en '0000-01-01' pour PG -> ERREUR:  valeur du champ date/time en dehors
// des limites : «0000-01-01». Il faut verifier ..NULL apres l'affectation
// et, si non applique, forcer une date sentinelle valide.
//
// SENTINELLE : 1900-01-01 est PG-valide, distinctive et facile a filtrer
// cote app ("if date >= '1901-01-01' alors la date est significative").
// Cf memo reference_wlanguage_gotchas 'Dates vides HFSQL'.

PROCEDURE INTERNE TryAssignDate(LOCAL sFilePG, sColPG, sFileHF, sColHF is string)
    WHEN EXCEPTION IN
        // Premier filtre brut sur la chaine (sans appeler DateVersChaine qui plante
        // sur l'annee 0000).
        sValSrc is string = "" + {sFileHF + "." + sColHF}
        bEmpty is boolean = (sValSrc = "" ...
                          OR sValSrc = "00000000" ...
                          OR sValSrc = "0000-00-00" ...
                          OR sValSrc = "0000-01-01" ...
                          OR sValSrc = "00/00/0000" ...
                          OR sValSrc = "01/01/0000" ...
                          OR Gauche(sValSrc, 4) = "0000")
        IF bEmpty THEN
            ForceNullOuSentinelle(sFilePG, sColPG)
        ELSE
            {sFilePG + "." + sColPG} = {sFileHF + "." + sColHF}
            // Si l'affectation a leve une erreur HFSQL silencieuse (ex. erreur 80
            // = format date invalide cote source : "24/01/20", textes pourris...),
            // ErrorOccurred est positionne mais aucune exception WLangage n'est
            // levee -> ce DO n'attrape rien. On force NULL/sentinelle pour ne
            // pas que ErrorOccurred persiste sur le HAdd/HModify suivant.
            IF ErrorOccurred THEN
                ForceNullOuSentinelle(sFilePG, sColPG)
            END
        END
    DO
        // exception WLangage (DateVersChaine sur annee 0000, type mismatch...)
        // -> delegue a la proc de fallback (WLangage interdit d'imbriquer
        // WHEN EXCEPTION dans un DO).
        SafeForceNullOuSentinelle(sFilePG, sColPG)
    END
END

// -- Force une sentinelle 1900-01-01 sur une rubrique date/timestamp.
//    On n'utilise PLUS ..NULL car il est trop capricieux avec le
//    driver PG WinDev : meme quand ..NULL semble applique, le buffer
//    est parfois re-serialise en '0000-01-01' a l'INSERT. Le seul
//    moyen fiable est d'ecraser explicitement avec un objet Date/
//    DateHeure typé et rempli par membres (evite les conversions
//    string qui peuvent silencieusement echouer).
PROCEDURE INTERNE ForceNullOuSentinelle(LOCAL sFilePG, sColPG is string)
    // 1. Tente comme Date (rubrique de type "date" cote PG)
    IF TryAssignSentinelleDate(sFilePG, sColPG) THEN
        RETURN
    END
    // 2. Fallback DateHeure (rubrique de type "timestamp" cote PG)
    TryAssignSentinelleDateHeure(sFilePG, sColPG)
END

// -- Tente d'affecter une Date sentinelle typee.
//    Retourne True si affectation OK, False si exception.
PROCEDURE INTERNE TryAssignSentinelleDate(LOCAL sFilePG, sColPG is string) : boolean
    bOK is boolean = True
    WHEN EXCEPTION IN
        // Objet Date typé avec membres explicites : evite les
        // conversions string qui peuvent silencieusement ne pas
        // s'appliquer sur le driver PG WinDev.
        dtSentinelle is Date
        dtSentinelle..Annee = 1900
        dtSentinelle..Mois = 1
        dtSentinelle..Jour = 1
        {sFilePG + "." + sColPG} = dtSentinelle
    DO
        bOK = False
    END
    RESULT bOK
END

// -- Fallback pour les rubriques timestamp (DateHeure) qui n'acceptent
//    pas un objet Date pur.
PROCEDURE INTERNE TryAssignSentinelleDateHeure(LOCAL sFilePG, sColPG is string)
    WHEN EXCEPTION IN
        dhSentinelle is DateHeure
        dhSentinelle..Annee = 1900
        dhSentinelle..Mois = 1
        dhSentinelle..Jour = 1
        dhSentinelle..Heure = 0
        dhSentinelle..Minute = 0
        dhSentinelle..Seconde = 0
        {sFilePG + "." + sColPG} = dhSentinelle
    DO
        // Meme le DateHeure echoue -> tant pis, cette ligne sera KO au
        // HAdd. Le log de UpsertRow signalera l'echec.
    END
END

// -- Version defensive (utilisee dans le DO du WHEN EXCEPTION externe de
//    TryAssignDate ou WHEN EXCEPTION IN imbrique est interdit).
PROCEDURE INTERNE SafeForceNullOuSentinelle(LOCAL sFilePG, sColPG is string)
    WHEN EXCEPTION IN
        ForceNullOuSentinelle(sFilePG, sColPG)
    DO
        // Tant pis
    END
END

// =============================================================================
//  AFFECTATION STRING TOLERANTE (UUID 256b, binaire, memos)
// =============================================================================
// Une rubrique HFSQL de type "UUID sur 256 bits" (ex.
// divers.UUID_connexion.IDUUID_connexion) NE SE CONVERTIT PAS
// implicitement vers une chaine Unicode via l'indirection {fic.rub}.
// WinDev leve : "Un element de type 'UUID sur 256 bits' ne peut pas
// etre converti vers le type 'chaine Unicode'".
//
// On tente l'affectation directe, puis en fallback on force le passage
// par UUIDVersChaine() qui gere le type nativement. En dernier recours
// on met une chaine vide pour ne pas bloquer toute la ligne.

// NOTE WLangage : interdit d'imbriquer WHEN EXCEPTION IN dans un DO.
// On chaine donc les fallbacks via des procs dediees (meme pattern que
// TryAssignDate -> SafeForceNullOuSentinelle).
//   TryAssignString -> SafeAssignStringHexa -> SafeAssignStringVide
//
// Cas typique : rubrique HFSQL "UUID sur 256 bits" affectee a une colonne
// PG varchar. WinDev refuse la conversion implicite ("Un element de type
// 'UUID sur 256 bits' ne peut pas etre converti vers le type 'chaine
// Unicode'"). Un UUID 256b est fondamentalement un buffer de 32 octets,
// BufferVersHexa() en produit une representation hexadecimale de 64 car.
PROCEDURE INTERNE TryAssignString(LOCAL sFilePG, sColPG, sFileHF, sColHF is string)
    WHEN EXCEPTION IN
        // Voie normale (marche pour tous les types texte usuels)
        {sFilePG + "." + sColPG} = {sFileHF + "." + sColHF}
    DO
        // Cas UUID/binaire/incompat : passe la main a la proc de fallback
        SafeAssignStringHexa(sFilePG, sColPG, sFileHF, sColHF)
    END
END

// Fallback 1 : buffer -> hexadecimal (UUID 256b, buffers binaires).
PROCEDURE INTERNE SafeAssignStringHexa(LOCAL sFilePG, sColPG, sFileHF, sColHF is string)
    WHEN EXCEPTION IN
        {sFilePG + "." + sColPG} = BufferVersHexa({sFileHF + "." + sColHF})
    DO
        SafeAssignStringVide(sFilePG, sColPG)
    END
END

// Fallback 2 : chaine vide (dernier recours, la ligne passe quand meme).
PROCEDURE INTERNE SafeAssignStringVide(LOCAL sFilePG, sColPG is string)
    WHEN EXCEPTION IN
        {sFilePG + "." + sColPG} = ""
    DO
        // Meme "" echoue -> on abandonne, HAdd/HModify signalera.
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
            ELSE IF Gauche(col.pg_type, 7) = "varchar" ...
                 OR Gauche(col.pg_type, 4) = "char" ...
                 OR col.pg_type = "text" THEN
                // Cible string PG : peut recevoir une rubrique HFSQL UUID 256b
                // qui ne se convertit PAS implicitement -> exception. Delegue.
                TryAssignString(sTablePG, col.pg_column, sTableHF, col.hfsql_column)
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
Ferme()