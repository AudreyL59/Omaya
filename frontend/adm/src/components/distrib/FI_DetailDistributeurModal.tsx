/**
 * FI_DetailDistributeur - fenetre interne detail d'un distributeur.
 *
 * 4 blocs (cf. WinDev) :
 *   1. Docs uniques (rappel_annuel=0) + Combo type + Btn '+' ajout
 *   2. Docs annuels (rappel_annuel>0) filtres par annee
 *   3. Suivi Facturation (tickets type 28 + boutons ouvrir/recharger)
 *   4. Suivi ADM (memos gerant)
 *
 * Boutons metier :
 *   - Ticket de reclamation (type 31) -> haut ou bas
 *   - Voir le ticket (redirige vers page tickets)
 *   - Ticket Facturation (upload PDF + montant)
 *   - Ouvrir la facture / preuve virement
 *   - Recharger la facture sur le Ticket
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  X, Loader2, Ticket, Eye, Plus, RefreshCw,
  Link2, Link2Off, Trash2, Download, Bell, BellOff,
  MessageSquare, Send,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

interface Bootstrap {
  id_ste: string
  raison_sociale: string
  siret: string
  num_orias: string
  id_gerant: string
  nom_gerant: string
  date_creation: string
  annee_selectionnee: number
  annees_disponibles: number[]
}

interface DocRow {
  id_doc_distrib: string
  id_type_doc_distributeur: string
  lib_doc: string
  date_prevue: string
  date_depot: string
  nom_fichier: string
  rappel_annuel: number
  obligatoire_dem: boolean
  afaire_signer: boolean
  id_doc_courtage: string
  id_tk: string
  tk_cloture: boolean
}

interface FacturationRow {
  id_tk_liste: string
  date_crea: string
  prenom_crea: string
  id_gerant: string
  fic_facture: string
  fic_preuve_virement: string
  date_virement: string
  montant: number
  cloturee: boolean
}

interface TypeDocUnique {
  id_type_doc_distributeur: string
  lib_doc: string
  obligatoire_dem: boolean
  afaire_signer: boolean
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10
    ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

// Initiales : "LOUDIEUX Audrey" -> "LA", "DOINEAU MEHDI" -> "DM"
const getInitials = (name: string): string => {
  if (!name) return '?'
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 1) return parts[0][0].toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// Couleur deterministe par nom (palette OMAYA-friendly, saturee mais douce)
const _AVATAR_COLORS = [
  '#8B7355', // marron OMAYA
  '#17494E', // teal
  '#B25E43', // terracotta
  '#4E7C59', // vert olive
  '#7A5D82', // prune
  '#C77D3E', // ambre
  '#3D6B8C', // bleu ardoise
  '#8E4162', // grenat
]
const colorFromName = (name: string): string => {
  if (!name) return '#8B7355'
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  }
  return _AVATAR_COLORS[hash % _AVATAR_COLORS.length]
}

export default function FI_DetailDistributeurModal({
  idSte,
  onClose,
}: {
  idSte: string
  onClose: () => void
}) {
  const [boot, setBoot] = useState<Bootstrap | null>(null)
  const [docsUnique, setDocsUnique] = useState<DocRow[]>([])
  const [docsAnnuel, setDocsAnnuel] = useState<DocRow[]>([])
  const [facturations, setFacturations] = useState<FacturationRow[]>([])
  const [types, setTypes] = useState<TypeDocUnique[]>([])
  const [annee, setAnnee] = useState<number>(new Date().getFullYear())
  const [selectedType, setSelectedType] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<string>('')
  const [selDocUnique, setSelDocUnique] = useState<DocRow | null>(null)
  const [selDocAnnuel, setSelDocAnnuel] = useState<DocRow | null>(null)
  const rechargeInputRef = useRef<HTMLInputElement>(null)
  const [rechargeTkId, setRechargeTkId] = useState<string>('')
  const factureInputRef = useRef<HTMLInputElement>(null)
  // Overlay Suivi ADM
  const [suiviOpen, setSuiviOpen] = useState(false)
  const [suiviMemos, setSuiviMemos] = useState<
    Array<{ id: string; depose_le: string; par: string; message: string }>
  >([])
  const [suiviLoading, setSuiviLoading] = useState(false)
  const [newMemo, setNewMemo] = useState('')

  const _fetch = (u: string, opts: RequestInit = {}) =>
    fetch(u, {
      ...opts,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        ...(opts.headers || {}),
      },
    })

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [b, du, da, fa, ty] = await Promise.all([
        _fetch(`${API_BASE}/distributeurs/${idSte}`).then((r) =>
          r.ok ? r.json() : Promise.reject(r.status),
        ),
        _fetch(`${API_BASE}/distributeurs/${idSte}/docs-unique`).then((r) =>
          r.ok ? r.json() : { items: [] },
        ),
        _fetch(
          `${API_BASE}/distributeurs/${idSte}/docs-annuel?annee=${annee}`,
        ).then((r) => (r.ok ? r.json() : { items: [] })),
        _fetch(`${API_BASE}/distributeurs/${idSte}/facturations`).then(
          (r) => (r.ok ? r.json() : { items: [] }),
        ),
        _fetch(`${API_BASE}/distributeurs/refs/types-doc-unique`).then(
          (r) => (r.ok ? r.json() : { items: [] }),
        ),
      ])
      setBoot(b)
      setDocsUnique(du.items || [])
      setDocsAnnuel(da.items || [])
      setFacturations(fa.items || [])
      setTypes(ty.items || [])
      // Init combo annee au bootstrap
      if (b?.annee_selectionnee && annee === new Date().getFullYear()) {
        setAnnee(b.annee_selectionnee)
      }
    } catch (e) {
      showToast(`Erreur chargement : ${e}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSte, annee])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  // Verif automatique a l'ouverture (cf. WinDev Code Init)
  useEffect(() => {
    if (!boot) return
    // Appelle les 2 verif au chargement pour auto-creer les manquants
    void (async () => {
      await _fetch(`${API_BASE}/distributeurs/${idSte}/docs-unique/verif`, {
        method: 'POST',
      })
      await _fetch(
        `${API_BASE}/distributeurs/${idSte}/docs-annuel/verif?annee=${annee}`,
        { method: 'POST' },
      )
      // Reload apres verif
      const [du, da] = await Promise.all([
        _fetch(`${API_BASE}/distributeurs/${idSte}/docs-unique`).then((r) =>
          r.ok ? r.json() : { items: [] },
        ),
        _fetch(
          `${API_BASE}/distributeurs/${idSte}/docs-annuel?annee=${annee}`,
        ).then((r) => (r.ok ? r.json() : { items: [] })),
      ])
      setDocsUnique(du.items || [])
      setDocsAnnuel(da.items || [])
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boot?.id_ste, annee])

  // --- Handlers ------------------------------------------------------

  const addDocUnique = async () => {
    if (!selectedType) {
      showToast('Choisis un type de doc', 'info')
      return
    }
    setAction('add')
    try {
      const r = await _fetch(
        `${API_BASE}/distributeurs/${idSte}/docs-unique`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id_type_doc_distributeur: Number(selectedType),
          }),
        },
      )
      const d = await r.json()
      if (d.ok) {
        showToast('Doc ajouté', 'success')
        setSelectedType('')
        void loadAll()
      } else {
        showToast(d.error || 'Erreur', 'error')
      }
    } finally {
      setAction('')
    }
  }

  const createTicketReclam = async (doc: DocRow) => {
    if (!boot?.id_gerant) {
      showToast('Pas de gérant associé', 'error')
      return
    }
    const ok = await showConfirm({
      title: 'Créer un ticket',
      message: 'Vous êtes sur le point de créer un ticket. Voulez-vous continuer ?',
    })
    if (!ok) return
    setAction(`reclam-${doc.id_doc_distrib}`)
    try {
      const r = await _fetch(
        `${API_BASE}/distributeurs/${idSte}/tickets/reclam`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id_doc_distrib: Number(doc.id_doc_distrib),
            id_gerant: Number(boot.id_gerant),
          }),
        },
      )
      const d = await r.json()
      if (!d.ok) {
        showToast(d.error || 'Erreur', 'error')
        return
      }
      if (d.afaire_signer) {
        showToast(
          'Ce document nécessite une redirection vers l\'écran Contrat de Courtage.',
          'info',
        )
      } else {
        // cf. WinDev : SMS envoye au gerant + histo cote backend
        const smsMsg = d.sms_statut
          ? ` — SMS : ${d.sms_statut}`
          : ''
        showToast(`Ticket créé${smsMsg}`, 'success')
      }
      void loadAll()
    } finally {
      setAction('')
    }
  }

  const createTicketFact = async () => {
    if (!boot?.id_gerant) {
      showToast('Pas de gérant associé', 'error')
      return
    }
    factureInputRef.current?.click()
  }

  const onFactureSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !boot) return
    const montantStr = window.prompt('Montant de la facture (€) :')
    if (!montantStr) return
    const montant = Number(montantStr.replace(',', '.'))
    if (isNaN(montant) || montant <= 0) {
      showToast('Montant invalide', 'error')
      return
    }
    setAction('ticket-fact')
    try {
      const fd = new FormData()
      fd.append('id_gerant', boot.id_gerant)
      fd.append('montant', String(montant))
      fd.append('facture', file)
      const r = await _fetch(
        `${API_BASE}/distributeurs/${idSte}/tickets/facturation`,
        { method: 'POST', body: fd },
      )
      const d = await r.json()
      if (d.ok) {
        showToast('Ticket facturation créé', 'success')
        void loadAll()
      } else {
        showToast(d.error || 'Erreur', 'error')
      }
    } finally {
      setAction('')
    }
  }

  const onRechargeSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !rechargeTkId) return
    setAction(`recharge-${rechargeTkId}`)
    try {
      const fd = new FormData()
      fd.append('facture', file)
      const r = await _fetch(
        `${API_BASE}/distributeurs/facturation/${rechargeTkId}/recharger`,
        { method: 'POST', body: fd },
      )
      const d = await r.json()
      if (d.ok) {
        showToast('Facture rechargée', 'success')
        void loadAll()
      } else {
        showToast(d.error || 'Erreur', 'error')
      }
    } finally {
      setAction('')
      setRechargeTkId('')
    }
  }

  // --- Render helpers ------------------------------------------------

  // --- Handlers Suivi ADM (overlay memos) ----------------------------

  const openSuiviAdm = async () => {
    setSuiviOpen(true)
    setSuiviLoading(true)
    setNewMemo('')
    try {
      const r = await _fetch(
        `${API_BASE}/distributeurs/${idSte}/suivi-adm`,
      )
      const d = await r.json()
      setSuiviMemos(d.items || [])
    } catch {
      setSuiviMemos([])
    } finally {
      setSuiviLoading(false)
    }
  }

  const envoyerMemo = async () => {
    const msg = newMemo.trim()
    if (!msg) return
    setAction('memo')
    try {
      const r = await _fetch(
        `${API_BASE}/distributeurs/${idSte}/suivi-adm`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg }),
        },
      )
      const d = await r.json()
      if (d.ok) {
        showToast(
          d.mail_statut === 'envoye'
            ? 'Mémo enregistré + mail envoyé'
            : 'Mémo enregistré',
          'success',
        )
        setNewMemo('')
        // Recharge la liste
        const r2 = await _fetch(
          `${API_BASE}/distributeurs/${idSte}/suivi-adm`,
        )
        const d2 = await r2.json()
        setSuiviMemos(d2.items || [])
      } else {
        showToast(d.error || 'Erreur', 'error')
      }
    } finally {
      setAction('')
    }
  }

  // --- Handlers boutons doc (associer/desassocier/supprimer/DL/rappel) ---
  const docAssocierInputRef = useRef<HTMLInputElement>(null)
  const [docActionId, setDocActionId] = useState<string>('')

  const associerDoc = (d: DocRow) => {
    setDocActionId(d.id_doc_distrib)
    docAssocierInputRef.current?.click()
  }

  const onAssocierFileSelected = async (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !docActionId) {
      setDocActionId('')
      return
    }
    setAction(`assoc-${docActionId}`)
    try {
      const fd = new FormData()
      fd.append('fichier', file)
      const r = await _fetch(
        `${API_BASE}/distributeurs/docs/${docActionId}/associer-pc`,
        { method: 'POST', body: fd },
      )
      const d = await r.json()
      if (d.ok) {
        showToast('Document associé', 'success')
        void loadAll()
      } else {
        showToast(d.error || 'Erreur', 'error')
      }
    } finally {
      setAction('')
      setDocActionId('')
    }
  }

  const desassocierDoc = async (d: DocRow) => {
    const ok = await showConfirm({
      title: 'Dissocier le document',
      message: 'Vous êtes sur le point de dissocier ce document. Voulez-vous continuer ?',
      variant: 'danger',
    })
    if (!ok) return
    setAction(`desassoc-${d.id_doc_distrib}`)
    try {
      const r = await _fetch(
        `${API_BASE}/distributeurs/docs/${d.id_doc_distrib}/desassocier`,
        { method: 'POST' },
      )
      const j = await r.json()
      if (j.ok) {
        showToast('Document dissocié', 'success')
        void loadAll()
      } else {
        showToast(j.error || 'Erreur', 'error')
      }
    } finally {
      setAction('')
    }
  }

  const supprimerDoc = async (d: DocRow) => {
    const ok = await showConfirm({
      title: 'Supprimer cet enregistrement',
      message:
        'Le document ne sera pas supprimé de l\'espace salarié. Voulez-vous continuer ?',
      variant: 'danger',
    })
    if (!ok) return
    setAction(`del-${d.id_doc_distrib}`)
    try {
      const r = await _fetch(
        `${API_BASE}/distributeurs/docs/${d.id_doc_distrib}`,
        { method: 'DELETE' },
      )
      const j = await r.json()
      if (j.ok) {
        showToast('Document supprimé', 'success')
        void loadAll()
      } else {
        showToast(j.error || 'Erreur', 'error')
      }
    } finally {
      setAction('')
    }
  }

  const telechargerDoc = (d: DocRow) => {
    if (!d.nom_fichier || d.nom_fichier === 'PAS RAPPEL') return
    const url = `${API_BASE}/distributeurs/docs/${d.id_doc_distrib}/telecharger`
    // Ouvre dans un nouvel onglet avec le token en param URL (le
    // navigateur ne peut pas ajouter le header Authorization sur un
    // window.open). Fallback : fetch + blob URL.
    void (async () => {
      setAction(`dl-${d.id_doc_distrib}`)
      try {
        const r = await _fetch(url)
        if (!r.ok) {
          showToast(`Téléchargement KO : ${r.status}`, 'error')
          return
        }
        const blob = await r.blob()
        const objUrl = URL.createObjectURL(blob)
        window.open(objUrl, '_blank')
        setTimeout(() => URL.revokeObjectURL(objUrl), 30_000)
      } finally {
        setAction('')
      }
    })()
  }

  const toggleRappelDoc = async (d: DocRow) => {
    if (d.nom_fichier && d.nom_fichier !== 'PAS RAPPEL') {
      showToast('Document déjà fourni : pas de bascule.', 'info')
      return
    }
    const label = d.nom_fichier === 'PAS RAPPEL'
      ? 'Réactiver le rappel'
      : 'Désactiver le rappel'
    const ok = await showConfirm({
      title: label,
      message: 'Voulez-vous continuer ?',
    })
    if (!ok) return
    setAction(`rappel-${d.id_doc_distrib}`)
    try {
      const r = await _fetch(
        `${API_BASE}/distributeurs/docs/${d.id_doc_distrib}/toggle-rappel`,
        { method: 'POST' },
      )
      const j = await r.json()
      if (j.ok) {
        showToast('Rappel mis à jour', 'success')
        void loadAll()
      } else {
        showToast(j.error || 'Erreur', 'error')
      }
    } finally {
      setAction('')
    }
  }

  // --- renderDocRow --------------------------------------------------

  const renderDocRow = (
    d: DocRow, selected: DocRow | null,
    setSelected: (d: DocRow | null) => void,
  ) => {
    const isEmpty = !d.nom_fichier
    const isNoRappel = d.nom_fichier === 'PAS RAPPEL'
    const bg = isEmpty && !isNoRappel
      ? 'bg-[#FED2D2]'
      : isNoRappel
        ? 'bg-[#E3E3E3] line-through'
        : ''
    const hasFile = !!d.nom_fichier && d.nom_fichier !== 'PAS RAPPEL'
    const busy = action.endsWith(`-${d.id_doc_distrib}`)
    return (
      <tr
        key={d.id_doc_distrib}
        onClick={() => setSelected(d)}
        className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${bg} ${
          selected?.id_doc_distrib === d.id_doc_distrib ? 'ring-2 ring-[#8B7355]' : ''
        }`}
      >
        <td className="py-2 px-2">{d.lib_doc}</td>
        <td className="py-2 px-2 text-xs">
          {d.nom_fichier || <span className="text-red-600 italic">Manquant</span>}
        </td>
        <td className="py-2 px-2 text-xs">{shortDate(d.date_prevue)}</td>
        <td className="py-2 px-2 text-xs">{shortDate(d.date_depot)}</td>
        <td className="py-2 px-2 text-center">
          {d.obligatoire_dem && <span className="text-[#059669]">✓</span>}
        </td>
        <td
          className="py-1 px-1"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex gap-0.5 justify-end">
            <button
              onClick={() => associerDoc(d)}
              disabled={busy || hasFile}
              className="p-1 rounded hover:bg-[#DEF7EC] disabled:opacity-30 disabled:cursor-not-allowed"
              title="Associer un fichier"
            >
              <Link2 className="w-3.5 h-3.5 text-[#059669]" />
            </button>
            <button
              onClick={() => desassocierDoc(d)}
              disabled={busy || !hasFile}
              className="p-1 rounded hover:bg-[#FDE2E2] disabled:opacity-30 disabled:cursor-not-allowed"
              title="Dissocier le fichier"
            >
              <Link2Off className="w-3.5 h-3.5 text-[#DC2626]" />
            </button>
            <button
              onClick={() => supprimerDoc(d)}
              disabled={busy}
              className="p-1 rounded hover:bg-[#FDE2E2] disabled:opacity-30"
              title="Supprimer l'enregistrement"
            >
              <Trash2 className="w-3.5 h-3.5 text-[#8B7355]" />
            </button>
            <button
              onClick={() => telechargerDoc(d)}
              disabled={busy || !hasFile}
              className="p-1 rounded hover:bg-[#ECF1F2] disabled:opacity-30 disabled:cursor-not-allowed"
              title="Télécharger le fichier"
            >
              <Download className="w-3.5 h-3.5 text-[#8B7355]" />
            </button>
            <button
              onClick={() => toggleRappelDoc(d)}
              disabled={busy || hasFile}
              className="p-1 rounded hover:bg-[#ECF1F2] disabled:opacity-30 disabled:cursor-not-allowed"
              title={
                isNoRappel
                  ? 'Réactiver le rappel'
                  : 'Désactiver le rappel'
              }
            >
              {isNoRappel
                ? <BellOff className="w-3.5 h-3.5 text-[#8B7355]" />
                : <Bell className="w-3.5 h-3.5 text-[#8B7355]" />}
            </button>
          </div>
        </td>
      </tr>
    )
  }

  const canReclam = (sel: DocRow | null): boolean =>
    !!sel && !sel.id_tk
  const canVoirTk = (sel: DocRow | null): boolean =>
    !!sel && !!sel.id_tk && !sel.tk_cloture

  // --- UI ------------------------------------------------------------

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-[#F5F5F0] rounded-lg shadow-xl w-[95vw] max-w-[1600px] max-h-[95vh] overflow-y-auto">
        <div className="sticky top-0 bg-[#F5F5F0] border-b border-[#E5E0D5] px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-[#8B7355]">
              {boot?.raison_sociale || 'Chargement...'}
            </h2>
            {boot && (
              <p className="text-xs text-gray-600 mt-1">
                SIRET {boot.siret} · Orias {boot.num_orias} · Gérant{' '}
                {boot.nom_gerant || (
                  <span className="text-red-700">non associé</span>
                )}{' '}
                · Créée le {shortDate(boot.date_creation)}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={openSuiviAdm}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm bg-white border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]"
              title="Suivi ADM (mémos)"
            >
              <MessageSquare className="w-4 h-4" />
              Suivi ADM
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded hover:bg-white/50"
              title="Fermer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {loading || !boot ? (
          <div className="flex items-center justify-center p-16">
            <Loader2 className="w-8 h-8 animate-spin text-[#8B7355]" />
          </div>
        ) : (
          <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* --- Bloc 1 : Docs uniques ------------------------- */}
            <div className="bg-white rounded shadow p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-[#8B7355]">Docs uniques</h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => selDocUnique && createTicketReclam(selDocUnique)}
                    disabled={!canReclam(selDocUnique) || !!action}
                    className="text-xs px-2 py-1 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
                    title="Créer un ticket de réclamation"
                  >
                    <Ticket className="w-3 h-3 inline mr-1" />
                    Ticket de réclam
                  </button>
                  <Link
                    to={selDocUnique?.id_tk ? `/tickets/${selDocUnique.id_tk}` : '#'}
                    onClick={(e) => {
                      if (!canVoirTk(selDocUnique)) e.preventDefault()
                    }}
                    className={`text-xs px-2 py-1 rounded border border-[#8B7355] text-[#8B7355] ${
                      !canVoirTk(selDocUnique) ? 'opacity-40 cursor-not-allowed' : 'hover:bg-[#ECF1F2]'
                    }`}
                    title="Voir le ticket"
                  >
                    <Eye className="w-3 h-3 inline mr-1" />
                    Voir le ticket
                  </Link>
                </div>
              </div>
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-white">
                    <tr className="text-left text-xs text-[#8B7355] border-b border-[#E5E0D5]">
                      <th className="py-1 px-2">Type Doc</th>
                      <th className="py-1 px-2">Nom Fichier</th>
                      <th className="py-1 px-2">Prévue</th>
                      <th className="py-1 px-2">Dépôt</th>
                      <th className="py-1 px-2 text-center">Obl. Dém.</th>
                      <th className="py-1 px-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docsUnique.map((d) =>
                      renderDocRow(d, selDocUnique, setSelDocUnique),
                    )}
                    {docsUnique.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-4 text-center text-gray-400">
                          Aucun doc unique.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {/* Btn '+' ajout doc unique */}
              <div className="flex items-center gap-2 mt-3">
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="flex-1 text-sm border border-[#E5E0D5] rounded px-2 py-1"
                >
                  <option value="">— Ajouter un doc unique —</option>
                  {types.map((t) => (
                    <option
                      key={t.id_type_doc_distributeur}
                      value={t.id_type_doc_distributeur}
                    >
                      {t.lib_doc}
                    </option>
                  ))}
                </select>
                <button
                  onClick={addDocUnique}
                  disabled={!selectedType || action === 'add'}
                  className="p-1.5 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
                  title="Ajouter"
                >
                  {action === 'add' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Plus className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* --- Bloc 2 : Docs annuels ------------------------- */}
            <div className="bg-white rounded shadow p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-[#8B7355]">
                    Docs avec rappels
                  </h3>
                  <select
                    value={annee}
                    onChange={(e) => setAnnee(Number(e.target.value))}
                    className="text-sm border border-[#E5E0D5] rounded px-2 py-1"
                  >
                    {boot.annees_disponibles.map((a) => (
                      <option key={a} value={a}>
                        {a}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => selDocAnnuel && createTicketReclam(selDocAnnuel)}
                    disabled={!canReclam(selDocAnnuel) || !!action}
                    className="text-xs px-2 py-1 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
                  >
                    <Ticket className="w-3 h-3 inline mr-1" />
                    Ticket de réclam
                  </button>
                  <Link
                    to={selDocAnnuel?.id_tk ? `/tickets/${selDocAnnuel.id_tk}` : '#'}
                    onClick={(e) => {
                      if (!canVoirTk(selDocAnnuel)) e.preventDefault()
                    }}
                    className={`text-xs px-2 py-1 rounded border border-[#8B7355] text-[#8B7355] ${
                      !canVoirTk(selDocAnnuel) ? 'opacity-40 cursor-not-allowed' : 'hover:bg-[#ECF1F2]'
                    }`}
                  >
                    <Eye className="w-3 h-3 inline mr-1" />
                    Voir le ticket
                  </Link>
                </div>
              </div>
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-white">
                    <tr className="text-left text-xs text-[#8B7355] border-b border-[#E5E0D5]">
                      <th className="py-1 px-2">Lib Doc</th>
                      <th className="py-1 px-2">Nom Fichier</th>
                      <th className="py-1 px-2">Prévue</th>
                      <th className="py-1 px-2">Dépôt</th>
                      <th className="py-1 px-2 text-center">Obl. Dém.</th>
                      <th className="py-1 px-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docsAnnuel.map((d) =>
                      renderDocRow(d, selDocAnnuel, setSelDocAnnuel),
                    )}
                    {docsAnnuel.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-4 text-center text-gray-400">
                          Aucun doc annuel pour {annee}.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* --- Bloc 3 : Suivi Facturation --------------------- */}
            <div className="bg-white rounded shadow p-4 lg:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-[#8B7355]">
                  Suivi Facturation
                </h3>
                <button
                  onClick={createTicketFact}
                  disabled={!boot.id_gerant || action === 'ticket-fact'}
                  className="text-xs px-3 py-1.5 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
                >
                  {action === 'ticket-fact' ? (
                    <Loader2 className="w-3 h-3 inline mr-1 animate-spin" />
                  ) : (
                    <Plus className="w-3 h-3 inline mr-1" />
                  )}
                  Ticket Facturation
                </button>
                <input
                  ref={factureInputRef}
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={onFactureSelected}
                />
                <input
                  ref={rechargeInputRef}
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={onRechargeSelected}
                />
                <input
                  ref={docAssocierInputRef}
                  type="file"
                  className="hidden"
                  onChange={onAssocierFileSelected}
                />
              </div>
              <div className="max-h-56 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-white">
                    <tr className="text-left text-xs text-[#8B7355] border-b border-[#E5E0D5]">
                      <th className="py-1 px-2">Créée le</th>
                      <th className="py-1 px-2">Par</th>
                      <th className="py-1 px-2">Facture</th>
                      <th className="py-1 px-2">Preuve Vir.</th>
                      <th className="py-1 px-2">Date Vir.</th>
                      <th className="py-1 px-2 text-right">Montant</th>
                      <th className="py-1 px-2 text-center">Statut</th>
                      <th className="py-1 px-2 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {facturations.map((f) => (
                      <tr key={f.id_tk_liste} className="border-b border-[#F0EDE5]">
                        <td className="py-2 px-2 text-xs">
                          {shortDate(f.date_crea)}
                        </td>
                        <td className="py-2 px-2 text-xs">{f.prenom_crea}</td>
                        <td className="py-2 px-2 text-xs font-mono">
                          {f.fic_facture || '—'}
                        </td>
                        <td className="py-2 px-2 text-xs font-mono">
                          {f.fic_preuve_virement || '—'}
                        </td>
                        <td className="py-2 px-2 text-xs">
                          {shortDate(f.date_virement)}
                        </td>
                        <td className="py-2 px-2 text-right text-xs font-semibold">
                          {f.montant.toFixed(2)}€
                        </td>
                        <td className="py-2 px-2 text-center text-xs">
                          {f.cloturee ? (
                            <span className="text-green-700">Clôturé</span>
                          ) : (
                            <span className="text-orange-700">En cours</span>
                          )}
                        </td>
                        <td className="py-2 px-2 text-center">
                          <div className="flex gap-1 justify-center">
                            <Link
                              to={`/tickets/${f.id_tk_liste}`}
                              className="p-1 hover:bg-[#ECF1F2] rounded"
                              title="Ouvrir le ticket"
                            >
                              <Eye className="w-3.5 h-3.5 text-[#8B7355]" />
                            </Link>
                            {!f.cloturee && (
                              <button
                                onClick={() => {
                                  setRechargeTkId(f.id_tk_liste)
                                  rechargeInputRef.current?.click()
                                }}
                                disabled={action === `recharge-${f.id_tk_liste}`}
                                className="p-1 hover:bg-[#ECF1F2] rounded disabled:opacity-40"
                                title="Recharger la facture"
                              >
                                {action === `recharge-${f.id_tk_liste}` ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                  <RefreshCw className="w-3.5 h-3.5 text-[#8B7355]" />
                                )}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {facturations.length === 0 && (
                      <tr>
                        <td colSpan={8} className="py-4 text-center text-gray-400">
                          Aucune facturation.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Overlay Suivi ADM (memos gerant) */}
      {suiviOpen && boot && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col">
            <div className="border-b border-[#E5E0D5] px-5 py-3 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-[#8B7355]">
                  Suivi ADM — {boot.raison_sociale}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Gérant : {boot.nom_gerant || 'non associé'}
                </p>
              </div>
              <button
                onClick={() => setSuiviOpen(false)}
                className="p-2 rounded hover:bg-[#ECF1F2]"
                title="Fermer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Liste memos */}
            <div className="flex-1 overflow-y-auto p-5">
              {suiviLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-[#8B7355]" />
                </div>
              ) : suiviMemos.length === 0 ? (
                <p className="text-center text-sm text-gray-400 py-8">
                  Aucun mémo pour ce gérant.
                </p>
              ) : (
                <ul className="space-y-3">
                  {suiviMemos.map((m) => {
                    const initials = getInitials(m.par)
                    const bg = colorFromName(m.par)
                    return (
                      <li
                        key={m.id}
                        className="bg-white border border-[#E5E0D5] rounded-lg p-3 shadow-sm hover:shadow transition-shadow"
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-semibold"
                            style={{ backgroundColor: bg }}
                            title={m.par}
                          >
                            {initials}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-baseline justify-between gap-2 mb-1">
                              <span className="text-sm font-medium text-[#4E1D17] truncate">
                                {m.par || 'Inconnu'}
                              </span>
                              <span className="text-[11px] text-gray-500 shrink-0">
                                {shortDate(m.depose_le)}
                              </span>
                            </div>
                            <p className="text-sm text-[#3F3F3F] whitespace-pre-wrap break-words leading-relaxed">
                              {m.message}
                            </p>
                          </div>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>

            {/* Zone de saisie */}
            <div className="border-t border-[#E5E0D5] p-4">
              <label className="text-xs text-[#8B7355] font-medium">
                Saisir un nouveau mémo
              </label>
              <div className="flex items-end gap-2 mt-1">
                <textarea
                  value={newMemo}
                  onChange={(e) => setNewMemo(e.target.value)}
                  rows={3}
                  placeholder="Votre mémo..."
                  className="flex-1 text-sm border border-[#E5E0D5] rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-[#8B7355]/40 resize-none"
                />
                <button
                  onClick={envoyerMemo}
                  disabled={!newMemo.trim() || action === 'memo'}
                  className="flex items-center gap-1.5 px-3 py-2 rounded bg-[#059669] text-white disabled:opacity-40 hover:bg-[#047857]"
                  title="Envoyer le mémo"
                >
                  {action === 'memo' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  Envoyer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
