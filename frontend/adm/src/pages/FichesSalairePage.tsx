/**
 * Fen_FicheSalaires - Envoi fiches de salaire.
 *
 * 2 plans :
 *   Plan 1 : Découpage PDF + attribution vendeurs
 *   Plan 2 : Prépaie Excel + envoi FDP par email
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft, Send, Loader2, Upload, Check, X as XIcon, Save,
  FileText, ArrowLeftCircle,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'

const API_BASE = '/api/adm'

interface SocieteFDV {
  id_ste: string
  raison_sociale: string
  rs_interne: string
}

interface VendeurRow {
  id_salarie: string
  vendeur: string
  nom_prenom: string
  num_page: number
  nb_page: number
  choix: boolean
  fichier_pdf: string
  base_pdf: string
  tab_prepaies: string
  mail: string
  gsm: string
  couleur: string
}

const currentMoisPaie = (): string => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const bgFromCouleur = (c: string): string => {
  if (c === 'vert') return 'bg-[#D1F2C9]'
  if (c === 'orange') return 'bg-[#FFC6A8]'
  if (c === 'rouge') return 'bg-[#FED2D2]'
  return ''
}

export default function FichesSalairePage() {
  useDocumentTitle('Envoi fiches de salaire')
  const [plan, setPlan] = useState<1 | 2>(1)

  // Header
  const [societes, setSocietes] = useState<SocieteFDV[]>([])
  const [idSte, setIdSte] = useState<string>('')
  const [moisPaie, setMoisPaie] = useState<string>(currentMoisPaie())

  // Plan 1
  const [pdfB64, setPdfB64] = useState('')
  const [vendeurs, setVendeurs] = useState<VendeurRow[]>([])
  const [selectedIdx, setSelectedIdx] = useState<number>(-1)
  const [loading, setLoading] = useState(false)
  const pdfInputRef = useRef<HTMLInputElement>(null)
  const xlsxInputRef = useRef<HTMLInputElement>(null)

  // Plan 2 - Prépaie
  const [prepaieCells, setPrepaieCells] = useState<string[][]>([])
  const [plage, setPlage] = useState<string>('')
  const [xlsxB64, setXlsxB64] = useState('')
  const prepaieInputRef = useRef<HTMLInputElement>(null)
  const gridScrollRef = useRef<HTMLDivElement>(null)
  const [selCell1, setSelCell1] = useState<{ r: number; c: number } | null>(null)
  const [selCell2, setSelCell2] = useState<{ r: number; c: number } | null>(null)

  // Attribution manuelle (ligne rouge)
  const [pickerOpen, setPickerOpen] = useState(false)

  // ------ Chargement initial ------
  const loadSocietes = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/paies/fiches/societes-fdv`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const d = await r.json()
      setSocietes(d.items || [])
    } catch {
      /* silent */
    }
  }, [])

  useEffect(() => {
    void loadSocietes()
  }, [loadSocietes])

  const societe = societes.find((s) => s.id_ste === idSte)

  // ------ Btn Charger PDF ------
  const onPdfSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (!idSte || !moisPaie) {
      showToast('Choisis d\'abord une société et un mois', 'info')
      return
    }
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('fichier', file)
      const r = await fetch(`${API_BASE}/paies/fiches/charger-pdf`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur PDF', 'error')
        return
      }
      setPdfB64(d.pdf_b64)
      setVendeurs(d.vendeurs || [])
      setSelectedIdx(-1)
      showToast(d.message || 'PDF chargé', 'success')
    } finally {
      setLoading(false)
    }
  }

  // ------ Btn Valider (bascule Plan 2) ------
  const doValider = async () => {
    const nonAttr = vendeurs.filter((v) => v.id_salarie === '0').length
    if (nonAttr > 0) {
      showToast(
        `${nonAttr} ligne(s) rouge(s) - Merci de vérifier les lignes en rouge`,
        'error',
      )
      return
    }
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/paies/fiches/valider`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mois_paiement: moisPaie,
          pdf_b64: pdfB64,
          vendeurs,
        }),
      })
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur validation', 'error')
        return
      }
      setVendeurs(d.vendeurs || [])
      showToast(d.message || 'Validation OK', 'success')
      if (d.nb_erreurs === 0) setPlan(2)
    } finally {
      setLoading(false)
    }
  }

  // ------ Btn Sauve EXCEL ------
  const doSauveXlsx = async () => {
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/paies/fiches/sauvegarder-xlsx`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ vendeurs }),
        },
      )
      const d = await r.json()
      if (!d.ok || !d.xlsx_b64) {
        showToast('Erreur sauvegarde', 'error')
        return
      }
      const bytes = atob(d.xlsx_b64)
      const buf = new Uint8Array(bytes.length)
      for (let i = 0; i < bytes.length; i++) buf[i] = bytes.charCodeAt(i)
      const blob = new Blob([buf])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = d.fic_name || 'SauveEnvoieFicSalaires.xlsx'
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
      showToast('XLSX téléchargé', 'success')
    } finally {
      setLoading(false)
    }
  }

  // ------ Btn Réimporter XLSX ------
  const onXlsxSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('fichier', file)
      const r = await fetch(`${API_BASE}/paies/fiches/reimporter-xlsx`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      setVendeurs(d.vendeurs || [])
      showToast(d.message || 'XLSX rechargé', 'success')
    } finally {
      setLoading(false)
    }
  }

  // ------ Blob URL du PDF (pour preview iframe) ------
  const pdfBlobUrl = useMemo<string>(() => {
    if (!pdfB64) return ''
    try {
      const bytes = atob(pdfB64)
      const buf = new Uint8Array(bytes.length)
      for (let i = 0; i < bytes.length; i++) buf[i] = bytes.charCodeAt(i)
      const blob = new Blob([buf], { type: 'application/pdf' })
      return URL.createObjectURL(blob)
    } catch {
      return ''
    }
  }, [pdfB64])

  useEffect(() => {
    // Revoke le blob URL quand il change ou au demontage
    return () => {
      if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl)
    }
  }, [pdfBlobUrl])

  // ------ Attribution manuelle (ligne rouge) ------
  // + affiche le PDF a la page du vendeur clique
  const onLigneRougeClick = (idx: number) => {
    setSelectedIdx(idx)
    if (vendeurs[idx].id_salarie === '0') {
      setPickerOpen(true)
    }
  }

  const onPickSalarie = (s: SalarieItem) => {
    if (selectedIdx < 0) return
    setVendeurs((rows) =>
      rows.map((r, i) =>
        i === selectedIdx
          ? {
              ...r,
              id_salarie: s.id_salarie,
              vendeur: `${s.prenom.toUpperCase()} ${s.nom.toUpperCase()}`,
              nom_prenom: `${s.nom.toUpperCase()} ${s.prenom.charAt(0).toUpperCase()}${s.prenom.slice(1).toLowerCase()}`,
              couleur: 'vert',
            }
          : r,
      ),
    )
    setPickerOpen(false)
  }

  // ------ Btn Ouvrir tableau prépaies ------
  const onPrepaieSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setLoading(true)
    try {
      const arrayBuf = await file.arrayBuffer()
      const b64 = btoa(
        new Uint8Array(arrayBuf).reduce(
          (s, b) => s + String.fromCharCode(b), '',
        ),
      )
      setXlsxB64(b64)

      const fd = new FormData()
      fd.append('fichier', file)
      const r = await fetch(
        `${API_BASE}/paies/fiches/prepaie/parse-xlsx`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        },
      )
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur XLSX', 'error')
        return
      }
      setPrepaieCells(d.cells || [])
      setSelCell1(null)
      setSelCell2(null)
      setPlage('')
      showToast(`${d.nrows} × ${d.ncols} cellules chargées`, 'success')
    } finally {
      setLoading(false)
    }
  }

  // ------ Sélection cellules Excel (drag pour multi) ------
  const [dragging, setDragging] = useState(false)

  const onCellMouseDown = (r: number, c: number, evt: React.MouseEvent) => {
    evt.preventDefault()
    if (evt.shiftKey && selCell1) {
      setSelCell2({ r, c })
      setPlage(cellsToPlage(selCell1, { r, c }))
    } else {
      setSelCell1({ r, c })
      setSelCell2({ r, c })
      setPlage(cellsToPlage({ r, c }, { r, c }))
    }
    setDragging(true)
  }

  const onCellMouseEnter = (r: number, c: number) => {
    if (!dragging || !selCell1) return
    setSelCell2({ r, c })
    setPlage(cellsToPlage(selCell1, { r, c }))
  }

  useEffect(() => {
    const stop = () => setDragging(false)
    if (!dragging) return undefined

    // Auto-scroll du container quand le curseur approche des bords
    const EDGE = 40           // px depuis le bord
    const MAX_SPEED = 20      // px par frame
    let rafId: number | null = null
    let lastMouse = { x: 0, y: 0 }

    const tick = () => {
      const el = gridScrollRef.current
      if (!el) { rafId = null; return }
      const rect = el.getBoundingClientRect()
      const dxLeft = lastMouse.x - rect.left
      const dxRight = rect.right - lastMouse.x
      const dyTop = lastMouse.y - rect.top
      const dyBottom = rect.bottom - lastMouse.y
      let sx = 0
      let sy = 0
      if (dxLeft < EDGE && dxLeft > -EDGE)
        sx = -Math.round(((EDGE - dxLeft) / EDGE) * MAX_SPEED)
      else if (dxRight < EDGE && dxRight > -EDGE)
        sx = Math.round(((EDGE - dxRight) / EDGE) * MAX_SPEED)
      if (dyTop < EDGE && dyTop > -EDGE)
        sy = -Math.round(((EDGE - dyTop) / EDGE) * MAX_SPEED)
      else if (dyBottom < EDGE && dyBottom > -EDGE)
        sy = Math.round(((EDGE - dyBottom) / EDGE) * MAX_SPEED)
      if (sx !== 0) el.scrollLeft += sx
      if (sy !== 0) el.scrollTop += sy
      rafId = requestAnimationFrame(tick)
    }

    const onMove = (e: MouseEvent) => {
      lastMouse = { x: e.clientX, y: e.clientY }
      if (rafId == null) rafId = requestAnimationFrame(tick)
    }

    window.addEventListener('mouseup', stop)
    window.addEventListener('mousemove', onMove)
    return () => {
      window.removeEventListener('mouseup', stop)
      window.removeEventListener('mousemove', onMove)
      if (rafId != null) cancelAnimationFrame(rafId)
    }
  }, [dragging])

  // Auto-selection du premier vendeur choix=true au passage en Plan 2
  // (necessaire pour activer le btn Enregistrer la selection en PDF)
  useEffect(() => {
    if (plan !== 2) return
    if (selectedIdx >= 0 && vendeurs[selectedIdx]?.choix) return
    const first = vendeurs.findIndex((v) => v.choix)
    if (first >= 0) setSelectedIdx(first)
  }, [plan, vendeurs, selectedIdx])

  const cellsToPlage = (a: { r: number; c: number }, b: { r: number; c: number }): string => {
    const rMin = Math.min(a.r, b.r) + 1
    const rMax = Math.max(a.r, b.r) + 1
    const cMin = Math.min(a.c, b.c)
    const cMax = Math.max(a.c, b.c)
    return `${colLetter(cMin)}${rMin}:${colLetter(cMax)}${rMax}`
  }

  const colLetter = (n: number): string => {
    let s = ''
    let x = n
    do {
      s = String.fromCharCode(65 + (x % 26)) + s
      x = Math.floor(x / 26) - 1
    } while (x >= 0)
    return s
  }

  const isCellSelected = (r: number, c: number): boolean => {
    if (!selCell1 || !selCell2) return false
    return (
      r >= Math.min(selCell1.r, selCell2.r)
      && r <= Math.max(selCell1.r, selCell2.r)
      && c >= Math.min(selCell1.c, selCell2.c)
      && c <= Math.max(selCell1.c, selCell2.c)
    )
  }

  // ------ Btn Enregistrer la sélection en PDF ------
  const doEnregistrerSelection = async () => {
    if (selectedIdx < 0) {
      showToast('Sélectionne un vendeur', 'info')
      return
    }
    if (!plage || !xlsxB64) {
      showToast('Sélectionne une plage dans le tableau Excel', 'info')
      return
    }
    const v = vendeurs[selectedIdx]
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/paies/fiches/prepaie/generer-pdf`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_salarie: v.id_salarie,
            nom_prenom: v.nom_prenom,
            mois_paiement: moisPaie,
            xlsx_b64: xlsxB64,
            plage,
          }),
        },
      )
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      // Applique couleur + nom fichier
      setVendeurs((rows) =>
        rows.map((row, i) =>
          i === selectedIdx
            ? { ...row, tab_prepaies: d.fic_name, couleur: d.couleur }
            : row,
        ),
      )
      showToast(d.message || 'PDF prépaie envoyé', 'success')
    } finally {
      setLoading(false)
    }
  }

  // ------ Btn Valider et envoyer les FDP ------
  const doEnvoyerFDP = async () => {
    if (!societe) return
    const nb = vendeurs.filter((v) => v.choix).length
    const ok = await showConfirm({
      title: 'Envoyer les FDP',
      message: `Envoyer ${nb} email(s) aux vendeurs avec pièces jointes ZIP ?`,
    })
    if (!ok) return
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/paies/fiches/envoyer-fdp`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_ste: idSte,
          raison_sociale: societe.raison_sociale,
          mois_paiement: moisPaie,
          vendeurs,
        }),
      })
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      // Applique couleurs
      const majMap = new Map(
        (d.envois || []).map((e: EnvoiVendeurResult) => [
          e.id_salarie, e,
        ]),
      )
      setVendeurs((rows) =>
        rows.map((r) => {
          const m = majMap.get(r.id_salarie) as
            | { couleur: string } | undefined
          return m ? { ...r, couleur: m.couleur } : r
        }),
      )
      showToast(d.message || 'Envois terminés', 'success')
    } finally {
      setLoading(false)
    }
  }

  // ------ Rendu ------
  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Link
            to="/"
            className="p-2 rounded hover:bg-white/50"
            title="Retour"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Send className="w-6 h-6 text-[#8B7355]" />
          <h1 className="text-2xl font-semibold text-[#8B7355]">
            Envoi des fiches de salaires
          </h1>
          <div className="ml-auto text-xs text-gray-500">
            Plan {plan}/2
          </div>
        </div>

        {/* Header commun */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex items-center gap-4 flex-wrap">
            <label className="flex flex-col text-xs gap-1 min-w-[240px]">
              <span className="text-[#8B7355] font-medium">Société</span>
              <select
                value={idSte}
                onChange={(e) => setIdSte(e.target.value)}
                className="px-2 py-1.5 border border-[#E5E0D5] rounded"
              >
                <option value="">Choisir une entité</option>
                {societes.map((s) => (
                  <option key={s.id_ste} value={s.id_ste}>
                    {s.rs_interne}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Salaire du (MM-AAAA)</span>
              <input
                type="month"
                value={moisPaie}
                onChange={(e) => setMoisPaie(e.target.value)}
                className="px-2 py-1.5 border border-[#E5E0D5] rounded"
              />
            </label>

            {plan === 1 && (
              <>
                <button
                  onClick={() => pdfInputRef.current?.click()}
                  disabled={loading || !idSte || !moisPaie}
                  className="ml-auto flex items-center gap-2 px-3 py-2 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
                >
                  <Upload className="w-4 h-4" />
                  Charger le fichier PDF
                </button>
                <button
                  onClick={doValider}
                  disabled={loading || vendeurs.length === 0}
                  className="flex items-center gap-2 px-3 py-2 rounded bg-[#059669] text-white disabled:opacity-40 hover:bg-[#047857]"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Valider
                </button>
              </>
            )}
            <input
              ref={pdfInputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={onPdfSelected}
            />
            <input
              ref={xlsxInputRef}
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={onXlsxSelected}
            />
          </div>

          {plan === 1 && vendeurs.length > 0 && (
            <div className="mt-3 flex items-center gap-2">
              <button
                onClick={doSauveXlsx}
                className="flex items-center gap-1.5 text-sm px-2 py-1 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]"
              >
                <Save className="w-3.5 h-3.5" />
                Sauve EXCEL
              </button>
              <button
                onClick={() => xlsxInputRef.current?.click()}
                className="flex items-center gap-1.5 text-sm px-2 py-1 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]"
              >
                <Upload className="w-3.5 h-3.5" />
                Réimporter Sauve XLS
              </button>
              <span className="text-xs text-gray-500 ml-auto">
                {vendeurs.length} vendeur(s) - {vendeurs.filter((v) => v.id_salarie === '0').length} en rouge
              </span>
            </div>
          )}
        </div>

        {/* Plan 2 - Actions supp */}
        {plan === 2 && (
          <div className="bg-white rounded-lg shadow p-4 mb-4">
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() => setPlan(1)}
                className="flex items-center gap-1.5 px-3 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]"
              >
                <ArrowLeftCircle className="w-4 h-4" />
                Retour étape précédente
              </button>
              <button
                onClick={() => prepaieInputRef.current?.click()}
                className="flex items-center gap-1.5 px-3 py-2 rounded bg-[#8B7355] text-white hover:bg-[#725e46]"
              >
                <Upload className="w-4 h-4" />
                Ouvrir un tableau prépaies
              </button>
              <button
                onClick={doEnregistrerSelection}
                disabled={loading || !plage || selectedIdx < 0}
                title={
                  selectedIdx < 0
                    ? 'Sélectionne d\'abord un vendeur dans la liste'
                    : !plage
                    ? 'Sélectionne d\'abord une plage dans le tableau'
                    : ''
                }
                className="flex items-center gap-1.5 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
              >
                <FileText className="w-4 h-4" />
                Enregistrer la sélection en PDF
              </button>
              <button
                onClick={doEnvoyerFDP}
                disabled={loading || vendeurs.filter((v) => v.choix).length === 0}
                className="ml-auto flex items-center gap-2 px-3 py-2 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Valider et envoyer les FDP
              </button>
              <input
                ref={prepaieInputRef}
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={onPrepaieSelected}
              />
            </div>
            {plan === 2 && plage && (
              <div className="mt-2 text-xs text-[#8B7355]">
                Plage sélectionnée : <span className="font-mono font-semibold">{plage}</span>
                {selectedIdx >= 0 && (
                  <span className="ml-2">
                    → Sera enregistrée pour {vendeurs[selectedIdx]?.nom_prenom}
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* 2 colonnes : Table vendeurs + Preview PDF/XLSX */}
        <div className="grid grid-cols-1 lg:grid-cols-[420px_minmax(0,1fr)] gap-4">
          {/* Table vendeurs */}
          <div className="bg-white rounded-lg shadow p-4">
            <div className="max-h-[700px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-white">
                  <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
                    {plan === 1 ? (
                      <>
                        <th className="py-1.5 px-2">Vendeur</th>
                        <th className="py-1.5 px-2 text-right">Page</th>
                        <th className="py-1.5 px-2 text-right">Nb</th>
                      </>
                    ) : (
                      <>
                        <th className="py-1.5 px-2 text-center w-6">
                          <Check className="w-3 h-3 inline" />
                        </th>
                        <th className="py-1.5 px-2">Nom Prénom</th>
                        <th className="py-1.5 px-2 text-center">FS</th>
                        <th className="py-1.5 px-2 text-center">Base</th>
                        <th className="py-1.5 px-2 text-center">Prep</th>
                      </>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {vendeurs.map((v, i) => (
                    <tr
                      key={i}
                      onClick={() => onLigneRougeClick(i)}
                      className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${bgFromCouleur(v.couleur)} ${
                        selectedIdx === i ? 'ring-2 ring-[#8B7355]' : ''
                      }`}
                    >
                      {plan === 1 ? (
                        <>
                          <td className="py-1.5 px-2">
                            {v.vendeur}
                            {v.nom_prenom && (
                              <div className="text-[10px] text-gray-500">
                                → {v.nom_prenom}
                              </div>
                            )}
                          </td>
                          <td className="py-1.5 px-2 text-right tabular-nums">
                            {v.num_page}
                          </td>
                          <td className="py-1.5 px-2 text-right tabular-nums">
                            {v.nb_page}
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="py-1.5 px-2 text-center">
                            {v.choix ? (
                              <Check className="w-3 h-3 inline text-green-700" />
                            ) : (
                              <XIcon className="w-3 h-3 inline text-gray-300" />
                            )}
                          </td>
                          <td className="py-1.5 px-2">
                            <div>{v.nom_prenom}</div>
                            <div className="text-[10px] text-gray-500 truncate max-w-[180px]">
                              {v.mail}
                            </div>
                          </td>
                          <td className="py-1.5 px-2 text-center">
                            {v.fichier_pdf ? (
                              <span className="text-green-700">●</span>
                            ) : ''}
                          </td>
                          <td className="py-1.5 px-2 text-center">
                            {v.base_pdf ? (
                              <span className="text-green-700">●</span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </td>
                          <td className="py-1.5 px-2 text-center">
                            {v.tab_prepaies ? (
                              <span className="text-green-700">●</span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </td>
                        </>
                      )}
                    </tr>
                  ))}
                  {vendeurs.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-gray-400">
                        {plan === 1
                          ? 'Charge un PDF ou réimporte un XLSX'
                          : 'Aucun vendeur'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Preview */}
          <div className="bg-white rounded-lg shadow p-4">
            {plan === 1 && pdfBlobUrl && (
              <div>
                <div className="text-[11px] text-gray-500 mb-2">
                  {vendeurs.length} vendeur(s) identifié(s) - Cliquez sur
                  une ligne pour afficher la page. Ligne rouge : ouvre
                  aussi la recherche salarié.
                  {selectedIdx >= 0 && vendeurs[selectedIdx] && (
                    <span className="ml-2 text-[#8B7355] font-medium">
                      Page {vendeurs[selectedIdx].num_page}
                      {vendeurs[selectedIdx].nb_page > 1
                        ? `-${vendeurs[selectedIdx].num_page + vendeurs[selectedIdx].nb_page - 1}`
                        : ''}
                    </span>
                  )}
                </div>
                <iframe
                  key={selectedIdx >= 0 ? vendeurs[selectedIdx]?.num_page : 0}
                  title="Aperçu PDF"
                  src={`${pdfBlobUrl}#page=${
                    selectedIdx >= 0 ? vendeurs[selectedIdx]?.num_page || 1 : 1
                  }&toolbar=1&navpanes=0`}
                  className="w-full border border-[#E5E0D5] rounded"
                  style={{ height: '650px' }}
                />
              </div>
            )}
            {plan === 1 && !pdfBlobUrl && (
              <div className="py-8 text-center text-sm text-gray-400">
                Chargez un PDF pour voir l'aperçu
              </div>
            )}
            {plan === 2 && prepaieCells.length > 0 && (
              <div>
                <div className="text-xs text-[#8B7355] font-medium mb-2">
                  Cliquez-glissez pour sélectionner une plage (ou clic + Maj+clic)
                </div>
                <div
                  ref={gridScrollRef}
                  className="overflow-auto max-h-[600px] border border-[#E5E0D5] rounded"
                >
                  <table className="text-[10px] border-collapse">
                    <thead>
                      <tr>
                        <th className="bg-[#E5E0D5] px-1 py-0.5 sticky top-0 left-0 z-20"></th>
                        {prepaieCells[0]?.map((_, c) => (
                          <th
                            key={c}
                            className="bg-[#E5E0D5] px-2 py-0.5 sticky top-0 z-10 text-[#8B7355] font-mono"
                          >
                            {colLetter(c)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {prepaieCells.map((row, r) => (
                        <tr key={r}>
                          <th className="bg-[#E5E0D5] px-2 py-0.5 sticky left-0 text-[#8B7355] font-mono">
                            {r + 1}
                          </th>
                          {row.map((cell, c) => (
                            <td
                              key={c}
                              onMouseDown={(e) => onCellMouseDown(r, c, e)}
                              onMouseEnter={() => onCellMouseEnter(r, c)}
                              className={`border border-[#E5E0D5] px-1 py-0.5 whitespace-nowrap cursor-pointer ${
                                isCellSelected(r, c)
                                  ? 'bg-[#8B7355] text-white'
                                  : 'hover:bg-[#ECF1F2]'
                              }`}
                            >
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            {plan === 2 && prepaieCells.length === 0 && (
              <div className="py-8 text-center text-sm text-gray-400">
                Utilisez « Ouvrir un tableau prépaies » pour charger un XLSX
              </div>
            )}
          </div>
        </div>
      </div>

      {pickerOpen && (
        <PersonnePicker
          title="Attribuer un salarié"
          onClose={() => setPickerOpen(false)}
          onSelect={onPickSalarie}
        />
      )}
    </div>
  )
}

// Utils
interface EnvoiVendeurResult {
  id_salarie: string
  nom_prenom: string
  mail: string
  couleur: string
  message: string
}

