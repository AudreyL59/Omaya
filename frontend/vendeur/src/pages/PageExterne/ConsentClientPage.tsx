/**
 * Page publique de consentement client (fin d'appel Call) — sans login.
 *
 * URL : /vendeur/PageExterne/consent-client?p=<TypeTK><IdTicket>
 *       ex. ?p=SFR20220315123456789  ou  ?p=ENI...
 *
 * Portage Page_ConsentClient WinDev :
 *   - Plan 1 : formulaire (info client + panier + 2 interrupteurs + valider)
 *   - Plan 2 : "Merci de transmettre le code ci-dessous au vendeur"
 *
 * Regle UX : le bouton Valider est desactive tant que le client n'a pas
 * choisi J'accepte OU Je refuse sur l'option Rappel (option "facultative"
 * partenaire a un defaut = "J'accepte le partage").
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Loader2, XCircle } from 'lucide-react'
import logoOmaya from '@/assets/logo-omaya.png'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_GREEN = '#0F8C4E'
const COL_RED = '#8C1F1F'

interface PanierLine {
  type: string
  nom: string
  montant: number | null
  id_panier: string
}

interface PublicConsent {
  type_tk: string
  id_ticket: string
  info_client: string
  code_valid: string
  deja_valide: boolean
  panier: PanierLine[]
}

export default function ConsentClientPage() {
  const [params] = useSearchParams()
  const p = params.get('p') || ''

  const [data, setData] = useState<PublicConsent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Etat interrupteurs
  // rappel: null tant que non choisi, true si "J'accepte", false si "Je refuse"
  const [rappel, setRappel] = useState<boolean | null>(null)
  // partagePartenaire (option facultative) : defaut = true = J'accepte le partage
  const [partagePartenaire, setPartagePartenaire] = useState(true)

  const [submitting, setSubmitting] = useState(false)
  const [showCode, setShowCode] = useState(false)  // plan 2

  useEffect(() => {
    if (!p) {
      setError('Lien invalide (paramètre manquant)')
      setLoading(false)
      return
    }
    fetch(`/api/public/consent-client?p=${encodeURIComponent(p)}`)
      .then(async (r) => {
        if (r.status === 404) throw new Error('Ticket introuvable')
        if (!r.ok) throw new Error(`Erreur ${r.status}`)
        return r.json()
      })
      .then((d: PublicConsent) => {
        setData(d)
        // Si deja_valide = true (Opt_Rappel=1 en BDD), on affiche direct le plan 2
        if (d.deja_valide) setShowCode(true)
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [p])

  const valider = async () => {
    if (rappel === null || !data) return
    setSubmitting(true)
    try {
      // Semantique WinDev inversee : Opt_Partenaire = 1 = OPPOSITION.
      // partagePartenaire=true (J'accepte le partage) -> opt_oppose_partenaire=false
      const body = {
        opt_rappel: rappel,
        opt_oppose_partenaire: !partagePartenaire,
      }
      const r = await fetch(
        `/api/public/consent-client/validate?p=${encodeURIComponent(p)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const res = await r.json()
      // Met a jour le code (au cas ou il ne serait pas rempli en BDD avant)
      if (res.code_valid) {
        setData({ ...data, code_valid: res.code_valid })
      }
      // Bascule plan 2 uniquement si Rappel = J'accepte
      if (rappel) setShowCode(true)
      else alert('Vos choix ont bien été enregistrés.')
    } catch (e) {
      alert(`Erreur : ${(e as Error).message}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center"
           style={{ backgroundColor: '#FDECEA' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: COL_PRIMARY }} />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4"
           style={{ backgroundColor: '#FDECEA' }}>
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center"
             style={{ border: `1px solid ${COL_BORDER}` }}>
          <XCircle className="w-12 h-12 mx-auto mb-3" style={{ color: '#B91C1C' }} />
          <h1 className="text-lg font-bold mb-2" style={{ color: COL_BRUN }}>
            Lien invalide
          </h1>
          <p className="text-sm" style={{ color: COL_BRUN }}>
            {error || "Ce lien de consentement n'est pas valide."}
          </p>
        </div>
      </div>
    )
  }

  // -----------------------------------------------------------------------
  // PLAN 2 : "Merci de transmettre le code ci-dessous au vendeur"
  // -----------------------------------------------------------------------
  if (showCode) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4"
           style={{ backgroundColor: '#FDECEA' }}>
        <div className="bg-white rounded-xl shadow-lg max-w-lg w-full overflow-hidden"
             style={{ border: `1px solid ${COL_BORDER}` }}>
          <div className="p-5 text-center text-white"
               style={{ backgroundColor: COL_PRIMARY }}>
            <img src={logoOmaya} alt="Omaya"
                 className="w-12 h-12 mx-auto mb-2 bg-white rounded-full p-1" />
            <h1 className="text-lg font-semibold">Confirmation</h1>
          </div>
          <div className="p-8 text-center">
            <p className="text-sm mb-6" style={{ color: COL_BRUN }}>
              Merci de transmettre le code ci-dessous au vendeur
            </p>
            <div className="inline-block px-8 py-4 rounded-lg font-mono text-3xl font-bold tracking-widest"
                 style={{
                   backgroundColor: '#F8F5F4',
                   border: `2px solid ${COL_PRIMARY}`,
                   color: COL_BRUN,
                 }}>
              {data.code_valid || '—'}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // -----------------------------------------------------------------------
  // PLAN 1 : formulaire
  // -----------------------------------------------------------------------
  const showMontant = data.type_tk !== 'ENI'
  const canValidate = rappel !== null

  return (
    <div className="min-h-screen p-4"
         style={{ backgroundColor: '#FDECEA' }}>
      <div className="bg-white rounded-xl shadow-lg max-w-lg mx-auto overflow-hidden"
           style={{ border: `1px solid ${COL_BORDER}` }}>
        {/* HEADER */}
        <div className="p-5 text-center text-white"
             style={{ backgroundColor: COL_PRIMARY }}>
          <img src={logoOmaya} alt="Omaya"
               className="w-12 h-12 mx-auto mb-2 bg-white rounded-full p-1" />
          <h1 className="text-lg font-semibold">Validation de votre commande</h1>
        </div>

        <div className="p-5 space-y-5">
          {/* Vos informations */}
          <section>
            <h2 className="text-sm font-semibold mb-2" style={{ color: COL_BRUN }}>
              Vos informations :
            </h2>
            <pre className="text-sm whitespace-pre-wrap font-sans p-3 rounded-lg"
                 style={{ backgroundColor: '#F8F5F4',
                          border: `1px solid ${COL_BORDER}`,
                          color: COL_BRUN }}>
              {data.info_client}
            </pre>
          </section>

          {/* Votre panier */}
          <section>
            <h2 className="text-sm font-semibold mb-2" style={{ color: COL_BRUN }}>
              Votre Panier :
            </h2>
            <div className="rounded-lg overflow-hidden"
                 style={{ border: `1px solid ${COL_BORDER}` }}>
              <table className="w-full text-sm">
                <thead style={{ backgroundColor: '#F8F5F4' }}>
                  <tr>
                    <th className="text-left px-3 py-2" style={{ color: COL_BRUN }}>Type</th>
                    <th className="text-left px-3 py-2" style={{ color: COL_BRUN }}>Offre</th>
                    {showMontant && (
                      <th className="text-right px-3 py-2" style={{ color: COL_BRUN }}>Montant</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {data.panier.length === 0 && (
                    <tr>
                      <td colSpan={showMontant ? 3 : 2}
                          className="text-center px-3 py-4 text-gray-500 italic">
                        (panier vide)
                      </td>
                    </tr>
                  )}
                  {data.panier.map((l) => (
                    <tr key={l.id_panier} className="border-t"
                        style={{ borderColor: COL_BORDER }}>
                      <td className="px-3 py-2" style={{ color: COL_BRUN }}>{l.type}</td>
                      <td className="px-3 py-2" style={{ color: COL_BRUN }}>{l.nom}</td>
                      {showMontant && (
                        <td className="px-3 py-2 text-right" style={{ color: COL_BRUN }}>
                          {l.montant != null
                            ? l.montant.toLocaleString('fr-FR', {
                                style: 'currency', currency: 'EUR',
                              })
                            : ''}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Option obligatoire - Rappel */}
          <section>
            <h2 className="text-sm font-semibold mb-2" style={{ color: COL_BRUN }}>
              Option obligatoire pour valider le panier
            </h2>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRappel(false)}
                className="p-3 rounded-lg text-white text-xs font-semibold transition"
                style={{
                  backgroundColor: rappel === false ? COL_RED : '#B87878',
                  outline: rappel === false ? `3px solid ${COL_BRUN}` : 'none',
                }}
              >
                Je refuse d'être rappelé immédiatement par le service qualité afin de valider le panier listé ci-dessus.
              </button>
              <button
                type="button"
                onClick={() => setRappel(true)}
                className="p-3 rounded-lg text-white text-xs font-semibold transition"
                style={{
                  backgroundColor: rappel === true ? COL_GREEN : '#7FB99A',
                  outline: rappel === true ? `3px solid ${COL_BRUN}` : 'none',
                }}
              >
                J'accepte d'être rappelé immédiatement par le service qualité afin de valider le panier listé ci-dessus.
              </button>
            </div>
          </section>

          {/* Option facultative - Partage partenaires */}
          <section>
            <h2 className="text-sm font-semibold mb-2" style={{ color: COL_BRUN }}>
              Option facultative
            </h2>
            <p className="text-xs mb-3" style={{ color: COL_BRUN }}>
              Transmission de mes coordonnées postales et/ou mon numéro de téléphone
              aux partenaires de la société EXOSPHERE à des fins de prospection
              commerciale par courrier postal et/ou par téléphone.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setPartagePartenaire(true)}
                className="p-2.5 rounded-lg text-white text-sm font-semibold transition"
                style={{
                  backgroundColor: partagePartenaire ? COL_GREEN : '#7FB99A',
                  outline: partagePartenaire ? `3px solid ${COL_BRUN}` : 'none',
                }}
              >
                J'accepte
              </button>
              <button
                type="button"
                onClick={() => setPartagePartenaire(false)}
                className="p-2.5 rounded-lg text-sm font-semibold transition"
                style={{
                  backgroundColor: !partagePartenaire ? '#333' : '#DDD',
                  color: !partagePartenaire ? '#FFF' : COL_BRUN,
                  outline: !partagePartenaire ? `3px solid ${COL_BRUN}` : 'none',
                }}
              >
                Je m'y oppose
              </button>
            </div>
          </section>

          {/* Bouton Valider */}
          <button
            type="button"
            onClick={valider}
            disabled={!canValidate || submitting}
            className="w-full py-3 rounded-lg text-white font-semibold transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: '#1a1a1a' }}
          >
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            Je valide mes choix
          </button>
          {!canValidate && (
            <p className="text-xs text-center italic" style={{ color: COL_BRUN }}>
              Veuillez d'abord choisir une option obligatoire ci-dessus.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
