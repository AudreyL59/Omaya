/**
 * Fen_Call — Ticket Call ENERGIE (Vendeur).
 *
 * Portage 1:1 de d:/Claude/omayapp_flutter/lib/features/call/call_screen.dart.
 * 11 plans (pager) : Tickets / Client / Panier / Partenaires / Offre /
 * OHM (logement/install/financiers) / Justif (vestige) / Docs Pro.
 *
 * Phase 2 : les appels API tapent sur /api/vendeur/ticket-call-energie/*
 * (proxy backend vers WebRest_Omayapp/Call/...). Phase 3 : chaque
 * endpoint migre en PG au fur et a mesure.
 *
 * Cf. docs/tickets_call_screens_analysis.md pour la spec detaillee.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  ArrowLeft, Check, Loader2, Plus, Send, Trash2, ChevronRight,
} from 'lucide-react'
import { getToken } from '@/api'
import PhotoInputMulti from '@/components/PhotoInputMulti'
import { generateImagesPdf } from '@/lib/pdfSpecimen'
import { uploadFichier } from '@/lib/uploadFichier'
import { showConfirm } from '@shared/ui/dialog'


const API = '/api/vendeur/ticket-call-energie'
const API_COMMON = '/api/vendeur/ticket-call'

// --- Types --------------------------------------------------------------

interface Ticket {
  IDTK_Liste: number
  NomClient?: string
  PrenomClient?: string
  ClientPro?: boolean | number
  ClientRS?: string
  CP?: string
  VILLE?: string
  DateCreation?: string
  PhotoOK?: boolean | number
  KbisOK?: boolean | number
  Code?: string
}

interface Partenaire {
  Nom: string
  Bdd: string   // OEN | ENI | STR | VAL | PRO | OHM
  Logo?: string  // base64
}

interface Produit {
  IDProduit: number
  LibProd: string
}

interface TypeInstallOHM {
  TypeInstall: number
  LibTypeInstall: string
  Chauffage?: boolean | number
  EauChaude?: boolean | number
  _chauffage?: boolean
  _eauChaude?: boolean
}

interface PanierItem {
  IDtk_Call_Panier: number
  LibOffre?: string
  Part?: string
  NumBS?: string
}


// --- Helpers ------------------------------------------------------------

const auth = () => ({ Authorization: `Bearer ${getToken()}` })
const _bool = (v: any) => v === true || v === 1 || v === '1' || v === 'true'
const _toInt = (v: any, d = 0) => {
  const n = typeof v === 'string' ? parseInt(v, 10) : Number(v)
  return Number.isFinite(n) ? n : d
}
const fmtDateApi = (fr: string): string => {
  // 'dd/MM/yyyy' -> 'yyyyMMdd'
  const m = fr.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (!m) return ''
  return `${m[3]}${m[2]}${m[1]}`
}
const yy = (d: Date) => d.getFullYear().toString().slice(2)
const pad2 = (n: number) => n.toString().padStart(2, '0')
const todayCodePrefix = (prefix: string) => {
  const d = new Date()
  return `${prefix}-${yy(d)}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}`
}


// --- Page ---------------------------------------------------------------

export default function TicketCallEnergiePage() {
  const [plan, setPlan] = useState<number>(1)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('')
  const [toast, setToast] = useState('')

  // Init
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [partenaires, setPartenaires] = useState<Partenaire[]>([])
  const [idTicketEnCours, setIdTicketEnCours] = useState(0)

  // Formulaire client
  const [civilite, setCivilite] = useState(1)  // 1=M, 2=Mme, 3=Melle
  const [nom, setNom] = useState('')
  const [nomMarital, setNomMarital] = useState('')
  const [prenom, setPrenom] = useState('')
  const [dnaiss, setDnaiss] = useState('')  // dd/MM/yyyy
  const [depNaiss, setDepNaiss] = useState('')
  const [typeLogement, setTypeLogement] = useState(1)  // 1=Maison, 2=Appart
  const [adresse1, setAdresse1] = useState('')
  const [adresse2, setAdresse2] = useState('')
  const [cp, setCp] = useState('')
  const [villes, setVilles] = useState<{ id: number; nom_ville: string; cp: string }[]>([])
  const [villeId, setVilleId] = useState(0)
  const [villeNom, setVilleNom] = useState('')
  const [mobile1, setMobile1] = useState('')
  const [mail, setMail] = useState('')
  const [clientPro, setClientPro] = useState(false)
  const [rs, setRs] = useState('')
  const [siret, setSiret] = useState('')

  // Panier + validation code
  const [panier, setPanier] = useState<PanierItem[]>([])
  const [, setCodeGenere] = useState('')
  const [codeSaisi, setCodeSaisi] = useState('')
  const [codeTest, setCodeTest] = useState('')
  const [showCodeInput, setShowCodeInput] = useState(false)

  // Partenaire selectionne + produits
  const [libPart, setLibPart] = useState('')
  const [typePart, setTypePart] = useState('')  // OEN|ENI|STR|VAL|PRO|OHM
  const [produits, setProduits] = useState<Produit[]>([])
  const [selectedProdId, setSelectedProdId] = useState(0)
  const [selectedProdDualId, setSelectedProdDualId] = useState(0)
  const [oenTypeOffre, setOenTypeOffre] = useState(1)  // 1=Mono, 2=Dual

  // Options produit
  const [numBS, setNumBS] = useState('')
  const [numBSDual, setNumBSDual] = useState('')
  const [refClient, setRefClient] = useState('')
  const [dateActiv, setDateActiv] = useState('')
  const [infosContrat, setInfosContrat] = useState('')
  const [optAcceptComPart, setOptAcceptComPart] = useState(false)
  const [optConsentDistri, setOptConsentDistri] = useState(false)
  const [optMaintenance, setOptMaintenance] = useState(false)
  const [optMandat, setOptMandat] = useState(false)
  const [optNumerique, setOptNumerique] = useState(false)

  // OHM
  const [nbPersFoyer, setNbPersFoyer] = useState('')
  const [sitPro, setSitPro] = useState('')
  const [rfr, setRfr] = useState('')
  const [dateEntree, setDateEntree] = useState('')
  const [superficie, setSuperficie] = useState('')
  const [anneeConstru, setAnneeConstru] = useState('')
  const [anneeInstall, setAnneeInstall] = useState('')
  const [typesInstall, setTypesInstall] = useState<TypeInstallOHM[]>([])
  const [autreInstall, setAutreInstall] = useState(false)
  const [autreInstallLibelle, setAutreInstallLibelle] = useState('')
  const [montantGaz, setMontantGaz] = useState('')
  const [montantElec, setMontantElec] = useState('')
  const [chauffAppoint, setChauffAppoint] = useState(false)
  const [isoCombles, setIsoCombles] = useState(false)
  const [chauffAlter, setChauffAlter] = useState(2)  // 1=Oui, 2=Non
  const [chauffAlterLibelle, setChauffAlterLibelle] = useState('')
  const [observations, setObservations] = useState('')

  // Docs Pro
  const [cinFiles, setCinFiles] = useState<File[]>([])
  const [kbisFiles, setKbisFiles] = useState<File[]>([])
  const [cinOk, setCinOk] = useState(false)
  const [kbisOk, setKbisOk] = useState(false)

  useEffect(() => { document.title = 'Ticket Énergie · Omaya' }, [])

  // --- API helpers ---------------------------------------------------

  const call = useCallback(async <T = any>(
    method: 'GET' | 'POST', url: string, body?: any,
  ): Promise<T | null> => {
    try {
      const r = await fetch(url, {
        method,
        headers: {
          ...auth(),
          ...(body ? { 'Content-Type': 'application/json' } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
      })
      if (!r.ok) {
        const t = await r.text()
        setToast(`Erreur : ${r.status} ${t.slice(0, 120)}`)
        return null
      }
      return r.json()
    } catch (e: any) {
      setToast(`Erreur reseau : ${e?.message || e}`)
      return null
    }
  }, [])

  // --- Init : tickets + partenaires ---------------------------------

  const loadInit = useCallback(async () => {
    setLoading(true)
    setLoadingMsg('Chargement...')
    const [ts, ps] = await Promise.all([
      call<Ticket[]>('POST', `${API}/clients-non-finalises`),
      call<Partenaire[]>('POST', `${API}/partenaires`),
    ])
    if (Array.isArray(ts)) {
      setTickets(ts)
      setPartenaires(Array.isArray(ps) ? ps : [])
      setPlan(ts.length === 0 ? 2 : 1)
    }
    setLoading(false)
    setLoadingMsg('')
  }, [call])
  useEffect(() => { void loadInit() }, [loadInit])

  const loadPanier = useCallback(async (idTicket: number) => {
    const r = await call<PanierItem[]>('POST', `${API}/panier/${idTicket}`)
    if (Array.isArray(r)) setPanier(r)
  }, [call])

  // --- Recherche villes par CP -------------------------------------

  const searchVilles = useCallback(async (cpVal: string) => {
    if (cpVal.length < 4) { setVilles([]); return }
    const r = await call<any[]>('GET', `${API_COMMON}/villes/${encodeURIComponent(cpVal)}`)
    setVilles(Array.isArray(r) ? r : [])
  }, [call])

  // --- Reset form client -------------------------------------------

  const resetClientForm = () => {
    setCivilite(1); setNom(''); setNomMarital(''); setPrenom('')
    setDnaiss(''); setDepNaiss(''); setTypeLogement(1)
    setAdresse1(''); setAdresse2(''); setCp(''); setVilles([])
    setVilleId(0); setVilleNom(''); setMobile1(''); setMail('')
    setClientPro(false); setRs(''); setSiret('')
    setPanier([]); setCinFiles([]); setKbisFiles([])
    setCinOk(false); setKbisOk(false); setIdTicketEnCours(0)
  }

  // --- Actions Plan 1 : ouvrir / supprimer ticket ------------------

  const openTicket = async (t: Ticket) => {
    setIdTicketEnCours(_toInt(t.IDTK_Liste))
    setClientPro(_bool(t.ClientPro))
    setCinOk(_bool(t.PhotoOK))
    setKbisOk(_bool(t.KbisOK))
    if (_bool(t.ClientPro) && (!_bool(t.KbisOK) || !_bool(t.PhotoOK))) {
      setPlan(11)
    } else {
      await loadPanier(_toInt(t.IDTK_Liste))
      setPlan(3)
    }
  }

  const supprimerTicket = async (t: Ticket) => {
    const ok = await showConfirm({
      title: 'Supprimer le ticket',
      message: `Supprimer le ticket de ${t.NomClient || ''} ?`,
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setLoading(true)
    await call('POST', `${API}/supprimer-ticket`, { IDTK_Liste: t.IDTK_Liste })
    setTickets(tickets.filter(x => x.IDTK_Liste !== t.IDTK_Liste))
    setLoading(false)
  }

  // --- Plan 2 -> validation client ---------------------------------

  const validerClient = async () => {
    // Validations locales
    if (!nom || !prenom || !cp || !villeId || !mobile1) {
      setToast('Merci de completer les champs obligatoires'); return
    }
    if (typeLogement === 2 && !adresse2) {
      setToast("Merci de renseigner le complement d'adresse (appartement)")
      return
    }
    if (clientPro && (!rs || !siret)) {
      setToast('Raison sociale + SIRET obligatoires pour un client Pro'); return
    }
    setLoading(true)
    setLoadingMsg('Creation du client en cours (peut prendre jusqu\'a 1 minute)...')
    const payload = {
      CiviliteClient: civilite,
      NomClient: nom,
      NomMaritalClient: nomMarital,
      PrenomClient: prenom,
      DATENAISS: fmtDateApi(dnaiss),
      DEPNAISS: _toInt(depNaiss),
      ADRESSE1: adresse1,
      ADRESSE2: adresse2,
      CP: cp,
      VILLE: villeNom,
      adrMail: mail,
      Mobile1: mobile1,
      TypeLogement: typeLogement,
      ClientPro: clientPro,
      ClientRS: rs,
      ClientSiret: siret,
    }
    const r = await call<{ nIdDemande: number; sInfoData?: string }>(
      'POST', `${API}/nouveau-ticket`, payload,
    )
    setLoading(false)
    setLoadingMsg('')
    if (!r || !r.nIdDemande) {
      setToast(r?.sInfoData || 'Echec creation client'); return
    }
    const newTicket: Ticket = {
      IDTK_Liste: r.nIdDemande,
      NomClient: nom, PrenomClient: prenom,
      ClientPro: clientPro, ClientRS: rs,
      CP: cp, VILLE: villeNom,
    }
    setTickets([newTicket, ...tickets])
    setIdTicketEnCours(r.nIdDemande)
    setPlan(clientPro ? 11 : 4)
  }

  // --- Plan 11 : docs Pro (CIN + KBIS) ------------------------------

  const uploadDoc = async (
    files: File[], kind: 'PieceIdentite' | 'KBIS',
  ) => {
    if (files.length === 0) { setToast('Aucun fichier'); return false }
    setLoading(true)
    setLoadingMsg(`Upload ${kind}...`)
    try {
      const pdf = await generateImagesPdf(files, { filigrane: true })
      const fname = `${idTicketEnCours}_${kind}.pdf`
      const res = await uploadFichier(pdf, fname)
      if (!res.ok) { setToast(`Echec upload ${kind} : ${res.error}`); return false }
      setToast(`${kind} uploade`)
      return true
    } finally {
      setLoading(false); setLoadingMsg('')
    }
  }

  const validerDocs = async () => {
    setLoading(true)
    setLoadingMsg('Verification serveur...')
    const cin = await call<any>(
      'GET', `${API}/verif-photo/${idTicketEnCours}/PieceIdentite`,
    )
    const cinOkNow = _toInt(cin?.nIdDemande) !== 0
    let kbisOkNow = true
    if (clientPro) {
      const kbis = await call<any>(
        'GET', `${API}/verif-photo/${idTicketEnCours}/KBIS`,
      )
      kbisOkNow = _toInt(kbis?.nIdDemande) !== 0
    }
    setLoading(false); setLoadingMsg('')
    setCinOk(cinOkNow); setKbisOk(kbisOkNow)
    if (!cinOkNow || !kbisOkNow) {
      setToast('Un ou plusieurs documents sont manquants sur le serveur'); return
    }
    setPlan(4)
  }

  // --- Plan 4 -> chargement produits partenaire --------------------

  const initOffreFields = () => {
    setSelectedProdId(0); setSelectedProdDualId(0); setOenTypeOffre(1)
    setNumBS(''); setNumBSDual('')
    setRefClient(''); setDateActiv(''); setInfosContrat('')
    setOptAcceptComPart(false); setOptConsentDistri(false)
    setOptMaintenance(false); setOptMandat(false); setOptNumerique(false)
    // OHM defaults
    setNbPersFoyer(''); setSitPro(''); setRfr(''); setDateEntree('')
    setSuperficie(''); setAnneeConstru(''); setAnneeInstall('')
    setAutreInstall(false); setAutreInstallLibelle('')
    setMontantGaz(''); setMontantElec('')
    setChauffAppoint(false); setIsoCombles(false)
    setChauffAlter(2); setChauffAlterLibelle('')
    setObservations('')
  }

  const selectPartenaire = async (p: Partenaire) => {
    setLibPart(p.Nom); setTypePart(p.Bdd)
    initOffreFields()
    if (p.Bdd === 'OEN') {
      setNumBS(todayCodePrefix('CT'))
      setRefClient(todayCodePrefix('CM'))
    }
    setLoading(true)
    const r = await call<Produit[]>('POST', `${API}/produits-actifs/${p.Bdd}`)
    setLoading(false)
    setProduits(Array.isArray(r) ? r : [])
    if (p.Bdd === 'OHM') {
      // charge la liste type install + Plan 6
      const t = await call<TypeInstallOHM[]>('GET', `${API}/ohm/liste-type-install`)
      setTypesInstall((Array.isArray(t) ? t : []).map((x) => ({
        ...x, _chauffage: _bool(x.Chauffage), _eauChaude: _bool(x.EauChaude),
      })))
      setPlan(6)
    } else {
      setPlan(5)
    }
  }

  // --- Plan 5 : ajout produit (selon partenaire) -------------------

  const buildBaseProd = (idProduit: number, numBSVal: string): any => ({
    IDSalarie: 0,  // rempli cote serveur via usersCial
    IDTK_Liste: idTicketEnCours,
    IDProduit: idProduit,
    NumBS: numBSVal,
    RefClient: refClient,
    Observations: refClient,  // OEN : RefClient est dans Observations
    DateEntree: fmtDateApi(dateActiv),
    InfosContrat: infosContrat,
    OPT_CialPart: optAcceptComPart,
    OPT_ConsentDistri: optConsentDistri,
    Opt_Maintenance: optMaintenance,
    Opt_Mandat: optMandat,
    FormatNumerique: optNumerique ? 1 : 0,
    // Options forcees false (cf. commentaire code Flutter)
    OPT_Reforestation: false,
    OPT_EnergieVerteGaz: false,
    OPT_Mail: false,
    OPT_eCommunication: false,
    OPT_eFacture: false,  // optProtected
    OPT_optinCommercial: false,
  })

  const ajouterProduit = async () => {
    setLoading(true)
    let ok = false
    if (typePart === 'VAL') {
      // Boucle sur tous les produits VAL
      const rprod = await call<Produit[]>('POST', `${API}/produits-actifs/VAL`)
      const list = Array.isArray(rprod) ? rprod : []
      for (const p of list) {
        const r = await call<{ nIdDemande: number }>(
          'POST', `${API}/panier/produit/ajouter`, buildBaseProd(p.IDProduit, ''),
        )
        if (r?.nIdDemande) ok = true
      }
    } else if (typePart === 'OEN' && oenTypeOffre === 2) {
      // Dual : 2 POST successifs
      const r1 = await call<{ nIdDemande: number }>(
        'POST', `${API}/panier/produit/ajouter`,
        buildBaseProd(selectedProdId, numBS),
      )
      const r2 = await call<{ nIdDemande: number }>(
        'POST', `${API}/panier/produit/ajouter`,
        buildBaseProd(selectedProdDualId, numBSDual),
      )
      if (r1?.nIdDemande && r2?.nIdDemande) {
        ok = true
        setToast('2 contrats OEN ajoutes. Pense a joindre la clarification.')
      }
    } else if (selectedProdId) {
      const r = await call<{ nIdDemande: number }>(
        'POST', `${API}/panier/produit/ajouter`,
        buildBaseProd(selectedProdId, numBS),
      )
      if (r?.nIdDemande) ok = true
    }
    setLoading(false)
    if (ok) {
      await loadPanier(idTicketEnCours)
      setPlan(3)
    } else {
      setToast('Echec ajout produit')
    }
  }

  // --- Plans 6-8 : OHM -> ajouter produit OHM ---------------------

  const ajouterProduitOHM = async () => {
    setLoading(true)
    const payload = {
      ...buildBaseProd(0, ''),  // pas d'idProduit pour OHM
      NbPersFoyer: _toInt(nbPersFoyer),
      SitPro: sitPro,
      RFR: _toInt(rfr),
      DateEntree: fmtDateApi(dateEntree),
      Supercie: _toInt(superficie),   // typo preservee cf. Flutter
      AnneeConstruction: _toInt(anneeConstru),
      AnneeInstallation: _toInt(anneeInstall),
      TypesInstall: typesInstall.map((t) => ({
        TypeInstall: t.TypeInstall,
        Chauffage: t._chauffage ? 1 : 0,
        EauChaude: t._eauChaude ? 1 : 0,
      })),
      AutreInstall: autreInstall,
      AutreInstallation: autreInstallLibelle,
      MontantMensGaz: _toInt(montantGaz),
      MontantMensElec: _toInt(montantElec),
      ChauffageAppoint: chauffAppoint,
      IsolationCombles: isoCombles,
      ChauffageAlternantif: chauffAlter === 1,  // typo preservee
      TypeChauffAlter: chauffAlterLibelle,
      Observations: observations,
    }
    const r = await call<{ nIdDemande: number }>(
      'POST', `${API}/panier/produit/ajouter`, payload,
    )
    setLoading(false)
    if (r?.nIdDemande) {
      await loadPanier(idTicketEnCours)
      setPlan(3)
    } else {
      setToast('Echec ajout produit OHM')
    }
  }

  // --- Plan 3 : suppr produit + valider panier --------------------

  const supprimerProduit = async (item: PanierItem) => {
    const ok = await showConfirm({
      title: 'Supprimer le produit',
      message: `Supprimer ${item.LibOffre} du panier ?`,
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setLoading(true)
    await call('POST', `${API}/panier/produit/supprimer`,
                { IDtk_Call_Panier: item.IDtk_Call_Panier })
    await loadPanier(idTicketEnCours)
    setLoading(false)
  }

  const genererCode = async () => {
    const code = (100000 + (Date.now() % 900000)).toString()
    setCodeGenere(code); setCodeTest(code); setCodeSaisi(''); setShowCodeInput(true)
    setLoading(true)
    await call('POST', `${API}/envoi-lien/${code}`, { IDTK_Liste: idTicketEnCours })
    setLoading(false)
    setToast(`SMS envoye avec le code ${code}`)
  }

  const validerPanier = async () => {
    if (codeSaisi !== codeTest) { setToast('Code incorrect'); return }
    const ok = await showConfirm({
      title: 'Valider le panier',
      message: 'Cette action est irréversible. Confirmer la validation ?',
      confirmLabel: 'Valider',
    })
    if (!ok) return
    setLoading(true)
    await call('POST', `${API}/validation`, { IDTK_Liste: idTicketEnCours })
    setLoading(false)
    setToast('Panier valide')
    resetClientForm(); setShowCodeInput(false)
    await loadInit()
  }

  // --- Header retour selon plan -----------------------------------

  const goBack = () => {
    const table: Record<number, number> = {
      2: 1, 3: 1, 4: 3, 5: 4, 6: 4, 7: 6, 8: 7, 9: 5, 11: 1,
    }
    setPlan(table[plan] ?? 1)
  }
  const titreParPlan: Record<number, string> = {
    1: 'Mes Paniers en cours',
    2: 'Mon Client', 3: 'Panier', 4: 'Panier', 5: 'Mon Offre',
    6: 'Mon Offre', 7: 'Mon Offre', 8: 'Mon Offre',
    9: 'Mon Offre', 11: 'Mon Client',
  }

  // ---------------------------------------------------------------
  // RENDU
  // ---------------------------------------------------------------
  return (
    <div className="p-4 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        {plan !== 1 && (
          <button onClick={goBack}
            className="p-2 rounded hover:bg-c-brand-soft text-c-ink"
            title="Retour">
            <ArrowLeft className="w-5 h-5" />
          </button>
        )}
        <h1 className="text-xl font-bold text-c-ink">
          {titreParPlan[plan] || 'Ticket Énergie'}
        </h1>
      </div>

      {plan === 1 && <PlanTickets tickets={tickets}
                                  onOpen={openTicket}
                                  onSuppr={supprimerTicket}
                                  onNew={() => { resetClientForm(); setPlan(2) }} />}

      {plan === 2 && <PlanClient
        civilite={civilite} setCivilite={setCivilite}
        nom={nom} setNom={setNom}
        nomMarital={nomMarital} setNomMarital={setNomMarital}
        prenom={prenom} setPrenom={setPrenom}
        dnaiss={dnaiss} setDnaiss={setDnaiss}
        depNaiss={depNaiss} setDepNaiss={setDepNaiss}
        typeLogement={typeLogement} setTypeLogement={setTypeLogement}
        adresse1={adresse1} setAdresse1={setAdresse1}
        adresse2={adresse2} setAdresse2={setAdresse2}
        cp={cp} setCp={(v: string) => { setCp(v); searchVilles(v) }}
        villes={villes} villeId={villeId}
        setVille={(id: number, nom: string) => { setVilleId(id); setVilleNom(nom) }}
        mobile1={mobile1} setMobile1={setMobile1}
        mail={mail} setMail={setMail}
        clientPro={clientPro} setClientPro={setClientPro}
        rs={rs} setRs={setRs}
        siret={siret} setSiret={setSiret}
        onValider={validerClient} />}

      {plan === 3 && <PlanPanier
        panier={panier}
        showCodeInput={showCodeInput}
        codeSaisi={codeSaisi} setCodeSaisi={setCodeSaisi}
        onSuppr={supprimerProduit}
        onAjouter={() => setPlan(4)}
        onGenerer={genererCode}
        onValider={validerPanier} />}

      {plan === 4 && <PlanPartenaires
        partenaires={partenaires}
        onSelect={selectPartenaire} />}

      {plan === 5 && <PlanOffre
        typePart={typePart} libPart={libPart} produits={produits}
        selectedProdId={selectedProdId} setSelectedProdId={setSelectedProdId}
        selectedProdDualId={selectedProdDualId} setSelectedProdDualId={setSelectedProdDualId}
        oenTypeOffre={oenTypeOffre} setOenTypeOffre={setOenTypeOffre}
        numBS={numBS} setNumBS={setNumBS}
        numBSDual={numBSDual} setNumBSDual={setNumBSDual}
        refClient={refClient} setRefClient={setRefClient}
        dateActiv={dateActiv} setDateActiv={setDateActiv}
        infosContrat={infosContrat} setInfosContrat={setInfosContrat}
        optAcceptComPart={optAcceptComPart} setOptAcceptComPart={setOptAcceptComPart}
        optConsentDistri={optConsentDistri} setOptConsentDistri={setOptConsentDistri}
        optMaintenance={optMaintenance} setOptMaintenance={setOptMaintenance}
        optMandat={optMandat} setOptMandat={setOptMandat}
        optNumerique={optNumerique} setOptNumerique={setOptNumerique}
        onAjouter={ajouterProduit} />}

      {plan === 6 && <PlanOHMLogement
        nbPersFoyer={nbPersFoyer} setNbPersFoyer={setNbPersFoyer}
        sitPro={sitPro} setSitPro={setSitPro}
        rfr={rfr} setRfr={setRfr}
        dateEntree={dateEntree} setDateEntree={setDateEntree}
        superficie={superficie} setSuperficie={setSuperficie}
        anneeConstru={anneeConstru} setAnneeConstru={setAnneeConstru}
        anneeInstall={anneeInstall} setAnneeInstall={setAnneeInstall}
        onNext={() => setPlan(7)} />}

      {plan === 7 && <PlanOHMInstall
        typesInstall={typesInstall}
        setChauffage={(i: number, v: boolean) => {
          const t = [...typesInstall]; t[i] = { ...t[i], _chauffage: v }; setTypesInstall(t)
        }}
        setEauChaude={(i: number, v: boolean) => {
          const t = [...typesInstall]; t[i] = { ...t[i], _eauChaude: v }; setTypesInstall(t)
        }}
        autreInstall={autreInstall} setAutreInstall={setAutreInstall}
        autreInstallLibelle={autreInstallLibelle} setAutreInstallLibelle={setAutreInstallLibelle}
        onBack={() => setPlan(6)} onNext={() => setPlan(8)} />}

      {plan === 8 && <PlanOHMFinancier
        montantGaz={montantGaz} setMontantGaz={setMontantGaz}
        montantElec={montantElec} setMontantElec={setMontantElec}
        chauffAppoint={chauffAppoint} setChauffAppoint={setChauffAppoint}
        isoCombles={isoCombles} setIsoCombles={setIsoCombles}
        chauffAlter={chauffAlter} setChauffAlter={setChauffAlter}
        chauffAlterLibelle={chauffAlterLibelle} setChauffAlterLibelle={setChauffAlterLibelle}
        observations={observations} setObservations={setObservations}
        onBack={() => setPlan(7)} onAjouter={ajouterProduitOHM} />}

      {plan === 11 && <PlanDocsPro
        clientPro={clientPro} cinOk={cinOk} kbisOk={kbisOk}
        onCinChange={setCinFiles} onKbisChange={setKbisFiles}
        onUploadCin={async () => { const ok = await uploadDoc(cinFiles, 'PieceIdentite'); if (ok) setCinOk(true) }}
        onUploadKbis={async () => { const ok = await uploadDoc(kbisFiles, 'KBIS'); if (ok) setKbisOk(true) }}
        onValider={validerDocs} />}

      {loading && <LoadingOverlay msg={loadingMsg} />}
      {toast && <Toast msg={toast} onClose={() => setToast('')} />}
    </div>
  )
}


// ============================================================================
// Sous-composants — un par plan + composants UI reutilisables
// ============================================================================

function LoadingOverlay({ msg }: { msg: string }) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg p-6 flex flex-col items-center gap-3 max-w-md text-center">
        <Loader2 className="w-8 h-8 animate-spin text-c-brand" />
        <div className="text-sm text-c-ink">{msg || 'Chargement...'}</div>
      </div>
    </div>
  )
}


function Toast({ msg, onClose }: { msg: string; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 4000); return () => clearTimeout(t) }, [onClose])
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
      <div className="bg-gray-900 text-white text-sm rounded-md px-4 py-2 shadow-lg">
        {msg}
      </div>
    </div>
  )
}


function SegRow({ options, value, onChange }: {
  options: { value: number | boolean; label: string }[]
  value: number | boolean
  onChange: (v: any) => void
}) {
  return (
    <div className="flex gap-2">
      {options.map((o, i) => (
        <button key={i}
          onClick={() => onChange(o.value)}
          className={`px-4 py-1.5 rounded-full border-[1.5px] text-sm transition-colors
                      ${value === o.value
                        ? 'bg-gray-900 text-white border-gray-900'
                        : 'bg-white text-c-ink border-gray-900 hover:bg-c-brand-soft'}`}>
          {o.label}
        </button>
      ))}
    </div>
  )
}


function Field({ label, value, onChange, type = 'text', className = '' }: {
  label: string; value: string
  onChange: (v: string) => void
  type?: string; className?: string
}) {
  return (
    <label className={`block ${className}`}>
      <span className="block text-xs text-c-ink-soft mb-0.5">{label}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)}
             className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none" />
    </label>
  )
}


function CheckOpt({ label, value, onChange }: {
  label: string; value: boolean; onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-start gap-2 text-sm py-1 cursor-pointer">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)}
             className="mt-0.5 accent-c-brand" />
      <span>{label}</span>
    </label>
  )
}


function NavBar({ onBack, onNext, nextLabel = 'Étape suivante' }: {
  onBack?: () => void; onNext: () => void; nextLabel?: string
}) {
  return (
    <div className="flex items-center justify-between border-t border-c-line-soft pt-3 mt-4">
      {onBack ? (
        <button onClick={onBack} className="flex items-center gap-1 text-sm px-3 py-1.5 rounded border border-c-line-strong text-c-ink hover:bg-c-brand-soft">
          <ArrowLeft className="w-4 h-4" /> Retour
        </button>
      ) : <div />}
      <button onClick={onNext} className="flex items-center gap-1 text-sm px-3 py-1.5 rounded bg-gray-900 text-white hover:brightness-110">
        {nextLabel} <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  )
}


// --- Plan 1 : liste des tickets --------------------------------------

function PlanTickets({ tickets, onOpen, onSuppr, onNew }: {
  tickets: Ticket[]
  onOpen: (t: Ticket) => void
  onSuppr: (t: Ticket) => void
  onNew: () => void
}) {
  return (
    <div className="space-y-2">
      <button onClick={onNew}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-md bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
        <Plus className="w-4 h-4" /> Nouveau client
      </button>
      {tickets.length === 0 && (
        <div className="text-center text-c-ink-faint text-sm py-6 italic">
          Aucun panier en cours
        </div>
      )}
      {tickets.map((t) => (
        <div key={t.IDTK_Liste}
          onDoubleClick={() => onOpen(t)}
          className="bg-white border border-c-line-soft rounded p-3 flex items-center gap-3 hover:bg-c-brand-soft cursor-pointer">
          <div className="flex-1">
            <div className="font-medium text-sm">
              {t.NomClient || ''} {t.PrenomClient || ''}
              {_bool(t.ClientPro) && (
                <span className="ml-2 text-[10px] bg-orange-100 text-orange-700 rounded px-1.5">PRO</span>
              )}
            </div>
            <div className="text-xs text-c-ink-soft">
              {t.CP || ''} {t.VILLE || ''}
            </div>
          </div>
          <button onClick={(e) => { e.stopPropagation(); onSuppr(t) }}
            className="text-red-600 hover:text-red-800">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  )
}


// --- Plan 2 : formulaire client --------------------------------------

function PlanClient(p: any) {
  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <span className="block text-xs text-c-ink-soft mb-1">Civilité</span>
        <SegRow value={p.civilite} onChange={p.setCivilite}
          options={[{ value: 1, label: 'M.' }, { value: 2, label: 'Mme' }, { value: 3, label: 'Melle' }]} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Field label="Nom" value={p.nom} onChange={p.setNom} />
        <Field label="Nom marital" value={p.nomMarital} onChange={p.setNomMarital} />
        <Field label="Prénom" value={p.prenom} onChange={p.setPrenom} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Field label="Date de naissance (jj/mm/aaaa)" value={p.dnaiss} onChange={p.setDnaiss} />
        <Field label="Département de naissance" value={p.depNaiss} onChange={p.setDepNaiss} />
      </div>
      <div>
        <span className="block text-xs text-c-ink-soft mb-1">Type de logement</span>
        <SegRow value={p.typeLogement} onChange={p.setTypeLogement}
          options={[{ value: 1, label: 'Maison' }, { value: 2, label: 'Appartement' }]} />
      </div>
      <Field label="Adresse ligne 1" value={p.adresse1} onChange={p.setAdresse1} />
      <Field label="Complément (obligatoire pour Appartement)" value={p.adresse2} onChange={p.setAdresse2} />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Field label="Code postal" value={p.cp} onChange={p.setCp} />
        <label className="md:col-span-2 block">
          <span className="block text-xs text-c-ink-soft mb-0.5">Ville</span>
          <select value={p.villeId}
            onChange={(e) => {
              const v = p.villes.find((x: any) => x.id === Number(e.target.value))
              p.setVille(Number(e.target.value), v?.nom_ville || '')
            }}
            className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white">
            <option value={0}>Choisir…</option>
            {p.villes.map((v: any) => (
              <option key={v.id} value={v.id}>{v.nom_ville} ({v.cp})</option>
            ))}
          </select>
        </label>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Field label="Mobile" value={p.mobile1} onChange={p.setMobile1} />
        <Field label="Email" value={p.mail} onChange={p.setMail} type="email" />
      </div>
      <div>
        <span className="block text-xs text-c-ink-soft mb-1">Type client</span>
        <SegRow value={p.clientPro} onChange={p.setClientPro}
          options={[{ value: false, label: 'Particulier' }, { value: true, label: 'Professionnel' }]} />
      </div>
      {p.clientPro && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label="Raison sociale" value={p.rs} onChange={p.setRs} />
          <Field label="SIRET" value={p.siret} onChange={p.setSiret} />
        </div>
      )}
      <button onClick={p.onValider}
        className="w-full py-3 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
        Valider les infos client
      </button>
    </div>
  )
}


// --- Plan 3 : panier + validation ------------------------------------

function PlanPanier({ panier, showCodeInput, codeSaisi, setCodeSaisi,
                     onSuppr, onAjouter, onGenerer, onValider }: any) {
  return (
    <div className="space-y-3">
      {panier.length === 0 && (
        <div className="text-center italic text-c-ink-faint py-4">
          Aucun produit dans le panier
        </div>
      )}
      {panier.map((p: PanierItem) => (
        <div key={p.IDtk_Call_Panier}
          className="bg-white border border-c-line-soft rounded p-3 flex items-center gap-3 hover:bg-c-brand-soft cursor-pointer"
          onClick={() => onSuppr(p)}>
          <div className="flex-1">
            <div className="text-sm font-medium">{p.LibOffre}</div>
            <div className="text-xs text-c-ink-soft">
              {p.Part} {p.NumBS && `— NumBS ${p.NumBS}`}
            </div>
          </div>
          <Trash2 className="w-4 h-4 text-red-600" />
        </div>
      ))}
      <div className="flex gap-2">
        <button onClick={onAjouter}
          className="flex-1 flex items-center justify-center gap-1 px-4 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
          <Plus className="w-4 h-4" /> Ajouter un produit
        </button>
        {panier.length > 0 && !showCodeInput && (
          <button onClick={onGenerer}
            className="flex items-center gap-1 px-4 py-2 rounded bg-green-700 text-white text-sm font-semibold hover:brightness-110">
            <Send className="w-4 h-4" /> Valider le panier
          </button>
        )}
      </div>
      {showCodeInput && (
        <div className="border border-c-line-soft rounded p-4 space-y-2 bg-c-surface-soft">
          <div className="text-sm">
            SMS envoyé au client. Saisis le code qu'il te dicte :
          </div>
          <div className="flex gap-2 items-end">
            <input value={codeSaisi} onChange={(e) => setCodeSaisi(e.target.value)}
                   maxLength={6}
                   className="flex-1 border border-c-line rounded px-2 py-1.5 text-sm text-center tracking-widest text-lg bg-white" />
            <button onClick={onValider}
              className="p-2 rounded bg-green-700 text-white hover:brightness-110">
              <Check className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}


// --- Plan 4 : grille partenaires ------------------------------------

function PlanPartenaires({ partenaires, onSelect }: {
  partenaires: Partenaire[]; onSelect: (p: Partenaire) => void
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {partenaires.map((p) => {
        const logo = (p.Logo || '').replace(/\r?\n/g, '')
        return (
          <button key={p.Bdd} onClick={() => onSelect(p)}
            className="bg-white border border-c-line-soft rounded-lg p-4 hover:bg-c-brand-soft flex flex-col items-center gap-2">
            {logo
              ? <img src={`data:image/png;base64,${logo}`} alt={p.Nom} className="max-h-16 max-w-full object-contain" />
              : <div className="h-16 flex items-center text-lg font-bold text-c-ink">{p.Nom}</div>}
            <div className="text-xs text-c-ink-soft">{p.Nom}</div>
          </button>
        )
      })}
    </div>
  )
}


// --- Plan 5 : formulaire offre (selon partenaire) --------------------

function PlanOffre(p: any) {
  const isDual = p.typePart === 'OEN' && p.oenTypeOffre === 2
  const produitsFiltres = p.typePart === 'OEN'
    ? p.produits.filter((x: Produit) =>
        p.oenTypeOffre === 2
          ? x.LibProd.toUpperCase().includes('DUAL')
          : !x.LibProd.toUpperCase().includes('DUAL'))
    : p.produits

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="text-sm font-medium">{p.libPart}</div>

      {p.typePart === 'OEN' && (
        <SegRow value={p.oenTypeOffre} onChange={p.setOenTypeOffre}
          options={[{ value: 1, label: 'Mono' }, { value: 2, label: 'Dual' }]} />
      )}

      {p.typePart !== 'VAL' && (
        <label className="block">
          <span className="block text-xs text-c-ink-soft mb-0.5">Produit</span>
          <select value={p.selectedProdId} onChange={(e) => p.setSelectedProdId(Number(e.target.value))}
            className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white">
            <option value={0}>Choisir…</option>
            {produitsFiltres.map((x: Produit) => (
              <option key={x.IDProduit} value={x.IDProduit}>{x.LibProd}</option>
            ))}
          </select>
        </label>
      )}

      {isDual && (
        <label className="block">
          <span className="block text-xs text-c-ink-soft mb-0.5">2ème produit (Dual)</span>
          <select value={p.selectedProdDualId} onChange={(e) => p.setSelectedProdDualId(Number(e.target.value))}
            className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white">
            <option value={0}>Choisir…</option>
            {produitsFiltres.map((x: Produit) => (
              <option key={x.IDProduit} value={x.IDProduit}>{x.LibProd}</option>
            ))}
          </select>
        </label>
      )}

      {['OEN', 'ENI', 'STR', 'PRO'].includes(p.typePart) && (
        <Field label="N° BS" value={p.numBS} onChange={p.setNumBS} />
      )}
      {isDual && <Field label="N° BS (Dual)" value={p.numBSDual} onChange={p.setNumBSDual} />}

      {p.typePart === 'OEN' && (
        <>
          <Field label="Réf Client" value={p.refClient} onChange={p.setRefClient} />
          <Field label="Date d'activation (jj/mm/aaaa)" value={p.dateActiv} onChange={p.setDateActiv} />
          <label className="block">
            <span className="block text-xs text-c-ink-soft mb-0.5">Infos contrat</span>
            <textarea value={p.infosContrat} onChange={(e) => p.setInfosContrat(e.target.value)}
              rows={3}
              className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white" />
          </label>
        </>
      )}

      {p.typePart === 'ENI' && (
        <div className="space-y-1">
          <CheckOpt label="Acceptation Commerciale Partenaire" value={p.optAcceptComPart} onChange={p.setOptAcceptComPart} />
          <CheckOpt label="Consentement Consultation Distributeur" value={p.optConsentDistri} onChange={p.setOptConsentDistri} />
          <CheckOpt label="PLENICOACH DEPANNAGE PREMIUM" value={p.optMaintenance} onChange={p.setOptMaintenance} />
        </div>
      )}

      {p.typePart === 'STR' && (
        <CheckOpt label="Mandat" value={p.optMandat} onChange={p.setOptMandat} />
      )}

      {p.typePart === 'VAL' && (
        <CheckOpt label="Format numérique" value={p.optNumerique} onChange={p.setOptNumerique} />
      )}

      <button onClick={p.onAjouter}
        className="w-full py-3 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
        Ajouter ce produit
      </button>
    </div>
  )
}


// --- Plans 6-8 : OHM ------------------------------------------------

function PlanOHMLogement(p: any) {
  return (
    <div className="space-y-4 max-w-3xl">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Field label="Nombre de personnes au foyer" value={p.nbPersFoyer} onChange={p.setNbPersFoyer} type="number" />
        <Field label="Situation professionnelle" value={p.sitPro} onChange={p.setSitPro} />
        <Field label="RFR (revenu fiscal)" value={p.rfr} onChange={p.setRfr} type="number" />
        <Field label="Date d'entrée dans le logement (jj/mm/aaaa)" value={p.dateEntree} onChange={p.setDateEntree} />
        <Field label="Superficie (m²)" value={p.superficie} onChange={p.setSuperficie} type="number" />
        <Field label="Année de construction" value={p.anneeConstru} onChange={p.setAnneeConstru} type="number" />
        <Field label="Année installation chauffage" value={p.anneeInstall} onChange={p.setAnneeInstall} type="number" />
      </div>
      <NavBar onNext={p.onNext} />
    </div>
  )
}


function PlanOHMInstall({ typesInstall, setChauffage, setEauChaude,
                          autreInstall, setAutreInstall,
                          autreInstallLibelle, setAutreInstallLibelle,
                          onBack, onNext }: any) {
  return (
    <div className="space-y-4 max-w-3xl">
      <div className="text-sm font-medium mb-2">Types d'installations présents :</div>
      <table className="text-xs w-full border border-c-line-soft">
        <thead className="bg-c-surface-soft">
          <tr>
            <th className="text-left px-2 py-1">Installation</th>
            <th className="text-center px-2 py-1">Chauffage</th>
            <th className="text-center px-2 py-1">Eau chaude</th>
          </tr>
        </thead>
        <tbody>
          {typesInstall.map((t: TypeInstallOHM, i: number) => (
            <tr key={t.TypeInstall} className="border-b border-c-line-soft">
              <td className="px-2 py-1">{t.LibTypeInstall}</td>
              <td className="text-center">
                <input type="checkbox" checked={!!t._chauffage}
                       onChange={(e) => setChauffage(i, e.target.checked)}
                       className="accent-c-brand" />
              </td>
              <td className="text-center">
                <input type="checkbox" checked={!!t._eauChaude}
                       onChange={(e) => setEauChaude(i, e.target.checked)}
                       className="accent-c-brand" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <CheckOpt label="Autre installation" value={autreInstall} onChange={setAutreInstall} />
      {autreInstall && (
        <Field label="Précisez" value={autreInstallLibelle} onChange={setAutreInstallLibelle} />
      )}
      <NavBar onBack={onBack} onNext={onNext} />
    </div>
  )
}


function PlanOHMFinancier(p: any) {
  return (
    <div className="space-y-4 max-w-3xl">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Field label="Montant mensuel Gaz (€)" value={p.montantGaz} onChange={p.setMontantGaz} type="number" />
        <Field label="Montant mensuel Électricité (€)" value={p.montantElec} onChange={p.setMontantElec} type="number" />
      </div>
      <CheckOpt label="Chauffage d'appoint" value={p.chauffAppoint} onChange={p.setChauffAppoint} />
      <CheckOpt label="Isolation des combles" value={p.isoCombles} onChange={p.setIsoCombles} />
      <div>
        <span className="block text-xs text-c-ink-soft mb-1">Chauffage alternatif</span>
        <SegRow value={p.chauffAlter} onChange={p.setChauffAlter}
          options={[{ value: 1, label: 'Oui' }, { value: 2, label: 'Non' }]} />
      </div>
      {p.chauffAlter === 1 && (
        <Field label="Type de chauffage alternatif" value={p.chauffAlterLibelle} onChange={p.setChauffAlterLibelle} />
      )}
      <label className="block">
        <span className="block text-xs text-c-ink-soft mb-0.5">Observations</span>
        <textarea value={p.observations} onChange={(e) => p.setObservations(e.target.value)}
          rows={3} className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white" />
      </label>
      <NavBar onBack={p.onBack} onNext={p.onAjouter} nextLabel="Ajouter au panier" />
    </div>
  )
}


// --- Plan 11 : docs Pro (CIN + KBIS) --------------------------------

function PlanDocsPro({ clientPro, cinOk, kbisOk,
                       onCinChange, onKbisChange,
                       onUploadCin, onUploadKbis, onValider }: any) {
  return (
    <div className="space-y-6 max-w-2xl">
      <section>
        <div className="flex items-center gap-2 mb-2">
          <div className="text-sm font-medium">Pièce d'identité (recto/verso)</div>
          {cinOk && <span className="text-green-600 text-xs">✓ présente serveur</span>}
        </div>
        <PhotoInputMulti label="Choisir les fichiers CIN" onChange={onCinChange} />
        <button onClick={onUploadCin}
          className="mt-2 px-4 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
          Uploader CIN (avec filigrane SPECIMEN)
        </button>
      </section>

      {clientPro && (
        <section>
          <div className="flex items-center gap-2 mb-2">
            <div className="text-sm font-medium">Extrait KBIS</div>
            {kbisOk && <span className="text-green-600 text-xs">✓ présente serveur</span>}
          </div>
          <PhotoInputMulti label="Choisir les fichiers KBIS" onChange={onKbisChange} />
          <button onClick={onUploadKbis}
            className="mt-2 px-4 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
            Uploader KBIS (avec filigrane SPECIMEN)
          </button>
        </section>
      )}

      <button onClick={onValider}
        className="w-full py-3 rounded bg-green-700 text-white text-sm font-semibold hover:brightness-110">
        Valider les documents
      </button>
    </div>
  )
}
