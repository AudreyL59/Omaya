/**
 * Popup fiche d'un ticket Call Energie - Phase 2.
 *
 * 3 colonnes :
 * - Gauche : infos client + vendeur (editables, save via "Enregistrer les
 *   infos Client")
 * - Centre : tableau panier selectionnable + Statut Vente + Ref Appel +
 *   Intervention vendeur + Info Vente + 3 boutons d'action (grises en P2)
 * - Droite : header partenaire selectionne + champs SPECIFIQUES selon le
 *   partenaire (OEN/PRO/ENI/VAL/STR) + Num BS + Enregistrer
 *
 * Le bloc "Vente mobile en differe" n'existe pas pour Energie.
 */

import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Loader2,
  ArrowLeft,
  Phone,
  PhoneOff,
  CreditCard,
  FileText,
  ScrollText,
  Eye,
  EyeOff,
  Ban,
  Copy,
  Check,
} from 'lucide-react'
import DocumentViewerModal from './DocumentViewerModal'
import ConfirmDialog from './ConfirmDialog'
import AnnulLignePanierPopup from './AnnulLignePanierPopup'

// Token JWT : identique sur tous les intranets (meme cle localStorage).
const getToken = (): string | null => localStorage.getItem('token')

// --- Types ---------------------------------------------------------------

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
  info_vente: string
}

interface FicheOffre {
  id: string
  id_produit: number
  partenaire: string
  partenaire_lib: string
  // Options
  opt_energie_verte_elec: boolean
  opt_energie_verte_gaz: boolean
  opt_reforestation: boolean
  opt_mail: boolean
  opt_mandat: boolean
  format_numerique: boolean
  opt_maintenance: boolean
  opt_accept_com_parte: boolean
  opt_consent_consult_distri: boolean
  opt_e_communication: boolean
  opt_e_facture: boolean
  opt_optin_commercial: boolean
  // Etat
  statut_prod: number
  motif_annulation: string
  num_bs: string
  num_date_saisie: string
  // OEN
  date_activ: string
  ref_client_oen: string
}

interface StatutVenteOption {
  id: number
  label: string
}

interface FicheData {
  id_ticket: string
  id_call: string
  id_tk_statut: number
  is_cloture: boolean
  is_my_call: boolean
  appel_en_cours: boolean
  ope_en_cours_nom: string
  client: FicheClient
  vendeur: FicheVendeur
  vente: FicheVente
  panier: FicheOffre[]
  nb_prod_total: number
  nb_prod_valide: number
  nb_prod_annule: number
  btn_valider_actif: boolean
  btn_annuler_actif: boolean
  statuts_vente: StatutVenteOption[]
  ohm_login: string
  ohm_mdp: string
}

interface DocRef {
  url: string
  kind: 'pdf' | 'image' | ''
}


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
  onAfterAction?: () => void
  readonly?: boolean           // ouverte depuis les traites -> consultation (pas de boutons)
  // Endpoints paramitres par l'intranet consommateur (Call vs Vendeur Suivi).
  base: string                 // prefixe ressource, ex: /api/call/energie/tickets
  ficheUrl: (id: string) => string  // GET fiche (structure differente cote Vendeur)
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
      /* clipboard indisponible */
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

// --- Component principal -------------------------------------------------

export default function FicheTicketModal({ idTicket, onClose, onAfterAction, readonly = false, base, ficheUrl }: Props) {
  const [data, setData] = useState<FicheData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedPanierId, setSelectedPanierId] = useState('')
  const [docCin, setDocCin] = useState<DocRef>({ url: '', kind: '' })
  const [docKbis, setDocKbis] = useState<DocRef>({ url: '', kind: '' })
  const [docClarif, setDocClarif] = useState<DocRef>({ url: '', kind: '' })
  const [viewerOpen, setViewerOpen] = useState<null | 'cin' | 'kbis' | 'clarif'>(null)
  // States editables
  const [editClient, setEditClient] = useState<FicheClient | null>(null)
  const [editVente, setEditVente] = useState<FicheVente | null>(null)
  const [editOffres, setEditOffres] = useState<Record<string, FicheOffre>>({})
  const [savingClient, setSavingClient] = useState(false)
  const [savingOffre, setSavingOffre] = useState(false)
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)
  // Phase 3 : verrou ope + popups d'action
  const [verrouLoading, setVerrouLoading] = useState(false)
  const [verrouConfirm, setVerrouConfirm] = useState<VerrouPeek | null>(null)
  const [actionDialog, setActionDialog] = useState<null | 'valider' | 'annulVente' | 'renvoi' | 'renvoiClarif'>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [annulLigneOpen, setAnnulLigneOpen] = useState(false)
  // Alerte "un autre ope est en appel sur ce ticket" (nom de l'ope, ou null)
  const [appelEnCoursAlert, setAppelEnCoursAlert] = useState<string | null>(null)

  useEffect(() => {
    if (!idTicket) return
    setLoading(true)
    setError('')
    setData(null)
    setAppelEnCoursAlert(null)
    setDocCin({ url: '', kind: '' })
    setDocKbis({ url: '', kind: '' })
    setDocClarif({ url: '', kind: '' })
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
          } catch { /* ignore */ }
          setError(`Chargement échoué (${r.status})${detail}`)
          return
        }
        const d = (await r.json()) as FicheData
        setData(d)
        // Alerte si un AUTRE ope a un appel en cours sur ce ticket
        if (d.appel_en_cours && !d.is_my_call && d.ope_en_cours_nom) {
          setAppelEnCoursAlert(d.ope_en_cours_nom)
        }
        setEditClient({ ...d.client })
        setEditVente({ ...d.vente })
        const map: Record<string, FicheOffre> = {}
        for (const o of d.panier) map[o.id] = { ...o }
        setEditOffres(map)
        if (d.panier.length > 0) setSelectedPanierId(d.panier[0].id)
        // Documents en background
        fetch(`${API_BASE}/tickets/${idTicket}/documents?client_pro=${d.client.client_pro ? 1 : 0}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
          .then((r2) => (r2.ok ? r2.json() : null))
          .then((docs) => {
            if (docs?.cin) setDocCin(docs.cin)
            if (docs?.kbis) setDocKbis(docs.kbis)
          })
          .catch(() => { /* silencieux */ })
      } catch {
        setError('Erreur réseau')
      } finally {
        setLoading(false)
      }
    })()
  }, [idTicket])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 3000)
    return () => window.clearTimeout(t)
  }, [toast])

  const selectedOffre = useMemo(
    () => (selectedPanierId ? editOffres[selectedPanierId] || null : null),
    [editOffres, selectedPanierId],
  )

  // Lazy load clarif PDF quand on selectionne une ligne OEN
  const isSelectedOEN = selectedOffre?.partenaire.toUpperCase() === 'OEN'
  useEffect(() => {
    if (!isSelectedOEN || !selectedPanierId) {
      setDocClarif({ url: '', kind: '' })
      return
    }
    let cancelled = false
    fetch(`${API_BASE}/tickets/panier/${selectedPanierId}/clarification`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!cancelled && d) setDocClarif(d)
      })
      .catch(() => { /* silencieux */ })
    return () => { cancelled = true }
  }, [isSelectedOEN, selectedPanierId])

  const patchOffre = (id: string, patch: Partial<FicheOffre>) => {
    setEditOffres((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }))
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
      const map: Record<string, FicheOffre> = {}
      for (const o of d.panier) map[o.id] = { ...o }
      setEditOffres(map)
    } catch { /* ignore */ }
  }

  const handlePrendreAppel = async (force = false) => {
    if (!idTicket) return
    setVerrouLoading(true)
    try {
      const r = await fetch(`${API_BASE}/tickets/${idTicket}/verrou/prendre`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
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

  const handleAnnulerLigne = async (motifs: string[], precisions: string) => {
    if (!selectedPanierId) return
    setActionLoading(true)
    try {
      const r = await fetch(`${API_BASE}/tickets/panier/${selectedPanierId}/annuler-ligne`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
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

  const handleConfirmAction = async () => {
    if (!idTicket || !actionDialog) return
    setActionLoading(true)
    try {
      const venteBody = (() => {
        if (actionDialog === 'renvoi' || actionDialog === 'renvoiClarif') return {}
        return {
          client: editClient ? {
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
          } : undefined,
          vente: editVente ? {
            ref_appel: editVente.ref_appel,
            intervention_vendeur: editVente.intervention_vendeur,
            info_vente: editVente.info_vente,
          } : undefined,
        }
      })()
      const path =
        actionDialog === 'valider' ? 'valider-vente'
        : actionDialog === 'annulVente' ? 'annuler-vente'
        : actionDialog === 'renvoiClarif' ? 'renvoyer-clarification'
        : 'renvoyer-complement'
      const r = await fetch(`${API_BASE}/tickets/${idTicket}/${path}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(venteBody),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Échec : ${j?.detail || r.status}` })
        return
      }
      const msg =
        actionDialog === 'valider' ? 'Panier validé'
        : actionDialog === 'annulVente' ? 'Vente annulée'
        : actionDialog === 'renvoiClarif' ? 'Panier renvoyé pour clarification'
        : 'Panier renvoyé pour complément'
      setToast({ kind: 'ok', msg })
      setActionDialog(null)
      onAfterAction?.()
      onClose()
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setActionLoading(false)
    }
  }

  const handleSaveClient = async () => {
    if (!idTicket || !editClient || !editVente) return
    setSavingClient(true)
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
          info_vente: editVente.info_vente,
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
      setToast({ kind: 'ok', msg: 'Infos client enregistrées' })
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setSavingClient(false)
    }
  }

  const handleSaveOffre = async (offre: FicheOffre, silent = false) => {
    setSavingOffre(true)
    try {
      // On envoie tous les champs (le backend update seulement ceux fournis)
      const body = {
        statut_prod: offre.statut_prod,
        num_bs: offre.num_bs,
        opt_mandat: offre.opt_mandat,
        format_numerique: offre.format_numerique,
        opt_maintenance: offre.opt_maintenance,
        opt_accept_com_parte: offre.opt_accept_com_parte,
        opt_consent_consult_distri: offre.opt_consent_consult_distri,
        opt_e_communication: offre.opt_e_communication,
        opt_e_facture: offre.opt_e_facture,
        opt_optin_commercial: offre.opt_optin_commercial,
        opt_energie_verte_elec: offre.opt_energie_verte_elec,
        opt_energie_verte_gaz: offre.opt_energie_verte_gaz,
        opt_reforestation: offre.opt_reforestation,
        opt_mail: offre.opt_mail,
        date_activ: offre.date_activ,
        ref_client_oen: offre.ref_client_oen,
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
      if (!silent) setToast({ kind: 'ok', msg: 'Offre enregistrée' })
    } catch {
      setToast({ kind: 'err', msg: 'Erreur réseau' })
    } finally {
      setSavingOffre(false)
    }
  }

  if (!idTicket) return null

  const viewerDoc: DocRef =
    viewerOpen === 'cin' ? docCin
    : viewerOpen === 'kbis' ? docKbis
    : viewerOpen === 'clarif' ? docClarif
    : { url: '', kind: '' }
  const viewerTitle =
    viewerOpen === 'cin' ? "Carte d'identité"
    : viewerOpen === 'kbis' ? 'KBIS'
    : viewerOpen === 'clarif' ? 'Fiche de clarification'
    : ''

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
          <div className="flex items-center justify-between px-5 py-3 border-b border-c-line">
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="p-1.5 rounded text-c-ink-soft hover:bg-c-brand-soft hover:text-c-ink"
                title="Retour"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h2 className="text-base font-bold text-c-ink">
                Fiche Ticket Call ENI
                {data ? ` — ${data.client.nom_format}` : ''}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded text-c-ink-soft hover:bg-c-brand-soft hover:text-c-ink"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-emerald-600 animate-spin" />
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center text-red-600 text-sm">{error}</div>
          ) : !data || !editClient || !editVente ? (
            <div className="flex-1 flex items-center justify-center text-c-ink-faint text-sm italic">
              Aucune donnée
            </div>
          ) : (
            <div className="flex-1 grid grid-cols-12 gap-4 p-4 overflow-auto bg-gray-50">
              <ColonneGauche
                data={data}
                client={editClient}
                onClientChange={(patch) => setEditClient((c) => (c ? { ...c, ...patch } : c))}
                cinAvailable={!!docCin.url}
                kbisAvailable={!!docKbis.url}
                onOpenCin={() => setViewerOpen('cin')}
                onOpenKbis={() => setViewerOpen('kbis')}
              />
              <ColonneCentre
                data={data}
                editOffres={editOffres}
                editVente={editVente}
                onVenteChange={(patch) => setEditVente((v) => (v ? { ...v, ...patch } : v))}
                selectedId={selectedPanierId}
                onSelect={setSelectedPanierId}
                onSaveClient={handleSaveClient}
                savingClient={savingClient}
                onAnnulLigne={() => setAnnulLigneOpen(true)}
                onAskValider={() => setActionDialog('valider')}
                onAskAnnulVente={() => setActionDialog('annulVente')}
                onAskRenvoi={() => setActionDialog('renvoi')}
                verrouLoading={verrouLoading}
                onPrendreAppel={() => handlePrendreAppel(false)}
                onLacherAppel={handleLacherAppel}
                readonly={readonly}
              />
              <ColonneDroite
                data={data}
                offre={selectedOffre}
                readonly={readonly}
                onOffreChange={(patch) =>
                  selectedPanierId && patchOffre(selectedPanierId, patch)
                }
                onSaveStatutAuto={(newStatut) => {
                  if (selectedOffre) {
                    const next = { ...selectedOffre, statut_prod: newStatut }
                    handleSaveOffre(next, false)
                  }
                }}
                onAskAnnulLigne={() => setAnnulLigneOpen(true)}
                onSaveOffre={() => selectedOffre && handleSaveOffre(selectedOffre)}
                savingOffre={savingOffre}
                clarifAvailable={!!docClarif.url}
                onOpenClarif={() => setViewerOpen('clarif')}
                onAskRenvoiClarif={() => setActionDialog('renvoiClarif')}
              />
            </div>
          )}
        </motion.div>

        <DocumentViewerModal
          open={viewerOpen !== null}
          title={viewerTitle}
          url={viewerDoc.url}
          kind={viewerDoc.kind}
          onClose={() => setViewerOpen(null)}
        />

        {/* Confirmation verrou pris par un autre ope */}
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

        {/* Annulation 1 ligne du panier */}
        <AnnulLignePanierPopup
          open={annulLigneOpen}
          loading={actionLoading}
          onCancel={() => setAnnulLigneOpen(false)}
          onConfirm={(motifs, prec) => handleAnnulerLigne(motifs, prec)}
        />

        <ConfirmDialog
          open={actionDialog === 'valider'}
          title="Voulez-vous vraiment valider le panier ?"
          confirmLabel="Valider le panier"
          confirmColor="green"
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionDialog(null)}
        />
        <ConfirmDialog
          open={actionDialog === 'annulVente'}
          title="Voulez-vous vraiment annuler le panier ?"
          confirmLabel="Annuler toute la vente"
          confirmColor="red"
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionDialog(null)}
        />
        <ConfirmDialog
          open={actionDialog === 'renvoi'}
          title="Voulez-vous vraiment renvoyer le panier ?"
          confirmLabel="Renvoyer le panier pour complément"
          confirmColor="orange"
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionDialog(null)}
        />
        <ConfirmDialog
          open={actionDialog === 'renvoiClarif'}
          title="Voulez-vous vraiment renvoyer le panier pour la fiche clarification ?"
          confirmLabel="Renvoyer pour fiche clarification"
          confirmColor="red"
          loading={actionLoading}
          onConfirm={handleConfirmAction}
          onCancel={() => setActionDialog(null)}
        />

        {/* Alerte : un autre ope a un appel en cours sur ce ticket */}
        <AnimatePresence>
          {appelEnCoursAlert && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setAppelEnCoursAlert(null)}
              className="fixed inset-0 bg-black/60 z-[80] flex items-center justify-center p-4"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6 text-center space-y-4"
              >
                <div className="w-12 h-12 mx-auto rounded-full bg-orange-100 flex items-center justify-center">
                  <Phone className="w-6 h-6 text-orange-600" />
                </div>
                <h3 className="text-lg font-semibold text-c-ink">Appel en cours</h3>
                <p className="text-sm text-c-ink-soft">
                  L'opérateur <span className="font-semibold text-c-ink">{appelEnCoursAlert}</span> est en cours d'appel sur ce ticket.
                </p>
                <button
                  onClick={() => setAppelEnCoursAlert(null)}
                  className="px-4 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110"
                >
                  Fermer
                </button>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

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

// --- Colonne gauche : Client + Vendeur ----------------------------------

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
      <div className="bg-white rounded-lg border border-c-line p-4">
        <h3 className="text-sm font-bold text-c-ink mb-3">Information contrat et client</h3>
        <div className="space-y-2.5 text-xs">
          <Radios
            label="Civilité"
            value={c.civilite}
            options={[{ v: 1, l: 'M.' }, { v: 2, l: 'Mme' }, { v: 3, l: 'Mlle' }]}
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
              <button onClick={onOpenCin} className="hover:underline">Voir la CIN</button>
            ) : (
              <span className="italic">Pas de CIN trouvée</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Field label="Né(e) le" type="date" value={c.date_naiss} onChange={(v) => onClientChange({ date_naiss: v })} />
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
            options={[{ v: 1, l: 'Maison' }, { v: 2, l: 'Appartement' }]}
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
          <Field label="Mobile 1" value={c.mobile1} muted={!data.is_my_call} />

          <div className="pt-2 space-y-2">
            <Toggle label="Le client est d'accord pour être rappelé immédiatement par le Call" value={c.opt_rappel} />
            <Toggle label="Le client accepte que ses coordonnées soient transmises aux partenaires" value={c.opt_partenaire} />
          </div>

          <div className="pt-2 flex bg-gray-900 text-white rounded-md p-0.5">
            <ProTab active={!c.client_pro} label="Client Part" />
            <ProTab active={c.client_pro} label="Client Pro" />
          </div>

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

// --- Colonne centre : Panier + Vente -----------------------------------

function ColonneCentre({
  data,
  editOffres,
  editVente,
  onVenteChange,
  selectedId,
  onSelect,
  onSaveClient,
  savingClient,
  onAnnulLigne,
  onAskValider,
  onAskAnnulVente,
  onAskRenvoi,
  verrouLoading,
  onPrendreAppel,
  onLacherAppel,
  readonly,
}: {
  data: FicheData
  editOffres: Record<string, FicheOffre>
  editVente: FicheVente
  onVenteChange: (patch: Partial<FicheVente>) => void
  selectedId: string
  onSelect: (id: string) => void
  onSaveClient: () => void
  savingClient: boolean
  onAnnulLigne: () => void
  onAskValider: () => void
  onAskAnnulVente: () => void
  onAskRenvoi: () => void
  verrouLoading: boolean
  onPrendreAppel: () => void
  onLacherAppel: () => void
  readonly: boolean
}) {
  const v = data.vendeur
  const offresList = data.panier.map((p) => editOffres[p.id] || p)
  const nbValide = offresList.filter((o) => o.statut_prod === 1 || o.statut_prod === 3).length
  const nbAnnule = offresList.filter((o) => o.statut_prod === 2).length
  const nbTotal = offresList.length
  // Boutons WinDev :
  // - Valider : nbValid > 0 ET nbValid+nbAnnul == nbTotal
  // - Annuler vente : nbAnnul == nbTotal (et > 0)
  const canValider = nbValide > 0 && nbValide + nbAnnule === nbTotal
  const canAnnulerVente = nbTotal > 0 && nbAnnule === nbTotal
  const selectedOffre = selectedId ? offresList.find((o) => o.id === selectedId) : null
  const canAnnulerLigne = !!selectedOffre && selectedOffre.statut_prod !== 2

  return (
    <div className="col-span-4 flex flex-col gap-3">
      {/* Tableau panier */}
      <div className="bg-white rounded-lg border border-c-line overflow-hidden flex flex-col" style={{ maxHeight: '40vh' }}>
        <div className="bg-gray-50 border-b border-c-line text-xs font-semibold text-c-ink-soft grid grid-cols-[150px_1fr]">
          <div className="px-2 py-2">Partenaire</div>
          <div className="px-2 py-2">Lib Offre / Num BS</div>
        </div>
        <div className="overflow-y-auto flex-1">
          {offresList.length === 0 ? (
            <div className="p-4 text-center text-c-ink-faint italic text-xs">Aucune offre</div>
          ) : (
            offresList.map((o) => {
              const isSel = o.id === selectedId
              return (
                <div
                  key={o.id}
                  onClick={() => onSelect(o.id)}
                  className={`grid grid-cols-[150px_1fr] text-xs border-b border-c-line-soft cursor-pointer transition-colors ${
                    isSel ? 'bg-emerald-50' : 'hover:bg-gray-50'
                  }`}
                  title={o.partenaire_lib || o.partenaire}
                >
                  <div className="px-2 py-2 font-semibold truncate">{o.partenaire_lib || o.partenaire || '—'}</div>
                  <div className="px-2 py-2 truncate">{o.num_bs || `Produit #${o.id_produit}`}</div>
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
            {!readonly && (data.is_my_call ? (
              <button
                onClick={onLacherAppel}
                disabled={verrouLoading}
                className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded border border-red-600 bg-red-600 text-white text-xs hover:brightness-110 disabled:opacity-60"
                title="Raccrocher / libérer le verrou"
              >
                {verrouLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PhoneOff className="w-3.5 h-3.5" />}
                Lâcher l'appel
              </button>
            ) : (
              <button
                onClick={onPrendreAppel}
                disabled={verrouLoading}
                className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded border border-green-600 bg-green-600 text-white text-xs hover:brightness-110 disabled:opacity-60"
                title="Démarrer l'appel (pose le verrou, démasque les mobiles, envoie un SMS au vendeur)"
              >
                {verrouLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Phone className="w-3.5 h-3.5" />}
                Démarrer l'appel
              </button>
            ))}
          </div>
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
      </div>

      {/* Intervention vendeur + Info Vente + Ref Appel + Enregistrer client */}
      <div className="bg-white rounded-lg border border-c-line p-4 space-y-3 text-xs">
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
        <div className="space-y-1">
          <label className="font-semibold text-c-ink">Info Vente</label>
          <textarea
            value={editVente.info_vente}
            onChange={(e) => onVenteChange({ info_vente: e.target.value })}
            rows={3}
            className="w-full px-2 py-1.5 border border-c-line rounded text-xs bg-white focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 focus:outline-none resize-none"
          />
        </div>
        <div className="grid grid-cols-[80px_1fr] gap-2 items-center">
          <label className="text-c-ink-soft">Réf Appel :</label>
          <input
            type="text"
            value={editVente.ref_appel}
            onChange={(e) => onVenteChange({ ref_appel: e.target.value })}
            className="px-2 py-1 border border-c-line rounded text-xs bg-white focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 focus:outline-none"
          />
        </div>
        {!readonly && (
          <button
            onClick={onSaveClient}
            disabled={savingClient}
            className="w-full py-2 rounded bg-gray-900 text-white text-xs font-semibold hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {savingClient && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Enregistrer les infos Client
          </button>
        )}
      </div>

      {/* Action sur la ligne selectionnee (masque en consultation) */}
      {!readonly && selectedOffre && (
        <button
          onClick={onAnnulLigne}
          disabled={!canAnnulerLigne}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded border border-red-300 text-red-600 text-xs font-medium hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Annuler uniquement la ligne sélectionnée (motifs)"
        >
          <Ban className="w-3.5 h-3.5" />
          {selectedOffre.statut_prod === 2 ? 'Offre déjà annulée' : 'Annuler cette offre'}
        </button>
      )}

      {/* Boutons d'action panier (masques en consultation) */}
      {!readonly && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <ActionButton label="Valider le panier" disabled={!canValider} variant="green" onClick={onAskValider} />
            <ActionButton label="Annuler toute la vente" disabled={!canAnnulerVente} onClick={onAskAnnulVente} />
          </div>
          <ActionButton label="Renvoyer le panier pour complément" variant="orange" full onClick={onAskRenvoi} />
        </div>
      )}
    </div>
  )
}

// --- Colonne droite : Statut + bloc spécifique par Partenaire ----------

function ColonneDroite({
  data,
  offre,
  readonly,
  onOffreChange,
  onSaveStatutAuto,
  onAskAnnulLigne,
  onSaveOffre,
  savingOffre,
  clarifAvailable,
  onOpenClarif,
  onAskRenvoiClarif,
}: {
  data: FicheData
  offre: FicheOffre | null
  readonly: boolean
  onOffreChange: (patch: Partial<FicheOffre>) => void
  onSaveStatutAuto: (newStatut: number) => void
  onAskAnnulLigne: () => void
  onSaveOffre: () => void
  savingOffre: boolean
  clarifAvailable: boolean
  onOpenClarif: () => void
  onAskRenvoiClarif: () => void
}) {
  if (!offre) {
    return (
      <div className="col-span-4 flex flex-col gap-3">
        <div className="bg-white rounded-lg border border-c-line p-6 text-center text-sm text-c-ink-faint italic flex items-center justify-center" style={{ minHeight: 200 }}>
          Sélectionne une ligne du panier
        </div>
      </div>
    )
  }

  return (
    <div className="col-span-4 flex flex-col gap-3">
      {/* Bloc partenaire-specifique en haut */}
      <PartenaireBlock
        data={data}
        offre={offre}
        readonly={readonly}
        onOffreChange={onOffreChange}
        onSaveOffre={onSaveOffre}
        savingOffre={savingOffre}
        clarifAvailable={clarifAvailable}
        onOpenClarif={onOpenClarif}
      />

      {/* Statut Vente (auto-save) - commun a tous les partenaires.
          En consultation : select desactive (pas d'auto-save). */}
      <div className="bg-white rounded-lg border border-c-line p-4 space-y-3 text-xs">
        <div className="space-y-0.5">
          <label className="text-c-ink-soft">Statut Vente</label>
          <select
            value={offre.statut_prod}
            disabled={readonly}
            onChange={(e) => {
              let v = parseInt(e.target.value, 10)
              // Cas WinDev : statut = 2 (Annulee) -> ouvre la popup motif
              // d'annulation au lieu de sauver directement.
              if (v === 2) {
                onAskAnnulLigne()
                return
              }
              // Cas WinDev specifique Energie : si NumBS deja saisi et statut
              // choisi = 1 (Validee), on bascule auto a 3 (Validee bureau).
              if (v === 1 && (offre.num_bs || '').trim() !== '') {
                v = 3
              }
              onOffreChange({ statut_prod: v })
              onSaveStatutAuto(v)
            }}
            className="w-full px-2 py-1 border border-c-line rounded text-xs bg-white focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 focus:outline-none"
          >
            {data.statuts_vente.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Consultation : motif d'annulation de la ligne (si annulee) */}
      {readonly && offre.statut_prod === 2 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <div className="text-[11px] font-semibold text-red-700 mb-1">
            Motif d'annulation de l'offre
          </div>
          <div className="text-xs text-c-ink whitespace-pre-wrap">
            {offre.motif_annulation || '—'}
          </div>
        </div>
      )}

      {/* Bouton "Renvoyer pour fiche clarification" - OEN uniquement (masque en consultation) */}
      {!readonly && offre.partenaire.toUpperCase() === 'OEN' && (
        <button
          onClick={onAskRenvoiClarif}
          className="w-full py-2 px-3 rounded bg-red-600 text-white text-xs font-semibold hover:brightness-110"
          title="Renvoyer le panier pour la fiche clarification (statut 28 + SMS spécifique)"
        >
          Renvoyer le panier pour la fiche clarification
        </button>
      )}
    </div>
  )
}

function PartenaireBlock({
  data,
  offre,
  readonly,
  onOffreChange,
  onSaveOffre,
  savingOffre,
  clarifAvailable,
  onOpenClarif,
}: {
  data: FicheData
  offre: FicheOffre
  readonly: boolean
  onOffreChange: (patch: Partial<FicheOffre>) => void
  onSaveOffre: () => void
  savingOffre: boolean
  clarifAvailable: boolean
  onOpenClarif: () => void
}) {
  const p = offre.partenaire.toUpperCase()
  const partenaireLabel = offre.partenaire_lib || offre.partenaire || 'Partenaire'

  return (
    <div className="bg-white rounded-lg border border-c-line p-4 space-y-3 text-xs">
      {/* Header avec libelle complet du partenaire */}
      <div className="flex items-center justify-between border-b border-c-line-soft pb-2 mb-1">
        <span className="text-sm font-bold text-emerald-700">{partenaireLabel}</span>
      </div>

      {/* Credentials Ohm Energie + bouton fiche clarification (OEN uniquement) */}
      {p === 'OEN' && (
        <>
          <OhmCredentials login={data.ohm_login} mdp={data.ohm_mdp} />
          <button
            onClick={onOpenClarif}
            disabled={!clarifAvailable}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded border border-c-line hover:bg-c-brand-soft text-xs text-c-ink-soft disabled:opacity-40 disabled:cursor-not-allowed"
            title={clarifAvailable ? 'Voir la fiche de clarification' : 'Aucune fiche de clarification'}
          >
            <ScrollText className="w-3.5 h-3.5" />
            {clarifAvailable ? 'Fiche de clarification' : 'Pas de fiche de clarification'}
          </button>
          {/* Date Activ + Ref Client OEN */}
          <div className="grid grid-cols-2 gap-2">
            <Field
              label="Date Activ"
              type="date"
              value={offre.date_activ}
              onChange={(v) => onOffreChange({ date_activ: v })}
            />
            <Field
              label="Ref Client"
              value={offre.ref_client_oen}
              onChange={(v) => onOffreChange({ ref_client_oen: v })}
            />
          </div>
        </>
      )}

      {/* Num BS commun a tous */}
      <Field
        label="Num BS"
        value={offre.num_bs}
        onChange={(v) => onOffreChange({ num_bs: v })}
      />

      {/* Options specifiques */}
      {p === 'PRO' && (
        <CheckboxField
          label="Format numérique"
          checked={offre.format_numerique}
          onChange={(v) => onOffreChange({ format_numerique: v })}
        />
      )}
      {p === 'ENI' && (
        <div className="space-y-2">
          <CheckboxField
            label="Mandat"
            checked={offre.opt_mandat}
            onChange={(v) => onOffreChange({ opt_mandat: v })}
          />
          <CheckboxField
            label="PLENICOACH DEPANNAGE PREMIUM"
            checked={offre.opt_maintenance}
            onChange={(v) => onOffreChange({ opt_maintenance: v })}
          />
          <CheckboxField
            label="Acceptation Commerciales Partenaires"
            checked={offre.opt_accept_com_parte}
            onChange={(v) => onOffreChange({ opt_accept_com_parte: v })}
          />
          <CheckboxField
            label="Consentement consultation distributeurs"
            checked={offre.opt_consent_consult_distri}
            onChange={(v) => onOffreChange({ opt_consent_consult_distri: v })}
          />
        </div>
      )}

      {/* Bouton Enregistrer (masque en consultation) */}
      {!readonly && (
        <button
          onClick={onSaveOffre}
          disabled={savingOffre}
          className="w-full py-2 rounded bg-gray-900 text-white text-xs font-semibold hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {savingOffre && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          Enregistrer
        </button>
      )}
    </div>
  )
}

function OhmCredentials({ login, mdp }: { login: string; mdp: string }) {
  const [show, setShow] = useState(false)
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-[60px_1fr] gap-2 items-center">
        <label className="text-c-ink-soft">Login :</label>
        <input
          type="text"
          value={login}
          readOnly
          className="px-2 py-1 border border-c-line rounded text-xs bg-gray-50 font-mono"
        />
      </div>
      <div className="grid grid-cols-[60px_1fr_30px] gap-2 items-center">
        <label className="text-c-ink-soft">MPD :</label>
        <input
          type={show ? 'text' : 'password'}
          value={mdp}
          readOnly
          className="px-2 py-1 border border-c-line rounded text-xs bg-gray-50 font-mono"
        />
        <button
          onClick={() => setShow((s) => !s)}
          className="p-1 text-c-ink-soft hover:text-c-ink"
          title={show ? 'Masquer' : 'Afficher'}
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  )
}

// --- Helpers UI ---------------------------------------------------------

function Field({
  label, value, multi, muted, onChange, type = 'text',
}: {
  label: string
  value: string | number
  multi?: boolean
  muted?: boolean
  onChange?: (v: string) => void
  type?: 'text' | 'date' | 'email'
}) {
  const readOnly = !onChange
  const cls = `w-full px-2 py-1 border border-c-line rounded text-xs ${
    readOnly ? 'bg-gray-50' : 'bg-white focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 focus:outline-none'
  } ${muted ? 'text-c-ink-faint italic' : ''}`
  return (
    <div className="space-y-0.5">
      <label className="block text-c-ink-soft">{label}</label>
      {multi ? (
        <textarea
          value={String(value ?? '')}
          readOnly={readOnly}
          onChange={onChange ? (e) => onChange(e.target.value) : undefined}
          rows={2}
          className={`${cls} resize-none`}
        />
      ) : (
        <input
          type={type}
          value={String(value ?? '')}
          readOnly={readOnly}
          onChange={onChange ? (e) => onChange(e.target.value) : undefined}
          className={cls}
        />
      )}
    </div>
  )
}

function CheckboxField({
  label, checked, onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="accent-emerald-600"
      />
      <span className="text-c-ink">{label}</span>
    </label>
  )
}

function Radios({
  label, value, options, onChange,
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
            className="accent-emerald-600"
          />
          <span className="text-c-ink">{opt.l}</span>
        </label>
      ))}
    </div>
  )
}

function Radio({ active, label, onClick }: { active: boolean; label: string; onClick?: () => void }) {
  return (
    <label className={`flex items-center gap-1 ${onClick ? 'cursor-pointer' : 'cursor-default'}`}>
      <input
        type="radio"
        checked={active}
        readOnly={!onClick}
        onChange={onClick ? () => onClick() : undefined}
        className="accent-emerald-600"
      />
      <span>{label}</span>
    </label>
  )
}

function Toggle({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center gap-2 text-c-ink">
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
    <div className={`flex-1 text-center text-xs font-semibold py-1.5 rounded ${active ? 'bg-white text-gray-900' : 'text-gray-300'}`}>
      {label}
    </div>
  )
}

function ActionButton({
  label, disabled, variant = 'dark', full, onClick,
}: {
  label: string
  disabled?: boolean
  variant?: 'dark' | 'orange' | 'green'
  full?: boolean
  onClick?: () => void
}) {
  const cls =
    variant === 'green'
      ? 'bg-green-600 text-white'
      : variant === 'orange'
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
