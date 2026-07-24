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
 * Charte visuelle : intranet Vendeur (noir + blanc, accent bleu discret).
 *
 * Regle UX : bouton Valider desactive tant que le client n'a pas choisi
 * J'accepte OU Je refuse sur l'option Rappel. Option "facultative"
 * Partenaire a un defaut = "J'accepte le partage".
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Loader2, XCircle } from 'lucide-react'
import logoOmaya from '@/assets/logo-omaya.png'

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

  // rappel : null tant que non choisi, true si "J'accepte", false si "Je refuse"
  const [rappel, setRappel] = useState<boolean | null>(null)
  // partagePartenaire (facultatif) : defaut = true = J'accepte le partage
  const [partagePartenaire, setPartagePartenaire] = useState(true)

  const [submitting, setSubmitting] = useState(false)
  const [showCode, setShowCode] = useState(false)

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
      if (res.code_valid) setData({ ...data, code_valid: res.code_valid })
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
      <div className="min-h-screen flex items-center justify-center bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-gray-900" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-white">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 max-w-md text-center">
          <XCircle className="w-12 h-12 mx-auto mb-3 text-red-600" />
          <h1 className="text-lg font-semibold text-gray-900 mb-2">
            Lien invalide
          </h1>
          <p className="text-sm text-gray-600">
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
      <div className="min-h-screen flex items-center justify-center p-4 bg-white">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 max-w-lg w-full overflow-hidden">
          <div className="p-5 text-center bg-gray-900 text-white">
            <img src={logoOmaya} alt="Omaya"
                 className="w-12 h-12 mx-auto mb-2 bg-white rounded-full p-1" />
            <h1 className="text-lg font-semibold">Confirmation</h1>
          </div>
          <div className="p-8 text-center">
            <p className="text-sm text-gray-700 mb-6">
              Merci de transmettre le code ci-dessous au vendeur
            </p>
            <div className="inline-block px-8 py-4 rounded-xl font-mono text-3xl font-bold tracking-widest bg-gray-50 border-2 border-gray-900 text-gray-900">
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
  // Bouton actif uniquement si le client ACCEPTE d'etre rappele.
  // Refus = pas de validation possible (le vendeur devra rappeler
  // ou renvoyer un nouveau lien).
  const canValidate = rappel === true

  return (
    <div className="min-h-screen p-4 bg-white">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 max-w-lg mx-auto overflow-hidden">
        {/* HEADER */}
        <div className="p-5 text-center bg-gray-900 text-white">
          <img src={logoOmaya} alt="Omaya"
               className="w-12 h-12 mx-auto mb-2 bg-white rounded-full p-1" />
          <h1 className="text-lg font-semibold">Validation de votre commande</h1>
        </div>

        <div className="p-5 space-y-5">
          {/* Vos informations */}
          <section>
            <h2 className="text-sm font-semibold text-gray-900 mb-2">
              Vos informations :
            </h2>
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans p-3 rounded-xl bg-gray-50 border border-gray-200">
              {data.info_client}
            </pre>
          </section>

          {/* Votre panier */}
          <section>
            <h2 className="text-sm font-semibold text-gray-900 mb-2">
              Votre Panier :
            </h2>
            <div className="rounded-xl overflow-hidden border border-gray-200">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left px-3 py-2 text-gray-700 font-medium">Type</th>
                    <th className="text-left px-3 py-2 text-gray-700 font-medium">Offre</th>
                    {showMontant && (
                      <th className="text-right px-3 py-2 text-gray-700 font-medium">Montant</th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {data.panier.length === 0 && (
                    <tr>
                      <td colSpan={showMontant ? 3 : 2}
                          className="text-center px-3 py-4 text-gray-400 italic">
                        (panier vide)
                      </td>
                    </tr>
                  )}
                  {data.panier.map((l) => (
                    <tr key={l.id_panier} className="border-t border-gray-200">
                      <td className="px-3 py-2 text-gray-900">{l.type}</td>
                      <td className="px-3 py-2 text-gray-900">{l.nom}</td>
                      {showMontant && (
                        <td className="px-3 py-2 text-right text-gray-900">
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
            <h2 className="text-sm font-semibold text-gray-900 mb-2">
              Option obligatoire pour valider le panier
            </h2>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRappel(false)}
                className={
                  'p-3 rounded-xl text-xs font-semibold transition border-2 ' +
                  (rappel === false
                    ? 'bg-red-700 text-white border-red-800 shadow'
                    : 'bg-white text-red-700 border-red-200 hover:border-red-400')
                }
              >
                Je refuse d'être rappelé immédiatement par le service qualité afin de valider le panier listé ci-dessus.
              </button>
              <button
                type="button"
                onClick={() => setRappel(true)}
                className={
                  'p-3 rounded-xl text-xs font-semibold transition border-2 ' +
                  (rappel === true
                    ? 'bg-green-700 text-white border-green-800 shadow'
                    : 'bg-white text-green-700 border-green-200 hover:border-green-400')
                }
              >
                J'accepte d'être rappelé immédiatement par le service qualité afin de valider le panier listé ci-dessus.
              </button>
            </div>
          </section>

          {/* Option facultative - Partage partenaires */}
          <section>
            <h2 className="text-sm font-semibold text-gray-900 mb-2">
              Option facultative
            </h2>
            <p className="text-xs text-gray-700 mb-3 leading-relaxed">
              Transmission de mes coordonnées postales et/ou mon numéro de téléphone
              aux partenaires de la société EXOSPHERE à des fins de prospection
              commerciale par courrier postal et/ou par téléphone.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setPartagePartenaire(true)}
                className={
                  'p-2.5 rounded-xl text-sm font-semibold transition border-2 ' +
                  (partagePartenaire
                    ? 'bg-green-700 text-white border-green-800 shadow'
                    : 'bg-white text-green-700 border-green-200 hover:border-green-400')
                }
              >
                J'accepte
              </button>
              <button
                type="button"
                onClick={() => setPartagePartenaire(false)}
                className={
                  'p-2.5 rounded-xl text-sm font-semibold transition border-2 ' +
                  (!partagePartenaire
                    ? 'bg-gray-900 text-white border-black shadow'
                    : 'bg-white text-gray-900 border-gray-200 hover:border-gray-400')
                }
              >
                Je m'y oppose
              </button>
            </div>
          </section>

          {/* Bouton Valider (charte Vendeur : noir plein) */}
          <button
            type="button"
            onClick={valider}
            disabled={!canValidate || submitting}
            className="w-full flex items-center justify-center gap-2 bg-gray-900 hover:bg-black text-white font-medium py-3 rounded-xl shadow-sm transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
            Je valide mes choix
          </button>
          {rappel === null && (
            <p className="text-xs text-center text-gray-500 italic">
              Veuillez d'abord choisir une option obligatoire ci-dessus.
            </p>
          )}
          {rappel === false && (
            <p className="text-xs text-center text-red-700 italic">
              La validation nécessite d'accepter d'être rappelé
              par le service qualité.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
