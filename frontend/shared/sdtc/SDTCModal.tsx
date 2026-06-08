/**
 * SDTCModal : popup partagee Solde De Tout Compte (transposition Fen_SDTC).
 *
 * Composant utilisable depuis n'importe quel intranet :
 *   <SDTCModal
 *     open={open}
 *     onClose={() => setOpen(false)}
 *     getToken={getToken}
 *     idSalarie="123456"
 *   />
 *
 * Scaffold pour cette etape : chargement des donnees de base + onglet
 * 'Resume' fonctionnel (bloc HTML façon WinDev avec nom / societe /
 * adresse / date naiss / num SS / sortie / mutuelle).
 *
 * Onglets restants en placeholder, branches dans des commits dedies :
 *   - Contrats deja traites (grille selection mois + qte)
 *   - Contrats SDTC (selection + valider)
 *   - Resume Solde de tout compte (NB Pts / Comm Pts / Bareme / Total)
 *   - Contrats a editer pour le salarie (grille)
 *   - Recap Ctts pour le BO (recap par produit)
 */

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Loader2, Wallet, X } from 'lucide-react'

import { showToast } from '../ui/dialog'

const COLOR_PRIMARY = '#17494E'
const COLOR_BRUN = '#4E1D17'
const COLOR_BG_SOFT = '#EFE9E7'

interface SalarieInfo {
  nom: string
  prenom: string
  lib_nom: string
  num_ss: string
  date_naiss: string
  lieu_naiss: string
  dep_naiss: string
  adresse1: string
  adresse2: string
  cp: string
  ville: string
  date_embauche: string
  date_anciennete: string
  id_ste: string
  lib_societe: string
}

interface SortieInfo {
  date_sortie_reelle: string
  lib_sortie_raw: string
  titre_sortie: string
  kind: string
  courrier_info: string
}

interface SDTCData {
  found: boolean
  id_salarie: string
  salarie: SalarieInfo
  sortie: SortieInfo
  info_mutuelle: string
  date_dernier_ctt: string
}

type Tab =
  | 'resume'
  | 'deja_traites'
  | 'contrats_sdtc'
  | 'resume_stc'
  | 'a_editer'
  | 'recap_bo'

const TABS: { key: Tab; label: string }[] = [
  { key: 'resume',        label: 'Résumé' },
  { key: 'deja_traites',  label: 'Contrats déjà traités' },
  { key: 'contrats_sdtc', label: 'Contrats SDTC' },
  { key: 'resume_stc',    label: 'Résumé Solde de tout compte' },
  { key: 'a_editer',      label: 'Contrats à éditer pour le salarié' },
  { key: 'recap_bo',      label: 'Récap Ctts pour le BO' },
]

interface Props {
  open: boolean
  onClose: () => void
  getToken: () => string | null
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function SDTCModal({ open, onClose, getToken, idSalarie }: Props) {
  const [data, setData] = useState<SDTCData | null>(null)
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<Tab>('resume')

  useEffect(() => {
    if (!open || !idSalarie) return
    let cancelled = false
    setLoading(true)
    setData(null)
    setTab('resume')
    fetch(`/api/shared/sdtc/${idSalarie}/load`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(async (r) => {
        if (!r.ok) {
          const j = await r.json().catch(() => ({}))
          throw new Error((j as { detail?: string })?.detail || String(r.status))
        }
        return r.json()
      })
      .then((j) => {
        if (cancelled) return
        setData(j as SDTCData)
      })
      .catch((e) => {
        if (cancelled) return
        showToast(`Échec chargement SDTC : ${e?.message || e}`, 'error')
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [open, idSalarie, getToken])

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
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-[1300px] max-w-[97vw] h-[88vh] flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: COLOR_BG_SOFT }}>
          <div className="flex items-center gap-2">
            <Wallet className="w-5 h-5" style={{ color: COLOR_PRIMARY }} />
            <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
              Solde de tout compte
            </h2>
            {data && (
              <span className="text-sm" style={{ color: COLOR_BRUN }}>
                — {data.salarie.lib_nom}
                {data.salarie.lib_societe && (
                  <span style={{ opacity: 0.7 }}> ({data.salarie.lib_societe})</span>
                )}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[#EFE9E7]"
            style={{ color: COLOR_BRUN }}
            title="Fermer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 px-3 pt-2 border-b" style={{ borderColor: COLOR_BG_SOFT }}>
          {TABS.map((t) => {
            const active = t.key === tab
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className="px-3 py-1.5 text-sm rounded-t transition"
                style={{
                  color: active ? COLOR_PRIMARY : COLOR_BRUN,
                  backgroundColor: active ? '#ECF1F2' : 'transparent',
                  borderBottom: active ? `2px solid ${COLOR_PRIMARY}` : '2px solid transparent',
                  fontWeight: active ? 600 : 400,
                }}
              >
                {t.label}
              </button>
            )
          })}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading && (
            <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
              <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
            </div>
          )}
          {!loading && data && tab === 'resume' && <ResumeTab data={data} />}
          {!loading && data && tab !== 'resume' && <ComingSoon label={TABS.find((t) => t.key === tab)?.label || ''} />}
        </div>
      </motion.div>
    </motion.div>
  )
}

// --- Onglet "Resume" ----------------------------------------------------

function ResumeTab({ data }: { data: SDTCData }) {
  const { salarie, sortie, info_mutuelle, date_dernier_ctt } = data
  return (
    <div className="max-w-3xl mx-auto">
      <div
        className="border rounded-lg p-5"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
      >
        <h3
          className="text-lg font-semibold text-center pb-2 border-b"
          style={{ color: COLOR_BRUN, borderColor: COLOR_BG_SOFT }}
        >
          SOLDE DE TOUT COMPTE
        </h3>
        <p className="text-center font-medium mt-3" style={{ color: COLOR_BRUN }}>
          {salarie.lib_nom}
          {salarie.lib_societe && <span> chez {salarie.lib_societe}</span>}
        </p>

        <p className="text-xs text-center mt-3" style={{ color: COLOR_BRUN }}>
          Entré(e) le {fmtDate(salarie.date_embauche) || '—'}
        </p>
        <p className="text-xs text-center" style={{ color: COLOR_BRUN }}>
          Sorti(e) le {fmtDate(sortie.date_sortie_reelle) || ':'} {sortie.courrier_info}
        </p>

        {sortie.titre_sortie && (
          <p className="text-sm font-semibold text-center mt-3" style={{ color: COLOR_BRUN }}>
            {sortie.titre_sortie}
          </p>
        )}

        <div className="mt-4 space-y-1 text-sm" style={{ color: COLOR_BRUN }}>
          {salarie.adresse1 && <div>{salarie.adresse1}</div>}
          {salarie.adresse2 && <div>{salarie.adresse2}</div>}
          <div>
            {salarie.cp} {salarie.ville}
          </div>
          <div>
            N° SS : {salarie.num_ss || '—'}
          </div>
          <div>
            Né(e) le : {fmtDate(salarie.date_naiss) || '—'} à {salarie.lieu_naiss}
            {salarie.dep_naiss && ` (${salarie.dep_naiss})`}
          </div>
        </div>

        <div className="mt-5 space-y-1 text-sm" style={{ color: COLOR_BRUN }}>
          <Placeholder label="COMM" value="MONTANT_COMM" />
          <Placeholder label="CP" value="MONTANT_CP" />
          <Placeholder label="DECO" value="MONTANT_DECO" />
          <Placeholder label="AVANCE" value="MONTANT_AVANCE" />
          <Placeholder label="Nombre de TR" value="NB_TR" />
          <div>
            Mutuelle Entreprise : <strong>{info_mutuelle}</strong>
          </div>
          <Placeholder label="Absence" value="DATEABS" />
        </div>

        {date_dernier_ctt && (
          <p className="mt-4 text-xs text-emerald-700">
            Dernier contrat signé le {fmtDate(date_dernier_ctt)}
          </p>
        )}

        <p className="mt-4 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
          Cordialement.
        </p>
      </div>

      <p className="mt-4 text-xs text-center" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
        Les montants COMM/CP/DECO/AVANCE/TR et les contrats seront calculés à partir
        des onglets suivants (à venir).
      </p>
    </div>
  )
}

function Placeholder({ label, value }: { label: string; value: string }) {
  return (
    <div>
      {label} :{' '}
      <span className="font-mono text-xs italic" style={{ opacity: 0.6 }}>
        {value}
      </span>
    </div>
  )
}

function ComingSoon({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center h-full text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
      « {label} » — à brancher dans un prochain commit.
    </div>
  )
}
