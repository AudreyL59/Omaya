/**
 * Popup 'Liste des documents ULEASE disponibles'
 * (transposition Fen_SalarieDocUlease WinDev).
 *
 * Liste les modeles ulease.pgt_doc_ulease filtres par societe du salarie.
 * 2 actions :
 *  - Ticket Omaya : genere DOCX + PDF + 3 INSERTs (suivi + demande + ticket)
 *    + upload FTP TempCttw (avec OuiNon prealable pour le suivi d'edition).
 *  - Export PDF  : genere le PDF sans rien ecrire en base.
 *
 * Cf. WinDev : si IDTypeDoc != 4 et idPC = 0, affiche un Info.
 */

import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { FileText, Loader2, Send, X } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import CheckMark from '../../CheckMark'

interface DocModel {
  id_doc_ulease: string
  id_type_doc: number
  lib_type: string
  titre: string
  info_cpl: string
  id_ste: string
  rs_interne: string
  prioritaire: boolean
}

interface Props {
  idSalarie: string
  idVehiculePC?: string // attribution vehicule (idPC). '' = aucun
  onClose: () => void
  onGenerated?: () => void
}

export default function SalarieDocUleaseModal({
  idSalarie,
  idVehiculePC = '',
  onClose,
  onGenerated,
}: Props) {
  const [models, setModels] = useState<DocModel[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!idSalarie) return
    setLoading(true)
    fetch(`/api/adm/fiche-salarie/${idSalarie}/ulease/doc-models`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((j) => setModels(Array.isArray(j) ? j : []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [idSalarie])

  const selectedItem = models.find((m) => m.id_doc_ulease === selected) || null

  // Cf. WinDev : si IDTypeDoc != 4 (mise a dispo) et idPC = 0, on alerte.
  const handleSelect = (m: DocModel) => {
    setSelected(m.id_doc_ulease)
    if (m.id_type_doc !== 4 && !idVehiculePC) {
      showToast(
        'Attention : vous ne pouvez faire signer ce type de document sans avoir sélectionné une attribution de véhicule.',
        'info',
      )
    }
  }

  const handleTicketOmaya = async () => {
    if (!selectedItem) {
      showToast('Sélectionner un modèle.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Suivi d’édition',
      message: 'Souhaitez-vous ajouter un suivi d’édition pour ce salarié ?',
      confirmLabel: 'Oui',
      cancelLabel: 'Non',
    })
    // ok = true -> create_suivi = true, sinon false. Dans les 2 cas on continue.
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/ulease/doc-generate`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_doc_ulease: selectedItem.id_doc_ulease,
            id_vehicule_pc: idVehiculePC,
            create_suivi: ok,
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { id_ticket: string; pdf_url?: string }
      showToast(`Ticket généré : ${j.id_ticket}`, 'success')
      onGenerated?.()
      onClose()
    } catch (e) {
      showToast(`Échec génération : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleExportPDF = async () => {
    if (!selectedItem) {
      showToast('Sélectionner un modèle.', 'info')
      return
    }
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/ulease/doc-preview-pdf`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_doc_ulease: selectedItem.id_doc_ulease,
            id_vehicule_pc: idVehiculePC,
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedItem.titre || 'doc-ulease'}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      showToast(`Échec export PDF : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const template = '160px 1fr 120px 70px'

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
          className="bg-white rounded-lg shadow-xl w-full max-w-3xl flex flex-col max-h-[85vh]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-2.5 border-b"
            style={{ borderColor: COLOR_BG_SOFT, backgroundColor: COLOR_BG_SOFT }}
          >
            <h3 className="font-bold text-sm" style={{ color: COLOR_BRUN }}>
              Liste des documents ULEASE disponibles
            </h3>
            <button
              type="button"
              onClick={onClose}
              className="p-1 hover:bg-white/40 rounded"
            >
              <X className="w-4 h-4" style={{ color: COLOR_BRUN }} />
            </button>
          </div>

          {/* Toolbar */}
          <div
            className="flex items-center justify-end gap-2 px-4 py-2 border-b"
            style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
          >
            <button
              type="button"
              onClick={() => void handleTicketOmaya()}
              disabled={!selectedItem || busy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
              style={{ backgroundColor: COLOR_PRIMARY, color: 'white', borderColor: COLOR_PRIMARY }}
            >
              <Send className="w-4 h-4" />
              Ticket Omaya
            </button>
            <button
              type="button"
              onClick={() => void handleExportPDF()}
              disabled={!selectedItem || busy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
              style={{ backgroundColor: 'white', color: COLOR_PRIMARY, borderColor: COLOR_PRIMARY }}
            >
              <FileText className="w-4 h-4" />
              Export PDF
            </button>
            {(loading || busy) && (
              <Loader2 className="w-4 h-4 animate-spin ml-2" style={{ color: COLOR_PRIMARY }} />
            )}
          </div>

          {/* Tableau */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <div
              className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
              style={{
                gridTemplateColumns: template,
                color: COLOR_BRUN,
                backgroundColor: COLOR_BG_SOFT,
                borderColor: COLOR_BG_SOFT,
              }}
            >
              <div>Type Doc</div>
              <div>Titre</div>
              <div>Info Cplt</div>
              <div className="text-center">Prioritaire</div>
            </div>
            <div className="flex-1 overflow-y-auto">
              {!loading && models.length === 0 && (
                <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
                  Aucun modèle disponible.
                </div>
              )}
              {/* Groupage par societe (en-tete RS_Interne) */}
              {Array.from(new Set(models.map((m) => m.rs_interne || '(global)'))).map(
                (rs) => (
                  <div key={rs}>
                    <div
                      className="px-3 py-1.5 text-xs font-bold"
                      style={{ backgroundColor: '#F7EEEB', color: COLOR_BRUN }}
                    >
                      {rs}
                    </div>
                    {models
                      .filter((m) => (m.rs_interne || '(global)') === rs)
                      .map((m) => {
                        const sel = selected === m.id_doc_ulease
                        return (
                          <div
                            key={m.id_doc_ulease}
                            onClick={() => handleSelect(m)}
                            className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                            style={{
                              gridTemplateColumns: template,
                              backgroundColor: sel ? COLOR_BG_SOFT : 'white',
                              borderColor: COLOR_BG_SOFT,
                              color: COLOR_BRUN,
                            }}
                          >
                            <div className="truncate" title={m.lib_type}>
                              {m.lib_type || '—'}
                            </div>
                            <div className="truncate font-medium" title={m.titre}>
                              {m.titre}
                            </div>
                            <div className="truncate" title={m.info_cpl}>
                              {m.info_cpl}
                            </div>
                            <div className="text-center">
                              <CheckMark active={m.prioritaire} />
                            </div>
                          </div>
                        )
                      })}
                  </div>
                ),
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
