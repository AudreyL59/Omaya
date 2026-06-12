/**
 * Popup 'Info Livret' (transposition Fen_SalarieLivretFiche WinDev).
 *
 * Champs :
 *  - Type Opération (combo type_operation_livret)
 *  - BtnChallenge (selecteur de challenge si Type=1 Challenge)
 *  - 'Voir le ticket' (visible si IDTK_Liste <> 0 — placeholder)
 *  - Crédit / Débit
 *  - Date Opération
 *  - Enregistrer
 */

import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Loader2, Save, Search, Ticket, Trash2, X } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'

const TYPE_CHALLENGE = 1
const TYPE_CMD_EXOCASH = 3

interface TypeOp {
  id_type_operation_livret: number
  lib_opeation: string
}

interface Challenge {
  id_challenge_evenement: string
  libelle: string
  date_debut: string
  date_fin: string
}

interface LivretDetail {
  id_salarie_livret: string
  id_type_operation_livret: number
  id_challenge: string
  lib_challenge: string
  id_tk_liste: string
  montant_credit: number
  montant_debit: number
  date_operation: string
}

interface Props {
  idSalarie: string
  idLivret: string // '' = creation
  onClose: () => void
  onSaved: () => void
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function defaultToday(): string {
  const n = new Date()
  return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, '0')}-${String(n.getDate()).padStart(2, '0')}`
}

export default function SalarieLivretModal({
  idSalarie,
  idLivret,
  onClose,
  onSaved,
}: Props) {
  const [types, setTypes] = useState<TypeOp[]>([])
  const [idType, setIdType] = useState<number>(0)
  const [idChallenge, setIdChallenge] = useState<string>('')
  const [libChallenge, setLibChallenge] = useState<string>('')
  const [idTkListe, setIdTkListe] = useState<string>('')
  const [credit, setCredit] = useState<string>('')
  const [debit, setDebit] = useState<string>('')
  const [dateOp, setDateOp] = useState<string>(defaultToday())
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [challengeOpen, setChallengeOpen] = useState(false)
  const [challenges, setChallenges] = useState<Challenge[]>([])
  const [loadingChall, setLoadingChall] = useState(false)

  // Charge la combo Types Operation
  useEffect(() => {
    fetch('/api/adm/fiche-salarie/exo-cash/types-operation', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((j) => setTypes(Array.isArray(j) ? j : []))
      .catch(() => {})
  }, [])

  // Modification : recupere la ligne
  useEffect(() => {
    if (!idLivret) return
    setLoading(true)
    fetch(`/api/adm/fiche-salarie/exo-cash/${idLivret}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((j: LivretDetail) => {
        setIdType(j.id_type_operation_livret || 0)
        setIdChallenge(j.id_challenge || '')
        setLibChallenge(j.lib_challenge || '')
        setIdTkListe(j.id_tk_liste || '')
        setCredit(j.montant_credit ? String(j.montant_credit) : '')
        setDebit(j.montant_debit ? String(j.montant_debit) : '')
        setDateOp(j.date_operation || defaultToday())
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [idLivret])

  const openChallengePicker = () => {
    setChallengeOpen(true)
    if (challenges.length === 0) {
      setLoadingChall(true)
      fetch('/api/adm/fiche-salarie/exo-cash/challenges', {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
        .then((r) => (r.ok ? r.json() : []))
        .then((j) => setChallenges(Array.isArray(j) ? j : []))
        .catch(() => {})
        .finally(() => setLoadingChall(false))
    }
  }

  const pickChallenge = (c: Challenge) => {
    setIdChallenge(c.id_challenge_evenement)
    setLibChallenge(
      `${c.libelle}, du ${fmtDate(c.date_debut)} au ${fmtDate(c.date_fin)}`,
    )
    setChallengeOpen(false)
  }

  const clearChallenge = () => {
    setIdChallenge('')
    setLibChallenge('')
  }

  const handleSave = async () => {
    if (!idType) {
      showToast('Choisir un type d’opération.', 'info')
      return
    }
    if (!dateOp) {
      showToast('Renseigner la date d’opération.', 'info')
      return
    }
    setSaving(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/exo-cash`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_salarie_livret: idLivret || '',
          id_type_operation_livret: idType,
          id_challenge: idChallenge,
          montant_credit: parseFloat(credit) || 0,
          montant_debit: parseFloat(debit) || 0,
          date_operation: dateOp,
        }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Opération enregistrée.', 'success')
      onSaved()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const isChallenge = idType === TYPE_CHALLENGE
  const isCmdExoCash = idType === TYPE_CMD_EXOCASH

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-lg shadow-xl w-full max-w-md flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-2.5 border-b"
            style={{ borderColor: COLOR_BG_SOFT, backgroundColor: COLOR_BG_SOFT }}
          >
            <h3 className="font-bold text-sm" style={{ color: COLOR_BRUN }}>
              Info Livret
            </h3>
            <button
              type="button"
              onClick={onClose}
              className="p-1 hover:bg-white/40 rounded"
            >
              <X className="w-4 h-4" style={{ color: COLOR_BRUN }} />
            </button>
          </div>

          {/* Body */}
          <div className="p-4 flex flex-col gap-3">
            {loading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin" style={{ color: COLOR_PRIMARY }} />
              </div>
            )}

            {/* Type Opération */}
            <div className="grid grid-cols-3 items-center gap-2">
              <label className="text-sm" style={{ color: COLOR_BRUN }}>
                Type Opération
              </label>
              <select
                value={idType}
                onChange={(e) => setIdType(parseInt(e.target.value, 10) || 0)}
                className="col-span-2 px-2 py-1 text-sm rounded border bg-white"
                style={{ borderColor: COLOR_BG_SOFT }}
              >
                <option value={0}>—</option>
                {types.map((t) => (
                  <option key={t.id_type_operation_livret} value={t.id_type_operation_livret}>
                    {t.lib_opeation}
                  </option>
                ))}
              </select>
            </div>

            {/* Challenge selector (uniquement si Type=1 Challenge) */}
            {isChallenge && (
              <div
                className="flex items-center gap-2 p-2 rounded border"
                style={{ borderColor: COLOR_BG_SOFT, backgroundColor: COLOR_BG_SOFT }}
              >
                <button
                  type="button"
                  onClick={openChallengePicker}
                  className="flex-1 inline-flex items-center gap-2 px-3 py-1.5 text-sm font-semibold rounded"
                  style={{ backgroundColor: COLOR_PRIMARY, color: 'white' }}
                >
                  <Search className="w-4 h-4" />
                  {libChallenge || 'Choisir un challenge'}
                </button>
                {idChallenge && (
                  <button
                    type="button"
                    onClick={clearChallenge}
                    className="p-1.5 rounded"
                    style={{ backgroundColor: 'white', color: '#B91C1C' }}
                    title="Supprimer le challenge"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            )}

            {/* Voir le ticket (visible si IDTK_Liste != 0) */}
            {idTkListe && idTkListe !== '0' && (
              <div className="flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() =>
                    showToast(
                      'Voir le ticket : à implémenter (Fen_TicketContenu).',
                      'info',
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border"
                  style={{
                    backgroundColor: 'white',
                    color: COLOR_PRIMARY,
                    borderColor: COLOR_PRIMARY,
                  }}
                >
                  <Ticket className="w-4 h-4" />
                  Voir le ticket
                </button>
                <span className="text-xs" style={{ color: COLOR_BRUN }}>
                  Id Ticket : {idTkListe}
                </span>
              </div>
            )}

            {/* Si Type=3 Commande ExoCash et pas de ticket : afficher zone Id Ticket vide */}
            {isCmdExoCash && (!idTkListe || idTkListe === '0') && (
              <div className="text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
                Aucun ticket associé.
              </div>
            )}

            {/* Crédit */}
            <div className="grid grid-cols-3 items-center gap-2">
              <label className="text-sm" style={{ color: COLOR_BRUN }}>
                Crédit
              </label>
              <input
                type="number"
                step="0.01"
                value={credit}
                onChange={(e) => setCredit(e.target.value)}
                className="col-span-2 px-2 py-1 text-sm rounded border"
                style={{ borderColor: COLOR_BG_SOFT }}
              />
            </div>

            {/* Débit */}
            <div className="grid grid-cols-3 items-center gap-2">
              <label className="text-sm" style={{ color: COLOR_BRUN }}>
                Débit
              </label>
              <input
                type="number"
                step="0.01"
                value={debit}
                onChange={(e) => setDebit(e.target.value)}
                className="col-span-2 px-2 py-1 text-sm rounded border"
                style={{ borderColor: COLOR_BG_SOFT }}
              />
            </div>

            {/* Date Opération */}
            <div className="grid grid-cols-3 items-center gap-2">
              <label className="text-sm" style={{ color: COLOR_BRUN }}>
                Date Opération
              </label>
              <div
                className="col-span-2 px-2 py-1 rounded border bg-white"
                style={{ borderColor: COLOR_BG_SOFT }}
              >
                <input
                  type="date"
                  value={dateOp}
                  onChange={(e) => setDateOp(e.target.value)}
                  className="text-sm w-full"
                />
              </div>
            </div>

            {/* Enregistrer */}
            <div className="flex justify-center pt-2">
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving}
                className="inline-flex items-center gap-2 px-6 py-2 text-sm font-semibold rounded disabled:opacity-50"
                style={{ backgroundColor: COLOR_PRIMARY, color: 'white' }}
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Enregistrer
              </button>
            </div>
          </div>
        </motion.div>

        {/* Picker challenges */}
        {challengeOpen && (
          <motion.div
            className="fixed inset-0 z-[60] flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
            onClick={() => setChallengeOpen(false)}
          >
            <div
              className="bg-white rounded-lg shadow-xl w-full max-w-lg flex flex-col max-h-[80vh]"
              onClick={(e) => e.stopPropagation()}
            >
              <div
                className="flex items-center justify-between px-4 py-2.5 border-b"
                style={{ borderColor: COLOR_BG_SOFT, backgroundColor: COLOR_BG_SOFT }}
              >
                <h3 className="font-bold text-sm" style={{ color: COLOR_BRUN }}>
                  Choisir un challenge
                </h3>
                <button
                  type="button"
                  onClick={() => setChallengeOpen(false)}
                  className="p-1 hover:bg-white/40 rounded"
                >
                  <X className="w-4 h-4" style={{ color: COLOR_BRUN }} />
                </button>
              </div>
              <div className="overflow-y-auto flex-1">
                {loadingChall && (
                  <div className="flex items-center justify-center py-6">
                    <Loader2 className="w-5 h-5 animate-spin" style={{ color: COLOR_PRIMARY }} />
                  </div>
                )}
                {!loadingChall && challenges.length === 0 && (
                  <div className="p-4 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
                    Aucun challenge disponible.
                  </div>
                )}
                {challenges.map((c) => (
                  <button
                    key={c.id_challenge_evenement}
                    type="button"
                    onClick={() => pickChallenge(c)}
                    className="w-full text-left px-4 py-2 text-sm border-b hover:bg-gray-50"
                    style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                  >
                    <div className="font-semibold">{c.libelle || '—'}</div>
                    <div className="text-xs opacity-70">
                      Du {fmtDate(c.date_debut)} au {fmtDate(c.date_fin)}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
