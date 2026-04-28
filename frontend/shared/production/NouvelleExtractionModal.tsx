import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Calendar,
  ChevronDown,
  Loader2,
  Search,
  User,
  Users,
  Globe,
  X,
  Check,
} from 'lucide-react'
import { getToken, getStoredUser } from '@/api'

interface PartenaireItem {
  lib: string
  prefix: string
  is_actif: boolean
  couleur_hex: string
}

interface TypeEtatItem {
  id: number
  lib: string
  couleur_hex: string
}

interface SalarieItem {
  id_salarie: string
  nom: string
  prenom: string
}

interface OrgaItem {
  id_organigramme: string
  lib_orga: string
  parent_lib: string
}

type Scope = 1 | 2 | 3 | 4

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

function toYMD(iso: string): string {
  // "2026-04-01" -> "20260401"
  return iso.replace(/-/g, '')
}

interface Props {
  apiBase: string  // ex: '/api/vendeur' ou '/api/adm'
  open: boolean
  onClose: () => void
  onCreated: (idJob: string) => void
}

export default function NouvelleExtractionModal({ apiBase, open, onClose, onCreated }: Props) {
  const stored = getStoredUser()
  const today = new Date().toISOString().slice(0, 10)

  const [modeDate, setModeDate] = useState<1 | 2>(1)
  const [dateDu, setDateDu] = useState(today)
  const [dateAu, setDateAu] = useState(today)

  const [partenaires, setPartenaires] = useState<PartenaireItem[]>([])
  const [selectedParts, setSelectedParts] = useState<Set<string>>(new Set())
  const [typesEtat, setTypesEtat] = useState<TypeEtatItem[]>([])
  const [idTypeEtat, setIdTypeEtat] = useState(0)

  const [scope, setScope] = useState<Scope>(1)
  const [prodGroupe, setProdGroupe] = useState(false)

  const [vendeur, setVendeur] = useState<SalarieItem | null>(
    stored
      ? {
          id_salarie: String(stored.id_salarie),
          nom: stored.nom,
          prenom: stored.prenom,
        }
      : null,
  )
  const [showVendeurPicker, setShowVendeurPicker] = useState(false)

  const [orga, setOrga] = useState<OrgaItem | null>(null)
  const [showOrgaPicker, setShowOrgaPicker] = useState(false)

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // Chargement des référentiels à l'ouverture
  useEffect(() => {
    if (!open) return
    const h = { Authorization: `Bearer ${getToken()}` }
    fetch(`${apiBase}/production/partenaires`, { headers: h })
      .then((r) => r.json())
      .then((d) => {
        setPartenaires(Array.isArray(d) ? d : [])
        // Pré-sélectionner les actifs par défaut
        const active = new Set<string>(
          (Array.isArray(d) ? d : [])
            .filter((p: PartenaireItem) => p.is_actif)
            .map((p: PartenaireItem) => p.prefix),
        )
        setSelectedParts(active)
      })
    fetch(`${apiBase}/production/etats`, { headers: h })
      .then((r) => r.json())
      .then((d) => setTypesEtat(Array.isArray(d) ? d : []))
  }, [open])

  const togglePart = (prefix: string) => {
    const s = new Set(selectedParts)
    if (s.has(prefix)) s.delete(prefix)
    else s.add(prefix)
    setSelectedParts(s)
  }

  const canSubmit = useMemo(() => {
    if (!dateDu || !dateAu || dateDu > dateAu) return false
    if (selectedParts.size === 0) return false
    if (scope === 1 && !vendeur) return false
    if (scope === 2 && !orga) return false
    return true
  }, [dateDu, dateAu, selectedParts, scope, vendeur, orga])

  const handleSubmit = async () => {
    setError('')
    if (!canSubmit) {
      setError('Veuillez compléter les champs requis')
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        mode_date: modeDate,
        date_du: toYMD(dateDu),
        date_au: toYMD(dateAu),
        partenaires: Array.from(selectedParts),
        id_type_etat: idTypeEtat,
        scope,
        id_salarie: scope === 1 ? vendeur!.id_salarie : '0',
        prod_groupe: scope === 1 ? prodGroupe : false,
        id_organigramme: scope === 2 ? orga!.id_organigramme : '0',
      }
      const res = await fetch(`${apiBase}/production/jobs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Erreur')
      }
      const data = await res.json()
      onCreated(data.id_job)
    } catch (e: any) {
      setError(e.message || 'Erreur à la création du job')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[92vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--c-line)] sticky top-0 bg-white z-10">
          <div>
            <h2 className="text-lg font-semibold text-[var(--c-ink)]">Nouvelle extraction</h2>
            <p className="text-xs text-[var(--c-ink-faint)] mt-0.5">
              L'extraction part en tâche de fond — tu pourras consulter le résultat plus tard.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--c-surface-medium)] text-[var(--c-ink-faint-2)] hover:text-[var(--c-ink-soft)]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Mode date */}
          <div>
            <label className="text-xs font-medium text-[var(--c-ink-faint)] uppercase tracking-wide mb-2 block">
              Mode
            </label>
            <div className="flex gap-2">
              {([
                [1, 'Par Période'],
                [2, 'Par mois de paiement'],
              ] as const).map(([k, label]) => (
                <button
                  key={k}
                  onClick={() => setModeDate(k)}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    modeDate === k
                      ? 'bg-[var(--c-inverse)] text-white'
                      : 'bg-[var(--c-surface-medium)] text-[var(--c-ink-soft)] hover:bg-[var(--c-surface-medium)]'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-[var(--c-ink-faint)] uppercase tracking-wide mb-1 block">
                Du
              </label>
              <div className="flex items-center gap-2 px-3 py-2 border border-[var(--c-line-strong)] rounded-lg">
                <Calendar className="w-4 h-4 text-[var(--c-ink-faint-2)]" />
                <input
                  type="date"
                  value={dateDu}
                  onChange={(e) => setDateDu(e.target.value)}
                  className="flex-1 border-0 text-sm focus:outline-none bg-transparent"
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--c-ink-faint)] uppercase tracking-wide mb-1 block">
                Au
              </label>
              <div className="flex items-center gap-2 px-3 py-2 border border-[var(--c-line-strong)] rounded-lg">
                <Calendar className="w-4 h-4 text-[var(--c-ink-faint-2)]" />
                <input
                  type="date"
                  value={dateAu}
                  onChange={(e) => setDateAu(e.target.value)}
                  className="flex-1 border-0 text-sm focus:outline-none bg-transparent"
                />
              </div>
            </div>
          </div>

          {/* Partenaires */}
          <div>
            <label className="text-xs font-medium text-[var(--c-ink-faint)] uppercase tracking-wide mb-2 block">
              Partenaires
            </label>
            <div className="grid grid-cols-3 gap-2">
              {partenaires.map((p) => {
                const selected = selectedParts.has(p.prefix)
                return (
                  <button
                    key={p.prefix}
                    onClick={() => togglePart(p.prefix)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition-colors ${
                      selected
                        ? 'border-[var(--c-inverse)] bg-[var(--c-inverse)] text-white'
                        : 'border-[var(--c-line)] bg-white hover:bg-[var(--c-surface-soft)]'
                    } ${!p.is_actif ? 'opacity-60' : ''}`}
                  >
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center shrink-0 ${
                        selected ? 'bg-white/20' : 'bg-[var(--c-surface-medium)]'
                      }`}
                    >
                      {selected && <Check className="w-3 h-3" />}
                    </div>
                    <span className="flex-1 text-left truncate">
                      {p.lib || p.prefix}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* État */}
          <div>
            <label className="text-xs font-medium text-[var(--c-ink-faint)] uppercase tracking-wide mb-1 block">
              État
            </label>
            <select
              value={idTypeEtat}
              onChange={(e) => setIdTypeEtat(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-[var(--c-line-strong)] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--c-inverse)]"
            >
              <option value={0}>Tous</option>
              {typesEtat.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.lib}
                </option>
              ))}
            </select>
          </div>

          {/* Scope */}
          <div>
            <label className="text-xs font-medium text-[var(--c-ink-faint)] uppercase tracking-wide mb-2 block">
              Périmètre
            </label>
            <div className="grid grid-cols-2 gap-2">
              {([
                [1, 'Vendeur', User],
                [2, 'Équipe', Users],
                [3, 'Réseau', Globe],
                [4, 'Réseau Hors Distrib', Globe],
              ] as const).map(([k, label, Icon]) => (
                <button
                  key={k}
                  onClick={() => setScope(k as Scope)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    scope === k
                      ? 'bg-[var(--c-inverse)] text-white border-[var(--c-inverse)]'
                      : 'bg-white text-[var(--c-ink-soft)] border-[var(--c-line)] hover:bg-[var(--c-surface-soft)]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Scope Vendeur : picker + Prod Groupe */}
          {scope === 1 && (
            <div className="space-y-3 border-t border-[var(--c-line-soft)] pt-4">
              <button
                onClick={() => setShowVendeurPicker(true)}
                className="w-full flex items-center justify-between px-3 py-2.5 border border-[var(--c-line-strong)] rounded-lg hover:bg-[var(--c-surface-soft)] text-sm"
              >
                <span className="flex items-center gap-2 text-[var(--c-ink-soft)]">
                  <User className="w-4 h-4 text-[var(--c-ink-faint-2)]" />
                  {vendeur ? (
                    <span className="font-medium">
                      {vendeur.nom} {capitalize(vendeur.prenom)}
                    </span>
                  ) : (
                    <span className="text-[var(--c-ink-faint-2)]">Choisir le vendeur</span>
                  )}
                </span>
                <ChevronDown className="w-4 h-4 text-[var(--c-ink-faint-2)]" />
              </button>
              <label className="flex items-center gap-2 text-sm text-[var(--c-ink-soft)]">
                <input
                  type="checkbox"
                  checked={prodGroupe}
                  onChange={(e) => setProdGroupe(e.target.checked)}
                  className="w-4 h-4"
                />
                Prod Groupe avec dérogation
              </label>
            </div>
          )}

          {/* Scope Équipe : picker orga */}
          {scope === 2 && (
            <div className="border-t border-[var(--c-line-soft)] pt-4">
              <button
                onClick={() => setShowOrgaPicker(true)}
                className="w-full flex items-center justify-between px-3 py-2.5 border border-[var(--c-line-strong)] rounded-lg hover:bg-[var(--c-surface-soft)] text-sm"
              >
                <span className="flex items-center gap-2 text-[var(--c-ink-soft)]">
                  <Users className="w-4 h-4 text-[var(--c-ink-faint-2)]" />
                  {orga ? (
                    <span className="font-medium">
                      {orga.parent_lib ? `${orga.parent_lib} → ` : ''}
                      {orga.lib_orga}
                    </span>
                  ) : (
                    <span className="text-[var(--c-ink-faint-2)]">Choisir l'équipe</span>
                  )}
                </span>
                <ChevronDown className="w-4 h-4 text-[var(--c-ink-faint-2)]" />
              </button>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>

        <div className="flex gap-2 px-6 py-4 border-t border-[var(--c-line)] bg-[var(--c-surface-soft)] sticky bottom-0">
          <button
            onClick={onClose}
            className="flex-1 px-3 py-2.5 border border-[var(--c-line-strong)] rounded-lg text-sm font-medium bg-white hover:bg-[var(--c-surface-medium)]"
          >
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
            className="flex-1 px-3 py-2.5 bg-[var(--c-inverse)] text-white rounded-lg text-sm font-medium hover:bg-[var(--c-inverse-hover)] disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            Lancer l'extraction
          </button>
        </div>
      </motion.div>

      {showVendeurPicker && (
        <VendeurPicker
          apiBase={apiBase}
          onClose={() => setShowVendeurPicker(false)}
          onSelect={(v) => {
            setVendeur(v)
            setShowVendeurPicker(false)
          }}
        />
      )}
      {showOrgaPicker && (
        <OrgaPicker
          apiBase={apiBase}
          onClose={() => setShowOrgaPicker(false)}
          onSelect={(o) => {
            setOrga(o)
            setShowOrgaPicker(false)
          }}
        />
      )}
    </motion.div>
  )
}

// ---- Sub-components ----

function VendeurPicker({
  apiBase,
  onClose,
  onSelect,
}: {
  apiBase: string
  onClose: () => void
  onSelect: (v: SalarieItem) => void
}) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<SalarieItem[]>([])
  const [loading, setLoading] = useState(false)

  const doSearch = () => {
    if (!q.trim()) return
    setLoading(true)
    fetch(`${apiBase}/production/vendeurs?q=${encodeURIComponent(q.trim())}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setResults)
      .catch(() => setResults([]))
      .finally(() => setLoading(false))
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 z-[60] flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-xl shadow-2xl w-full max-w-md"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--c-line)]">
          <h3 className="text-base font-semibold">Choisir un vendeur</h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[var(--c-surface-medium)] text-[var(--c-ink-faint-2)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <div className="flex gap-2">
            <input
              autoFocus
              type="text"
              placeholder="Nom…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) =>
                e.key === 'Enter' && (e.preventDefault(), doSearch())
              }
              className="flex-1 px-3 py-2 border border-[var(--c-line-strong)] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--c-inverse)]"
            />
            <button
              onClick={doSearch}
              className="px-3 py-2 border border-[var(--c-line-strong)] rounded-lg hover:bg-[var(--c-surface-soft)]"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto border border-[var(--c-line)] rounded-lg divide-y divide-[var(--c-line-soft)]">
            {results.length === 0 ? (
              <div className="text-center py-8 text-[var(--c-ink-faint-2)] text-sm">
                {loading ? '' : 'Saisis un nom…'}
              </div>
            ) : (
              results.map((v) => (
                <button
                  key={v.id_salarie}
                  onClick={() => onSelect(v)}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-[var(--c-surface-soft)]"
                >
                  <span className="font-medium">{v.nom}</span>{' '}
                  <span className="text-[var(--c-ink-muted)]">{capitalize(v.prenom)}</span>
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function OrgaPicker({
  apiBase,
  onClose,
  onSelect,
}: {
  apiBase: string
  onClose: () => void
  onSelect: (o: OrgaItem) => void
}) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<OrgaItem[]>([])
  const [loading, setLoading] = useState(false)

  const doSearch = () => {
    if (q.trim().length < 2) return
    setLoading(true)
    fetch(`${apiBase}/production/organigrammes?q=${encodeURIComponent(q.trim())}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setResults)
      .catch(() => setResults([]))
      .finally(() => setLoading(false))
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 z-[60] flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-xl shadow-2xl w-full max-w-md"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--c-line)]">
          <h3 className="text-base font-semibold">Choisir une équipe</h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[var(--c-surface-medium)] text-[var(--c-ink-faint-2)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <div className="flex gap-2">
            <input
              autoFocus
              type="text"
              placeholder="Nom d'équipe…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value)
                if (e.target.value.trim().length >= 2) {
                  // Auto-search au bout de 2 chars
                  setTimeout(doSearch, 200)
                }
              }}
              onKeyDown={(e) =>
                e.key === 'Enter' && (e.preventDefault(), doSearch())
              }
              className="flex-1 px-3 py-2 border border-[var(--c-line-strong)] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--c-inverse)]"
            />
            <button
              onClick={doSearch}
              className="px-3 py-2 border border-[var(--c-line-strong)] rounded-lg hover:bg-[var(--c-surface-soft)]"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto border border-[var(--c-line)] rounded-lg divide-y divide-[var(--c-line-soft)]">
            {results.length === 0 ? (
              <div className="text-center py-8 text-[var(--c-ink-faint-2)] text-sm">
                {loading ? '' : 'Saisis au moins 2 caractères…'}
              </div>
            ) : (
              results.map((o) => (
                <button
                  key={o.id_organigramme}
                  onClick={() => onSelect(o)}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-[var(--c-surface-soft)]"
                >
                  <div className="font-medium">{o.lib_orga}</div>
                  {o.parent_lib && (
                    <div className="text-xs text-[var(--c-ink-faint)]">{o.parent_lib}</div>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
