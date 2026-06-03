/**
 * Popup fiche d'un ticket Call Energie (transposition PAGE_TicketFicheEnergie).
 *
 * Phase 1 : colonne gauche uniquement (infos client + vendeur). Les 2
 * autres colonnes (panier + detail offre/vente) sont des placeholders
 * en attendant Phase 2.
 *
 * Differences vs Fibre :
 * - Pas de Mobile 2 / Fixe
 * - Pas de MobPropoVend ni bloc anomalie
 * - Documents : CIN + KBIS (si Pro) + Justif (specifique Energie)
 */

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Loader2,
  ArrowLeft,
  Phone,
  CreditCard,
  FileText,
  ScrollText,
} from 'lucide-react'
import { getToken } from '@/api'
import DocumentViewerModal from '@/components/DocumentViewerModal'

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
  opt_energie_verte_elec: boolean
  opt_energie_verte_gaz: boolean
  opt_reforestation: boolean
  opt_mail: boolean
  opt_mandat: boolean
  format_numerique: boolean
  statut_prod: number
  motif_annulation: string
  num_bs: string
  num_date_saisie: string
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
}

interface DocRef {
  url: string
  kind: 'pdf' | 'image' | ''
}

const API_BASE = '/api/call/energie'

interface Props {
  idTicket: string | null
  onClose: () => void
  onAfterAction?: () => void
}

export default function FicheTicketModal({ idTicket, onClose }: Props) {
  const [data, setData] = useState<FicheData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [docCin, setDocCin] = useState<DocRef>({ url: '', kind: '' })
  const [docKbis, setDocKbis] = useState<DocRef>({ url: '', kind: '' })
  const [docJustif, setDocJustif] = useState<DocRef>({ url: '', kind: '' })
  const [viewerOpen, setViewerOpen] = useState<null | 'cin' | 'kbis' | 'justif'>(null)

  useEffect(() => {
    if (!idTicket) return
    setLoading(true)
    setError('')
    setData(null)
    setDocCin({ url: '', kind: '' })
    setDocKbis({ url: '', kind: '' })
    setDocJustif({ url: '', kind: '' })
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
        // Documents en background
        fetch(
          `${API_BASE}/tickets/${idTicket}/documents?client_pro=${d.client.client_pro ? 1 : 0}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
          .then((r2) => (r2.ok ? r2.json() : null))
          .then((docs) => {
            if (docs?.cin) setDocCin(docs.cin)
            if (docs?.kbis) setDocKbis(docs.kbis)
            if (docs?.justif) setDocJustif(docs.justif)
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
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!idTicket) return null

  const viewerDoc: DocRef =
    viewerOpen === 'cin' ? docCin
    : viewerOpen === 'kbis' ? docKbis
    : viewerOpen === 'justif' ? docJustif
    : { url: '', kind: '' }
  const viewerTitle =
    viewerOpen === 'cin' ? "Carte d'identité"
    : viewerOpen === 'kbis' ? 'KBIS'
    : viewerOpen === 'justif' ? 'Justificatif de domicile'
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
                Fiche Ticket Call ENI
                {data ? ` — ${data.client.nom_format}` : ''}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded text-c-ink-soft hover:bg-c-brand-soft hover:text-c-ink transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Corps */}
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-emerald-600 animate-spin" />
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
                cinAvailable={!!docCin.url}
                kbisAvailable={!!docKbis.url}
                justifAvailable={!!docJustif.url}
                onOpenCin={() => setViewerOpen('cin')}
                onOpenKbis={() => setViewerOpen('kbis')}
                onOpenJustif={() => setViewerOpen('justif')}
              />

              {/* Colonne centre : placeholder Phase 2 */}
              <div className="col-span-4 flex flex-col gap-3">
                <div className="bg-white rounded-lg border border-c-line p-6 text-center text-sm text-c-ink-faint italic flex-1 flex items-center justify-center">
                  Panier (Phase 2)
                </div>
              </div>

              {/* Colonne droite : placeholder Phase 2 */}
              <div className="col-span-4 flex flex-col gap-3">
                <div className="bg-white rounded-lg border border-c-line p-6 text-center text-sm text-c-ink-faint italic flex-1 flex items-center justify-center">
                  Détail offre + Vente (Phase 2)
                </div>
              </div>
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
      </motion.div>
    </AnimatePresence>
  )
}

// --- Colonne gauche : Client + Vendeur (identique structure Fibre) -------

function ColonneGauche({
  data,
  cinAvailable,
  kbisAvailable,
  justifAvailable,
  onOpenCin,
  onOpenKbis,
  onOpenJustif,
}: {
  data: FicheData
  cinAvailable: boolean
  kbisAvailable: boolean
  justifAvailable: boolean
  onOpenCin: () => void
  onOpenKbis: () => void
  onOpenJustif: () => void
}) {
  const c = data.client
  const v = data.vendeur
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
          />
          <Field label="Nom" value={c.nom} />
          <Field label="Nom Marital" value={c.nom_marital} />
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Field label="Prénom" value={c.prenom} />
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
                Voir la CIN
              </button>
            ) : (
              <span className="italic">Pas de CIN trouvée</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Né(e) le" type="date" value={c.date_naiss} />
            <Field label="Dép" value={c.dep_naiss ? String(c.dep_naiss).padStart(2, '0') : ''} />
          </div>
          <Radios
            label="Logement"
            value={c.type_logement}
            options={[
              { v: 1, l: 'Maison' },
              { v: 2, l: 'Appartement' },
            ]}
          />
          <Field label="Adresse" value={c.adresse1} />
          <Field label="Cplt" value={c.adresse2} />
          <div className="grid grid-cols-3 gap-3">
            <Field label="CP" value={c.cp} />
            <div className="col-span-2">
              <Field label="Ville" value={c.ville} />
            </div>
          </div>
          <Field label="Email" type="email" value={c.email} />
          <div className="grid grid-cols-2 gap-3">
            {/* Energie n'a qu'un seul Mobile */}
            <Field label="Mobile 1" value={c.mobile1} muted={!data.is_my_call} />
            <div className="flex items-end">
              {/* Bouton Justificatif (specifique Energie) */}
              <button
                onClick={onOpenJustif}
                disabled={!justifAvailable}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded border border-c-line hover:bg-c-brand-soft text-xs text-c-ink-soft disabled:opacity-40 disabled:cursor-not-allowed"
                title={justifAvailable ? 'Voir le justificatif' : 'Aucun justificatif'}
              >
                <ScrollText className="w-3.5 h-3.5" />
                Justificatif
              </button>
            </div>
          </div>

          {/* Consentements (lecture seule en Phase 1) */}
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

          {/* Switch Part / Pro */}
          <div className="pt-2 flex bg-gray-900 text-white rounded-md p-0.5">
            <ProTab active={!c.client_pro} label="Client Part" />
            <ProTab active={c.client_pro} label="Client Pro" />
          </div>

          {/* Si client Pro : Raison Sociale + SIRET + KBIS */}
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

      {/* Bloc vendeur */}
      <div className="bg-white rounded-lg border border-c-line p-4">
        <h3 className="text-sm font-bold text-c-ink mb-3">Information Vendeur</h3>
        <div className="space-y-2.5 text-xs">
          <Field label="Nom" value={v.nom} />
          <Field label="Prénom" value={v.prenom} />
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Field label="Mobile" value={v.gsm} muted={!data.is_my_call} />
            </div>
            <button
              disabled
              className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded border border-c-line text-xs text-c-ink-soft cursor-not-allowed"
              title="À venir (Phase 3)"
            >
              <Phone className="w-3.5 h-3.5 text-green-600" />
              Démarrer l'appel
            </button>
          </div>
          {v.lib_affectation && (
            <div className="text-[10px] text-c-ink-faint mt-1">{v.lib_affectation}</div>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Helpers UI ----------------------------------------------------------

function Field({
  label,
  value,
  multi,
  muted,
  type = 'text',
}: {
  label: string
  value: string | number
  multi?: boolean
  muted?: boolean
  type?: 'text' | 'date' | 'email'
}) {
  const baseCls = `w-full px-2 py-1 border border-c-line rounded text-xs bg-gray-50 ${muted ? 'text-c-ink-faint italic' : ''}`
  return (
    <div className="space-y-0.5">
      <label className="block text-c-ink-soft">{label}</label>
      {multi ? (
        <textarea
          value={String(value ?? '')}
          readOnly
          rows={2}
          className={`${baseCls} resize-none`}
        />
      ) : (
        <input
          type={type}
          value={String(value ?? '')}
          readOnly
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
}: {
  label: string
  value: number
  options: { v: number; l: string }[]
}) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-c-ink-soft w-20">{label} :</span>
      {options.map((opt) => (
        <label key={opt.v} className="flex items-center gap-1 cursor-default">
          <input type="radio" checked={value === opt.v} readOnly className="accent-emerald-600" />
          <span className="text-c-ink">{opt.l}</span>
        </label>
      ))}
    </div>
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
    <div
      className={`flex-1 text-center text-xs font-semibold py-1.5 rounded ${
        active ? 'bg-white text-gray-900' : 'text-gray-300'
      }`}
    >
      {label}
    </div>
  )
}
