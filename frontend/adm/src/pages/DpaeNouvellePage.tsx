/**
 * Fen_DPAE_Nouvelle (placeholder).
 *
 * Cette page est ouverte depuis Fen_DPAE_Recherche avec :
 *   ?id_ticket=N&type_dpae=0|1|2|3&id_elem=N&id_cv_suivi=N
 *
 * TypeDpae :
 *   0 = vierge (pas de pre-remplissage)
 *   1 = depuis un CV (id_elem = id_cvtheque)
 *   2 = depuis le registre RH, salarie sorti (id_elem = id_salarie)
 *   3 = depuis le registre RH, salarie toujours actif (id_elem = id_salarie)
 *       -> WinDev demande confirmation : continuer la DPAE OU archiver la
 *       fiche actuelle pour en faire une nouvelle.
 *
 * TODO : transposer Fen_DPAE_Nouvelle quand le code WinDev sera dispo.
 */

import { useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Construction } from 'lucide-react'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'

const TYPE_LABELS: Record<string, string> = {
  '0': 'DPAE vierge',
  '1': 'depuis un CV',
  '2': 'depuis le registre RH (salarié sorti)',
  '3': 'depuis le registre RH (salarié toujours actif)',
}

export default function DpaeNouvellePage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const typeDpae = params.get('type_dpae') || '0'
  const idElem = params.get('id_elem') || '0'
  const idCvSuivi = params.get('id_cv_suivi') || '0'
  const idTicket = params.get('id_ticket') || '0'

  return (
    <div className="p-6 max-w-3xl mx-auto font-normal">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm mb-4 hover:underline"
        style={{ color: COL_PRIMARY }}
      >
        <ArrowLeft className="w-4 h-4" />
        Retour
      </button>

      <div
        className="bg-white rounded-lg shadow-sm p-6 border"
        style={{ borderColor: COL_BORDER }}
      >
        <div className="flex items-center gap-3 mb-4">
          <Construction className="w-6 h-6" style={{ color: COL_BRUN }} />
          <h1 className="text-xl font-bold" style={{ color: COL_BRUN }}>
            Nouvelle DPAE
          </h1>
        </div>

        <p className="text-sm mb-4" style={{ color: COL_BRUN }}>
          Cette fenêtre sera implémentée à partir du code WinDev de
          Fen_DPAE_Nouvelle.
        </p>

        <div
          className="text-xs space-y-1 p-3 rounded-md font-mono"
          style={{ backgroundColor: '#F8F5F4', color: COL_BRUN }}
        >
          <div>idTicket : {idTicket}</div>
          <div>
            TypeDpae : {typeDpae} ({TYPE_LABELS[typeDpae] || 'inconnu'})
          </div>
          <div>IdElement : {idElem}</div>
          <div>IdcvSuiv : {idCvSuivi}</div>
        </div>
      </div>
    </div>
  )
}
