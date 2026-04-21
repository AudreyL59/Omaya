import { useState, useEffect, type FormEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { UserPlus, Loader2, X, Search, Check } from 'lucide-react'
import { getToken, getStoredUser } from '@/api'

interface CooptationItem {
  nom: string
  prenom: string
  date_saisie: string
}

interface VendeurItem {
  id_salarie: string
  nom: string
  prenom: string
  poste: string
}

interface VilleItem {
  id: number
  nom_ville: string
  cp: string
}

const LIENS_PARENTE = [
  'Père / Mère',
  'Grand-Père / Grand-Mère',
  'Cousin(e)',
  'Oncle / Tante',
  'Frère / Sœur',
  'Ami(e)',
  'Conjoint(e) / Epoux(se)',
  'Connaissance',
  'Client / Cliente',
  'Autre',
]

function formatDateSaisie(raw: string): string {
  if (!raw) return ''
  // Format ISO : 2026-04-20T20:12:34 ou 2026-04-20 20:12:34
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (iso) {
    return `${iso[3]}/${iso[2]}/${iso[1]} ${iso[4]}:${iso[5]}`
  }
  // Format WinDev : YYYYMMDDHHMMSSmmm
  if (raw.length >= 12 && /^\d+$/.test(raw.slice(0, 12))) {
    return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)} ${raw.slice(8, 10)}:${raw.slice(10, 12)}`
  }
  return raw
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

export default function CooptationPage() {
  const [items, setItems] = useState<CooptationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  const loadItems = () => {
    setLoading(true)
    fetch('/api/vendeur/cooptation', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(loadItems, [])

  return (
    <div className="p-8 max-w-5xl">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cooptations</h1>
          <p className="text-gray-500 mt-1">Mes cooptations du jour</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors shadow-sm"
        >
          <UserPlus className="w-4 h-4" />
          Nouvelle cooptation
        </button>
      </motion.div>

      <div className="mt-6 bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">
            Aucune cooptation saisie aujourd'hui
          </div>
        ) : (
          <div className="max-h-[500px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  <th className="text-left px-6 py-3">Nom</th>
                  <th className="text-left px-6 py-3">Prénom</th>
                  <th className="text-left px-6 py-3">Saisie le</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr
                    key={i}
                    className="border-t border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-6 py-3 font-medium text-gray-900">{item.nom}</td>
                    <td className="px-6 py-3 text-gray-700">{capitalize(item.prenom)}</td>
                    <td className="px-6 py-3 text-gray-500">
                      {formatDateSaisie(item.date_saisie)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!loading && items.length > 0 && (
          <div className="px-6 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
            {items.length} cooptation{items.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      <AnimatePresence>
        {showForm && (
          <CooptationForm
            onClose={() => setShowForm(false)}
            onCreated={() => {
              setShowForm(false)
              loadItems()
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function CooptationForm({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const currentUser = getStoredUser()
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [dateNaiss, setDateNaiss] = useState('')
  const [age, setAge] = useState('')
  const [cp, setCp] = useState('')
  const [villes, setVilles] = useState<VilleItem[]>([])
  const [idVille, setIdVille] = useState<number>(0)
  const [loadingVilles, setLoadingVilles] = useState(false)
  const [gsm, setGsm] = useState('')
  const [commentaire, setCommentaire] = useState('')
  const [cooptation_directe, setCooptationDirecte] = useState(false)
  const [nomParrain, setNomParrain] = useState('')
  const [lienParente, setLienParente] = useState('')
  const [idVendeur, setIdVendeur] = useState<string>(
    currentUser?.id_salarie ? String(currentUser.id_salarie) : ''
  )
  const [nomVendeur, setNomVendeur] = useState(
    currentUser ? `${currentUser.nom} ${capitalize(currentUser.prenom)}` : ''
  )
  const [showCoopteurPicker, setShowCoopteurPicker] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const searchVilles = () => {
    if (!cp) return
    setLoadingVilles(true)
    fetch(`/api/vendeur/cooptation/villes/${cp}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((data: VilleItem[]) => {
        setVilles(data)
        if (data.length === 1) setIdVille(data[0].id)
      })
      .catch(() => {})
      .finally(() => setLoadingVilles(false))
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!cp) return setError('Code postal requis')
    if (!idVendeur || idVendeur === '0') return setError('Veuillez choisir le coopteur')
    if (idVille === 0) return setError('Veuillez choisir la ville')
    if (!gsm) return setError('Numéro de téléphone requis')
    if (!cooptation_directe && !lienParente)
      return setError('Veuillez indiquer le lien de parenté du parrain')

    setSubmitting(true)
    try {
      const res = await fetch('/api/vendeur/cooptation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          nom,
          prenom,
          date_naissance: dateNaiss.replace(/-/g, ''),
          age: parseInt(age) || 0,
          cp,
          id_ville: idVille,
          gsm,
          commentaire,
          id_vendeur: idVendeur,
          cooptation_directe,
          nom_parrain: nomParrain,
          lien_parente: lienParente,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Erreur')
      }
      onCreated()
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la création')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
            <h2 className="text-lg font-semibold text-gray-900">Ajouter une cooptation</h2>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-3">
            <input
              type="text"
              placeholder="Nom"
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              required
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
            />
            <input
              type="text"
              placeholder="Prénom"
              value={prenom}
              onChange={(e) => setPrenom(e.target.value)}
              required
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
            />

            <div className="flex gap-2 items-center">
              <div className="flex-1">
                <label className="text-xs text-gray-500 block mb-1">Né(e) le</label>
                <input
                  type="date"
                  value={dateNaiss}
                  onChange={(e) => setDateNaiss(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              <div className="w-24">
                <label className="text-xs text-gray-500 block mb-1">ou âge</label>
                <input
                  type="number"
                  placeholder="Âge"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                placeholder="CP"
                value={cp}
                onChange={(e) => setCp(e.target.value)}
                onBlur={searchVilles}
                maxLength={5}
                className="w-24 px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
              />
              <button
                type="button"
                onClick={searchVilles}
                className="px-3 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                {loadingVilles ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Check className="w-4 h-4 text-gray-700" />
                )}
              </button>
              <select
                value={idVille}
                onChange={(e) => setIdVille(parseInt(e.target.value))}
                className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                disabled={villes.length === 0}
              >
                <option value={0}>Ville</option>
                {villes.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.nom_ville} ({v.cp})
                  </option>
                ))}
              </select>
            </div>

            <input
              type="tel"
              placeholder="Mobile"
              value={gsm}
              onChange={(e) => setGsm(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
            />

            <textarea
              placeholder="Commentaire"
              value={commentaire}
              onChange={(e) => setCommentaire(e.target.value)}
              rows={3}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm resize-none"
            />

            <button
              type="button"
              onClick={() => setShowCoopteurPicker(true)}
              className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 text-gray-900"
            >
              {nomVendeur || 'Choisir le coopteur'}
            </button>

            <label className="flex items-center gap-2 text-sm text-gray-700 pt-1">
              <input
                type="checkbox"
                checked={cooptation_directe}
                onChange={(e) => setCooptationDirecte(e.target.checked)}
                className="w-4 h-4"
              />
              Cooptation Directe
            </label>

            {!cooptation_directe && (
              <>
                <input
                  type="text"
                  placeholder="Nom du Parrain"
                  value={nomParrain}
                  onChange={(e) => setNomParrain(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                />
                <select
                  value={lienParente}
                  onChange={(e) => setLienParente(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="">---- Lien de cooptation ----</option>
                  {LIENS_PARENTE.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </>
            )}

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full px-3 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Valider
            </button>
          </form>
        </motion.div>
      </motion.div>

      <AnimatePresence>
        {showCoopteurPicker && (
          <CoopteurPicker
            onClose={() => setShowCoopteurPicker(false)}
            onSelect={(v) => {
              setIdVendeur(v.id_salarie)
              setNomVendeur(`${v.nom} ${capitalize(v.prenom)}`)
              setShowCoopteurPicker(false)
            }}
          />
        )}
      </AnimatePresence>
    </>
  )
}

function CoopteurPicker({
  onClose,
  onSelect,
}: {
  onClose: () => void
  onSelect: (v: VendeurItem) => void
}) {
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<VendeurItem[]>([])
  const [selected, setSelected] = useState<VendeurItem | null>(null)
  const [loading, setLoading] = useState(false)

  const doSearch = () => {
    if (!search.trim()) return
    setLoading(true)
    fetch(`/api/vendeur/cooptation/vendeurs?q=${encodeURIComponent(search.trim())}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setResults)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Choisir le coopteur</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Nom du coopteur"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), doSearch())}
              autoFocus
              className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
            />
            <button
              type="button"
              onClick={doSearch}
              className="px-3 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4 text-gray-700" />
              )}
            </button>
          </div>

          <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
            {results.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm">
                {loading ? '' : 'Aucun résultat'}
              </div>
            ) : (
              results.map((v) => (
                <button
                  key={v.id_salarie}
                  type="button"
                  onClick={() => setSelected(v)}
                  className={`w-full text-left px-4 py-2.5 text-sm border-b border-gray-100 last:border-0 hover:bg-gray-50 ${
                    selected?.id_salarie === v.id_salarie ? 'bg-gray-100' : ''
                  }`}
                >
                  <span className="font-medium text-gray-900">{v.nom}</span>{' '}
                  <span className="text-gray-600">{capitalize(v.prenom)}</span>
                  {v.poste && <span className="text-gray-400 text-xs"> ({v.poste})</span>}
                </button>
              ))
            )}
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={() => selected && onSelect(selected)}
              disabled={!selected}
              className="flex-1 px-3 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
            >
              Valider
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50"
            >
              Annuler
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
