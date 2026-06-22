/**
 * Popup 'Liste des documents RH disponible' (transposition Fen_SalarieDocRH).
 *
 * Affiche :
 *  - Combo Type Produit (filtre FDV cote backend)
 *  - Table des modeles de docs disponibles pour le salarie + type produit
 *    (JOIN pgt_doc_rh + pgt_societe : id_ste du salarie OU id_ste=0)
 *  - Bouton 'Ticket Omaya' : publipostage du DOCX + creation du ticket
 *    Demande CttW (a brancher dans un prochain commit)
 *  - Bouton 'Export PDF' : placeholder
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { FileText, Loader2, Send, Ticket, X } from 'lucide-react'

import { getToken } from '@/api'
import { showPrompt, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import CheckMark from '../CheckMark'

interface TypeProduit {
  id_type_produit: string
  lib: string
}

interface DocDispo {
  id_doc_rh: string
  id_ste: string
  rs_interne: string
  id_type_doc: string
  type_doc_lib: string
  titre: string
  info_cpl: string
  prioritaire: boolean
}

interface Props {
  idSalarie: string
  onClose: () => void
  onCreated: () => void
}

export default function NewDocRHModal({ idSalarie, onClose, onCreated }: Props) {
  const [typesProduit, setTypesProduit] = useState<TypeProduit[]>([])
  const [idTypeProduit, setIdTypeProduit] = useState<string>('')
  const [docs, setDocs] = useState<DocDispo[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [busyTicket, setBusyTicket] = useState(false)
  const [busyExport, setBusyExport] = useState(false)

  // Charge la liste des types produit + le default du salarie
  useEffect(() => {
    void (async () => {
      try {
        const [rTypes, rDocs] = await Promise.all([
          fetch(`/api/adm/fiche-salarie/doc-rh/types-produit`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
          fetch(`/api/adm/fiche-salarie/${idSalarie}/doc-rh/docs-disponibles`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
        ])
        if (rTypes.ok) {
          const j = (await rTypes.json()) as { items: TypeProduit[] }
          setTypesProduit(j.items || [])
        }
        if (rDocs.ok) {
          const j = (await rDocs.json()) as {
            default_id_type_produit: string
            id_type_produit: string
            items: DocDispo[]
          }
          setIdTypeProduit(j.id_type_produit || j.default_id_type_produit || '')
          setDocs(j.items || [])
        }
      } catch {
        showToast('Échec chargement des documents disponibles', 'error')
      }
    })()
  }, [idSalarie])

  // Recharge la liste des docs quand on change le type produit
  const reloadDocs = useCallback(async (tp: string) => {
    setLoadingDocs(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/doc-rh/docs-disponibles?id_type_produit=${tp}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { items: DocDispo[] }
      setDocs(j.items || [])
      setSelected(null)
    } catch (e) {
      showToast(`Échec chargement docs : ${(e as Error).message}`, 'error')
    } finally {
      setLoadingDocs(false)
    }
  }, [idSalarie])

  const handleChangeTypeProduit = (tp: string) => {
    setIdTypeProduit(tp)
    if (tp) void reloadDocs(tp)
  }

  const selectedDoc = useMemo(
    () => docs.find((d) => d.id_doc_rh === selected) || null,
    [docs, selected],
  )

  const handleTicketOmaya = async () => {
    if (!selectedDoc) {
      showToast('Sélectionner un document.', 'info')
      return
    }
    // Cas AVENANT : demande la date d'avenant a l'operateur
    let dateAvenant = ''
    if (/AVENANT/i.test(selectedDoc.titre)) {
      const raw = await showPrompt({
        title: 'Date de l\'avenant',
        message: 'Merci de saisir la date de l\'avenant :',
        inputType: 'date',
        confirmLabel: 'Valider',
        validator: (v) => (v ? null : 'Date requise'),
      })
      if (!raw) return // annule
      // showPrompt avec inputType=date retourne du ISO (YYYY-MM-DD) ;
      // on tolere aussi le format JJ/MM/AAAA si saisi en texte.
      const m = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
      if (m) {
        dateAvenant = `${m[3]}-${m[2]}-${m[1]}`
      } else if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        dateAvenant = raw
      } else {
        showToast('Format de date invalide.', 'error')
        return
      }
    }
    setBusyTicket(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/doc-rh/generate-cttw`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            id_doc_rh: selectedDoc.id_doc_rh,
            date_avenant: dateAvenant,
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { id_ticket: string; pdf_url: string }
      showToast(`Contrat généré (ticket ${j.id_ticket}).`, 'success')
      // ouvre le PDF dans un nouvel onglet pour controle
      if (j.pdf_url) {
        window.open(j.pdf_url, '_blank', 'noopener,noreferrer')
      }
      onCreated()
    } catch (e) {
      showToast(`Échec génération : ${(e as Error).message}`, 'error')
    } finally {
      setBusyTicket(false)
    }
  }

  const handleExportPDF = async () => {
    if (!selectedDoc) {
      showToast('Sélectionner un document.', 'info')
      return
    }
    // Cas AVENANT : prompt date charté
    let dateAvenant = ''
    if (/AVENANT/i.test(selectedDoc.titre)) {
      const raw = await showPrompt({
        title: 'Date de l\'avenant',
        message: 'Merci de saisir la date de l\'avenant :',
        inputType: 'date',
        confirmLabel: 'Valider',
        validator: (v) => (v ? null : 'Date requise'),
      })
      if (!raw) return
      const m = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
      if (m) {
        dateAvenant = `${m[3]}-${m[2]}-${m[1]}`
      } else if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        dateAvenant = raw
      } else {
        showToast('Format de date invalide.', 'error')
        return
      }
    }
    setBusyExport(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/doc-rh/preview-pdf`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            id_doc_rh: selectedDoc.id_doc_rh,
            date_avenant: dateAvenant,
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      // Recupere le filename depuis Content-Disposition
      const cd = r.headers.get('Content-Disposition') || ''
      const m = cd.match(/filename="?([^";]+)"?/)
      const filename = m ? decodeURIComponent(m[1]) : 'export.pdf'
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      // Telecharge ET ouvre en aperçu
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 5000)
      showToast('PDF généré.', 'success')
    } catch (e) {
      showToast(`Échec génération PDF : ${(e as Error).message}`, 'error')
    } finally {
      setBusyExport(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-2xl shadow-2xl w-[1100px] max-w-[97vw] max-h-[85vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5" style={{ color: COLOR_PRIMARY }} />
              <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
                Liste des documents RH disponible
              </h2>
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

          {/* Bandeau combo + boutons */}
          <div
            className="flex items-center gap-3 px-5 py-3 border-b"
            style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FBF9F8' }}
          >
            <label className="text-sm" style={{ color: COLOR_BRUN }}>
              Type Produit :
            </label>
            <select
              value={idTypeProduit}
              onChange={(e) => handleChangeTypeProduit(e.target.value)}
              className="px-2 py-1 border rounded text-sm bg-white"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, minWidth: 200 }}
            >
              <option value="">— (sélectionner) —</option>
              {typesProduit.map((t) => (
                <option key={t.id_type_produit} value={t.id_type_produit}>
                  {t.lib}
                </option>
              ))}
            </select>
            <div className="flex-1" />
            <button
              type="button"
              onClick={handleTicketOmaya}
              disabled={!selectedDoc || busyTicket || busyExport}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
              style={{ backgroundColor: COLOR_PRIMARY }}
            >
              {busyTicket ? <Loader2 className="w-4 h-4 animate-spin" /> : <Ticket className="w-4 h-4" />}
              Ticket Omaya
            </button>
            <button
              type="button"
              onClick={handleExportPDF}
              disabled={!selectedDoc || busyTicket || busyExport}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
              style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
            >
              {busyExport ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Export PDF
            </button>
          </div>

          {/* Tableau */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <div
              className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
              style={{
                gridTemplateColumns: '180px 130px 1fr 140px 90px',
                color: COLOR_BRUN,
                backgroundColor: COLOR_BG_SOFT,
                borderColor: COLOR_BG_SOFT,
              }}
            >
              <div>Société (RS Interne)</div>
              <div>Type Doc</div>
              <div>Titre</div>
              <div>Info Cplt</div>
              <div className="text-center">Prioritaire</div>
            </div>
            <div className="flex-1 overflow-y-auto">
              {loadingDocs && (
                <div className="p-3 flex items-center gap-2 text-xs" style={{ color: COLOR_BRUN }}>
                  <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
                </div>
              )}
              {!loadingDocs && docs.length === 0 && (
                <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
                  Aucun document disponible pour ce type produit.
                </div>
              )}
              {!loadingDocs &&
                docs.map((d) => {
                  const isSelected = selected === d.id_doc_rh
                  return (
                    <div
                      key={d.id_doc_rh}
                      onClick={() => setSelected(d.id_doc_rh)}
                      className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                      style={{
                        gridTemplateColumns: '180px 130px 1fr 140px 90px',
                        backgroundColor: isSelected ? COLOR_BG_SOFT : 'white',
                        borderColor: COLOR_BG_SOFT,
                        color: COLOR_BRUN,
                      }}
                    >
                      <div className="truncate" title={d.rs_interne}>
                        {d.rs_interne || '—'}
                      </div>
                      <div className="truncate" title={d.type_doc_lib}>
                        {d.type_doc_lib}
                      </div>
                      <div className="truncate font-medium" title={d.titre}>
                        {d.titre}
                      </div>
                      <div className="truncate" title={d.info_cpl}>
                        {d.info_cpl}
                      </div>
                      <div className="text-center"><CheckMark active={d.prioritaire} /></div>
                    </div>
                  )
                })}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
