/**
 * Fen_CallSFR — Ticket Call FIBRE SFR (Vendeur).
 *
 * Portage 1:1 de d:/Claude/omayapp_flutter/lib/features/call_sfr/call_sfr_screen.dart.
 * 7 plans : Tickets / Client / Docs / Panier / Offres / Portabilite /
 * WebView eligibilite.
 *
 * Phase 2 : les appels tapent sur /api/vendeur/ticket-call-fibre/*
 * (proxy backend). Phase 3 : chaque endpoint migre en PG.
 *
 * Cf. docs/tickets_call_screens_analysis.md.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  ArrowLeft, Check, Loader2, Plus, Send, Trash2, ExternalLink,
  CheckCircle2, XCircle,
} from 'lucide-react'
import { getToken } from '@/api'
import PhotoInputMulti from '@/components/PhotoInputMulti'
import { generateImagesPdf } from '@/lib/pdfSpecimen'
import { uploadFichier } from '@/lib/uploadFichier'
import { showChoice, showConfirm } from '@shared/ui/dialog'


const API = '/api/vendeur/ticket-call-fibre'
const API_COMMON = '/api/vendeur/ticket-call'

// --- Types --------------------------------------------------------------

// Les IDs 8 octets (WinDev 'entier non signe 8 octets') sont passes en
// string car JS Number perd la precision au-dela de 2^53 (les IDs base
// sur DateHeureSys() font ~17 chiffres). Cf. memoire
// feedback_ids_8octets_string.
interface Ticket {
  IDTK_Liste: string
  NomClient?: string; PrenomClient?: string
  ClientPro?: boolean | number; ClientRS?: string
  CP?: string; VILLE?: string
  PhotoOK?: boolean | number; KbisOK?: boolean | number
}
interface Anomalie {
  IDtk_CallSFR_Anomalie: string
  LibTypeAnomalie: string
}
interface Offre {
  IDOffres_SFR: string
  Lib_Offre: string
  PrixOffre?: number | string
  Engagement?: string
  EnPromo?: boolean | number
  InfoPromo?: string
  DebitDown?: string; DebitUp?: string
  ServiceInclus?: string
  Type?: string
}
interface PanierItem {
  IDtk_CallSFR_Panier: string
  LibOffre?: string
  MontantOffre?: number
  Type?: string
  NumPortabilite?: string
}


// --- Helpers ------------------------------------------------------------

const auth = () => ({ Authorization: `Bearer ${getToken()}` })
const _bool = (v: any) => v === true || v === 1 || v === '1' || v === 'true'
const _toInt = (v: any, d = 0) => {
  const n = typeof v === 'string' ? parseInt(v, 10) : Number(v)
  return Number.isFinite(n) ? n : d
}
const fmtEUR = (v: any) => {
  const n = typeof v === 'string' ? parseFloat(v) : Number(v)
  return Number.isFinite(n)
    ? n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
    : ''
}
const fmtDateApi = (fr: string) => {
  const m = fr.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  return m ? `${m[3]}${m[2]}${m[1]}` : ''
}
const cleanRIO = (v: string) => v.replace(/\s/g, '').toUpperCase()
const cleanNumPrise = (v: string) => v.replace(/\s/g, '').replace(/_/g, '-')
const cleanNumPort = (v: string) => v.replace(/\./g, '')

const SFR_ELIGIBILITE_URL =
  'https://www.sfr.fr/offre-internet/test-eligibilite-adsl-vdsl-fibre'


// --- Page --------------------------------------------------------------

export default function TicketCallFibrePage() {
  const [plan, setPlan] = useState(1)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('')
  const [toast, setToast] = useState('')

  // Droits
  const [droits] = useState<string[]>(() => {
    try {
      const t = getToken()
      if (!t) return []
      const b = JSON.parse(atob(t.split('.')[1]))
      return b.droits || []
    } catch { return [] }
  })
  const hasDroitBSSFRDiff = droits.includes('BS_SFRDiff')

  // Init
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [anomalies, setAnomalies] = useState<Anomalie[]>([])
  const [idTicketEnCours, setIdTicketEnCours] = useState('')

  // Formulaire client
  const [civilite, setCivilite] = useState(1)
  const [nom, setNom] = useState('')
  const [nomMarital, setNomMarital] = useState('')
  const [prenom, setPrenom] = useState('')
  const [dnaiss, setDnaiss] = useState('')
  const [depNaiss, setDepNaiss] = useState('')
  const [typeLogement, setTypeLogement] = useState(1)
  const [adresse1, setAdresse1] = useState('')
  const [adresse2, setAdresse2] = useState('')
  const [cp, setCp] = useState('')
  const [villes, setVilles] = useState<{ id: number; nom_ville: string; cp: string }[]>([])
  const [villeId, setVilleId] = useState(0)
  const [villeNom, setVilleNom] = useState('')
  const [mobile1, setMobile1] = useState('')
  const [mobile2, setMobile2] = useState('')
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

  // Vente mobile
  const [venteMobile, setVenteMobile] = useState(1)  // 1=direct, 2=differee
  const [selectedAnomalie, setSelectedAnomalie] = useState('')
  const [infoCpltAnomalie, setInfoCpltAnomalie] = useState('')

  // Offres
  const [offres, setOffres] = useState<Offre[]>([])
  const [typeOffre, setTypeOffre] = useState('FIBRE')  // FIBRE|MOBILE|FIB PRO|MOB PRO
  const [avecTV, setAvecTV] = useState(false)
  const [optChoisies, setOptChoisies] = useState('')

  // Portabilite + prise
  const [idProdChoisi, setIdProdChoisi] = useState('')
  const [typeProdChoisi, setTypeProdChoisi] = useState('')
  const [portabilite, setPortabilite] = useState(true)
  const [numPort, setNumPort] = useState('')
  const [codeRIO, setCodeRIO] = useState('')
  const [nouvellePrise, setNouvellePrise] = useState(true)
  const [numPrise, setNumPrise] = useState('')
  const [ficResil, setFicResil] = useState('')
  const [resilOnServer, setResilOnServer] = useState<boolean | null>(null)

  // Docs
  const [cinFiles, setCinFiles] = useState<File[]>([])
  const [kbisFiles, setKbisFiles] = useState<File[]>([])
  const [cinOk, setCinOk] = useState(false)
  const [kbisOk, setKbisOk] = useState(false)

  useEffect(() => { document.title = 'Ticket Fibre · Omaya' }, [])

  // --- API helper -------------------------------------------------

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
        setToast(`Erreur ${r.status}: ${t.slice(0, 120)}`); return null
      }
      return r.json()
    } catch (e: any) {
      setToast(`Erreur reseau: ${e?.message || e}`); return null
    }
  }, [])

  // --- Init -------------------------------------------------------

  const loadInit = useCallback(async () => {
    setLoading(true)
    const [ts, ans] = await Promise.all([
      call<Ticket[]>('POST', `${API}/clients-non-finalises`),
      call<Anomalie[]>('GET', `${API}/anomalies`),
    ])
    setTickets(Array.isArray(ts) ? ts : [])
    setAnomalies(Array.isArray(ans) ? ans : [])
    setPlan(Array.isArray(ts) && ts.length > 0 ? 1 : 2)
    setLoading(false)
  }, [call])
  useEffect(() => { void loadInit() }, [loadInit])

  const loadPanier = useCallback(async (idTk: string) => {
    const r = await call<PanierItem[]>('POST', `${API}/panier/${idTk}`)
    if (Array.isArray(r)) setPanier(r)
  }, [call])

  const searchVilles = useCallback(async (cpVal: string) => {
    if (cpVal.length < 4) { setVilles([]); return }
    const r = await call<any[]>('GET', `${API_COMMON}/villes/${encodeURIComponent(cpVal)}`)
    setVilles(Array.isArray(r) ? r : [])
  }, [call])

  const resetClientForm = () => {
    setCivilite(1); setNom(''); setNomMarital(''); setPrenom('')
    setDnaiss(''); setDepNaiss(''); setTypeLogement(1)
    setAdresse1(''); setAdresse2(''); setCp(''); setVilles([])
    setVilleId(0); setVilleNom(''); setMobile1(''); setMobile2(''); setMail('')
    setClientPro(false); setRs(''); setSiret('')
    setPanier([]); setCinFiles([]); setKbisFiles([])
    setCinOk(false); setKbisOk(false); setIdTicketEnCours('')
  }

  // --- Plan 1 : ouvrir / suppr ticket ----------------------------

  const openTicket = async (t: Ticket) => {
    setIdTicketEnCours(t.IDTK_Liste)
    const isPro = _bool(t.ClientPro)
    setClientPro(isPro)
    setCinOk(_bool(t.PhotoOK)); setKbisOk(_bool(t.KbisOK))
    const docsOk = isPro ? _bool(t.KbisOK) : _bool(t.PhotoOK)
    if (docsOk) {
      await loadPanier(t.IDTK_Liste)
      setPlan(4)
    } else {
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

  // --- Plan 2 -> validation client -------------------------------

  const validerClient = async () => {
    if (!nom || !prenom || !cp || !villeId || !mobile1) {
      setToast('Merci de completer les champs obligatoires'); return
    }
    if (typeLogement === 2 && !adresse2) {
      setToast("Merci du complement d'adresse"); return
    }
    if (clientPro && (!rs || !siret)) {
      setToast('RS + SIRET obligatoires pour un Pro'); return
    }
    setLoading(true)
    setLoadingMsg('Creation du client (peut prendre jusqu\'a 1 minute)...')
    const payload = {
      CiviliteClient: civilite,
      NomClient: nom, NomMaritalClient: nomMarital, PrenomClient: prenom,
      DATENAISS: fmtDateApi(dnaiss), DEPNAISS: _toInt(depNaiss),
      ADRESSE1: adresse1, ADRESSE2: adresse2, CP: cp, VILLE: villeNom,
      adrMail: mail, Mobile1: mobile1, Mobile2: mobile2,
      TypeLogement: typeLogement, ClientPro: clientPro,
      ClientRS: rs, ClientSiret: siret,
    }
    const r = await call<{ nIdDemande: string; sInfoData?: string }>(
      'POST', `${API}/nouveau-ticket`, payload,
    )
    setLoading(false); setLoadingMsg('')
    if (!r?.nIdDemande) { setToast(r?.sInfoData || 'Echec creation'); return }
    setTickets([{
      IDTK_Liste: r.nIdDemande, NomClient: nom, PrenomClient: prenom,
      ClientPro: clientPro, ClientRS: rs, CP: cp, VILLE: villeNom,
    }, ...tickets])
    setIdTicketEnCours(r.nIdDemande)
    setPlan(3)   // Fibre : toujours Plan 3 (docs) meme pour Part
  }

  // --- Plan 3 : docs ---------------------------------------------

  const uploadDoc = async (files: File[], kind: 'PieceIdentite' | 'KBIS') => {
    if (files.length === 0) { setToast('Aucun fichier'); return false }
    setLoading(true); setLoadingMsg(`Upload ${kind}...`)
    try {
      const pdf = await generateImagesPdf(files, { filigrane: true })
      const fname = `${idTicketEnCours}_${kind}.pdf`
      const res = await uploadFichier(pdf, fname)
      if (!res.ok) { setToast(`Echec upload ${kind}: ${res.error}`); return false }
      setToast(`${kind} uploade`); return true
    } finally { setLoading(false); setLoadingMsg('') }
  }

  const validerDocs = async () => {
    setLoading(true); setLoadingMsg('Verification serveur...')
    const cin = await call<any>('GET', `${API}/verif-photo/${idTicketEnCours}/PieceIdentite`)
    const cinOkNow = _toInt(cin?.nIdDemande) !== 0
    let kbisOkNow = true
    if (clientPro) {
      const k = await call<any>('GET', `${API}/verif-photo/${idTicketEnCours}/KBIS`)
      kbisOkNow = _toInt(k?.nIdDemande) !== 0
    }
    setLoading(false); setLoadingMsg('')
    setCinOk(cinOkNow); setKbisOk(kbisOkNow)
    if (!cinOkNow || !kbisOkNow) { setToast('Documents manquants sur le serveur'); return }
    await loadPanier(idTicketEnCours)
    setPlan(4)
  }

  // --- Plan 4 : ajouter FIBRE / MOBILE ---------------------------

  const ajouterFibre = async () => {
    const t = clientPro ? 'FIB PRO' : 'FIBRE'
    setTypeOffre(t); setAvecTV(false)
    setLoading(true)
    const r = await call<Offre[]>('GET', `${API}/offres/${encodeURIComponent(t)}/0`)
    setLoading(false)
    setOffres(Array.isArray(r) ? r : [])
    setPlan(5)
  }

  const ajouterMobile = async () => {
    const t = clientPro ? 'MOB PRO' : 'MOBILE'
    setTypeOffre(t); setAvecTV(false)
    setLoading(true)
    const r = await call<Offre[]>('GET', `${API}/offres/${encodeURIComponent(t)}/0`)
    setLoading(false)
    setOffres(Array.isArray(r) ? r : [])
    setPlan(5)
  }

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
                { IDtk_CallSFR_Panier: item.IDtk_CallSFR_Panier })
    await loadPanier(idTicketEnCours)
    setLoading(false)
  }

  const changerVenteMobile = async (v: number) => {
    setVenteMobile(v)
    if (v === 2) {
      await call('POST', `${API}/panier/anomalie-mobile/0`, {
        IDTK_Liste: idTicketEnCours,
        IDtk_CallSFR_Anomalie: '',
        InfoCplAnomalie: '',
      })
    }
  }

  const changerAnomalie = async (id: string) => {
    setSelectedAnomalie(id)
    await call('POST', `${API}/panier/anomalie-mobile/1`, {
      IDTK_Liste: idTicketEnCours,
      IDtk_CallSFR_Anomalie: id,
      InfoCplAnomalie: infoCpltAnomalie,
    })
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

  // --- Plan 5 : choix offre -> Plan 6 (portabilite) ---------------

  const isFibreType = (t: string) => t === 'FIBRE' || t === 'FIB PRO'

  const choisirOffre = async (o: Offre) => {
    const okOffre = await showConfirm({
      title: 'Ajouter l\'offre au panier',
      message: `Ajouter l'offre ${o.Lib_Offre} au panier ?`,
      confirmLabel: 'Ajouter',
    })
    if (!okOffre) return
    setIdProdChoisi(o.IDOffres_SFR); setTypeProdChoisi(typeOffre)
    if (isFibreType(typeOffre)) {
      // Choix Conquete / Migration
      const kind = await showChoice({
        title: 'Type de vente',
        message: 'Choisis le type de vente pour cette offre Fibre :',
        options: [
          { label: 'Conquête', value: 'conquete', variant: 'brand' },
          { label: 'Migration', value: 'migration', variant: 'neutral' },
        ],
      })
      if (!kind) return
      if (kind === 'migration') {
        await ajouterProduitDirect(o.IDOffres_SFR, 3)  // TypeVente=3
        return
      }
    }
    setPlan(6)
  }

  const toggleTV = async (v: boolean) => {
    setAvecTV(v)
    setLoading(true)
    const r = await call<Offre[]>('GET',
      `${API}/offres/${encodeURIComponent(typeOffre)}/${v ? 1 : 0}`)
    setLoading(false)
    setOffres(Array.isArray(r) ? r : [])
  }

  const ajouterProduitDirect = async (idOffre: string, typeVente: number) => {
    setLoading(true)
    const r = await call<{ nIdDemande: string }>(
      'POST', `${API}/panier/produit/ajouter`, {
        IDTK_Liste: idTicketEnCours,
        IDOffres_SFR: idOffre,
        Opt_TV: avecTV,
        Type: typeOffre,
        Portabilite: false,
        NumPortabilite: '',
        NumPrise_RIO: '',
        NumPriseOptique: '',
        TypeVente: typeVente,
        OptionsChoisies: optChoisies,
      })
    setLoading(false)
    if (r?.nIdDemande) {
      await loadPanier(idTicketEnCours)
      setPlan(4)
    } else setToast('Echec ajout')
  }

  const validerPortabilite = async () => {
    if (portabilite) {
      if (!numPort || codeRIO.length < 12) {
        setToast('N° portabilité + code RIO (12 chars min) obligatoires'); return
      }
    } else if (isFibreType(typeProdChoisi) && !ficResil) {
      setToast('Lettre de résiliation manquante'); return
    }
    setLoading(true)
    const r = await call<{ nIdDemande: string }>(
      'POST', `${API}/panier/produit/ajouter`, {
        IDTK_Liste: idTicketEnCours,
        IDOffres_SFR: idProdChoisi,
        Opt_TV: avecTV,
        Type: typeProdChoisi,
        Portabilite: portabilite,
        NumPortabilite: cleanNumPort(numPort),
        NumPrise_RIO: cleanRIO(codeRIO),
        NumPriseOptique: nouvellePrise ? 'Nouvelle prise' : cleanNumPrise(numPrise),
        TypeVente: 1,
        OptionsChoisies: optChoisies,
      })
    setLoading(false)
    if (r?.nIdDemande) {
      await loadPanier(idTicketEnCours)
      setPlan(4)
    } else setToast('Echec ajout produit')
  }

  const scanResiliation = async (files: File[]) => {
    if (files.length === 0) return
    setLoading(true); setLoadingMsg('Upload lettre de resiliation...')
    try {
      // Pas de filigrane pour la lettre de resil (cf. Flutter)
      const pdf = await generateImagesPdf(files, { filigrane: false })
      const fname = `${idTicketEnCours}_LettreResil.pdf`
      const res = await uploadFichier(pdf, fname)
      if (res.ok) { setFicResil(fname); setResilOnServer(true) }
      else { setFicResil(''); setResilOnServer(false); setToast(`Echec upload: ${res.error}`) }
    } finally { setLoading(false); setLoadingMsg('') }
  }

  const checkResilOnServer = useCallback(async () => {
    if (!idTicketEnCours) return
    const r = await call<{ exists: boolean }>('GET',
      `${API}/lettre-resil-existe/${idTicketEnCours}`)
    setResilOnServer(!!r?.exists)
    if (r?.exists) setFicResil(`${idTicketEnCours}_LettreResil.pdf`)
  }, [call, idTicketEnCours])

  useEffect(() => {
    if (plan === 6 && !portabilite && isFibreType(typeProdChoisi)) {
      void checkResilOnServer()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan, portabilite, typeProdChoisi])

  // --- Header ----------------------------------------------------

  const goBack = () => {
    const table: Record<number, number> = { 2: 1, 3: 2, 4: 1, 5: 4, 6: 5, 7: 2 }
    setPlan(table[plan] ?? 1)
  }
  const titreParPlan: Record<number, string> = {
    1: 'Mes Paniers en cours', 2: 'Mon client', 3: 'Mon client',
    4: 'Panier Client', 5: 'Panier Client', 6: 'Portabilité',
    7: 'Mon client',
  }

  return (
    <div className="p-4 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        {plan !== 1 && (
          <button onClick={goBack}
            className="p-2 rounded hover:bg-c-brand-soft text-c-ink" title="Retour">
            <ArrowLeft className="w-5 h-5" />
          </button>
        )}
        <h1 className="text-xl font-bold text-c-ink">
          {titreParPlan[plan] || 'Ticket Fibre'}
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
        mobile2={mobile2} setMobile2={setMobile2}
        mail={mail} setMail={setMail}
        clientPro={clientPro} setClientPro={setClientPro}
        rs={rs} setRs={setRs}
        siret={siret} setSiret={setSiret}
        onValider={validerClient}
        onTestEligibilite={() => setPlan(7)} />}

      {plan === 3 && <PlanDocs
        clientPro={clientPro} cinOk={cinOk} kbisOk={kbisOk}
        onCinChange={setCinFiles} onKbisChange={setKbisFiles}
        onUploadCin={async () => { const ok = await uploadDoc(cinFiles, 'PieceIdentite'); if (ok) setCinOk(true) }}
        onUploadKbis={async () => { const ok = await uploadDoc(kbisFiles, 'KBIS'); if (ok) setKbisOk(true) }}
        onValider={validerDocs} />}

      {plan === 4 && <PlanPanier
        panier={panier} anomalies={anomalies}
        clientPro={clientPro}
        showVenteMobile={hasDroitBSSFRDiff && panier.some((p) => (p.Type || '').startsWith('MOB'))}
        venteMobile={venteMobile} setVenteMobile={changerVenteMobile}
        selectedAnomalie={selectedAnomalie} setSelectedAnomalie={changerAnomalie}
        infoCpltAnomalie={infoCpltAnomalie} setInfoCpltAnomalie={setInfoCpltAnomalie}
        showCodeInput={showCodeInput} codeSaisi={codeSaisi} setCodeSaisi={setCodeSaisi}
        onSuppr={supprimerProduit}
        onAjouterFibre={ajouterFibre}
        onAjouterMobile={ajouterMobile}
        onGenerer={genererCode} onValider={validerPanier} />}

      {plan === 5 && <PlanOffres
        offres={offres} typeOffre={typeOffre}
        avecTV={avecTV} setAvecTV={toggleTV}
        optChoisies={optChoisies} setOptChoisies={setOptChoisies}
        onChoisir={choisirOffre} />}

      {plan === 6 && <PlanPortabilite
        isFibre={isFibreType(typeProdChoisi)}
        portabilite={portabilite} setPortabilite={setPortabilite}
        numPort={numPort} setNumPort={setNumPort}
        codeRIO={codeRIO} setCodeRIO={setCodeRIO}
        nouvellePrise={nouvellePrise} setNouvellePrise={setNouvellePrise}
        numPrise={numPrise} setNumPrise={setNumPrise}
        ficResil={ficResil} resilOnServer={resilOnServer}
        onScanResil={scanResiliation}
        onValider={validerPortabilite} />}

      {plan === 7 && <PlanWebViewEligibilite onBack={goBack} />}

      {loading && <LoadingOverlay msg={loadingMsg} />}
      {toast && <Toast msg={toast} onClose={() => setToast('')} />}
    </div>
  )
}


// ============================================================================
// Sous-composants
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
      <div className="bg-gray-900 text-white text-sm rounded-md px-4 py-2 shadow-lg">{msg}</div>
    </div>
  )
}

function SegRow({ options, value, onChange }: {
  options: { value: any; label: string }[]
  value: any; onChange: (v: any) => void
}) {
  return (
    <div className="flex gap-2 flex-wrap">
      {options.map((o, i) => (
        <button key={i} onClick={() => onChange(o.value)}
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


function PlanTickets({ tickets, onOpen, onSuppr, onNew }: any) {
  return (
    <div className="space-y-2">
      <button onClick={onNew}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-md bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
        <Plus className="w-4 h-4" /> Nouveau client
      </button>
      {tickets.length === 0 && (
        <div className="text-center text-c-ink-faint text-sm py-6 italic">Aucun panier en cours</div>
      )}
      {tickets.map((t: Ticket) => (
        <div key={t.IDTK_Liste} onDoubleClick={() => onOpen(t)}
          className="bg-white border border-c-line-soft rounded p-3 flex items-center gap-3 hover:bg-c-brand-soft cursor-pointer">
          <div className="flex-1">
            <div className="font-medium text-sm">
              {t.NomClient} {t.PrenomClient}
              {_bool(t.ClientPro) && (
                <span className="ml-2 text-[10px] bg-orange-100 text-orange-700 rounded px-1.5">PRO</span>
              )}
            </div>
            <div className="text-xs text-c-ink-soft">{t.CP} {t.VILLE}</div>
          </div>
          <button onClick={(e) => { e.stopPropagation(); onSuppr(t) }} className="text-red-600 hover:text-red-800">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  )
}


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
        <Field label="Date naissance (jj/mm/aaaa)" value={p.dnaiss} onChange={p.setDnaiss} />
        <Field label="Département naissance" value={p.depNaiss} onChange={p.setDepNaiss} />
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Field label="Mobile 1" value={p.mobile1} onChange={p.setMobile1} />
        <Field label="Mobile 2" value={p.mobile2} onChange={p.setMobile2} />
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
      <div className="flex gap-2">
        <button onClick={p.onTestEligibilite}
          className="flex-1 py-3 rounded border border-gray-900 text-c-ink text-sm font-semibold hover:bg-c-brand-soft">
          Test d'éligibilité Fibre
        </button>
        <button onClick={p.onValider}
          className="flex-1 py-3 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
          Valider les infos client
        </button>
      </div>
    </div>
  )
}


function PlanDocs({ clientPro, cinOk, kbisOk,
                    onCinChange, onKbisChange,
                    onUploadCin, onUploadKbis, onValider }: any) {
  return (
    <div className="space-y-6 max-w-2xl">
      <section>
        <div className="flex items-center gap-2 mb-2">
          <div className="text-sm font-medium">Pièce d'identité</div>
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


function PlanPanier(p: any) {
  return (
    <div className="space-y-3">
      {p.panier.length === 0 && (
        <div className="text-center italic text-c-ink-faint py-4">Panier vide</div>
      )}
      {p.panier.map((it: PanierItem) => (
        <div key={it.IDtk_CallSFR_Panier} onClick={() => p.onSuppr(it)}
          className="bg-white border border-c-line-soft rounded p-3 flex items-center gap-3 hover:bg-c-brand-soft cursor-pointer">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium truncate">{it.LibOffre}</div>
            <div className="text-xs text-c-ink-soft">
              {it.Type} {it.NumPortabilite && `— portabilité ${it.NumPortabilite}`}
            </div>
          </div>
          <div className="text-sm font-semibold tabular-nums whitespace-nowrap">
            {fmtEUR(it.MontantOffre)}
          </div>
          <Trash2 className="w-4 h-4 text-red-600 shrink-0" />
        </div>
      ))}
      <div className="flex gap-2 flex-wrap">
        <button onClick={p.onAjouterFibre}
          className="flex-1 min-w-[160px] flex items-center justify-center gap-1 px-4 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
          <Plus className="w-4 h-4" /> Ajouter FIBRE
        </button>
        <button onClick={p.onAjouterMobile}
          className="flex-1 min-w-[160px] flex items-center justify-center gap-1 px-4 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
          <Plus className="w-4 h-4" /> Ajouter MOBILE
        </button>
      </div>
      {p.showVenteMobile && (
        <div className="border border-c-line-soft rounded p-3 space-y-2 bg-c-surface-soft">
          <div className="text-sm font-medium">Vente mobile</div>
          <SegRow value={p.venteMobile} onChange={p.setVenteMobile}
            options={[{ value: 1, label: 'En direct' }, { value: 2, label: 'Différée' }]} />
          {p.venteMobile === 2 && (
            <>
              <label className="block">
                <span className="block text-xs text-c-ink-soft mb-0.5">Motif d'anomalie</span>
                <select value={p.selectedAnomalie}
                  onChange={(e) => p.setSelectedAnomalie(e.target.value)}
                  className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white">
                  <option value="">Choisir…</option>
                  {p.anomalies.map((a: Anomalie) => (
                    <option key={a.IDtk_CallSFR_Anomalie} value={a.IDtk_CallSFR_Anomalie}>
                      {a.LibTypeAnomalie}
                    </option>
                  ))}
                </select>
              </label>
              {p.selectedAnomalie === '100' && (
                <Field label="Précisez" value={p.infoCpltAnomalie} onChange={p.setInfoCpltAnomalie} />
              )}
            </>
          )}
        </div>
      )}
      {p.panier.length > 0 && !p.showCodeInput && (
        <button onClick={p.onGenerer}
          className="w-full flex items-center justify-center gap-1 px-4 py-2 rounded bg-green-700 text-white text-sm font-semibold hover:brightness-110">
          <Send className="w-4 h-4" /> Valider le panier
        </button>
      )}
      {p.showCodeInput && (
        <div className="border border-c-line-soft rounded p-4 space-y-2 bg-c-surface-soft">
          <div className="text-sm">SMS envoyé au client. Saisis le code :</div>
          <div className="flex gap-2 items-end">
            <input value={p.codeSaisi} onChange={(e) => p.setCodeSaisi(e.target.value)}
                   maxLength={6}
                   className="flex-1 border border-c-line rounded px-2 py-1.5 text-center tracking-widest text-lg bg-white" />
            <button onClick={p.onValider}
              className="p-2 rounded bg-green-700 text-white hover:brightness-110">
              <Check className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}


function PlanOffres(p: any) {
  const isFibre = p.typeOffre === 'FIBRE' || p.typeOffre === 'FIB PRO'
  return (
    <div className="space-y-3">
      <div className="text-sm font-medium">{p.typeOffre}</div>
      {isFibre && (
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={p.avecTV} onChange={(e) => p.setAvecTV(e.target.checked)}
                   className="accent-c-brand" />
            Avec TV / PS5 / High Tech
          </label>
        </div>
      )}
      <Field label="Options choisies (texte libre)" value={p.optChoisies} onChange={p.setOptChoisies} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {p.offres.map((o: Offre) => (
          <button key={o.IDOffres_SFR} onClick={() => p.onChoisir(o)}
            className="text-left bg-white border border-c-line-soft rounded-lg p-3 hover:bg-c-brand-soft">
            <div className="font-semibold text-sm">{o.Lib_Offre}</div>
            {o.PrixOffre && (
              <div className="text-xl font-bold text-c-ink my-1">
                {o.PrixOffre} <span className="text-xs font-normal">€ / mois</span>
              </div>
            )}
            {o.Engagement && <div className="text-xs text-c-ink-soft">Engagement: {o.Engagement}</div>}
            {_bool(o.EnPromo) && o.InfoPromo && (
              <div className="text-xs text-orange-600 font-semibold mt-1">🔥 {o.InfoPromo}</div>
            )}
            {(o.DebitDown || o.DebitUp) && (
              <div className="text-xs text-c-ink-soft mt-1">
                {o.DebitDown && <>↓ {o.DebitDown} </>}
                {o.DebitUp && <>↑ {o.DebitUp}</>}
              </div>
            )}
            {o.ServiceInclus && (
              <div className="text-xs text-c-ink-soft mt-1">{o.ServiceInclus}</div>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}


function PlanPortabilite(p: any) {
  return (
    <div className="space-y-4 max-w-2xl">
      <div>
        <span className="block text-xs text-c-ink-soft mb-1">Portabilité</span>
        <SegRow value={p.portabilite} onChange={p.setPortabilite}
          options={[{ value: true, label: 'Oui' }, { value: false, label: 'Non' }]} />
      </div>
      {p.portabilite ? (
        <>
          <Field label="N° à conserver" value={p.numPort} onChange={p.setNumPort} />
          <Field label="Code RIO (12 chars min)" value={p.codeRIO} onChange={p.setCodeRIO} />
        </>
      ) : p.isFibre && (
        <div className="border border-c-line-soft rounded p-3 space-y-2 bg-c-surface-soft">
          <div className="text-sm font-medium flex items-center gap-2">
            Lettre de résiliation
            {p.resilOnServer === true && <CheckCircle2 className="w-4 h-4 text-green-600" />}
            {p.resilOnServer === false && <XCircle className="w-4 h-4 text-red-600" />}
          </div>
          <PhotoInputMulti label="Scanner la lettre de résiliation"
                           onChange={p.onScanResil} multiple={false} />
        </div>
      )}
      {p.isFibre && (
        <div>
          <span className="block text-xs text-c-ink-soft mb-1">Type de prise</span>
          <SegRow value={p.nouvellePrise} onChange={p.setNouvellePrise}
            options={[{ value: true, label: 'Nouvelle prise' }, { value: false, label: 'Prise parc' }]} />
          {!p.nouvellePrise && (
            <div className="mt-2">
              <Field label="Numéro de prise" value={p.numPrise} onChange={p.setNumPrise} />
            </div>
          )}
        </div>
      )}
      <button onClick={p.onValider}
        className="w-full py-3 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
        Ajouter au panier
      </button>
    </div>
  )
}


function PlanWebViewEligibilite({ onBack }: { onBack: () => void }) {
  // Simple iframe (Flutter avait un WebViewWidget natif).
  // Le site SFR autorise le iframe pour ces pages publiques.
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <div>Test d'éligibilité Fibre SFR</div>
        <a href={SFR_ELIGIBILITE_URL} target="_blank" rel="noreferrer"
           className="flex items-center gap-1 text-c-brand hover:underline">
          <ExternalLink className="w-3.5 h-3.5" /> Ouvrir dans un onglet
        </a>
      </div>
      <iframe src={SFR_ELIGIBILITE_URL}
        title="SFR - Test eligibilite Fibre"
        className="w-full h-[70vh] border border-c-line-soft rounded" />
      <button onClick={onBack}
        className="w-full py-2 rounded border border-gray-900 text-c-ink text-sm hover:bg-c-brand-soft">
        ← Retour au formulaire client
      </button>
    </div>
  )
}
