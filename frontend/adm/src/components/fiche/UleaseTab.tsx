/**
 * Onglet 'Ulease' de la fiche salarie ADM.
 *
 * Transposition de FI_SalarieUlease.
 *
 * Comportement :
 *  - Si la fiche conducteur n'existe pas -> bloc 'Creer une fiche conducteur'
 *    avec apercu des 3 champs Permis (vide), bouton 'Enregistrer' qui appelle
 *    la creation cote backend (copie depuis pgt_salarie).
 *  - Sinon -> entete avec numPermis / TypePermis / DateObtention + 4 sous-onglets.
 *
 * Boutons differes (en attendant les fenetres Parc Auto et Fen_SalarieDocUlease):
 *  - Voir la fiche vehicule          -> Fen_FicheVehicule
 *  - Generer la mise a dispo         -> Fen_SalarieDocUlease
 *  - Generer un document ULEASE      -> Fen_SalarieDocUlease
 *  - + / crayon attribution carte    -> Fen_AttCarteCarb
 */

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Save, UserPlus } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import UleaseFichierTab from './ulease/UleaseFichierTab'
import UleaseHistoTab from './ulease/UleaseHistoTab'
import UleaseDocEditionTab from './ulease/UleaseDocEditionTab'
import UleaseCarteCarbTab from './ulease/UleaseCarteCarbTab'

interface ConducteurInfo {
  exists: boolean
  id_conducteur: string
  num_permis: string
  type_permis: string
  date_obtention: string
}

type SubTab = 'fichier' | 'histo' | 'doc_edition' | 'carte'

interface Props {
  idSalarie: string
}

export default function UleaseTab({ idSalarie }: Props) {
  const [info, setInfo] = useState<ConducteurInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [savingPermis, setSavingPermis] = useState(false)
  const [numPermis, setNumPermis] = useState('')
  const [typePermis, setTypePermis] = useState('')
  const [dateObtention, setDateObtention] = useState('')
  const [sub, setSub] = useState<SubTab>('fichier')

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/ulease/conducteur`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as ConducteurInfo
      setInfo(j)
      setNumPermis(j.num_permis)
      setTypePermis(j.type_permis)
      setDateObtention(j.date_obtention)
    } catch (e) {
      showToast(`Échec chargement Ulease : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie])

  useEffect(() => {
    void reload()
  }, [reload])

  const handleCreate = async () => {
    setCreating(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/ulease/conducteur`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Fiche conducteur créée.', 'success')
      await reload()
    } catch (e) {
      showToast(`Échec création : ${(e as Error).message}`, 'error')
    } finally {
      setCreating(false)
    }
  }

  const handleSavePermis = async () => {
    if (!info?.id_conducteur) return
    setSavingPermis(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/ulease/conducteur/${info.id_conducteur}/permis`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            num_permis: numPermis,
            type_permis: typePermis,
            date_obtention: dateObtention,
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Permis enregistré.', 'success')
    } catch (e) {
      showToast(`Échec enregistrement : ${(e as Error).message}`, 'error')
    } finally {
      setSavingPermis(false)
    }
  }

  if (loading && !info) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin" style={{ color: COLOR_PRIMARY }} />
      </div>
    )
  }

  // Cas 1 : pas de fiche conducteur -> formulaire de creation
  if (info && !info.exists) {
    return (
      <div className="flex items-center justify-center h-full">
        <div
          className="border rounded p-6 max-w-md w-full flex flex-col gap-3"
          style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
        >
          <h3 className="text-base font-bold" style={{ color: COLOR_BRUN }}>
            Créer une fiche conducteur
          </h3>
          <p className="text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
            Les informations seront copiées depuis la fiche salarié (nom, prénom,
            coordonnées, société…).
          </p>
          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={creating}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold rounded disabled:opacity-50"
            style={{ backgroundColor: COLOR_PRIMARY, color: 'white' }}
          >
            {creating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <UserPlus className="w-4 h-4" />
            )}
            Créer la fiche conducteur
          </button>
        </div>
      </div>
    )
  }

  // Cas 2 : fiche conducteur OK -> entete permis + 4 sous-onglets
  const idCond = info?.id_conducteur || ''

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* En-tete : 3 champs Permis */}
      <div
        className="grid grid-cols-3 gap-3 p-3 border rounded flex-shrink-0"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
      >
        <div className="flex flex-col">
          <label className="text-xs mb-1" style={{ color: COLOR_BRUN }}>
            N° de permis
          </label>
          <input
            type="text"
            value={numPermis}
            onChange={(e) => setNumPermis(e.target.value)}
            className="px-2 py-1 text-sm"
            maxLength={25}
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs mb-1" style={{ color: COLOR_BRUN }}>
            Type permis (A, B…)
          </label>
          <input
            type="text"
            value={typePermis}
            onChange={(e) => setTypePermis(e.target.value)}
            className="px-2 py-1 text-sm"
            maxLength={3}
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs mb-1" style={{ color: COLOR_BRUN }}>
            Date d’obtention
          </label>
          <div
            className="px-2 py-1 rounded border bg-white"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <input
              type="date"
              value={dateObtention}
              onChange={(e) => setDateObtention(e.target.value)}
              className="text-sm w-full"
            />
          </div>
        </div>
        <div className="col-span-3 flex justify-end">
          <button
            type="button"
            onClick={() => void handleSavePermis()}
            disabled={savingPermis}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded disabled:opacity-50"
            style={{ backgroundColor: COLOR_PRIMARY, color: 'white' }}
          >
            {savingPermis ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Enregistrer
          </button>
        </div>
      </div>

      {/* Sous-onglets */}
      <div
        className="flex gap-1 flex-shrink-0 border-b"
        style={{ borderColor: COLOR_BG_SOFT }}
      >
        {(
          [
            ['fichier', 'Fichier Conducteur'],
            ['histo', 'Historique Attribution'],
            ['doc_edition', 'Édition documents'],
            ['carte', 'Attribution Carte Carburant'],
          ] as [SubTab, string][]
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            onClick={() => setSub(k)}
            className="px-3 py-1.5 text-xs font-semibold border-b-2"
            style={{
              color: sub === k ? COLOR_PRIMARY : COLOR_BRUN,
              borderColor: sub === k ? COLOR_PRIMARY : 'transparent',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden">
        {sub === 'fichier' && <UleaseFichierTab idConducteur={idCond} />}
        {sub === 'histo' && <UleaseHistoTab idConducteur={idCond} />}
        {sub === 'doc_edition' && (
          <UleaseDocEditionTab idSalarie={idSalarie} />
        )}
        {sub === 'carte' && <UleaseCarteCarbTab idConducteur={idCond} />}
      </div>
    </div>
  )
}
