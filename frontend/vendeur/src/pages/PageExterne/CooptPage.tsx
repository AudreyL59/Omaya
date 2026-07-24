/**
 * Page publique de saisie de cooptation — accessible sans login.
 *
 * URL : /vendeur/PageExterne/coopt?c=<idCoopteur>&s=<hmacSha256>
 * Lien genere par le coopteur depuis l'app mobile et partage au filleul.
 *
 * V1 : formulaire sans bouton de validation (juste les champs).
 * La signature 's' protege contre le bruteforce d'IDs.
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Check, Loader2, User, XCircle } from 'lucide-react'
import logoOmaya from '@/assets/logo-omaya.png'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'

interface CoopteurInfo {
  id: string
  nom: string
  prenom: string
}

interface VilleItem {
  id: string
  cp: string
  nom_ville: string
}

export default function CooptPage() {
  const [params] = useSearchParams()
  const c = params.get('c') || ''
  const s = params.get('s') || ''

  const [coopteur, setCoopteur] = useState<CoopteurInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Champs formulaire (comme le modal Ajouter une cooptation)
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [dateNaiss, setDateNaiss] = useState('')
  const [age, setAge] = useState('')
  const [cp, setCp] = useState('')
  const [idVille, setIdVille] = useState('0')
  const [villes, setVilles] = useState<VilleItem[]>([])
  const [loadingVilles, setLoadingVilles] = useState(false)
  const [gsm, setGsm] = useState('')

  useEffect(() => {
    if (!c || !s) {
      setError('Lien invalide (paramètres manquants)')
      setLoading(false)
      return
    }
    const qs = `c=${encodeURIComponent(c)}&s=${encodeURIComponent(s)}`
    fetch(`/api/public/coopt/coopteur?${qs}`)
      .then(async (r) => {
        if (r.status === 401) throw new Error('Lien invalide ou expiré')
        if (r.status === 404) throw new Error('Coopteur introuvable')
        if (!r.ok) throw new Error(`Erreur ${r.status}`)
        return r.json()
      })
      .then((d: CoopteurInfo) => setCoopteur(d))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [c, s])

  const searchVilles = () => {
    if (!cp || !c || !s) return
    setLoadingVilles(true)
    const qs = `c=${encodeURIComponent(c)}&s=${encodeURIComponent(s)}`
    fetch(`/api/public/coopt/villes/${encodeURIComponent(cp)}?${qs}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: VilleItem[]) => {
        setVilles(data)
        if (data.length === 1) setIdVille(data[0].id)
      })
      .catch(() => setVilles([]))
      .finally(() => setLoadingVilles(false))
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center"
           style={{ backgroundColor: '#F8F5F4' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: COL_PRIMARY }} />
      </div>
    )
  }

  if (error || !coopteur) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4"
           style={{ backgroundColor: '#F8F5F4' }}>
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center"
             style={{ border: `1px solid ${COL_BORDER}` }}>
          <XCircle className="w-12 h-12 mx-auto mb-3" style={{ color: '#B91C1C' }} />
          <h1 className="text-lg font-bold mb-2" style={{ color: COL_BRUN }}>
            Lien invalide
          </h1>
          <p className="text-sm" style={{ color: COL_BRUN }}>
            {error || "Ce lien de cooptation n'est pas valide."}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
         style={{ backgroundColor: '#F8F5F4' }}>
      <div className="bg-white rounded-xl shadow-lg max-w-lg w-full overflow-hidden"
           style={{ border: `1px solid ${COL_BORDER}` }}>
        {/* HEADER */}
        <div className="p-5 text-center text-white"
             style={{ backgroundColor: COL_PRIMARY }}>
          <img src={logoOmaya} alt="Omaya"
               className="w-12 h-12 mx-auto mb-2 bg-white rounded-full p-1" />
          <h1 className="text-lg font-semibold">Cooptation Omaya</h1>
        </div>

        {/* ENCART COOPTEUR */}
        <div className="mx-5 mt-5 rounded-lg p-4 flex items-center gap-3"
             style={{ backgroundColor: '#F8F5F4',
                       border: `1px solid ${COL_BORDER}` }}>
          <div className="w-10 h-10 rounded-full flex items-center justify-center"
               style={{ backgroundColor: COL_PRIMARY }}>
            <User className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <p className="text-xs uppercase tracking-wide"
               style={{ color: COL_BRUN, opacity: 0.7 }}>
              Vous êtes coopté(e) par
            </p>
            <p className="text-base font-semibold" style={{ color: COL_BRUN }}>
              {coopteur.prenom} {coopteur.nom}
            </p>
          </div>
        </div>

        {/* FORMULAIRE */}
        <form className="p-5 space-y-3" onSubmit={(e) => e.preventDefault()}>
          <input
            type="text"
            placeholder="Nom"
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            className="w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2"
            style={{ borderColor: COL_BORDER }}
          />
          <input
            type="text"
            placeholder="Prénom"
            value={prenom}
            onChange={(e) => setPrenom(e.target.value)}
            className="w-full px-3 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2"
            style={{ borderColor: COL_BORDER }}
          />

          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <label className="text-xs block mb-1" style={{ color: COL_BRUN, opacity: 0.7 }}>
                Né(e) le
              </label>
              <input
                type="date"
                value={dateNaiss}
                onChange={(e) => setDateNaiss(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                style={{ borderColor: COL_BORDER }}
              />
            </div>
            <div className="w-24">
              <label className="text-xs block mb-1" style={{ color: COL_BRUN, opacity: 0.7 }}>
                ou âge
              </label>
              <input
                type="number"
                placeholder="Âge"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm"
                style={{ borderColor: COL_BORDER }}
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
              className="w-24 px-3 py-2.5 border rounded-lg text-sm"
              style={{ borderColor: COL_BORDER }}
            />
            <button
              type="button"
              onClick={searchVilles}
              className="px-3 py-2.5 border rounded-lg hover:bg-gray-50"
              style={{ borderColor: COL_BORDER }}
            >
              {loadingVilles ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" style={{ color: COL_BRUN }} />
              )}
            </button>
            <select
              value={idVille}
              onChange={(e) => setIdVille(e.target.value)}
              className="flex-1 px-3 py-2.5 border rounded-lg text-sm bg-white"
              style={{ borderColor: COL_BORDER }}
              disabled={villes.length === 0}
            >
              <option value="0">Ville</option>
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
            className="w-full px-3 py-2.5 border rounded-lg text-sm"
            style={{ borderColor: COL_BORDER }}
          />
        </form>
      </div>
    </div>
  )
}
