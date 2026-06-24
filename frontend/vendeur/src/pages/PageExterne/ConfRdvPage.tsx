/**
 * Page publique de confirmation de RDV — accessible sans login.
 *
 * URL : /vendeur/PageExterne/conf-rdv/:idRdv
 * Lien envoye par SMS au candidat apres planification d'un RDV.
 */

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Calendar, Check, Loader2, MapPin, User, Video, XCircle,
} from 'lucide-react'
import logoOmaya from '@/assets/logo-omaya.png'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'

interface PublicRdvDetail {
  id_agenda_evenement: string
  candidat_nom: string
  candidat_prenom: string
  recruteur_nom: string
  date_debut: string
  date_fin: string
  type_entretien: string
  lib_lieu: string
  adresse1: string
  code_postal: string
  nom_ville: string
  latitude_deg?: number | null
  longitude_deg?: number | null
  lien_salon: string
  salon_id: string
  salon_mdp: string
  is_confirme: boolean
}

export default function ConfRdvPage() {
  const { idRdv = '' } = useParams<{ idRdv: string }>()
  const [rdv, setRdv] = useState<PublicRdvDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!idRdv) return
    fetch(`/api/public/rdv/${idRdv}`)
      .then(r => {
        if (!r.ok) throw new Error(r.status === 404 ? 'RDV introuvable' : `Erreur ${r.status}`)
        return r.json()
      })
      .then((d: PublicRdvDetail) => {
        setRdv(d)
        setConfirmed(d.is_confirme)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [idRdv])

  const confirmer = async () => {
    setConfirming(true)
    try {
      const r = await fetch(`/api/public/rdv/${idRdv}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirme: true }),
      })
      if (!r.ok) throw new Error(String(r.status))
      setConfirmed(true)
    } catch (e) {
      alert(`Erreur : ${(e as Error).message}`)
    } finally { setConfirming(false) }
  }

  const ouvrirMaps = () => {
    if (!rdv?.latitude_deg || !rdv?.longitude_deg) return
    window.open(`https://www.google.com/maps/?q=${rdv.latitude_deg},${rdv.longitude_deg}`,
                '_blank', 'noopener')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center"
           style={{ backgroundColor: '#F8F5F4' }}>
        <Loader2 className="w-8 h-8 animate-spin" style={{ color: COL_PRIMARY }} />
      </div>
    )
  }

  if (error || !rdv) {
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
            {error || 'Ce RDV n\'existe pas ou n\'est plus accessible.'}
          </p>
        </div>
      </div>
    )
  }

  const dateFormatted = new Date(rdv.date_debut.replace(' ', 'T'))
    .toLocaleDateString('fr-FR', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    })
  const heureFormatted = rdv.date_debut.slice(11, 16)

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
         style={{ backgroundColor: '#F8F5F4' }}>
      <div className="bg-white rounded-xl shadow-lg max-w-lg w-full overflow-hidden"
           style={{ border: `1px solid ${COL_BORDER}` }}>
        {/* HEADER */}
        <div className="p-5 text-center text-white"
             style={{ backgroundColor: COL_PRIMARY }}>
          <img src={logoOmaya} alt="Omaya" className="w-12 h-12 mx-auto mb-2 bg-white rounded-full p-1" />
          <h1 className="text-xl font-bold">Confirmation de votre RDV</h1>
          {(rdv.candidat_nom || rdv.candidat_prenom) && (
            <p className="text-sm opacity-90 mt-1">
              Bonjour {rdv.candidat_prenom} {rdv.candidat_nom}
            </p>
          )}
        </div>

        {/* CORPS */}
        <div className="p-5 space-y-4">
          <InfoRow icon={Calendar} label="Date">
            <div className="capitalize">{dateFormatted}</div>
            <div className="text-xl font-bold" style={{ color: COL_PRIMARY }}>
              {heureFormatted}
            </div>
          </InfoRow>

          <InfoRow icon={User} label="Recruteur">
            {rdv.recruteur_nom}
          </InfoRow>

          {rdv.type_entretien === 'Visio' ? (
            <InfoRow icon={Video} label="Visio">
              {rdv.lien_salon ? (
                <a href={rdv.lien_salon} target="_blank" rel="noopener noreferrer"
                   className="underline break-all" style={{ color: COL_PRIMARY }}>
                  {rdv.lien_salon}
                </a>
              ) : (
                <span className="italic">Lien à venir</span>
              )}
              {rdv.salon_id && <div className="text-xs mt-1">ID Réunion : {rdv.salon_id}</div>}
              {rdv.salon_mdp && <div className="text-xs">Code secret : {rdv.salon_mdp}</div>}
            </InfoRow>
          ) : (
            <InfoRow icon={MapPin} label="Lieu">
              <div className="font-semibold">{rdv.lib_lieu}</div>
              <div className="whitespace-pre-line text-sm">
                {rdv.adresse1}
                {rdv.adresse1 && '\n'}{rdv.code_postal} {rdv.nom_ville}
              </div>
              {rdv.latitude_deg && rdv.longitude_deg && (
                <button type="button" onClick={ouvrirMaps}
                        className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 rounded border text-xs"
                        style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                  <MapPin className="w-3 h-3" /> Itinéraire Google Maps
                </button>
              )}
            </InfoRow>
          )}

          {/* CTA Confirmation */}
          <div className="pt-3 border-t" style={{ borderColor: COL_BORDER }}>
            {confirmed ? (
              <div className="text-center py-3 rounded"
                   style={{ backgroundColor: '#D1FAE5', color: '#065F46' }}>
                <Check className="w-6 h-6 mx-auto mb-1" />
                <div className="font-semibold">RDV confirmé</div>
                <div className="text-xs">Merci, à très bientôt !</div>
              </div>
            ) : (
              <button type="button" onClick={confirmer} disabled={confirming}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-white font-semibold disabled:opacity-50"
                      style={{ backgroundColor: COL_PRIMARY }}>
                {confirming ? <Loader2 className="w-5 h-5 animate-spin" />
                            : <Check className="w-5 h-5" />}
                Confirmer ma présence
              </button>
            )}
          </div>
        </div>

        {/* FOOTER */}
        <div className="px-5 py-3 text-center text-xs"
             style={{ backgroundColor: '#F8F5F4', color: '#A68D8A' }}>
          Pour toute modification, contactez {rdv.recruteur_nom || 'votre recruteur'}.
        </div>
      </div>
    </div>
  )
}

function InfoRow({ icon: Icon, label, children }: {
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex gap-3">
      <div className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center"
           style={{ backgroundColor: '#EFE9E7' }}>
        <Icon className="w-5 h-5" style={{ color: COL_PRIMARY }} />
      </div>
      <div className="flex-1 min-w-0" style={{ color: COL_BRUN }}>
        <div className="text-xs opacity-70">{label}</div>
        <div className="text-sm">{children}</div>
      </div>
    </div>
  )
}
