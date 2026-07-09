/**
 * Fen_ScoolBulletin - Fiche bulletin S'Cool.
 *
 * URL : /scool/formations/:id_formation/bulletin/nouveau?id_salarie=X
 *       /scool/formations/:id_formation/bulletin/:id_bulletin
 *
 * Layout : formulaire complet + table des notes calculees + PDF.
 */
import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Save, FileText, ArrowLeft, Loader2, RefreshCw, Calculator,
  ClipboardCheck,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

interface Bulletin {
  id_bulletin: string
  id_formation: string
  id_salarie: string
  du: string; au: string
  type_bulletin: number
  nb_jours_form: number
  nb_jours_pres: number
  objectif_ctt: number
  objectif_decale: number
  objectif_coopt: number
  nb_ctt_hr: number
  nb_cqt_hr: number
  nb_prem_hr: number
  nb_mob_hr: number
  nb_coopt: number
  note_assiduite: number
  note_ctt_hr: number
  note_cqt: number
  note_prem: number
  note_mob: number
  note_coopt: number
  note_obj_decale: number
  note_app_theo: number
  note_app_pratique: number
  id_bulletin_mention: string
  observation: string
  axe_travail: string
}

interface StagiaireCombo { id_salarie: string; nom_prenom: string }
interface MentionCombo { id_bulletin_mention: string; lib_mention: string }
interface NoteCalculee {
  type_note: string; lib_note: string
  palier_calc: number; note: number
}

// Assigne chaque type_note calcule au champ correspondant du bulletin
const _TYPE_TO_FIELD: Record<string, keyof Bulletin> = {
  NoteAssiduite: 'note_assiduite',
  NoteCttHR: 'note_ctt_hr',
  NoteCQT: 'note_cqt',
  NotePREM: 'note_prem',
  NoteMOB: 'note_mob',
  NoteCoopt: 'note_coopt',
  'NoteObjDécalé': 'note_obj_decale',
  NoteObjDecale: 'note_obj_decale',
}

export default function ScoolBulletinPage() {
  useDocumentTitle('Fiche Bulletin')
  const nav = useNavigate()
  const { id_formation, id_bulletin } = useParams()
  const [sp] = useSearchParams()
  const idSalarieParam = sp.get('id_salarie') || ''

  const [data, setData] = useState<Bulletin | null>(null)
  const [stagiaires, setStagiaires] = useState<StagiaireCombo[]>([])
  const [mentions, setMentions] = useState<MentionCombo[]>([])
  const [notesCalc, setNotesCalc] = useState<NoteCalculee[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [recuperLoading, setRecuperLoading] = useState(false)
  const [notesLoading, setNotesLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)

  const isNew = !id_bulletin || id_bulletin === 'nouveau'

  const loadStagiaires = useCallback(async () => {
    if (!id_formation) return
    const r = await fetch(
      `${API_BASE}/scool/bulletins/stagiaires/${id_formation}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setStagiaires(await r.json())
  }, [id_formation])

  const loadMentions = useCallback(async () => {
    const r = await fetch(`${API_BASE}/scool/bulletins/mentions`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    setMentions(await r.json())
  }, [])

  const loadDetail = useCallback(async () => {
    if (!id_formation) return
    setLoading(true)
    try {
      if (isNew) {
        const idSal = idSalarieParam
        if (!idSal) {
          setData(null); return
        }
        const r = await fetch(
          `${API_BASE}/scool/bulletins?id_formation=${id_formation}&id_salarie=${idSal}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        setData(await r.json())
      } else {
        const r = await fetch(
          `${API_BASE}/scool/bulletins/${id_bulletin}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        setData(await r.json())
      }
    } finally { setLoading(false) }
  }, [id_formation, id_bulletin, isNew, idSalarieParam])

  useEffect(() => {
    void loadStagiaires()
    void loadMentions()
    void loadDetail()
  }, [loadStagiaires, loadMentions, loadDetail])

  const upd = (patch: Partial<Bulletin>) => {
    setData((d) => (d ? { ...d, ...patch } : d))
  }

  const doRecuperer = async () => {
    if (!data) return
    if (!data.id_salarie || data.id_salarie === '0') {
      showToast('Choisis un stagiaire', 'info'); return
    }
    setRecuperLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/scool/bulletins/recuperer-prod`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_formation: data.id_formation,
            id_salarie: data.id_salarie,
            du: data.du, au: data.au,
          }),
        },
      )
      const d = await r.json()
      if (!d.ok) { showToast('Erreur récup', 'error'); return }
      upd({
        nb_jours_form: d.nb_jours_form,
        nb_jours_pres: d.nb_jours_pres,
        nb_ctt_hr: d.res_note_ctt_hr,
        nb_cqt_hr: d.res_note_cqt,
        nb_prem_hr: d.res_note_prem,
        nb_mob_hr: d.res_note_mob,
        nb_coopt: d.res_note_coopt,
      })
      showToast('Prod et absences récupérées', 'success')
    } finally { setRecuperLoading(false) }
  }

  const doCalculerNotes = async () => {
    if (!data) return
    setNotesLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/scool/bulletins/calculer-notes`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_formation: data.id_formation,
            nb_jours_form: data.nb_jours_form,
            nb_absences: data.nb_jours_form - data.nb_jours_pres,
            objectif_ctt: data.objectif_ctt,
            objectif_coopt: data.objectif_coopt,
            objectif_decale: data.objectif_decale,
            res_note_ctt_hr: data.nb_ctt_hr,
            res_note_cqt: data.nb_cqt_hr,
            res_note_prem: data.nb_prem_hr,
            res_note_mob: data.nb_mob_hr,
            res_note_coopt: data.nb_coopt,
          }),
        },
      )
      const d = await r.json()
      if (!d.ok) { showToast('Erreur calcul', 'error'); return }
      setNotesCalc(d.notes || [])
      // Applique les notes au bulletin
      const patch: Partial<Bulletin> = {}
      ;(d.notes || []).forEach((n: NoteCalculee) => {
        const field = _TYPE_TO_FIELD[n.type_note]
        if (field) {
          (patch as Record<string, number>)[field as string] = n.note
        }
      })
      upd(patch)
      showToast('Notes calculées', 'success')
    } finally { setNotesLoading(false) }
  }

  const doSave = async () => {
    if (!data) return
    setSaving(true)
    try {
      const url = isNew
        ? `${API_BASE}/scool/bulletins`
        : `${API_BASE}/scool/bulletins/${id_bulletin}`
      const method = isNew ? 'POST' : 'PUT'
      const { id_bulletin: _, ...payload } = data
      const r = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      const d = await r.json()
      if (d.ok) {
        showToast('Bulletin enregistré', 'success')
        if (isNew && d.id_bulletin) {
          nav(`/scool/formations/${id_formation}/bulletin/${d.id_bulletin}`, { replace: true })
        }
      } else showToast('Erreur', 'error')
    } finally { setSaving(false) }
  }

  const doPdf = async () => {
    if (!id_bulletin || id_bulletin === 'nouveau') {
      showToast('Enregistre d\'abord le bulletin', 'info'); return
    }
    setPdfLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/scool/bulletins/${id_bulletin}/pdf`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) { showToast('Erreur PDF', 'error'); return }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = `Bulletin_${id_bulletin}.pdf`; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
    } finally { setPdfLoading(false) }
  }

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-[#F5F5F0] p-6 flex items-center gap-2 text-[#8B7355]">
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement...
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader
          icon={ClipboardCheck}
          backTo={`/scool/formations/${id_formation}`}
          title="Fiche Bulletin"
          right={
            <button onClick={() => nav(`/scool/formations/${id_formation}`)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm">
              <ArrowLeft className="w-4 h-4" /> Retour
            </button>
          }
        />

        <div className="bg-white rounded-lg shadow p-4 space-y-4">
          {/* Ligne 1 : Stagiaire + Dates + Type + Enregistrer */}
          <div className="flex items-end gap-3 flex-wrap">
            <label className="flex flex-col text-xs gap-1 min-w-[280px]">
              <span className="text-[#8B7355] font-medium">Stagiaire</span>
              <select value={data.id_salarie}
                      onChange={(e) => upd({ id_salarie: e.target.value })}
                      disabled={!isNew}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded">
                <option value="">Choisir...</option>
                {stagiaires.map((s) => (
                  <option key={s.id_salarie} value={s.id_salarie}>
                    {s.nom_prenom}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Du</span>
              <input type="date" value={data.du}
                     onChange={(e) => upd({ du: e.target.value })}
                     className="px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Au</span>
              <input type="date" value={data.au}
                     onChange={(e) => upd({ au: e.target.value })}
                     className="px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <button onClick={doRecuperer}
                    disabled={recuperLoading}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm disabled:opacity-40">
              {recuperLoading ? <Loader2 className="w-4 h-4 animate-spin" />
                : <RefreshCw className="w-4 h-4" />}
              Récupérer la prod et les absences
            </button>
            <div className="ml-auto flex items-center gap-2">
              <div className="flex rounded border border-[#E5E0D5]">
                <button onClick={() => upd({ type_bulletin: 0 })}
                        className={`px-3 py-1.5 text-sm ${
                          data.type_bulletin !== 1 ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                        }`}>
                  Intermédiaire
                </button>
                <button onClick={() => upd({ type_bulletin: 1 })}
                        className={`px-3 py-1.5 text-sm ${
                          data.type_bulletin === 1 ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                        }`}>
                  Définitif
                </button>
              </div>
              <button onClick={doSave} disabled={saving}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm disabled:opacity-40">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Save className="w-4 h-4" />}
                Enregistrer
              </button>
            </div>
          </div>

          <p className="text-xs text-red-700 italic">
            Si la prod n'a pas été importée, les tickets CALL validés
            avec Num BS seront ajoutés
          </p>

          {/* Ligne 2 : compteurs */}
          <div className="grid grid-cols-6 gap-3">
            <FieldNum label="nb Jours Formation" value={data.nb_jours_form}
                      onChange={(v) => upd({ nb_jours_form: v })} />
            <FieldNum label="Objectif Ctt" value={data.objectif_ctt}
                      onChange={(v) => upd({ objectif_ctt: v })} />
            <FieldNum label="nb Jours Présence" value={data.nb_jours_pres}
                      onChange={(v) => upd({ nb_jours_pres: v })} />
            <FieldNum label="nb Ctt Fibre HR" value={data.nb_ctt_hr}
                      onChange={(v) => upd({ nb_ctt_hr: v })} />
            <FieldNum label="nb Conquête HR" value={data.nb_cqt_hr}
                      onChange={(v) => upd({ nb_cqt_hr: v })} />
            <FieldNum label="nb Premium HR" value={data.nb_prem_hr}
                      onChange={(v) => upd({ nb_prem_hr: v })} />
            <FieldNum label="nb Mobile HR" value={data.nb_mob_hr}
                      onChange={(v) => upd({ nb_mob_hr: v })} />
            <FieldNum label="Objectif Cooptation" value={data.objectif_coopt}
                      onChange={(v) => upd({ objectif_coopt: v })} />
            <FieldNum label="nb Cooptation" value={data.nb_coopt}
                      onChange={(v) => upd({ nb_coopt: v })} />
            <div className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Objectif Décalé</span>
              <div className="flex rounded border border-[#E5E0D5]">
                <button onClick={() => upd({ objectif_decale: 0 })}
                        className={`flex-1 px-2 py-1.5 text-xs ${
                          data.objectif_decale === 0 ? 'bg-[#B91C1C] text-white' : 'text-[#B91C1C]'
                        }`}>
                  Non atteint
                </button>
                <button onClick={() => upd({ objectif_decale: 1 })}
                        className={`flex-1 px-2 py-1.5 text-xs ${
                          data.objectif_decale === 1 ? 'bg-green-700 text-white' : 'text-green-700'
                        }`}>
                  Atteint
                </button>
              </div>
            </div>
          </div>

          {/* Ligne 3 : Notes */}
          <div className="grid grid-cols-7 gap-3">
            <FieldNum label="Note Assiduité" value={data.note_assiduite}
                      onChange={(v) => upd({ note_assiduite: v })} step={0.01} decimal />
            <FieldNum label="Note Objectif" value={data.note_ctt_hr}
                      onChange={(v) => upd({ note_ctt_hr: v })} step={0.01} decimal />
            <FieldNum label="Note Conquête" value={data.note_cqt}
                      onChange={(v) => upd({ note_cqt: v })} step={0.01} decimal />
            <FieldNum label="Note Premium" value={data.note_prem}
                      onChange={(v) => upd({ note_prem: v })} step={0.01} decimal />
            <FieldNum label="Note Mobile" value={data.note_mob}
                      onChange={(v) => upd({ note_mob: v })} step={0.01} decimal />
            <FieldNum label="Note Objectif décalé" value={data.note_obj_decale}
                      onChange={(v) => upd({ note_obj_decale: v })} step={0.01} decimal />
            <FieldNum label="Note Cooptation" value={data.note_coopt}
                      onChange={(v) => upd({ note_coopt: v })} step={0.01} decimal />
          </div>

          <div className="flex items-center gap-2">
            <button onClick={doCalculerNotes}
                    disabled={notesLoading}
                    className="flex items-center gap-2 px-4 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438] disabled:opacity-40">
              {notesLoading ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Calculator className="w-4 h-4" />}
              Calculer les notes
            </button>
            <button onClick={doPdf}
                    disabled={pdfLoading || isNew}
                    title={isNew ? 'Enregistre d\'abord' : ''}
                    className="flex items-center gap-2 px-4 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40">
              {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" />
                : <FileText className="w-4 h-4" />}
              Générer le bulletin PDF
            </button>
          </div>

          {/* Table Notes calculees */}
          {notesCalc.length > 0 && (
            <div className="mt-2">
              <h3 className="text-sm font-semibold text-[#17494E] mb-2">
                Résultats du calcul
              </h3>
              <table className="text-xs w-full">
                <thead className="bg-[#17494E] text-white">
                  <tr>
                    <th className="py-1.5 px-2 text-left">Lib Note</th>
                    <th className="py-1.5 px-2 text-right">Palier calculé</th>
                    <th className="py-1.5 px-2 text-right">Note</th>
                  </tr>
                </thead>
                <tbody>
                  {notesCalc.map((n, i) => (
                    <tr key={i} className="border-b border-[#F0EDE5]">
                      <td className="py-1 px-2">{n.lib_note}</td>
                      <td className="py-1 px-2 text-right tabular-nums">
                        {n.palier_calc.toFixed(2)}
                      </td>
                      <td className="py-1 px-2 text-right tabular-nums font-semibold">
                        {n.note.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Notes attitude */}
          <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[#F0EDE5]">
            <FieldNum
              label="Note Théorique Attitude, État d'esprit, Présentation, Ponctualité"
              value={data.note_app_theo}
              onChange={(v) => upd({ note_app_theo: v })} step={0.01} decimal />
            <FieldNum
              label="Note Pratique Attitude, État d'esprit, Présentation, Ponctualité"
              value={data.note_app_pratique}
              onChange={(v) => upd({ note_app_pratique: v })} step={0.01} decimal />
          </div>

          {/* Partie formateurs */}
          <div className="border-t border-[#F0EDE5] pt-3 space-y-3">
            <h3 className="text-sm font-semibold text-[#17494E]">
              Partie réservée aux formateurs
            </h3>
            <label className="flex flex-col text-xs gap-1 max-w-md">
              <span className="text-[#8B7355] font-medium">Mention</span>
              <select value={data.id_bulletin_mention}
                      onChange={(e) => upd({ id_bulletin_mention: e.target.value })}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded">
                {mentions.map((m) => (
                  <option key={m.id_bulletin_mention} value={m.id_bulletin_mention}>
                    {m.lib_mention}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Observation</span>
                <textarea rows={4} value={data.observation}
                          onChange={(e) => upd({ observation: e.target.value })}
                          className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Axe de Travail</span>
                <textarea rows={4} value={data.axe_travail}
                          onChange={(e) => upd({ axe_travail: e.target.value })}
                          className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Champ numerique compact
function FieldNum({
  label, value, onChange, step, decimal,
}: {
  label: string; value: number
  onChange: (v: number) => void
  step?: number; decimal?: boolean
}) {
  return (
    <label className="flex flex-col text-xs gap-1">
      <span className="text-[#8B7355] font-medium truncate" title={label}>
        {label}
      </span>
      <input type="number" step={step || 1} value={value}
             onChange={(e) => onChange(
               decimal ? Number(e.target.value) : Math.round(Number(e.target.value)),
             )}
             className="px-2 py-1.5 border border-[#E5E0D5] rounded text-right tabular-nums" />
    </label>
  )
}
