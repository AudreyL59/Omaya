/**
 * Module Fen_RecherchePOO (WinDev) - recherche multi-cibles ADM.
 *
 * 4 modes (Selecteur1 WinDev) :
 *   - Client    : adv.pgt_client (+ option NumBS via OEN_contrat.RefClient)
 *   - Contrat   : cross-partenaires (ENI/SFR/OEN/STR/VAL/IAG/TLC)
 *                 + option NumBS commencant par 'LOT' -> info_interne
 *   - Salarie   : rh.pgt_salarie + coord + embauche + societe + type_poste
 *   - CVtheque  : recrutement.pgt_cvtheque + cv_source
 *
 * Layout : 2 colonnes (form gauche 380px + tableau resultats 1fr).
 * Clic ligne (selon origine) :
 *   - Salarie : ouvre FicheSalarieModal (existant)
 *   - Contrat : placeholder (TODO ouvrir le ticket via id_tk_liste)
 *   - Client/CV : placeholder ('Fiche a venir')
 *
 * Btn 'Rech. avancee' : placeholder (Fen_RechercheAvancee a coder plus tard).
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Eraser,
  FileText,
  Loader2,
  Plus,
  Search,
  Sliders,
  User as UserIcon,
} from 'lucide-react'

import { getToken } from '@/api'
import FicheSalarieModal from '@/components/FicheSalarieModal'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { showToast } from '@shared/ui/dialog'

type Mode = 'client' | 'contrat' | 'salarie' | 'cv'

const MODES: { key: Mode; label: string }[] = [
  { key: 'client', label: 'Client' },
  { key: 'contrat', label: 'Contrat' },
  { key: 'salarie', label: 'Salarié' },
  { key: 'cv', label: 'CVthèque' },
]

interface SearchRow {
  origine: 'CLIENT' | 'CONTRAT' | 'SALARIE' | 'CV'
  id: string
  att1: string
  att2: string
  att3: string
  att4: string
  att5: string
  att6: string
  att7: string
  att_aff?: string
  has_photo?: boolean
  en_activite?: boolean
}

interface Criteres {
  nom: string
  prenom: string
  tel: string
  mail: string
  id: string
  num_bs: string
}

const EMPTY_CRITERES: Criteres = {
  nom: '',
  prenom: '',
  tel: '',
  mail: '',
  id: '',
  num_bs: '',
}

// Couleurs cohérentes avec EmbaucheTab (cf. autres pages ADM)
const COLOR_PRIMARY = '#17494E'
const COLOR_BRUN = '#4E1D17'
const COLOR_BG_SOFT = '#EFE9E7'

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

// Définition des colonnes par mode (cf. WinDev libellés, tri, largeurs).
// Colonne 1 = icône 60px (cf. screen WinDev avec photo ronde). Largeurs
// textuelles ajustées pour montrer le contenu sans tronquer en standard.
const COLS_BY_MODE: Record<
  Mode,
  {
    headers: string[]
    showAff: boolean
    affLabel?: string
    template: string
    fmt?: ((v: string) => string)[]
  }
> = {
  client: {
    headers: ['Nom', 'Prénom', 'CP Ville', 'Mobile', 'Fixe', 'Mail'],
    showAff: false,
    template: '60px minmax(140px,1.2fr) minmax(120px,1fr) minmax(160px,1.2fr) 120px 120px minmax(180px,1.4fr)',
  },
  contrat: {
    headers: ['Num BS', 'Vendeur', 'Date Signature', 'Produit', 'État', 'Partenaire'],
    showAff: false,
    template: '60px minmax(120px,1fr) minmax(160px,1.2fr) 120px minmax(160px,1.4fr) minmax(140px,1.2fr) 100px',
    fmt: [(v) => v, (v) => v, fmtDate, (v) => v, (v) => v, (v) => v],
  },
  salarie: {
    headers: ['Nom Prénom', 'Entité - Poste', 'Date Embauche', 'Sortie', 'Mobile', 'Mail'],
    showAff: true,
    affLabel: 'Affectation',
    template: '60px minmax(220px,1.6fr) minmax(220px,1.6fr) 110px minmax(180px,1.2fr) 130px minmax(180px,1.4fr) minmax(120px,1fr)',
    fmt: [(v) => v, (v) => v, fmtDate, (v) => v, (v) => v, (v) => v],
  },
  cv: {
    headers: ['Nom Prénom', 'CP Ville', 'Date Saisie', 'Source', 'Mobile', 'Mail'],
    showAff: true,
    affLabel: 'Statut CV',
    template: '60px minmax(200px,1.5fr) minmax(140px,1fr) 110px minmax(120px,1fr) 130px minmax(180px,1.4fr) minmax(120px,1fr)',
    fmt: [(v) => v, (v) => v, fmtDate, (v) => v, (v) => v, (v) => v],
  },
}

export default function RecherchePage() {
  useDocumentTitle('Recherche')
  const [mode, setMode] = useState<Mode>('client')
  const [criteres, setCriteres] = useState<Criteres>(EMPTY_CRITERES)
  const [results, setResults] = useState<SearchRow[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [openFiche, setOpenFiche] = useState<{
    id: string
    nom: string
    prenom: string
  } | null>(null)

  const setField = (k: keyof Criteres) => (v: string) =>
    setCriteres((c) => ({ ...c, [k]: v }))

  const validate = (): string | null => {
    // Cf. WinDev : si Nom rempli et taille < 2 -> erreur
    const nom = criteres.nom.replace(/\s+/g, '')
    if (nom && nom.length < 2) {
      return 'Le nom doit comporter au moins 2 caractères.'
    }
    const hasAny =
      nom || criteres.prenom || criteres.tel || criteres.mail || criteres.id || criteres.num_bs
    if (!hasAny) {
      return 'Renseignez au moins un critère.'
    }
    // Cf. WinDev mode contrat : NumBS ou ID obligatoire
    if (mode === 'contrat' && !criteres.num_bs && !criteres.id) {
      return 'Mode Contrat : renseignez un Numéro de BS ou un ID.'
    }
    return null
  }

  const handleSearch = useCallback(async () => {
    const err = validate()
    if (err) {
      showToast(err, 'info')
      return
    }
    setLoading(true)
    setSearched(true)
    try {
      const r = await fetch(`/api/adm/recherche/${mode}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(criteres),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as SearchRow[]
      setResults(Array.isArray(j) ? j : [])
    } catch (e) {
      showToast(`Échec recherche : ${(e as Error).message}`, 'error')
      setResults([])
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, criteres])

  const handleClearForm = () => setCriteres(EMPTY_CRITERES)

  const handleNouvelleRech = () => {
    setCriteres(EMPTY_CRITERES)
    setResults([])
    setSearched(false)
  }

  const handleRowClick = (row: SearchRow) => {
    switch (row.origine) {
      case 'SALARIE': {
        const [nom, ...rest] = row.att2.split(' ')
        const prenom = rest.join(' ')
        setOpenFiche({ id: row.id, nom: nom || '', prenom: prenom || '' })
        break
      }
      case 'CONTRAT':
        showToast(
          `Fiche contrat ${row.att2} (${row.att7}) : à implémenter (ouverture ticket).`,
          'info',
        )
        break
      case 'CLIENT':
        showToast('Fiche client : à venir.', 'info')
        break
      case 'CV':
        showToast('Fiche CV : à venir.', 'info')
        break
    }
  }

  const cfg = COLS_BY_MODE[mode]

  return (
    <div className="flex h-[calc(100vh-100px)] gap-3 p-4">
      {/* --- Colonne gauche : Formulaire ----------------------------- */}
      <div
        className="w-[380px] shrink-0 flex flex-col gap-3 rounded-lg border p-3"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
      >
        <div className="flex items-center gap-2">
          <Search className="w-5 h-5" style={{ color: COLOR_PRIMARY }} />
          <h1 className="text-base font-bold" style={{ color: COLOR_BRUN }}>
            Recherche
          </h1>
        </div>

        {/* En-tete : 2 boutons (Nouvelle Rech / Rech. avancée) */}
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={handleNouvelleRech}
            className="inline-flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs rounded border"
            style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
          >
            <Plus className="w-3.5 h-3.5" />
            Nouvelle Rech.
          </button>
          <button
            type="button"
            onClick={() =>
              showToast(
                'Recherche avancée : à venir (Fen_RechercheAvancée).',
                'info',
              )
            }
            className="inline-flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs rounded border"
            style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
          >
            <Sliders className="w-3.5 h-3.5" />
            Rech. avancée
          </button>
        </div>

        {/* Selecteur de mode (cf. Selecteur1 WinDev) */}
        <div className="flex rounded overflow-hidden" style={{ border: `1px solid ${COLOR_PRIMARY}` }}>
          {MODES.map((m) => (
            <button
              key={m.key}
              type="button"
              onClick={() => setMode(m.key)}
              className="flex-1 px-2 py-1.5 text-xs font-medium transition"
              style={{
                backgroundColor: mode === m.key ? COLOR_PRIMARY : 'transparent',
                color: mode === m.key ? 'white' : COLOR_PRIMARY,
              }}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Champs de saisie */}
        <div className="flex flex-col gap-2">
          <Field
            placeholder="TOUT EN MAJUSCULE (SANS ACCENT)"
            value={criteres.nom}
            onChange={(v) => setField('nom')(v.toUpperCase())}
            label="Nom"
          />
          <Field
            placeholder="TOUT EN MAJUSCULE (SANS ACCENT)"
            value={criteres.prenom}
            onChange={setField('prenom')}
            label="Prénom"
          />
          <Field
            placeholder="1234567890"
            value={criteres.tel}
            onChange={setField('tel')}
            label="Téléphone"
          />
          <Field
            placeholder="tout en minuscules"
            value={criteres.mail}
            onChange={(v) => setField('mail')(v.toLowerCase())}
            label="Mail"
          />
          <Field
            placeholder="1234567890"
            value={criteres.id}
            onChange={setField('id')}
            label="ID"
          />
          <Field
            placeholder="TOUT EN MAJUSCULE (SANS ACCENT)"
            value={criteres.num_bs}
            onChange={(v) => setField('num_bs')(v.toUpperCase())}
            label="Num BS"
          />
        </div>

        {/* Bouton Rechercher (gros) */}
        <button
          type="button"
          onClick={() => void handleSearch()}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded text-white disabled:opacity-40"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          Rechercher
        </button>

        {/* Btn Vider formulaire */}
        <button
          type="button"
          onClick={handleClearForm}
          className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs rounded border w-fit"
          style={{ borderColor: '#B91C1C', color: '#B91C1C' }}
        >
          <Eraser className="w-3.5 h-3.5" />
          Vider formulaire de recherche
        </button>
      </div>

      {/* --- Colonne droite : Résultats ------------------------------ */}
      <div
        className="flex-1 flex flex-col rounded-lg border overflow-hidden"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
      >
        {/* Header tableau (centré comme WinDev) */}
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: cfg.template,
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          {/* Placeholder explicite pour la colonne icône */}
          <div className="min-w-0" />
          {cfg.headers.map((h) => (
            <div key={h} className="text-center min-w-0 truncate">
              {h}
            </div>
          ))}
          {cfg.showAff && (
            <div className="text-center min-w-0 truncate">{cfg.affLabel}</div>
          )}
        </div>

        {/* Lignes */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-6 flex items-center justify-center">
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: COLOR_PRIMARY }} />
            </div>
          )}
          {!loading && searched && results.length === 0 && (
            <div className="p-6 text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun résultat trouvé.
            </div>
          )}
          {!loading && !searched && results.length === 0 && (
            <div className="p-6 text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.5 }}>
              Saisissez un critère puis cliquez sur Rechercher.
            </div>
          )}
          {results.map((r, idx) => {
            const atts = [r.att2, r.att3, r.att4, r.att5, r.att6, r.att7]
            const formatted = atts.map((v, i) =>
              cfg.fmt && cfg.fmt[i] ? cfg.fmt[i](v) : v,
            )
            return (
              <div
                key={`${r.origine}-${r.id}-${idx}`}
                onClick={() => handleRowClick(r)}
                onDoubleClick={() => handleRowClick(r)}
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer hover:bg-[#FBF6F4]"
                style={{
                  gridTemplateColumns: cfg.template,
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
                title="Cliquer pour ouvrir la fiche"
              >
                {/* Wrapper stable pour l'icône (centré dans la cellule 60px) */}
                <div className="flex items-center justify-center min-w-0">
                  <RowIcon row={r} />
                </div>
                {formatted.map((v, i) => (
                  <div key={i} className="truncate min-w-0" title={v}>
                    {v || '—'}
                  </div>
                ))}
                {cfg.showAff && (
                  <div className="truncate min-w-0" title={r.att_aff}>
                    {r.att_aff || '—'}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Fiche salarié (modal) */}
      {openFiche && (
        <FicheSalarieModal
          idSalarie={openFiche.id}
          nom={openFiche.nom}
          prenom={openFiche.prenom}
          onClose={() => setOpenFiche(null)}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers UI
// ---------------------------------------------------------------------------

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-[10px]" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="px-2 py-1.5 text-sm rounded border"
        style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
      />
    </div>
  )
}

function RowIcon({ row }: { row: SearchRow }) {
  // Tailles fixes : 40x40 cercle (cf. screen WinDev avec photo ronde)
  const wrapperClass =
    'flex items-center justify-center rounded-full shrink-0'
  const wrapperStyle = {
    backgroundColor: COLOR_BG_SOFT,
    width: 40,
    height: 40,
  } as const
  const iconClass = 'w-5 h-5'
  const iconStyle = { color: COLOR_PRIMARY } as const

  switch (row.origine) {
    case 'CLIENT':
      return (
        <div className={wrapperClass} style={wrapperStyle}>
          <UserIcon className={iconClass} style={iconStyle} />
        </div>
      )
    case 'CV':
      return (
        <div className={wrapperClass} style={wrapperStyle}>
          <FileText className={iconClass} style={iconStyle} />
        </div>
      )
    case 'SALARIE':
      // L'endpoint photo est protege par Bearer token : on ne peut pas
      // mettre l'URL dans <img src=...> tel quel (le navigateur n'envoie
      // pas le header et le serveur repond 401 avec WWW-Authenticate ->
      // popup d'auth basique). On fetch en JS via AuthPhoto.
      return (
        <AuthPhoto
          src={`/api/adm/fiche-salarie/${row.id}/photo`}
          fallback={
            <div className={wrapperClass} style={wrapperStyle}>
              <UserIcon className={iconClass} style={iconStyle} />
            </div>
          }
        />
      )
    case 'CONTRAT':
      // TODO : afficher logo partenaire (att7) via /api/adm/partenaire/{prefix}/logo
      return (
        <div className={wrapperClass} style={wrapperStyle}>
          <FileText className={iconClass} style={iconStyle} />
        </div>
      )
  }
}

/**
 * Photo servie par un endpoint protégé Bearer. On la fetch en JS pour
 * pouvoir passer l'Authorization header, puis on l'affiche via objectURL.
 * Si le fetch échoue (404 ou autre), on rend le fallback.
 */
function AuthPhoto({
  src,
  fallback,
}: {
  src: string
  fallback: React.ReactNode
}) {
  const [blobUrl, setBlobUrl] = useState<string>('')
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!src) return
    let cancelled = false
    let createdUrl = ''
    ;(async () => {
      try {
        const r = await fetch(src, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) {
          if (!cancelled) setFailed(true)
          return
        }
        const blob = await r.blob()
        if (cancelled) return
        createdUrl = URL.createObjectURL(blob)
        setBlobUrl(createdUrl)
      } catch {
        if (!cancelled) setFailed(true)
      }
    })()
    return () => {
      cancelled = true
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [src])

  if (failed || !blobUrl) {
    return <>{fallback}</>
  }
  return (
    <img
      src={blobUrl}
      alt=""
      className="rounded-full object-cover shrink-0"
      style={{ width: 40, height: 40 }}
    />
  )
}
