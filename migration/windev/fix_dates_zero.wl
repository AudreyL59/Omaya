// =============================================================================
//  FIX DATES "AN ZERO" - HFSQL
//  Repare les lignes HFSQL dont une colonne date contient une valeur
//  invalide ("0000-00-00", "00000000", etc.) qui fait planter la sync PG :
//
//      ERREUR ...modif_date : L'an zero n'est pas une annee valide.
//
//  Strategie : pour chaque table listee, parcourt les enregistrements et
//  remplace la date fautive par DateHeureSys() (= maintenant) pour que la
//  synchro suivante passe la ligne en PG.
//
//  A coller dans un Set de procedures du projet WinDev (ou ajouter en
//  procedure globale). Lancer FixDatesZero() une seule fois depuis un btn
//  d'admin ou la console. La synchro suivante reprendra ces lignes.
//
//  Les 3 tables ciblees viennent des erreurs vues dans le logiciel de
//  synchro le 2026-06-12 :
//    - divers.FeuillePointePointage.ModifDate
//    - rh.societe_FormJuri.ModifDate
//    - rh.TypePrime.ModifDate
//
//  Ajouter d'autres tables au besoin via FixDateZeroTable().
// =============================================================================

PROCEDURE FixDatesZero()
    nbTotal is int = 0

    nbTotal += FixDateZeroTable("FeuillePointePointage", "ModifDate")
    nbTotal += FixDateZeroTable("societe_FormJuri",      "ModifDate")
    nbTotal += FixDateZeroTable("TypePrime",             "ModifDate")

    Info("Total : " + nbTotal + " ligne(s) corrigee(s).")
END

// -----------------------------------------------------------------------------
//  Helper : parcourt sTable et remplace toute date a 0000 par DateHeureSys().
//  Retourne le nb de lignes modifiees.
//
//  sTable : nom du fichier HFSQL (sans schema, ex. "FeuillePointePointage")
//  sCol   : nom de la rubrique date a tester (ex. "ModifDate")
// -----------------------------------------------------------------------------

PROCEDURE INTERNE FixDateZeroTable(sTable, sCol is string) : int
    nbModifs is int = 0
    nbScanned is int = 0

    HLitPremier(sTable)
    WHILE NOT HEnDehors(sTable)
        nbScanned++

        // Recupere la valeur en chaine (sans appeler DateVersChaine qui
        // plante sur an 0000).
        sVal is string = "" + {sTable + "." + sCol}

        bFautive is boolean = (sVal = "" ...
                            OR sVal = "00000000" ...
                            OR sVal = "00000000000000" ...
                            OR Gauche(sVal, 4) = "0000" ...
                            OR Gauche(sVal, 5) = "0000-" ...
                            OR Position(sVal, "0000-") > 0 ...
                            OR Position(sVal, "/0000") > 0)

        IF bFautive THEN
            WHEN EXCEPTION IN
                {sTable + "." + sCol} = DateHeureSys()
                IF HModifie(sTable) THEN
                    nbModifs++
                END
            DO
                Trace("FixDateZero KO sur " + sTable + " ligne " + nbScanned + " : " + ExceptionInfo())
            END
        END

        HLitSuivant(sTable)
    END

    Trace(sTable + ": " + nbModifs + " corrigee(s) / " + nbScanned + " scannee(s)")
    RESULT nbModifs
END
