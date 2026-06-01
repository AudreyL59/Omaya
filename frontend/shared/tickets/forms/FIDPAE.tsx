import { useCallback, useEffect, useState } from 'react'
import {
  FileText,
  Loader2,
  Play,
  Printer,
  RefreshCw,
  Save,
  UserPlus,
  Users,
} from 'lucide-react'

import type { FIProps } from './index'
import SearchPicker, { type PickerItem } from './SearchPicker'
import { showToast } from '../../ui/dialog'

type Form = Record<string, any>

export default function FIDPAE({ apiBase, getToken, idTicket }: FIProps) {
  const [form, setForm] = useState<Form | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [picker, setPicker] = useState<
    'coopteur' | 'jocoopteur' | 'equipe' | null
  >(null)
  const [docUrl, setDocUrl] = useState('')
  const [docMime, setDocMime] = useState('')
  const [docName, setDocName] = useState('')
  const [docLoading, setDocLoading] = useState(false)

  const openDoc = async (nomFichier: string) => {
    setDocLoading(true)
    setDocName(nomFichier)
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(
          nomFichier,
        )}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        showToast(`Erreur : ${e?.detail || resp.status}`, 'error')
        return
      }
      const blob = await resp.blob()
      setDocUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return URL.createObjectURL(blob)
      })
      setDocMime(blob.type || '')
    } catch {
      showToast('Erreur réseau lors du chargement du document.', 'error')
    } finally {
      setDocLoading(false)
    }
  }

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => setForm(d?.data?.found ? d.data : null))
      .catch(() => setForm(null))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, idTicket])

  useEffect(() => {
    reload()
  }, [reload])

  const set = (k: string, v: any) =>
    setForm((f) => (f ? { ...f, [k]: v } : f))

  const enregistrer = async () => {
    if (!form) return
    setSaving(true)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(form),
      })
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        showToast(`Erreur : ${e?.detail || resp.status}`, 'error')
        return
      }
      reload()
    } catch {
      showToast('Erreur réseau lors de l’enregistrement.', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }
  if (!form) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
        Aucune DPAE pour ce ticket.
      </div>
    )
  }

  const situOptions: Record<string, string> =
    form.situation_fam_options || {}

  const placeholderAction = (label: string) =>
    showToast(`${label} : bientôt disponible.`, 'info')

  return (
    <div className="space-y-4">
      {/* Top bar actions */}
      <div className="flex flex-wrap items-center gap-3 pb-3 border-b border-c-line">
        <button
          onClick={enregistrer}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Enregistrer le ticket
        </button>
        <button
          onClick={() => placeholderAction('Démarrer la DPAE')}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-c-brand-strong text-white text-sm font-semibold hover:brightness-110 transition-all"
        >
          <Play className="w-4 h-4" />
          Démarrer la DPAE
        </button>
        <button
          onClick={() => placeholderAction('Attest Info à Imprimer')}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-sm text-c-ink hover:bg-c-brand-soft transition-colors"
        >
          <Printer className="w-4 h-4 text-c-ink-soft" />
          Attest Info à Imprimer
        </button>
        <button
          onClick={() => placeholderAction('Régénérer Att Info')}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-sm text-c-ink hover:bg-c-brand-soft transition-colors"
        >
          <RefreshCw className="w-4 h-4 text-c-ink-soft" />
          Régénérer Att Info
        </button>
      </div>

      {/* Grid 3 cols pleines, chaque col empile 2 sections (sauf col 3 :
          liste documents + viewer PDF) */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* COL 1 : Etat civil + Coordonnees */}
        <div className="space-y-6">
          <Section title="Infos état civil">
            <Field labelW="w-20" label="Civilité">
              <ToggleGroup
                value={Number(form.civilite || 0)}
                options={[{ v: 1, lib: 'M.' }, { v: 2, lib: 'Mme' }]}
                onChange={(v) => set('civilite', v)}
              />
            </Field>
            <Field labelW="w-20" label="Nom">
              <input value={form.nom || ''} onChange={(e) => set('nom', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="Époux(se)">
              <input value={form.nom_marital || ''} onChange={(e) => set('nom_marital', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="Prénom">
              <input value={form.prenom || ''} onChange={(e) => set('prenom', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="N° SS">
              <input value={form.numss || ''} onChange={(e) => set('numss', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="Nationalité">
              <input value={form.nationalite || ''} onChange={(e) => set('nationalite', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="CPAM">
              <input value={form.cpam || ''} onChange={(e) => set('cpam', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="Né(e) le">
              <input type="date" value={form.dnaiss || ''} onChange={(e) => set('dnaiss', e.target.value)} className={inCls} />
            </Field>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-c-ink-soft w-20 shrink-0 text-right">à</span>
              <input value={form.lnaiss || ''} onChange={(e) => set('lnaiss', e.target.value)} className={inCls + ' flex-1 min-w-0'} />
              <span className="text-c-ink-soft shrink-0">Dép</span>
              <input type="number" value={form.depnaiss || 0} onChange={(e) => set('depnaiss', Number(e.target.value))} className={inCls + ' !w-12 shrink-0'} />
            </div>
            <Field labelW="w-20" label="N° CIN">
              <input value={form.numcin || ''} onChange={(e) => set('numcin', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="Sit. Fam.">
              <select
                value={form.situation_fam || 0}
                onChange={(e) => set('situation_fam', Number(e.target.value))}
                className={selCls}
              >
                {Object.entries(situOptions).map(([k, v]) => (
                  <option key={k} value={Number(k)}>{v}</option>
                ))}
              </select>
            </Field>
            <div className="flex items-center gap-4 pl-[5.75rem]">
              <Check label="Avec Enfant" checked={!!form.avec_enfant} onChange={(v) => set('avec_enfant', v)} />
              <span className="text-xs text-c-ink-soft">Nb :</span>
              <input
                type="number"
                value={form.nb_enfants || 0}
                onChange={(e) => set('nb_enfants', Number(e.target.value))}
                className={inCls + ' !w-12 shrink-0'}
              />
            </div>
            <div className="pl-[5.75rem]">
              <Check label="Travailleur Handicapé" checked={!!form.travailleur_handi} onChange={(v) => set('travailleur_handi', v)} />
            </div>
          </Section>

          <Section title="Coordonnées">
            <Field labelW="w-20" label="Adresse">
              <input value={form.adresse1 || ''} onChange={(e) => set('adresse1', e.target.value)} className={inCls} />
            </Field>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-c-ink-soft w-20 shrink-0 text-right">CP</span>
              <input value={form.cp || ''} onChange={(e) => set('cp', e.target.value)} className={inCls + ' !w-16 shrink-0'} />
              <span className="text-c-ink-soft shrink-0">Ville</span>
              <input value={form.ville || ''} onChange={(e) => set('ville', e.target.value)} className={inCls + ' flex-1 min-w-0'} />
            </div>
            <Field labelW="w-20" label="Mobile">
              <input value={form.gsm || ''} onChange={(e) => set('gsm', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="Mail">
              <input value={form.mail || ''} onChange={(e) => set('mail', e.target.value)} className={inCls} />
            </Field>
          </Section>

          <Section title="Contact en cas d'urgence">
            <Field labelW="w-20" label="Identité">
              <input value={form.urgnom || ''} onChange={(e) => set('urgnom', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="Parenté">
              <input value={form.urglien || ''} onChange={(e) => set('urglien', e.target.value)} className={inCls} />
            </Field>
            <Field labelW="w-20" label="Tél">
              <input value={form.urgtel || ''} onChange={(e) => set('urgtel', e.target.value)} className={inCls} />
            </Field>
          </Section>
        </div>

        {/* COL 2+3 : Embauche + Documents en haut (sous-grid 2fr/1fr pour
            laisser respirer Embauche), puis PDF viewer span pleine largeur */}
        <div className="xl:col-span-2 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-6">
          <Section title="Infos embauche">
            <Field label="Date Début">
              <input type="date" value={form.date_debut || ''} onChange={(e) => set('date_debut', e.target.value)} className={inCls} />
            </Field>
            <div className="flex items-center gap-3 text-sm">
              <Check label="Adhère à la mutuelle" checked={!!form.mutuelle} onChange={(v) => set('mutuelle', v)} />
              <span className="text-c-ink-soft shrink-0">Date</span>
              <input
                type="date"
                value={form.mutdate || ''}
                onChange={(e) => set('mutdate', e.target.value)}
                disabled={!form.mutuelle}
                className={inCls + ' flex-1 min-w-0'}
              />
            </div>
            <Check label="Coopté" checked={!!form.coopte} onChange={(v) => set('coopte', v)} />
            {form.coopte && (
              <PickerBtn
                icon={<UserPlus className="w-4 h-4 text-c-brand" />}
                label={form.coopteur_nom || 'Choisir le coopteur'}
                onClick={() => setPicker('coopteur')}
              />
            )}
            <Check label="JO Directe" checked={!!form.jodirecte} onChange={(v) => set('jodirecte', v)} />
            {form.jodirecte && (
              <PickerBtn
                icon={<UserPlus className="w-4 h-4 text-c-brand" />}
                label={form.jocoopteur_nom || 'Choisir le coopteur JO'}
                onClick={() => setPicker('jocoopteur')}
              />
            )}
            <PickerBtn
              icon={<Users className="w-4 h-4 text-c-brand" />}
              label={form.lib_equipe || "Choisir l'équipe"}
              onClick={() => setPicker('equipe')}
            />
          </Section>

          <Section title="Documents">
            {(form.documents || []).length === 0 ? (
              <div className="text-sm text-c-ink-faint">Aucun document.</div>
            ) : (
              <ul className="border border-c-line rounded-lg divide-y divide-c-line-soft overflow-hidden">
                {(form.documents as any[]).map((d) => (
                  <li key={d.id}>
                    <button
                      onClick={() => openDoc(d.nom_fichier)}
                      className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 transition-colors ${
                        docName === d.nom_fichier
                          ? 'bg-c-brand-soft'
                          : 'hover:bg-c-surface-soft'
                      }`}
                    >
                      <FileText className="w-4 h-4 text-c-brand shrink-0" />
                      <span className="truncate">{d.nom || d.nom_fichier}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>
          </div>

          {/* PDF viewer span pleine largeur de col 2+3 */}
          <div className="min-h-[600px] border border-c-line rounded-lg bg-c-surface-soft overflow-hidden">
            {docLoading ? (
              <div className="h-full flex items-center justify-center py-10">
                <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
              </div>
            ) : !docUrl ? (
              <div className="h-full flex items-center justify-center text-c-ink-faint text-sm py-10">
                Sélectionne un document pour l'aperçu.
              </div>
            ) : docMime.startsWith('image/') ? (
              <img src={docUrl} alt={docName} className="w-full h-full object-contain" />
            ) : (
              <iframe src={docUrl} title={docName} className="w-full h-[600px]" />
            )}
          </div>
        </div>
      </div>

      {picker === 'coopteur' && (
        <SearchPicker
          apiBase={apiBase}
          getToken={getToken}
          title="Choisir le coopteur"
          path="/tickets/salaries/search"
          mapItem={(s) => ({
            id: s.id_salarie,
            label: `${s.nom} ${cap(s.prenom)}`,
            sublabel: [s.poste, s.lib_societe].filter(Boolean).join(' · '),
          })}
          onClose={() => setPicker(null)}
          onPick={(it: PickerItem) => {
            set('coopteur', it.id)
            set('coopteur_nom', it.label)
            setPicker(null)
          }}
        />
      )}
      {picker === 'jocoopteur' && (
        <SearchPicker
          apiBase={apiBase}
          getToken={getToken}
          title="Choisir le coopteur JO"
          path="/tickets/salaries/search"
          mapItem={(s) => ({
            id: s.id_salarie,
            label: `${s.nom} ${cap(s.prenom)}`,
            sublabel: [s.poste, s.lib_societe].filter(Boolean).join(' · '),
          })}
          onClose={() => setPicker(null)}
          onPick={(it: PickerItem) => {
            set('jocoopteur', it.id)
            set('jocoopteur_nom', it.label)
            setPicker(null)
          }}
        />
      )}
      {picker === 'equipe' && (
        <SearchPicker
          apiBase={apiBase}
          getToken={getToken}
          title="Choisir l'équipe"
          path="/tickets/organigrammes/search"
          mapItem={(o) => ({ id: o.id_organigramme, label: o.lib_orga })}
          onClose={() => setPicker(null)}
          onPick={(it: PickerItem) => {
            set('id_equipe', it.id)
            set('lib_equipe', it.label)
            setPicker(null)
          }}
        />
      )}
    </div>
  )
}

const inCls =
  'w-full px-2 py-1 border border-c-line-strong rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-c-brand-line disabled:opacity-50'
const selCls = inCls + ' bg-white'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide mb-3">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

// Field : libelle a gauche (right-aligned), input a droite (flex-1).
// labelW : largeur du libelle (defaut w-28).
function Field({
  label,
  children,
  labelW = 'w-28',
}: {
  labelW?: string
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className={`text-c-ink-soft ${labelW} shrink-0 text-right`}>{label}</span>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  )
}

// Toggle M./Mme (et toute option a 2-3 valeurs).
function ToggleGroup({
  value,
  options,
  onChange,
}: {
  value: number
  options: { v: number; lib: string }[]
  onChange: (v: number) => void
}) {
  return (
    <div className="inline-flex rounded-md border border-c-line-strong overflow-hidden">
      {options.map((o) => (
        <button
          key={o.v}
          type="button"
          onClick={() => onChange(o.v)}
          className={`px-4 py-1 text-sm transition-colors ${
            value === o.v
              ? 'bg-c-brand text-white'
              : 'bg-white text-c-ink hover:bg-c-brand-soft'
          }`}
        >
          {o.lib}
        </button>
      ))}
    </div>
  )
}

function Check({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-c-ink cursor-pointer h-9">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4 cursor-pointer accent-c-brand"
      />
      {label}
    </label>
  )
}

function PickerBtn({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-sm text-c-ink hover:bg-c-brand-soft transition-colors"
    >
      {icon}
      <span className="truncate">{label}</span>
    </button>
  )
}

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : ''
}
