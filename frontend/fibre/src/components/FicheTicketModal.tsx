/**
 * Popup fiche d'un ticket Call Fibre (transposition PAGE_TicketFicheFibre).
 *
 * Phase 1 = lecture seule. Affichage en 3 colonnes :
 *  - Gauche : infos client + bloc vendeur en bas
 *  - Centre : panier d'offres + boutons d'action (grises en phase 1)
 *  - Droite : detail de l'offre selectionnee (portabilite + statut + type
 *    vente + options + test d'eligibilite) + bloc vente
 *
 * Mobile masque "0612345xx" tant que l'ope n'a pas pose le verrou (champ
 * is_my_call cote backend).
 */

import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Loader2,
  ArrowLeft,
  Phone,
  PhoneOff,
  ExternalLink,
  CreditCard,
  CheckCircle2,
  Circle,
  FileText,
  Ban,
  Copy,
  Check,
} from 'lucide-react'
import { getToken } from '@/api'
import DocumentViewerModal from '@/components/DocumentViewerModal'
import ConfirmDialog from '@/components/ConfirmDialog'
import AnnulLignePanierPopup from '@/components/AnnulLignePanierPopup'

interface FicheClient {
  civilite: number
  nom: string
  nom_marital: string
  prenom: string
  nom_format: string
  date_naiss: string
  dep_naiss: number
  type_logement: number
  adresse1: string
  adresse2: string
  cp: string
  ville: string
  email: string
  mobile1: string
  mobile2: string
  opt_rappel: boolean
  opt_partenaire: boolean
  client_pro: boolean
  client_rs: string
  client_siret: string
}

interface FicheVendeur {
  id_salarie: number
  nom: string
  prenom: string
  gsm: string
  lib_affectation: string
}

interface FicheVente {
  ref_appel: string
  intervention_vendeur: boolean
  mobile_propose_vendeur: boolean
  info_vente: string
}

interface FicheAnomalie {
  active: boolean
  id_type: number
  info_cplt: string
}

interface FicheOffre {
  id: string
  id_offre: string
  lib_offre: string
  type: string
  opt_tv: boolean
  portabilite: boolean
  type_vente: number
  statut_prod: number
  motif_annulation: string
  num_portabilite: string
  num_rio: string
  num_prise_optique: string
  opt_choisies: string
}

interface StatutVenteOption {
  id: number
  label: string
}

interface MotifAnomalieOption {
  id: number
  label: string
}

interface DocRef {
  url: string
  kind: 'pdf' | 'image' | ''
}

interface FicheData {
  id_ticket: string
  id_call_sfr: string
  id_tk_statut: number
  is_cloture: boolean
  is_statut_34: boolean
  is_my_call: boolean
  client: FicheClient
  vendeur: FicheVendeur
  vente: FicheVente
  anomalie: FicheAnomalie
  panier: FicheOffre[]
  nb_prod_total: number
  nb_prod_valide: number
  nb_prod_annule: number
  btn_valider_actif: boolean
  btn_annuler_actif: boolean
  statuts_vente: StatutVenteOption[]
  motifs_anomalie: MotifAnomalieOption[]
}

const API_BASE = '/api/call/fibre'

interface VerrouPeek {
  appel_en_cours: boolean
  ope_appel_id: number
  ope_appel_nom: string
  date_h_appel: string
  duree_minutes: number
  duree_secondes: number
}

interface Props {
  idTicket: string | null
  onClose: () => void
  onAfterAction?: () => void   // callback pour refresh la liste apres action panier
}

// --- Historique de saisie "Réf Appel" (local au poste, localStorage) -----
// Mémorise les valeurs déjà saisies/rencontrées sur ce navigateur pour les
// proposer en autocomplétion (datalist). Non partagé entre postes.
const REF_APPEL_HISTORY_KEY = 'cf_ref_appel_history'
const REF_APPEL_HISTORY_MAX = 50

function loadRefAppelHistory(): string[] {
  try {
    const arr = JSON.parse(localStorage.getItem(REF_APPEL_HISTORY_KEY) || '[]')
    return Array.isArray(arr) ? arr.filter((x) => typeof x === 'string') : []
  } catch {
    return []
  }
}

function pushRefAppelHistory(value: string): string[] {
  const v = (value || '').trim()
  const cur = loadRefAppelHistory()
  if (!v) return cur
  // Dédoublonnage insensible à la casse, plus récent en tête, plafonné.
  const next = [v, ...cur.filter((x) => x.toLowerCase() !== v.toLowerCase())].slice(
    0,
    REF_APPEL_HISTORY_MAX,
  )
  try {
    localStorage.setItem(REF_APPEL_HISTORY_KEY, JSON.stringify(next))
  } catch {
    /* quota/private mode : on ignore */
  }
  return next
}

// ISO 'YYYY-MM-DD' -> 'DD/MM/YYYY' (format a copier). Vide si non parsable.
function isoToFr(iso: string): string {
  if (!iso || iso.length < 10) return iso || ''
  const [y, m, d] = iso.slice(0, 10).split('-')
  if (!y || !m || !d) return iso
  return `${d}/${m}/${y}`
}

// Petit bouton "copier dans le presse-papier" avec feedback (coche 1.5s).
function CopyButton({ value, title }: { value: string; title?: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard indisponible (http non sécurisé / permission) */
    }
  }
  return (
    <button
      type="button"
      onClick={handleCopy}
      disabled={!value}
      title={title || 'Copier'}
      className="shrink-0 w-9 h-9 rounded border border-c-line hover:bg-c-brand-soft flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
    >
      {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4 text-c-ink-soft" />}
    </button>
  )
}

export default function FicheTicketModal({ idTicket, onClose, onAfterAction }: Props) {
  const [data, setData] = useState<FicheData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [selectedPanierId, setSelectedPanierId] = useState<string>('')
  // Etat du viewer doc (CIN / KBIS / Lettre resil) + URLs detectees
  const [docCin, setDocCin] = useState<DocRef>({ url: '', kind: '' })
  const [docKbis, setDocKbis] = useState<DocRef>({ url: '', kind: '' })
  const [docLettre, setDocLettre] = useState<DocRef>({ url: '', kind: '' })
  const [viewerOpen, setViewerOpen] = useState<null | 'cin' | 'kbis' | 'lettre'>(null)
  // States d'edition (initialises a partir des donnees du backend)
  const [editClient, setEditClient] = useState<FicheClient | null>(null)
  const [editVente, setEditVente] = useState<FicheVente | null>(null)
  const [editAnomalie, setEditAnomalie] = useState<FicheAnomalie | null>(null)
  const [editOffres, setEditOffres] = useState<Record<string, FicheOffre>>({})
  const [savingVente, setSavingVente] = useState(false)
  const [savingOffre, setSavingOffre] = useState(false)
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)
  // Phase 3 : verrou ope + sous-popups d'action
  const [verrouLoading, setVerrouLoading] = useState(false)
  const [verrouConfirm, setVerrouConfirm] = useState<VerrouPeek | null>(null)
  const [actionDialog, setActionDialog] = useState<null | 'valider' | 'annulVente' | 'renvoi'>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [annulLigneOpen, setAnnulLigneOpen] = useState(false)
  // Historique de saisie Réf Appel (local au poste)
  const [refAppelHistory, setRefAppelHistory] = useState<string[]>(() => loadRefAppelHistory())

  // Fetch fiche
  useEffect(() => {
    if (!idTicket) return
    setLoading(true)
    setError('')
    setData(null)
    setSelectedPanierId('')
    setDocCin({ url: '', kind: '' })
    setDocKbis({ url: '', kind: '' })
    setDocLettre({ url: '', kind: '' })
    ;(async () => {
      try {
        const r = await fetch(`${API_BASE}/tickets/${idTicket}/fiche`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) {
          let detail = ''
          try {
            const j = await r.json()
            detail = j?.detail ? `: ${j.detail}` : ''
          } catch {
            /* ignore */
          }
          setError(`Chargement échoué (${r.status})${detail}`)
          return
        }
        const d = (await r.json()) as FicheData
        setData(d)
        // Init des states d'edition (copies)
        setEditClient({ ...d.client })
        setEditVente({ ...d.vente })
        setEditAnomalie({ ...d.anomalie })
        // Mémorise la Réf Appel rencontrée pour l'autocomplétion future
        if (d.vente?.ref_appel) setRefAppelHistory(pushRefAppelHistory(d.vente.ref_appel))
        const offresMap: Record<string, FicheOffre> = {}
        for (const o of d.panier) offresMap[o.id] = { ...o }
        setEditOffres(offresMap)
        // Pré-sélection : 1re ligne FIBRE si présente, sinon 1re ligne
        const firstFibre = d.panier.find((p) => p.type === 'FIBRE')
        if (firstFibre) setSelectedPanierId(firstFibre.id)
        else if (d.panier.length > 0) setSelectedPanierId(d.panier[0].id)
        // Detecte les documents en arriere-plan (CIN + KBIS si Pro)
        fetch(`${API_BASE}/tickets/${idTicket}/documents?client_pro=${d.client.client_pro ? 1 : 0}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
          .then((r2) => (r2.ok ? r2.json() : null))
          .then((docs) => {
            if (docs?.cin) setDocCin(docs.cin)
            if (docs?.kbis) setDocKbis(docs.kbis)
          })
          .catch(() => {
            /* silencieux */
          })
      } catch (e) {
        setError('Erreur réseau')
      } finally {
        setLoading(false)
      }
    })()
  }, [idTicket])

  // Lazy load TestEligibilite quand on sélectionne une ligne FIBRE
  // (On lit depuis editOffres pour avoir les modifs en cours)
  const selectedOffre = useMemo(
    () => (selectedPanierId ? editOffres[selectedPanierId] || null : null),
    [editOffres, selectedPanierId],
  )
  // Recharge la lettre-resil uniquement quand on CHANGE de ligne ou que le
  // flag FIBRE/portabilite change (pas a chaque keystroke).
  const isFibre = selectedOffre?.type === 'FIBRE'
  const isPortabilite = !!selectedOffre?.portabilite
  useEffect(() => {
    if (!selectedPanierId || !isFibre) {
      setDocLettre({ url: '', kind: '' })
      return
    }
    let cancelled = false
    if (!isPortabilite && idTicket) {
      fetch(`${API_BASE}/tickets/${idTicket}/panier/${selectedPanierId}/lettre-resil`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (!cancelled && d) setDocLettre(d)
        })
        .catch(() => {
          /* silencieux */
        })
    } else {
      setDocLettre({ url: '', kind: '' })
    }
    return () => {
      cancelled = true
    }
  }, [selectedPanierId, isFibre, isPortabilite, idTicket])

  // Esc ferme la modal
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  // Auto-dismiss du toast apres 3s
  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 3000)
    return () => window.clearTimeout(t)
  }, [toast])

  // Save infos client + vente + anomalie
  const handleSaveVente = async () => {
    if (!idTicket || !editClient || !editVente || !editAnomalie) return
    setSavingVente(true)
    try {
      const body = {
        client: {
          civilite: editClient.civilite,
          nom: editClient.nom,
          nom_marital: editClient.nom_marital,
          prenom: editClient.prenom,
          date_naiss: editClient.date_naiss,
          dep_naiss: editClient.dep_naiss,
          type_logement: editClient.type_logement,
          adresse1: editClient.adresse1,
          adresse2: editClient.adresse2,
          cp: editClient.cp,
          ville: editClient.ville,
          email: editClient.email,
        },
        vente: {
          ref_appel: editVente.ref_appel,
          intervention_vendeur: editVente.intervention_vendeur,
          mobile_propose_vendeur: editVente.mobile_propose_vendeur,
          info_vente: editVente.info_vente,
        },
        anomalie: {
          active: editAnomalie.active,
          id_type: editAnomalie.id_type,
          info_cplt: editAnomalie.info_cplt,
        },
      }
      const r = await fetch(`${API_BASE}/tickets/${idTicket}/save-vente`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Échec : ${j?.detail || r.status}` })
        return
      }
      setToast({ kind: 'ok', msg: 'Informations client et vente enregistrées' })
      setRefAppelHistory(pushRefAppelHistory(editVente.ref_appel))
    } catch (e) {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setSavingVente(false)
    }
  }

  // Save offre selectionnee
  const handleSaveOffre = async () => {
    const offre = selectedPanierId ? editOffres[selectedPanierId] : null
    if (!offre) return
    setSavingOffre(true)
    try {
      const body = {
        portabilite: offre.portabilite,
        num_portabilite: offre.num_portabilite,
        num_rio: offre.num_rio,
        num_prise_optique: offre.num_prise_optique,
        opt_choisies: offre.opt_choisies,
        type_vente: offre.type_vente,
        statut_prod: offre.statut_prod,
      }
      const r = await fetch(`${API_BASE}/tickets/panier/${offre.id}/save-offre`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Échec : ${j?.detail || r.status}` })
        return
      }
      setToast({ kind: 'ok', msg: "Modifications de l'offre enregistrées" })
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setSavingOffre(false)
    }
  }

  // Helper : update partiel d'une offre dans editOffres
  const patchOffre = (id: string, patch: Partial<FicheOffre>) => {
    setEditOffres((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }))
  }

  // Save auto silencieux d'une offre (toast court). Utilise pour les
  // champs qui declenchent un save direct (Statut Vente).
  const saveOffreAuto = async (offre: FicheOffre) => {
    try {
      const body = {
        portabilite: offre.portabilite,
        num_portabilite: offre.num_portabilite,
        num_rio: offre.num_rio,
        num_prise_optique: offre.num_prise_optique,
        opt_choisies: offre.opt_choisies,
        type_vente: offre.type_vente,
        statut_prod: offre.statut_prod,
      }
      const r = await fetch(`${API_BASE}/tickets/panier/${offre.id}/save-offre`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Échec : ${j?.detail || r.status}` })
        return
      }
      setToast({ kind: 'ok', msg: 'Statut enregistré' })
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    }
  }

  // Recharge la fiche apres une action verrou ou panier
  const reloadFiche = async () => {
    if (!idTicket) return
    try {
      const r = await fetch(`${API_BASE}/tickets/${idTicket}/fiche`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) return
      const d = (await r.json()) as FicheData
      setData(d)
      setEditClient({ ...d.client })
      setEditVente({ ...d.vente })
      setEditAnomalie({ ...d.anomalie })
      const offresMap: Record<string, FicheOffre> = {}
      for (const o of d.panier) offresMap[o.id] = { ...o }
      setEditOffres(offresMap)
    } catch {
      /* ignore */
    }
  }

  // Bouton "Démarrer l'appel" : pose le verrou ope
  const handlePrendreAppel = async (force: boolean = false) => {
    if (!idTicket) return
    setVerrouLoading(true)
    try {
      const r = await fetch(`${API_BASE}/tickets/${idTicket}/verrou/prendre`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ force }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Échec : ${j?.detail || r.status}` })
        return
      }
      const j = await r.json()
      if (j.needs_confirm) {
        setVerrouConfirm(j.peek as VerrouPeek)
        return
      }
      setToast({ kind: 'ok', msg: 'Appel démarré (mobiles démasqués)' })
      setVerrouConfirm(null)
      await reloadFiche()
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setVerrouLoading(false)
    }
  }

  // Bouton "Lâcher l'appel" : libère le verrou
  const handleLacherAppel = async () => {
    if (!idTicket) return
    setVerrouLoading(true)
    try {
      const r = await fetch(`${API_BASE}/tickets/${idTicket}/verrou/lacher`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Échec : ${j?.detail || r.status}` })
        return
      }
      setToast({ kind: 'ok', msg: 'Appel terminé' })
      await reloadFiche()
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setVerrouLoading(false)
    }
  }

  // Annulation 1 ligne du panier (Popup1)
  const handleAnnulerLigne = async (motifs: string[], precisions: string) => {
    if (!selectedPanierId) return
    setActionLoading(true)
    try {
      const r = await fetch(`${API_BASE}/tickets/panier/${selectedPanierId}/annuler-ligne`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ motifs, precisions }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Échec : ${j?.detail || r.status}` })
        return
      }
      setToast({ kind: 'ok', msg: 'Offre annulée' })
      setAnnulLigneOpen(false)
      await reloadFiche()
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setActionLoading(false)
    }
  }

  // Confirmation des 3 actions panier (Valider / Annul vente / Renvoi)
  const handleConfirmAction = async () => {
    if (!idTicket || !actionDialog) return
    setActionLoading(true)
    try {
      // Pour valider/annuler : on envoie aussi les champs vente courants
      const body =
        actionDialog === 'renvoi'
          ? {}
          : {
              client: editClient
                ? {
                    civilite: editClient.civilite,
                    nom: editClient.nom,
                    nom_marital: editClient.nom_marital,
                    prenom: editClient.prenom,
                    date_naiss: editClient.date_naiss,
                    dep_naiss: editClient.dep_naiss,
                    type_logement: editClient.type_logement,
                    adresse1: editClient.adresse1,
                    adresse2: editClient.adresse2,
                    cp: editClient.cp,
                    ville: editClient.ville,
                    email: editClient.email,
                  }
                : undefined,
              vente: editVente
                ? {
                    ref_appel: editVente.ref_appel,
                    intervention_vendeur: editVente.intervention_vendeur,
                    mobile_propose_vendeur: editVente.mobile_propose_vendeur,
                    info_vente: editVente.info_vente,
                  }
                : undefined,
              anomalie: editAnomalie
                ? {
                    active: editAnomalie.active,
                    id_type: editAnomalie.id_type,
                    info_cplt: editAnomalie.info_cplt,
                  }
                : undefined,
            }
      const path =
        actionDialog === 'valider'
          ? 'valider-vente'
          : actionDialog === 'annulVente'
            ? 'annuler-vente'
            : 'renvoyer-complement'
      const r = await fetch(`${API_BASE}/tickets/${idTicket}/${path}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Échec : ${j?.detail || r.status}` })
        return
      }
      const msg =
        actionDialog === 'valider'
          ? 'Panier validé'
          : actionDialog === 'annulVente'
            ? 'Vente annulée'
            : 'Panier renvoyé pour complément'
      setToast({ kind: 'ok', msg })
      // valider/annuler envoient la Réf Appel -> on la mémorise
      if (actionDialog !== 'renvoi' && editVente?.ref_appel) {
        pushRefAppelHistory(editVente.ref_appel)
      }
      setActionDialog(null)
      onAfterAction?.()
      onClose()
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setActionLoading(false)
    }
  }

  if (!idTicket) return null

  // Document actif dans le viewer
  const viewerDoc: DocRef =
    viewerOpen === 'cin' ? docCin : viewerOpen === 'kbis' ? docKbis : viewerOpen === 'lettre' ? docLettre : { url: '', kind: '' }
  const viewerTitle =
    viewerOpen === 'cin' ? "Carte d'identité" : viewerOpen === 'kbis' ? 'KBIS' : viewerOpen === 'lettre' ? 'Lettre de résiliation' : ''

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-3"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.97 }}
          className="bg-white rounded-xl shadow-2xl w-full max-w-[1500px] h-[95vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-c-line">
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="p-1.5 rounded text-c-ink-soft hover:bg-c-brand-soft hover:text-c-ink transition-colors"
                title="Retour"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h2 className="text-base font-bold text-c-ink">
                Fiche Ticket Call SFR
                {data ? ` — ${data.client.nom_format}` : ''}
              </h2>
              {data?.is_statut_34 && (
                <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded">
                  Vente mobile en différé
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <a
                href="https://ezy-distrib.distrib.sfr.fr/home/frontoffice/dfo/dist/index.html#/portail"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-c-brand hover:underline flex items-center gap-1"
              >
                Portail de saisie EZY - SFR
                <ExternalLink className="w-3 h-3" />
              </a>
              <button
                onClick={onClose}
                className="p-1.5 rounded text-c-ink-soft hover:bg-c-brand-soft hover:text-c-ink transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Corps */}
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-c-brand animate-spin" />
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center text-red-600 text-sm">
              {error}
            </div>
          ) : !data ? (
            <div className="flex-1 flex items-center justify-center text-c-ink-faint text-sm italic">
              Aucune donnée
            </div>
          ) : (
            <div className="flex-1 grid grid-cols-12 gap-4 p-4 overflow-auto bg-gray-50">
              <ColonneGauche
                data={data}
                client={editClient!}
                onClientChange={(patch) => setEditClient((c) => (c ? { ...c, ...patch } : c))}
                cinAvailable={!!docCin.url}
                kbisAvailable={!!docKbis.url}
                onOpenCin={() => setViewerOpen('cin')}
                onOpenKbis={() => setViewerOpen('kbis')}
              />
              <ColonneCentre
                data={data}
                editOffres={editOffres}
                editVente={editVente!}
                onVenteChange={(patch) => setEditVente((v) => (v ? { ...v, ...patch } : v))}
                selectedId={selectedPanierId}
                onSelect={setSelectedPanierId}
                onAnnulLigne={() => setAnnulLigneOpen(true)}
                onAskValider={() => setActionDialog('valider')}
                onAskAnnulVente={() => setActionDialog('annulVente')}
                onAskRenvoi={() => setActionDialog('renvoi')}
                verrouLoading={verrouLoading}
                onPrendreAppel={() => handlePrendreAppel(false)}
                onLacherAppel={handleLacherAppel}
                refAppelHistory={refAppelHistory}
              />
              <ColonneDroite
                data={data}
                offre={selectedOffre}
                onOffreChange={(patch) =>
                  selectedPanierId && patchOffre(selectedPanierId, patch)
                }
                onSaveStatutAuto={(newStatut) => {
                  if (selectedOffre) {
                    saveOffreAuto({ ...selectedOffre, statut_prod: newStatut })
                  }
                }}
                onAskAnnulLigne={() => setAnnulLigneOpen(true)}
                editVente={editVente!}
                onVenteChange={(patch) => setEditVente((v) => (v ? { ...v, ...patch } : v))}
                editAnomalie={editAnomalie!}
                onAnomalieChange={(patch) =>
                  setEditAnomalie((a) => (a ? { ...a, ...patch } : a))
                }
                lettreAvailable={!!docLettre.url}
                onOpenLettre={() => setViewerOpen('lettre')}
                onSaveVente={handleSaveVente}
                onSaveOffre={handleSaveOffre}
                savingVente={savingVente}
                savingOffre={savingOffre}
              />
            </div>
          )}
        </motion.div>

        {/* Viewer documents (CIN / KBIS / Lettre resil) */}
        <DocumentViewerModal
          open={viewerOpen !== null}
          title={viewerTitle}
          url={viewerDoc.url}
          kind={viewerDoc.kind}
          onClose={() => setViewerOpen(null)}
        />

        {/* Confirmation : un autre ope a deja le verrou (ou trace recente) */}
        <ConfirmDialog
          open={verrouConfirm !== null}
          title={
            verrouConfirm?.appel_en_cours
              ? `${verrouConfirm.ope_appel_nom} est en train de contacter ce client depuis ${verrouConfirm.duree_minutes} min ${verrouConfirm.duree_secondes}s.\nSouhaitez-vous vraiment reprendre l'appel ?`
              : `${verrouConfirm?.ope_appel_nom} a raccroché avec ce client le ${verrouConfirm?.date_h_appel || ''}.\nSouhaitez-vous vraiment recontacter ce client ?`
          }
          confirmLabel="Oui, prendre l'appel"
          confirmColor="green"
          loading={verrouLoading}
          onConfirm={() => handlePrendreAppel(true)}
          onCancel={() => setVerrouConfirm(null)}
        />

        {/* Popup annulation 1 ligne du panier (motifs) */}
        <AnnulLignePanierPopup
          open={annulLigneOpen}
          loading={actionLoading}
          onCancel={() => setAnnulLigneOpen(false)}
          onConfirm={(motifs, prec) => handleAnnulerLigne(motifs, prec)}
        />

        {/* Confirmation : Valider le panier */}
        <ConfirmDialog
          open={actionDialog === 'valider'}
          title="Voulez-vous vraiment valider le panier ?"
          confirmLabel="Valider le panier"
          confirmColor="green"
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionDialog(null)}
        />

        {/* Confirmation : Annuler toute la vente */}
        <ConfirmDialog
          open={actionDialog === 'annulVente'}
          title="Voulez-vous vraiment annuler le panier ?"
          confirmLabel="Annuler toute la vente"
          confirmColor="red"
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionDialog(null)}
        />

        {/* Confirmation : Renvoyer pour complement */}
        <ConfirmDialog
          open={actionDialog === 'renvoi'}
          title="Voulez-vous vraiment renvoyer le panier ?"
          confirmLabel="Renvoyer le panier pour complément"
          confirmColor="orange"
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionDialog(null)}
        />

        {/* Toast feedback save */}
        {toast && (
          <div
            className={`fixed bottom-4 right-4 z-[70] px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
              toast.kind === 'ok' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
            }`}
          >
            {toast.msg}
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}

// --- Colonne gauche : Client --------------------------------------------

function ColonneGauche({
  data,
  client,
  onClientChange,
  cinAvailable,
  kbisAvailable,
  onOpenCin,
  onOpenKbis,
}: {
  data: FicheData
  client: FicheClient
  onClientChange: (patch: Partial<FicheClient>) => void
  cinAvailable: boolean
  kbisAvailable: boolean
  onOpenCin: () => void
  onOpenKbis: () => void
}) {
  const c = client
  return (
    <div className="col-span-4 flex flex-col gap-4">
      {/* Bloc client */}
      <div className="bg-white rounded-lg border border-c-line p-4">
        <h3 className="text-sm font-bold text-c-ink mb-3">Information contrat et client</h3>

        <div className="space-y-2.5 text-xs">
          <Radios
            label="Civilité"
            value={c.civilite}
            options={[
              { v: 1, l: 'M.' },
              { v: 2, l: 'Mme' },
              { v: 3, l: 'Mlle' },
            ]}
            onChange={(v) => onClientChange({ civilite: v })}
          />
          <Field label="Nom" value={c.nom} onChange={(v) => onClientChange({ nom: v })} />
          <Field label="Nom Marital" value={c.nom_marital} onChange={(v) => onClientChange({ nom_marital: v })} />
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Field label="Prénom" value={c.prenom} onChange={(v) => onClientChange({ prenom: v })} />
            </div>
            <button
              onClick={onOpenCin}
              disabled={!cinAvailable}
              className="shrink-0 w-12 h-9 rounded border border-c-line hover:bg-c-brand-soft flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
              title={cinAvailable ? 'Voir la CIN' : 'Aucune CIN disponible'}
            >
              <CreditCard className="w-5 h-5 text-c-ink-soft" />
            </button>
          </div>
          <div className="text-[10px] text-c-ink-faint text-right -mt-1.5">
            {cinAvailable ? (
              <button onClick={onOpenCin} className="hover:underline">
                Voir la CIN SOS
              </button>
            ) : (
              <span className="italic">Pas de CIN trouvée</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Field
                  label="Né(e) le"
                  type="date"
                  value={c.date_naiss}
                  onChange={(v) => onClientChange({ date_naiss: v })}
                />
              </div>
              <CopyButton value={isoToFr(c.date_naiss)} title="Copier la date de naissance" />
            </div>
            <Field
              label="Dép"
              value={c.dep_naiss ? String(c.dep_naiss).padStart(2, '0') : ''}
              onChange={(v) => onClientChange({ dep_naiss: parseInt(v || '0', 10) || 0 })}
            />
          </div>
          <Radios
            label="Logement"
            value={c.type_logement}
            options={[
              { v: 1, l: 'Maison' },
              { v: 2, l: 'Appartement' },
            ]}
            onChange={(v) => onClientChange({ type_logement: v })}
          />
          <Field label="Adresse" value={c.adresse1} onChange={(v) => onClientChange({ adresse1: v })} />
          <Field label="Cplt" value={c.adresse2} onChange={(v) => onClientChange({ adresse2: v })} />
          <div className="grid grid-cols-3 gap-3">
            <Field label="CP" value={c.cp} onChange={(v) => onClientChange({ cp: v })} />
            <div className="col-span-2">
              <Field label="Ville" value={c.ville} onChange={(v) => onClientChange({ ville: v })} />
            </div>
          </div>
          <Field label="Email" type="email" value={c.email} onChange={(v) => onClientChange({ email: v })} />
          <div className="grid grid-cols-2 gap-3">
            {/* Mobile 1/2 : readonly (saves seulement via verrou ope - Phase 3) */}
            <Field label="Mobile 1" value={c.mobile1} muted={!data.is_my_call} />
            <Field label="Mobile 2 / Fixe" value={c.mobile2} muted={!data.is_my_call} />
          </div>

          {/* Consentements (toggles affichage seul en phase 1) */}
          <div className="pt-2 space-y-2">
            <Toggle
              label="Le client est d'accord pour être rappelé immédiatement par le Call"
              value={c.opt_rappel}
            />
            <Toggle
              label="Le client accepte que ses coordonnées soient transmises aux partenaires"
              value={c.opt_partenaire}
            />
          </div>

          {/* Bouton Part / Pro */}
          <div className="pt-2 flex bg-gray-900 text-white rounded-md p-0.5">
            <ProTab active={!c.client_pro} label="Client Part" />
            <ProTab active={c.client_pro} label="Client Pro" />
          </div>

          {/* Si client Pro : Raison Sociale + SIRET + bouton KBIS */}
          {c.client_pro && (
            <div className="pt-2 space-y-2.5">
              <Field label="Raison Sociale" value={c.client_rs} />
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <Field label="n° SIRET" value={c.client_siret} />
                </div>
                <button
                  onClick={onOpenKbis}
                  disabled={!kbisAvailable}
                  className="shrink-0 flex items-center gap-1.5 px-3 h-9 rounded border border-c-line hover:bg-c-brand-soft text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                  title={kbisAvailable ? 'Voir le KBIS' : 'Aucun KBIS disponible'}
                >
                  <FileText className="w-3.5 h-3.5 text-c-ink-soft" />
                  KBIS
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Colonne centre : Panier ---------------------------------------------

function ColonneCentre({
  data,
  editOffres,
  editVente,
  onVenteChange,
  selectedId,
  onSelect,
  onAnnulLigne,
  onAskValider,
  onAskAnnulVente,
  onAskRenvoi,
  verrouLoading,
  onPrendreAppel,
  onLacherAppel,
  refAppelHistory,
}: {
  data: FicheData
  editOffres: Record<string, FicheOffre>
  editVente: FicheVente
  onVenteChange: (patch: Partial<FicheVente>) => void
  selectedId: string
  onSelect: (id: string) => void
  onAnnulLigne: () => void
  onAskValider: () => void
  onAskAnnulVente: () => void
  onAskRenvoi: () => void
  verrouLoading: boolean
  onPrendreAppel: () => void
  onLacherAppel: () => void
  refAppelHistory: string[]
}) {
  const v = data.vendeur
  // Compteurs recalcules en live depuis editOffres (les statuts ont pu changer)
  const offresList = data.panier.map((p) => editOffres[p.id] || p)
  const nbValide = offresList.filter((o) => o.statut_prod === 1).length
  const nbAnnule = offresList.filter((o) => o.statut_prod === 2).length
  const nbTotal = offresList.length
  // Boutons WinDev :
  // - Valider : actif si nbValide > 0 ET nbValide+nbAnnule == nbTotal
  // - Annuler vente : actif si nbAnnule == nbTotal (et > 0)
  const canValider = nbValide > 0 && nbValide + nbAnnule === nbTotal
  const canAnnulerVente = nbTotal > 0 && nbAnnule === nbTotal
  const selectedOffre = selectedId ? offresList.find((o) => o.id === selectedId) : null
  const canAnnulerLigne = !!selectedOffre && selectedOffre.statut_prod !== 2
  return (
    <div className="col-span-4 flex flex-col gap-3">
      <div className="bg-white rounded-lg border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="bg-gray-50 border-b border-c-line text-xs font-semibold text-c-ink-soft grid grid-cols-[80px_1fr_60px_70px]">
          <div className="px-2 py-2">Type</div>
          <div className="px-2 py-2">Lib Offre</div>
          <div className="px-2 py-2 text-center">Opt TV / PS5</div>
          <div className="px-2 py-2 text-center">Portabilité</div>
        </div>
        <div className="overflow-y-auto flex-1">
          {offresList.length === 0 ? (
            <div className="p-4 text-center text-c-ink-faint italic text-xs">
              Aucune offre au panier
            </div>
          ) : (
            offresList.map((p) => {
              const isSel = p.id === selectedId
              return (
                <div
                  key={p.id}
                  onClick={() => onSelect(p.id)}
                  className={`grid grid-cols-[80px_1fr_60px_70px] text-xs border-b border-c-line-soft cursor-pointer transition-colors ${
                    isSel ? 'bg-c-brand-soft' : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="px-2 py-2 font-semibold">{p.type}</div>
                  <div className="px-2 py-2">{p.lib_offre}</div>
                  <div className="px-2 py-2 text-center">
                    {p.opt_tv ? <CheckCircle2 className="w-4 h-4 inline text-c-brand" /> : <Circle className="w-4 h-4 inline text-c-ink-faint/50" />}
                  </div>
                  <div className="px-2 py-2 text-center">
                    {p.portabilite ? <CheckCircle2 className="w-4 h-4 inline text-c-brand" /> : <Circle className="w-4 h-4 inline text-c-ink-faint/50" />}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Bloc vendeur (sous le panier) - encadre vert clair */}
      <div className="bg-green-50 rounded-lg border border-green-300 p-4">
        <h3 className="text-sm font-bold text-c-ink mb-3">Information Vendeur</h3>
        <div className="space-y-2.5 text-xs">
          <Field label="Nom" value={v.nom} />
          <Field label="Prénom" value={v.prenom} />
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Field label="Mobile" value={v.gsm} muted={!data.is_my_call} />
            </div>
            {data.is_my_call ? (
              <button
                onClick={onLacherAppel}
                disabled={verrouLoading}
                className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded border border-red-600 bg-red-600 text-white text-xs hover:brightness-110 disabled:opacity-60"
                title="Raccrocher / libérer le verrou"
              >
                {verrouLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <PhoneOff className="w-3.5 h-3.5" />
                )}
                Lâcher l'appel
              </button>
            ) : (
              <button
                onClick={onPrendreAppel}
                disabled={verrouLoading}
                className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded border border-green-600 bg-green-600 text-white text-xs hover:brightness-110 disabled:opacity-60"
                title="Démarrer l'appel (pose le verrou, démasque les mobiles, envoie un SMS au vendeur)"
              >
                {verrouLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Phone className="w-3.5 h-3.5" />
                )}
                Démarrer l'appel
              </button>
            )}
          </div>
          {v.lib_affectation && (
            <div className="text-[10px] text-c-ink-faint mt-1">{v.lib_affectation}</div>
          )}
        </div>
      </div>

      {/* Compteurs */}
      <div className="bg-white rounded-lg border border-c-line p-3 text-xs space-y-2">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="text-c-ink-soft">nb Prod validé(s) : </span>
            <span className="font-bold text-c-ink">{nbValide}</span>
          </div>
          <div>
            <span className="text-c-ink-soft">nb Prod annulé(s) : </span>
            <span className="font-bold text-c-ink">{nbAnnule}</span>
          </div>
        </div>
        <div className="grid grid-cols-[80px_1fr] gap-2 items-center">
          <label className="text-c-ink-soft">Réf Appel :</label>
          <input
            type="text"
            value={editVente.ref_appel}
            onChange={(e) => onVenteChange({ ref_appel: e.target.value })}
            list="cf-ref-appel-history"
            autoComplete="off"
            className="px-2 py-1 border border-c-line rounded text-xs bg-white focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none"
          />
          <datalist id="cf-ref-appel-history">
            {refAppelHistory.map((ref) => (
              <option key={ref} value={ref} />
            ))}
          </datalist>
        </div>
      </div>

      {/* Action sur la ligne selectionnee : "Annuler cette offre" */}
      {selectedOffre && (
        <button
          onClick={onAnnulLigne}
          disabled={!canAnnulerLigne}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded border border-red-300 text-red-600 text-xs font-medium hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Annuler uniquement la ligne sélectionnée (motifs)"
        >
          <Ban className="w-3.5 h-3.5" />
          {selectedOffre.statut_prod === 2
            ? 'Offre déjà annulée'
            : 'Annuler cette offre'}
        </button>
      )}

      {/* Boutons d'action panier */}
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <ActionButton
            label="Valider le panier"
            disabled={!canValider}
            variant="dark"
            onClick={onAskValider}
          />
          <ActionButton
            label="Annuler toute la vente"
            disabled={!canAnnulerVente}
            variant="dark"
            onClick={onAskAnnulVente}
          />
        </div>
        <ActionButton
          label="Renvoyer le panier pour complément"
          variant="orange"
          full
          onClick={onAskRenvoi}
        />
      </div>
    </div>
  )
}

// --- Colonne droite : Détail offre + Vente -------------------------------

function ColonneDroite({
  data,
  offre,
  onOffreChange,
  onSaveStatutAuto,
  onAskAnnulLigne,
  editVente,
  onVenteChange,
  editAnomalie,
  onAnomalieChange,
  lettreAvailable,
  onOpenLettre,
  onSaveVente,
  onSaveOffre,
  savingVente,
  savingOffre,
}: {
  data: FicheData
  offre: FicheOffre | null
  onOffreChange: (patch: Partial<FicheOffre>) => void
  onSaveStatutAuto: (newStatut: number) => void
  onAskAnnulLigne: () => void
  editVente: FicheVente
  onVenteChange: (patch: Partial<FicheVente>) => void
  editAnomalie: FicheAnomalie
  onAnomalieChange: (patch: Partial<FicheAnomalie>) => void
  lettreAvailable: boolean
  onOpenLettre: () => void
  onSaveVente: () => void
  onSaveOffre: () => void
  savingVente: boolean
  savingOffre: boolean
}) {
  return (
    <div className="col-span-4 flex flex-col gap-4">
      {/* Bloc anomalie mobile en HAUT (visible uniquement si AnomalieMobile=1) */}
      {editAnomalie.active && (
        <div className="bg-red-50 rounded-lg border border-red-200 p-4">
          <h3 className="text-sm font-bold text-red-700 mb-2">Vente mobile en différé</h3>
          <div className="space-y-2 text-xs">
            <SelectField
              label="Motif"
              value={editAnomalie.id_type}
              options={[
                { v: 0, l: '— Choisir un motif —' },
                ...data.motifs_anomalie.map((m) => ({ v: m.id, l: m.label })),
              ]}
              onChange={(v) => onAnomalieChange({ id_type: v })}
            />
            <Field
              label="Si Autre, Précisions"
              value={editAnomalie.info_cplt}
              multi
              onChange={(v) => onAnomalieChange({ info_cplt: v })}
            />
            <div className="font-semibold text-red-700 mt-2">Demande de dégroupage Panier</div>
          </div>
        </div>
      )}

      {/* Détail offre sélectionnée */}
      <div className="bg-white rounded-lg border border-c-line p-4">
        {offre ? (
          <>
            <div className="flex items-center justify-between mb-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={offre.portabilite}
                  onChange={(e) => onOffreChange({ portabilite: e.target.checked })}
                  className="accent-c-brand"
                />
                <span className="text-sm font-semibold text-c-ink">Portabilité</span>
              </label>
              {offre.type === 'FIBRE' && !offre.portabilite && (
                <button
                  onClick={onOpenLettre}
                  disabled={!lettreAvailable}
                  className="px-3 py-1.5 rounded bg-orange-500 text-white text-xs font-semibold hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
                  title={lettreAvailable ? 'Ouvrir la Lettre de résiliation' : 'Aucune Lettre de résiliation trouvée'}
                >
                  Lettre de résil
                </button>
              )}
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <Field
                  label="Num à conserver"
                  value={offre.num_portabilite}
                  onChange={(v) => onOffreChange({ num_portabilite: v })}
                />
                <Field
                  label="Code RIO"
                  value={offre.num_rio}
                  onChange={(v) => onOffreChange({ num_rio: v })}
                />
              </div>
              {offre.type === 'FIBRE' && (
                <Field
                  label="Prise Optique"
                  value={offre.num_prise_optique}
                  onChange={(v) => onOffreChange({ num_prise_optique: v })}
                />
              )}
              <div className="grid grid-cols-2 gap-3">
                <SelectField
                  label="Statut Vente"
                  value={offre.statut_prod}
                  options={data.statuts_vente.map((s) => ({ v: s.id, l: s.label }))}
                  onChange={(v) => {
                    // Cas WinDev : statut = 2 (Annulee) -> ouvre la popup motif
                    // d'annulation au lieu de sauver directement. Le statut sera
                    // bascule par l'action "Annul ligne panier" complete (motifs +
                    // precisions). Le SelectField revient visuellement a l'ancienne
                    // valeur car on ne modifie pas offre.statut_prod.
                    if (v === 2) {
                      onAskAnnulLigne()
                      return
                    }
                    onOffreChange({ statut_prod: v })
                    onSaveStatutAuto(v)
                  }}
                />
                <SelectField
                  label="Type Vente"
                  value={offre.type_vente}
                  options={[
                    { v: 0, l: 'Non défini' },
                    { v: 1, l: 'Conquête' },
                    { v: 2, l: 'Mig Mobile / Mig ADSL' },
                  ]}
                  onChange={(v) => onOffreChange({ type_vente: v })}
                />
              </div>
              <Field
                label="Options Choisies"
                value={offre.opt_choisies}
                multi
                rows={12}
                onChange={(v) => onOffreChange({ opt_choisies: v })}
              />
            </div>

            <button
              onClick={onSaveOffre}
              disabled={savingOffre}
              className="mt-3 w-full py-2 rounded bg-gray-900 text-white text-xs font-semibold hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {savingOffre && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Enregistrer les modifs Offre
            </button>
          </>
        ) : (
          <div className="text-xs text-c-ink-faint italic py-8 text-center">
            Sélectionne une offre du panier pour voir son détail
          </div>
        )}
      </div>

      {/* Bloc vente : Intervention vendeur / Mobile proposé / Info vente */}
      <div className="bg-white rounded-lg border border-c-line p-4">
        <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
          <div>
            <div className="font-semibold text-c-ink mb-1">Intervention du vendeur :</div>
            <div className="flex gap-3">
              <Radio
                active={editVente.intervention_vendeur}
                label="Oui"
                onClick={() => onVenteChange({ intervention_vendeur: true })}
              />
              <Radio
                active={!editVente.intervention_vendeur}
                label="Non"
                onClick={() => onVenteChange({ intervention_vendeur: false })}
              />
            </div>
          </div>
          <div>
            <div className="font-semibold text-c-ink mb-1">Le vendeur a proposé un mobile :</div>
            <div className="flex gap-3">
              <Radio
                active={editVente.mobile_propose_vendeur}
                label="Oui"
                onClick={() => onVenteChange({ mobile_propose_vendeur: true })}
              />
              <Radio
                active={!editVente.mobile_propose_vendeur}
                label="Non"
                onClick={() => onVenteChange({ mobile_propose_vendeur: false })}
              />
            </div>
          </div>
        </div>

        <div className="space-y-1 text-xs">
          <label className="font-semibold text-c-ink">Info Vente</label>
          <textarea
            value={editVente.info_vente}
            onChange={(e) => onVenteChange({ info_vente: e.target.value })}
            rows={3}
            className="w-full px-2 py-1.5 border border-c-line rounded text-xs bg-white focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none resize-none"
          />
        </div>

        <button
          onClick={onSaveVente}
          disabled={savingVente}
          className="mt-3 w-full py-2 rounded bg-gray-900 text-white text-xs font-semibold hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {savingVente && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          Enregistrer les infos client et vente
        </button>
      </div>
    </div>
  )
}

// --- Helpers UI ----------------------------------------------------------

function Field({
  label,
  value,
  multi,
  rows = 2,
  muted,
  onChange,
  type = 'text',
}: {
  label: string
  value: string | number
  multi?: boolean
  rows?: number
  muted?: boolean
  onChange?: (v: string) => void
  type?: 'text' | 'date' | 'email'
}) {
  const readOnly = !onChange
  const baseCls = `w-full px-2 py-1 border border-c-line rounded text-xs ${readOnly ? 'bg-gray-50' : 'bg-white focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none'} ${muted ? 'text-c-ink-faint italic' : ''}`
  return (
    <div className="space-y-0.5">
      <label className="block text-c-ink-soft">{label}</label>
      {multi ? (
        <textarea
          value={String(value ?? '')}
          readOnly={readOnly}
          onChange={onChange ? (e) => onChange(e.target.value) : undefined}
          rows={rows}
          className={`${baseCls} resize-none`}
        />
      ) : (
        <input
          type={type}
          value={String(value ?? '')}
          readOnly={readOnly}
          onChange={onChange ? (e) => onChange(e.target.value) : undefined}
          className={baseCls}
        />
      )}
    </div>
  )
}

function Radios({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: number
  options: { v: number; l: string }[]
  onChange?: (v: number) => void
}) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-c-ink-soft w-20">{label} :</span>
      {options.map((opt) => (
        <label key={opt.v} className={`flex items-center gap-1 ${onChange ? 'cursor-pointer' : 'cursor-default'}`}>
          <input
            type="radio"
            checked={value === opt.v}
            readOnly={!onChange}
            onChange={onChange ? () => onChange(opt.v) : undefined}
            className="accent-c-brand"
          />
          <span className="text-c-ink">{opt.l}</span>
        </label>
      ))}
    </div>
  )
}

function Toggle({
  label,
  value,
  onChange,
}: {
  label: string
  value: boolean
  onChange?: (v: boolean) => void
}) {
  return (
    <div
      className={`flex items-center gap-2 text-c-ink ${onChange ? 'cursor-pointer select-none' : ''}`}
      onClick={onChange ? () => onChange(!value) : undefined}
    >
      <div
        className={`w-10 h-5 rounded-full p-0.5 flex items-center transition-colors ${
          value ? 'bg-green-500 justify-end' : 'bg-gray-300 justify-start'
        }`}
      >
        <div className="w-4 h-4 bg-white rounded-full shadow" />
      </div>
      <span className="flex-1">{label}</span>
    </div>
  )
}

function ProTab({ active, label }: { active: boolean; label: string }) {
  return (
    <div
      className={`flex-1 text-center text-xs font-semibold py-1.5 rounded ${
        active ? 'bg-white text-gray-900' : 'text-gray-300'
      }`}
    >
      {label}
    </div>
  )
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: number
  options: { v: number; l: string }[]
  onChange?: (v: number) => void
}) {
  return (
    <div className="space-y-0.5">
      <label className="block text-c-ink-soft">{label}</label>
      <select
        value={value}
        disabled={!onChange}
        onChange={onChange ? (e) => onChange(Number(e.target.value)) : undefined}
        className={`w-full px-2 py-1 border border-c-line rounded text-xs ${onChange ? 'bg-white focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none' : 'bg-gray-50 cursor-not-allowed'}`}
      >
        {options.map((opt) => (
          <option key={opt.v} value={opt.v}>
            {opt.l}
          </option>
        ))}
      </select>
    </div>
  )
}

function ActionButton({
  label,
  disabled,
  variant,
  full,
  onClick,
}: {
  label: string
  disabled?: boolean
  variant: 'dark' | 'orange'
  full?: boolean
  onClick?: () => void
}) {
  const cls =
    variant === 'orange'
      ? 'bg-orange-500 text-white'
      : 'bg-gray-900 text-white'
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${cls} ${full ? 'w-full' : ''} py-2 px-3 rounded text-xs font-semibold transition-opacity ${
        disabled ? 'opacity-50 cursor-not-allowed' : 'hover:brightness-110'
      }`}
    >
      {label}
    </button>
  )
}

function Radio({
  active,
  label,
  onClick,
}: {
  active: boolean
  label: string
  onClick?: () => void
}) {
  return (
    <label className={`flex items-center gap-1 ${onClick ? 'cursor-pointer' : 'cursor-default'}`}>
      <input
        type="radio"
        checked={active}
        readOnly={!onClick}
        onChange={onClick ? () => onClick() : undefined}
        className="accent-c-brand"
      />
      <span>{label}</span>
    </label>
  )
}
