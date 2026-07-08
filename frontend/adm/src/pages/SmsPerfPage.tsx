/**
 * Fen_SMSPerf - Gestion SMS Perf-Exo.
 *
 * 2 onglets :
 *   1. Règles d'envoi des SMS (config individuelle d'une regle)
 *   2. Destinataires et Scores (equipes destinataires + inclus)
 *
 * Header : toggle Perf-Exo actif + jetons Staff Destinataire
 * Tableau principal : liste des regles avec +/crayon/duplique/suppr
 * Btn Envoyer SMS avec date (proc Animation_SmsPerf - a venir commit 2/2)
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Loader2, Plus, Pencil, Copy, Trash2, Save, Send, X, Users,
  MessageSquare, Check,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'
import OrgaTreePickerModal from '@/components/OrgaTreePickerModal'

const API_BASE = '/api/adm'

// ------ Types ------

interface StaffItem { id_salarie: string; nom: string; prenom: string }
interface RegleEnvoi {
  id_regle: string
  type_sms: string
  code_animation: string
  texte_sms: string
  heure_envoi: number
  heure_debut: number
  heure_fin: number
  ordre: number
  sms_groupe: boolean
  partenaire: string
  prod_groupe: number    // 1=Vendeur / 2=Equipe / 3=Agence
  periode_calcul: number // 1=Journalier / 2=Hebdo / 3=Mensuel
  nb_bs_min: number
  is_actif: boolean
}
interface DestinataireRow {
  id_dest: string
  idorganigramme: string
  lib_orga: string
  anim_code: string
  du: string; au: string
  is_actif: boolean
}
interface EquipeScoreRow {
  id_orga_periode: string
  idorganigramme: string
  lib_orga: string
  code_animation: string
  type: string
  du: string; au: string
  is_actif: boolean
}

type Tab = 'regles' | 'scores'

const EMPTY_REGLE: Omit<RegleEnvoi, 'id_regle'> = {
  type_sms: 'Perf-Exo', code_animation: '', texte_sms: '',
  heure_envoi: 0, heure_debut: 0, heure_fin: 0, ordre: 0,
  sms_groupe: false, partenaire: '',
  prod_groupe: 1, periode_calcul: 1, nb_bs_min: 1, is_actif: true,
}

const PARTENAIRES = [
  { v: '', l: '— Aucun —' },
  { v: 'ENI', l: 'ENI (Plenitude)' },
  { v: 'SFR', l: 'SFR' },
  { v: 'IAG', l: 'IAG' },
  { v: 'STR', l: 'STRATO' },
  { v: 'VAL', l: 'VALANDRE' },
  { v: 'PRO', l: 'PROTECTED' },
  { v: 'OEN', l: 'OHM Energie' },
  { v: 'TLC', l: 'TLC' },
]

// ---------------------------------------------------------------------

export default function SmsPerfPage() {
  useDocumentTitle('SMS Perf-Exo')

  const [perfActif, setPerfActif] = useState(false)
  const [staff, setStaff] = useState<StaffItem[]>([])
  const [staffPickerOpen, setStaffPickerOpen] = useState(false)
  const [regles, setRegles] = useState<RegleEnvoi[]>([])
  const [selRegleIdx, setSelRegleIdx] = useState<number>(-1)
  const [regleModal, setRegleModal] = useState<{
    mode: 'new' | 'edit'; data: RegleEnvoi
  } | null>(null)
  const [tab, setTab] = useState<Tab>('regles')

  const [renvoiDate, setRenvoiDate] = useState(
    () => new Date().toISOString().slice(0, 10),
  )
  const [loading, setLoading] = useState(false)

  // ----- Chargements initiaux -----

  const loadActif = useCallback(async () => {
    const r = await fetch(`${API_BASE}/comm/sms-perf/actif`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    const d = await r.json()
    setPerfActif(!!d.is_actif)
  }, [])

  const loadStaff = useCallback(async () => {
    const r = await fetch(`${API_BASE}/comm/sms-perf/staff`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    const d: StaffItem[] = await r.json()
    setStaff(d || [])
  }, [])

  const loadRegles = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/comm/sms-perf/regles`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const d: RegleEnvoi[] = await r.json()
      setRegles(d || [])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    void loadActif()
    void loadStaff()
    void loadRegles()
  }, [loadActif, loadStaff, loadRegles])

  // ----- Toggle Perf-Exo -----

  const doToggle = async () => {
    const nouveau = !perfActif
    setPerfActif(nouveau)
    await fetch(`${API_BASE}/comm/sms-perf/actif`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ is_actif: nouveau }),
    })
    showToast(nouveau ? 'Perf-Exo activé' : 'Perf-Exo désactivé', 'success')
  }

  // ----- Staff -----

  const saveStaff = async (nouveaux: StaffItem[]) => {
    await fetch(`${API_BASE}/comm/sms-perf/staff`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id_salaries: nouveaux.map((s) => s.id_salarie),
      }),
    })
  }

  const onPickStaff = async (s: SalarieItem) => {
    setStaffPickerOpen(false)
    if (staff.some((x) => x.id_salarie === s.id_salarie)) return
    const item: StaffItem = {
      id_salarie: s.id_salarie, nom: s.nom, prenom: s.prenom,
    }
    const nouveaux = [...staff, item]
    setStaff(nouveaux)
    await saveStaff(nouveaux)
    showToast('Staff ajouté', 'success')
  }

  const removeStaff = async (id: string) => {
    const nouveaux = staff.filter((s) => s.id_salarie !== id)
    setStaff(nouveaux)
    await saveStaff(nouveaux)
  }

  // ----- CRUD Régles -----

  const saveRegle = async () => {
    if (!regleModal) return
    if (!regleModal.data.code_animation.trim()) {
      showToast('Code Animation requis', 'info')
      return
    }
    const url = regleModal.mode === 'new'
      ? `${API_BASE}/comm/sms-perf/regles`
      : `${API_BASE}/comm/sms-perf/regles/${regleModal.data.id_regle}`
    const method = regleModal.mode === 'new' ? 'POST' : 'PUT'
    const { id_regle: _, type_sms: __, ...payload } = regleModal.data
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
      showToast('Enregistré', 'success')
      setRegleModal(null)
      await loadRegles()
    } else showToast('Erreur', 'error')
  }

  const duplicateRegle = async (idx: number) => {
    const r = await fetch(
      `${API_BASE}/comm/sms-perf/regles/${regles[idx].id_regle}/dupliquer`,
      { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    const d = await r.json()
    if (d.ok) { showToast('Dupliqué', 'success'); await loadRegles() }
  }

  const deleteRegle = async (idx: number) => {
    if (!await showConfirm({
      title: 'Supprimer',
      message: `Supprimer la règle "${regles[idx].code_animation}" ?`,
    })) return
    await fetch(`${API_BASE}/comm/sms-perf/regles/${regles[idx].id_regle}`, {
      method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` },
    })
    await loadRegles()
    setSelRegleIdx(-1)
  }

  // ----- Envoi SMS -----

  const doEnvoyer = async (simulation: boolean) => {
    if (!await showConfirm({
      title: simulation ? 'Simuler l\'envoi' : 'Envoyer les SMS RÉELLEMENT',
      message: simulation
        ? `Calculer les scores + composer les SMS Perf-Exo pour ${renvoiDate} (sans envoyer) ?`
        : `⚠️ Envoi RÉEL des SMS Perf-Exo pour ${renvoiDate}. Continuer ?`,
    })) return
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/comm/sms-perf/envoyer`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ date_jour: renvoiDate, simulation }),
      })
      const d = await r.json()
      if (!d.ok) { showToast(d.message || 'Erreur', 'error'); return }
      showToast(d.message || '', 'success')
    } finally { setLoading(false) }
  }

  const regleSel = selRegleIdx >= 0 ? regles[selRegleIdx] : null

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader
          icon={MessageSquare}
          title="Gestion SMS Perf-Exo"
          right={
            <div className="flex items-center gap-3">
              <button
                onClick={doToggle}
                className={`px-4 py-1.5 text-sm rounded-full font-medium transition ${
                  perfActif
                    ? 'bg-[#17494E] text-white'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                SMS Perf {perfActif ? 'Activé' : 'Désactivé'}
              </button>
            </div>
          }
        />

        {/* Bloc Staff */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex items-start gap-3 flex-wrap">
            <div className="flex items-center gap-2 text-[#8B7355] text-sm font-medium">
              <Users className="w-4 h-4" /> Staff Destinataire :
            </div>
            <div className="flex flex-wrap gap-1.5 flex-1">
              {staff.map((s) => (
                <span key={s.id_salarie}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#ECF1F2] text-xs text-[#17494E]">
                  {s.prenom[0]?.toUpperCase()}{(s.prenom.slice(1)).toLowerCase()} {s.nom[0]?.toUpperCase()}.
                  <button onClick={() => removeStaff(s.id_salarie)}
                          className="hover:text-red-700">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
              <button onClick={() => setStaffPickerOpen(true)}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-dashed border-[#8B7355] text-xs text-[#8B7355] hover:bg-[#ECF1F2]">
                <Plus className="w-3 h-3" /> Ajouter
              </button>
            </div>
          </div>
        </div>

        {/* Tableau Régles + actions */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => setRegleModal({
                mode: 'new',
                data: { id_regle: '', ...EMPTY_REGLE },
              })}
              title="Ajouter"
              className="p-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
              <Plus className="w-4 h-4" />
            </button>
            <button
              onClick={() => selRegleIdx >= 0 && setRegleModal({
                mode: 'edit', data: { ...regles[selRegleIdx] },
              })}
              disabled={selRegleIdx < 0}
              title="Modifier"
              className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40">
              <Pencil className="w-4 h-4" />
            </button>
            <button
              onClick={() => selRegleIdx >= 0 && duplicateRegle(selRegleIdx)}
              disabled={selRegleIdx < 0}
              title="Dupliquer"
              className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40">
              <Copy className="w-4 h-4" />
            </button>
            <button
              onClick={() => selRegleIdx >= 0 && deleteRegle(selRegleIdx)}
              disabled={selRegleIdx < 0}
              title="Supprimer"
              className="p-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 disabled:opacity-40">
              <Trash2 className="w-4 h-4" />
            </button>

            <div className="ml-auto flex items-center gap-2">
              <label className="flex items-center gap-2 text-xs text-[#8B7355]">
                Renvoyer les sms du
                <input type="date" value={renvoiDate}
                       onChange={(e) => setRenvoiDate(e.target.value)}
                       className="px-2 py-1 border border-[#E5E0D5] rounded" />
              </label>
              <button
                onClick={() => doEnvoyer(true)}
                disabled={loading}
                title="Simuler (aucun SMS envoyé)"
                className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40">
                Simu
              </button>
              <button
                onClick={() => doEnvoyer(false)}
                disabled={loading}
                title="Envoyer réellement les SMS"
                className="p-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] disabled:opacity-40">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[40vh] overflow-y-auto">
            <table className="text-xs w-full">
              <thead className="sticky top-0 bg-[#F5F5F0]">
                <tr>
                  <th className="py-1.5 px-2 text-left">Code Animation</th>
                  <th className="py-1.5 px-2 text-right">Envoi</th>
                  <th className="py-1.5 px-2 text-right">Sig Deb</th>
                  <th className="py-1.5 px-2 text-right">Sig Fin</th>
                  <th className="py-1.5 px-2 text-right">Ordre</th>
                  <th className="py-1.5 px-2 text-left">Partenaire</th>
                  <th className="py-1.5 px-2 text-left">Prod</th>
                  <th className="py-1.5 px-2 text-left">Période</th>
                  <th className="py-1.5 px-2 text-center">Grp</th>
                  <th className="py-1.5 px-2 text-center">Actif</th>
                </tr>
              </thead>
              <tbody>
                {regles.map((r, i) => (
                  <tr key={i} onClick={() => setSelRegleIdx(i)}
                      className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                        selRegleIdx === i ? 'bg-[#FFF5E0] ring-1 ring-[#8B7355]' : ''
                      }`}>
                    <td className="py-1 px-2 font-medium">{r.code_animation}</td>
                    <td className="py-1 px-2 text-right tabular-nums">{r.heure_envoi}h</td>
                    <td className="py-1 px-2 text-right tabular-nums">{r.heure_debut}h</td>
                    <td className="py-1 px-2 text-right tabular-nums">{r.heure_fin}h</td>
                    <td className="py-1 px-2 text-right tabular-nums">{r.ordre}</td>
                    <td className="py-1 px-2">{r.partenaire}</td>
                    <td className="py-1 px-2">
                      {r.prod_groupe === 1 ? 'Vendeur' : r.prod_groupe === 2 ? 'Équipe' : 'Agence'}
                    </td>
                    <td className="py-1 px-2">
                      {r.periode_calcul === 1 ? 'Jour' : r.periode_calcul === 2 ? 'Hebdo' : 'Mensuel'}
                    </td>
                    <td className="py-1 px-2 text-center">{r.sms_groupe ? '✓' : ''}</td>
                    <td className="py-1 px-2 text-center">
                      {r.is_actif ? <Check className="w-3 h-3 inline text-green-700" /> : ''}
                    </td>
                  </tr>
                ))}
                {regles.length === 0 && !loading && (
                  <tr><td colSpan={10} className="py-6 text-center text-gray-400">
                    Aucune règle - Ajoute avec +
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Onglets bas */}
        {regleSel && (
          <>
            <div className="flex border-b border-[#E5E0D5] mb-4">
              {[
                { key: 'regles' as Tab, label: 'Règles d\'envoi des SMS' },
                { key: 'scores' as Tab, label: 'Destinataires et Scores' },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`px-4 py-2 text-sm font-medium border-b-2 ${
                    tab === t.key
                      ? 'border-[#17494E] text-[#17494E]'
                      : 'border-transparent text-gray-500 hover:text-[#17494E]'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {tab === 'regles' && (
              <div className="bg-white rounded-lg shadow p-4 text-sm text-gray-500">
                Sélectionne <b>Modifier</b> (crayon) pour éditer la règle
                "<b className="text-[#17494E]">{regleSel.code_animation}</b>".
              </div>
            )}

            {tab === 'scores' && (
              <ScoresTab codeAnim={regleSel.code_animation} />
            )}
          </>
        )}
      </div>

      {/* Modales */}
      {staffPickerOpen && (
        <PersonnePicker
          title="Choisir un membre du staff"
          onClose={() => setStaffPickerOpen(false)}
          onSelect={onPickStaff}
        />
      )}

      {regleModal && (
        <ModalRegle
          data={regleModal.data}
          onChange={(d) => setRegleModal({ ...regleModal, data: d })}
          onSave={saveRegle}
          onClose={() => setRegleModal(null)}
        />
      )}
    </div>
  )
}

// =====================================================================
// Onglet 2 - Destinataires et Scores
// =====================================================================

function ScoresTab({ codeAnim }: { codeAnim: string }) {
  const [dests, setDests] = useState<DestinataireRow[]>([])
  const [scores, setScores] = useState<EquipeScoreRow[]>([])
  const [destModal, setDestModal] = useState<{ mode: 'new' | 'edit'; data: DestinataireRow } | null>(null)
  const [scoreModal, setScoreModal] = useState<{ mode: 'new' | 'edit'; data: EquipeScoreRow } | null>(null)

  const loadDests = useCallback(async () => {
    const r = await fetch(
      `${API_BASE}/comm/sms-perf/destinataires?code=${encodeURIComponent(codeAnim)}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setDests(await r.json())
  }, [codeAnim])

  const loadScores = useCallback(async () => {
    const r = await fetch(
      `${API_BASE}/comm/sms-perf/equipes-scores?code=${encodeURIComponent(codeAnim)}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setScores(await r.json())
  }, [codeAnim])

  useEffect(() => {
    void loadDests(); void loadScores()
  }, [loadDests, loadScores])

  const saveDest = async () => {
    if (!destModal) return
    const url = destModal.mode === 'new'
      ? `${API_BASE}/comm/sms-perf/destinataires`
      : `${API_BASE}/comm/sms-perf/destinataires/${destModal.data.id_dest}`
    const method = destModal.mode === 'new' ? 'POST' : 'PUT'
    const { id_dest: _, lib_orga: __, ...payload } = destModal.data
    const r = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...payload, anim_code: codeAnim }),
    })
    const d = await r.json()
    if (d.ok) { showToast('Enregistré', 'success'); setDestModal(null); void loadDests() }
  }

  const deleteDest = async (id: string) => {
    if (!await showConfirm({ title: 'Supprimer', message: 'Supprimer ce destinataire ?' })) return
    await fetch(`${API_BASE}/comm/sms-perf/destinataires/${id}`, {
      method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` },
    })
    void loadDests()
  }

  const dupDest = async (id: string) => {
    await fetch(`${API_BASE}/comm/sms-perf/destinataires/${id}/duplicate`, {
      method: 'POST', headers: { Authorization: `Bearer ${getToken()}` },
    })
    void loadDests()
  }

  const saveScore = async () => {
    if (!scoreModal) return
    const url = scoreModal.mode === 'new'
      ? `${API_BASE}/comm/sms-perf/equipes-scores`
      : `${API_BASE}/comm/sms-perf/equipes-scores/${scoreModal.data.id_orga_periode}`
    const method = scoreModal.mode === 'new' ? 'POST' : 'PUT'
    const { id_orga_periode: _, lib_orga: __, ...payload } = scoreModal.data
    const r = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ...payload, code_animation: codeAnim, type: 'Perf-Exo' }),
    })
    const d = await r.json()
    if (d.ok) { showToast('Enregistré', 'success'); setScoreModal(null); void loadScores() }
  }

  const deleteScore = async (id: string) => {
    if (!await showConfirm({ title: 'Supprimer', message: 'Supprimer cette équipe ?' })) return
    await fetch(`${API_BASE}/comm/sms-perf/equipes-scores/${id}`, {
      method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` },
    })
    void loadScores()
  }

  const dupScore = async (id: string) => {
    await fetch(`${API_BASE}/comm/sms-perf/equipes-scores/${id}/duplicate`, {
      method: 'POST', headers: { Authorization: `Bearer ${getToken()}` },
    })
    void loadScores()
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Destinataires SMS */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold text-[#17494E] flex-1">Destinataires SMS</h3>
          <button onClick={() => setDestModal({
            mode: 'new',
            data: {
              id_dest: '', idorganigramme: '', lib_orga: '',
              anim_code: codeAnim, du: '', au: '', is_actif: true,
            },
          })} title="Ajouter"
                  className="p-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
        <table className="text-xs w-full">
          <thead>
            <tr className="text-[#8B7355] border-b border-[#F0EDE5]">
              <th className="py-1.5 px-2 text-left">Agence / Équipe</th>
              <th className="py-1.5 px-2">Du</th>
              <th className="py-1.5 px-2">Au</th>
              <th className="py-1.5 px-2 text-center">Actif</th>
              <th className="py-1.5 px-2 w-24"></th>
            </tr>
          </thead>
          <tbody>
            {dests.map((r) => (
              <tr key={r.id_dest} className="border-b border-[#F0EDE5]">
                <td className="py-1.5 px-2">{r.lib_orga}</td>
                <td className="py-1.5 px-2 tabular-nums text-xs">{r.du}</td>
                <td className="py-1.5 px-2 tabular-nums text-xs">{r.au}</td>
                <td className="py-1.5 px-2 text-center">{r.is_actif ? '✓' : ''}</td>
                <td className="py-1.5 px-2 text-right">
                  <button onClick={() => setDestModal({ mode: 'edit', data: { ...r } })}
                          className="p-1 rounded hover:bg-[#ECF1F2] text-[#8B7355]">
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button onClick={() => dupDest(r.id_dest)}
                          className="p-1 rounded hover:bg-[#ECF1F2] text-[#8B7355]">
                    <Copy className="w-3 h-3" />
                  </button>
                  <button onClick={() => deleteDest(r.id_dest)}
                          className="p-1 rounded hover:bg-red-50 text-[#B91C1C]">
                    <Trash2 className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
            {dests.length === 0 && (
              <tr><td colSpan={5} className="py-4 text-center text-gray-400">Aucun</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Equipes incluses dans les scores */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold text-[#17494E] flex-1">Équipes incluses dans les scores</h3>
          <button onClick={() => setScoreModal({
            mode: 'new',
            data: {
              id_orga_periode: '', idorganigramme: '', lib_orga: '',
              code_animation: codeAnim, type: 'Perf-Exo',
              du: '', au: '', is_actif: true,
            },
          })} title="Ajouter"
                  className="p-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
        <table className="text-xs w-full">
          <thead>
            <tr className="text-[#8B7355] border-b border-[#F0EDE5]">
              <th className="py-1.5 px-2 text-left">Agence / Équipe</th>
              <th className="py-1.5 px-2">Du</th>
              <th className="py-1.5 px-2">Au</th>
              <th className="py-1.5 px-2 text-center">Actif</th>
              <th className="py-1.5 px-2 w-24"></th>
            </tr>
          </thead>
          <tbody>
            {scores.map((r) => (
              <tr key={r.id_orga_periode} className="border-b border-[#F0EDE5]">
                <td className="py-1.5 px-2">{r.lib_orga}</td>
                <td className="py-1.5 px-2 tabular-nums text-xs">{r.du}</td>
                <td className="py-1.5 px-2 tabular-nums text-xs">{r.au}</td>
                <td className="py-1.5 px-2 text-center">{r.is_actif ? '✓' : ''}</td>
                <td className="py-1.5 px-2 text-right">
                  <button onClick={() => setScoreModal({ mode: 'edit', data: { ...r } })}
                          className="p-1 rounded hover:bg-[#ECF1F2] text-[#8B7355]">
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button onClick={() => dupScore(r.id_orga_periode)}
                          className="p-1 rounded hover:bg-[#ECF1F2] text-[#8B7355]">
                    <Copy className="w-3 h-3" />
                  </button>
                  <button onClick={() => deleteScore(r.id_orga_periode)}
                          className="p-1 rounded hover:bg-red-50 text-[#B91C1C]">
                    <Trash2 className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
            {scores.length === 0 && (
              <tr><td colSpan={5} className="py-4 text-center text-gray-400">Aucune</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {destModal && (
        <ModalDestOrScore
          title="Destinataire SMS"
          data={{
            lib_orga: destModal.data.lib_orga,
            idorganigramme: destModal.data.idorganigramme,
            du: destModal.data.du, au: destModal.data.au,
            is_actif: destModal.data.is_actif,
          }}
          onChange={(d) => setDestModal({
            ...destModal, data: { ...destModal.data, ...d },
          })}
          onSave={saveDest}
          onClose={() => setDestModal(null)}
        />
      )}
      {scoreModal && (
        <ModalDestOrScore
          title="Équipe incluse dans les scores"
          data={{
            lib_orga: scoreModal.data.lib_orga,
            idorganigramme: scoreModal.data.idorganigramme,
            du: scoreModal.data.du, au: scoreModal.data.au,
            is_actif: scoreModal.data.is_actif,
          }}
          onChange={(d) => setScoreModal({
            ...scoreModal, data: { ...scoreModal.data, ...d },
          })}
          onSave={saveScore}
          onClose={() => setScoreModal(null)}
        />
      )}
    </div>
  )
}

// =====================================================================
// Modales
// =====================================================================

function ModalRegle({
  data, onChange, onSave, onClose,
}: {
  data: RegleEnvoi
  onChange: (d: RegleEnvoi) => void
  onSave: () => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-4 my-8">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-[#17494E]">Règle d'envoi SMS</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100"><X className="w-4 h-4" /></button>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Code Animation</span>
              <input type="text" value={data.code_animation}
                     onChange={(e) => onChange({ ...data, code_animation: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded font-mono" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Ordre d'envoi</span>
              <input type="number" value={data.ordre}
                     onChange={(e) => onChange({ ...data, ordre: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>

          <label className="block text-xs">
            <span className="text-[#8B7355] font-medium">Texte SMS</span>
            <textarea value={data.texte_sms} rows={4}
                      onChange={(e) => onChange({ ...data, texte_sms: e.target.value })}
                      className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded font-mono text-xs" />
            <p className="text-[10px] text-gray-500 mt-1">
              Publipostage : [NOM] + [SCORE] pour SMS individuel · [LISTE] pour SMS groupé
            </p>
          </label>

          <div className="grid grid-cols-3 gap-3">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Heure d'envoi (0=direct)</span>
              <input type="number" min={0} max={23} value={data.heure_envoi}
                     onChange={(e) => onChange({ ...data, heure_envoi: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Heures signature entre</span>
              <input type="number" min={0} max={23} value={data.heure_debut}
                     onChange={(e) => onChange({ ...data, heure_debut: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">et</span>
              <input type="number" min={0} max={23} value={data.heure_fin}
                     onChange={(e) => onChange({ ...data, heure_fin: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>

          <label className="block text-xs">
            <span className="text-[#8B7355] font-medium">Partenaire</span>
            <select value={data.partenaire}
                    onChange={(e) => onChange({ ...data, partenaire: e.target.value })}
                    className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
              {PARTENAIRES.map((p) => (
                <option key={p.v} value={p.v}>{p.l}</option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Configuration du SMS</span>
              <div className="mt-1 flex rounded border border-[#E5E0D5]">
                <button onClick={() => onChange({ ...data, sms_groupe: false })}
                        className={`flex-1 px-3 py-1.5 text-sm ${
                          !data.sms_groupe ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                        }`}>
                  SMS individuel
                </button>
                <button onClick={() => onChange({ ...data, sms_groupe: true })}
                        className={`flex-1 px-3 py-1.5 text-sm ${
                          data.sms_groupe ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                        }`}>
                  SMS Groupé
                </button>
              </div>
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Objectif Min</span>
              <input type="number" min={0} value={data.nb_bs_min}
                     onChange={(e) => onChange({ ...data, nb_bs_min: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Calcul de la prod</span>
              <div className="mt-1 flex rounded border border-[#E5E0D5]">
                {[
                  { v: 1, l: 'Vendeur' }, { v: 2, l: 'Équipe' }, { v: 3, l: 'Agence' },
                ].map((o) => (
                  <button key={o.v}
                          onClick={() => onChange({ ...data, prod_groupe: o.v })}
                          className={`flex-1 px-2 py-1.5 text-xs ${
                            data.prod_groupe === o.v ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                          }`}>
                    {o.l}
                  </button>
                ))}
              </div>
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Période</span>
              <div className="mt-1 flex rounded border border-[#E5E0D5]">
                {[
                  { v: 1, l: 'Journalier' }, { v: 2, l: 'Hebdo' }, { v: 3, l: 'Mensuel' },
                ].map((o) => (
                  <button key={o.v}
                          onClick={() => onChange({ ...data, periode_calcul: o.v })}
                          className={`flex-1 px-2 py-1.5 text-xs ${
                            data.periode_calcul === o.v ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                          }`}>
                    {o.l}
                  </button>
                ))}
              </div>
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={data.is_actif}
                   onChange={(e) => onChange({ ...data, is_actif: e.target.checked })}
                   className="accent-[#17494E]" />
            <span className="text-[#8B7355]">Actif</span>
          </label>
        </div>

        <div className="flex gap-2 mt-4">
          <button onClick={onSave}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
            <Save className="w-4 h-4" /> Enregistrer
          </button>
          <button onClick={onClose}
                  className="flex-1 px-3 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
            Annuler
          </button>
        </div>
      </div>
    </div>
  )
}

// --- Modale commune Destinataire / Equipe Score ---

function ModalDestOrScore({
  title, data, onChange, onSave, onClose,
}: {
  title: string
  data: { lib_orga: string; idorganigramme: string; du: string; au: string; is_actif: boolean }
  onChange: (d: { lib_orga: string; idorganigramme: string; du: string; au: string; is_actif: boolean }) => void
  onSave: () => void
  onClose: () => void
}) {
  const [orgaPickerOpen, setOrgaPickerOpen] = useState(false)
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-[#17494E]">{title}</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100"><X className="w-4 h-4" /></button>
        </div>

        <div className="space-y-3">
          <div>
            <div className="text-xs text-[#8B7355] font-medium mb-1">Agence / Équipe</div>
            <button onClick={() => setOrgaPickerOpen(true)}
                    className="flex items-center gap-2 px-3 py-1.5 border border-[#E5E0D5] rounded w-full text-left hover:bg-[#ECF1F2]">
              <Users className="w-4 h-4 text-[#17494E] shrink-0" />
              <span className={`flex-1 truncate ${data.lib_orga ? 'text-[#17494E]' : 'text-gray-400'}`}>
                {data.lib_orga || 'Choisir l\'équipe...'}
              </span>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Du</span>
              <input type="date" value={data.du}
                     onChange={(e) => onChange({ ...data, du: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Au</span>
              <input type="date" value={data.au}
                     onChange={(e) => onChange({ ...data, au: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={data.is_actif}
                   onChange={(e) => onChange({ ...data, is_actif: e.target.checked })}
                   className="accent-[#17494E]" />
            <span className="text-[#8B7355]">Actif</span>
          </label>
        </div>

        <div className="flex gap-2 mt-4">
          <button onClick={onSave}
                  disabled={!data.idorganigramme || data.idorganigramme === '0'}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]">
            <Save className="w-4 h-4" /> Enregistrer
          </button>
          <button onClick={onClose}
                  className="flex-1 px-3 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
            Annuler
          </button>
        </div>

        {orgaPickerOpen && (
          <OrgaTreePickerModal
            title="Choisir une équipe / agence"
            onClose={() => setOrgaPickerOpen(false)}
            onSelect={(id, lib) => {
              onChange({ ...data, idorganigramme: id, lib_orga: lib })
              setOrgaPickerOpen(false)
            }}
          />
        )}
      </div>
    </div>
  )
}
