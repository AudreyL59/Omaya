import { useCallback, useEffect, useState } from 'react'
import { FileText, Loader2, Save, UserPlus, Users } from 'lucide-react'

import type { FIProps } from './index'
import SearchPicker, { type PickerItem } from './SearchPicker'

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
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      const blob = await resp.blob()
      setDocUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return URL.createObjectURL(blob)
      })
      setDocMime(blob.type || '')
    } catch {
      window.alert('Erreur réseau lors du chargement du document.')
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
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      reload()
    } catch {
      window.alert('Erreur réseau lors de l’enregistrement.')
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

  return (
    <div className="space-y-6">
      <button
        onClick={enregistrer}
        disabled={saving}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
      >
        {saving ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Save className="w-4 h-4" />
        )}
        Enregistrer le ticket
      </button>

      {/* ÉTAT CIVIL */}
      <Section title="Infos état civil">
        <Row>
          <Field label="Civilité">
            <select
              value={form.civilite || 0}
              onChange={(e) => set('civilite', Number(e.target.value))}
              className={selCls}
            >
              <option value={0}>—</option>
              <option value={1}>M.</option>
              <option value={2}>Mme</option>
            </select>
          </Field>
          <Field label="Nom">
            <input value={form.nom || ''} onChange={(e) => set('nom', e.target.value)} className={inCls} />
          </Field>
          <Field label="Nom marital / Époux(se)">
            <input value={form.nom_marital || ''} onChange={(e) => set('nom_marital', e.target.value)} className={inCls} />
          </Field>
          <Field label="Prénom">
            <input value={form.prenom || ''} onChange={(e) => set('prenom', e.target.value)} className={inCls} />
          </Field>
        </Row>
        <Row>
          <Field label="N° SS">
            <input value={form.numss || ''} onChange={(e) => set('numss', e.target.value)} className={inCls} />
          </Field>
          <Field label="Nationalité">
            <input value={form.nationalite || ''} onChange={(e) => set('nationalite', e.target.value)} className={inCls} />
          </Field>
          <Field label="CPAM">
            <input value={form.cpam || ''} onChange={(e) => set('cpam', e.target.value)} className={inCls} />
          </Field>
          <Field label="N° CIN">
            <input value={form.numcin || ''} onChange={(e) => set('numcin', e.target.value)} className={inCls} />
          </Field>
        </Row>
        <Row>
          <Field label="Né(e) le">
            <input type="date" value={form.dnaiss || ''} onChange={(e) => set('dnaiss', e.target.value)} className={inCls} />
          </Field>
          <Field label="à (lieu)">
            <input value={form.lnaiss || ''} onChange={(e) => set('lnaiss', e.target.value)} className={inCls} />
          </Field>
          <Field label="Dép. naiss.">
            <input type="number" value={form.depnaiss || 0} onChange={(e) => set('depnaiss', Number(e.target.value))} className={inCls} />
          </Field>
          <Field label="Situation familiale">
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
        </Row>
        <Row>
          <Check label="Avec enfant" checked={!!form.avec_enfant} onChange={(v) => set('avec_enfant', v)} />
          <Field label="Nb enfants">
            <input type="number" value={form.nb_enfants || 0} onChange={(e) => set('nb_enfants', Number(e.target.value))} className={inCls} />
          </Field>
          <Check label="Travailleur handicapé" checked={!!form.travailleur_handi} onChange={(v) => set('travailleur_handi', v)} />
        </Row>
      </Section>

      {/* COORDONNÉES */}
      <Section title="Coordonnées postales et téléphoniques">
        <Row>
          <Field label="Adresse" wide>
            <input value={form.adresse1 || ''} onChange={(e) => set('adresse1', e.target.value)} className={inCls} />
          </Field>
        </Row>
        <Row>
          <Field label="CP">
            <input value={form.cp || ''} onChange={(e) => set('cp', e.target.value)} className={inCls} />
          </Field>
          <Field label="Ville">
            <input value={form.ville || ''} onChange={(e) => set('ville', e.target.value)} className={inCls} />
          </Field>
          <Field label="Mobile">
            <input value={form.gsm || ''} onChange={(e) => set('gsm', e.target.value)} className={inCls} />
          </Field>
          <Field label="Mail">
            <input value={form.mail || ''} onChange={(e) => set('mail', e.target.value)} className={inCls} />
          </Field>
        </Row>
      </Section>

      {/* CONTACT URGENCE */}
      <Section title="Contact en cas d'urgence">
        <Row>
          <Field label="Identité">
            <input value={form.urgnom || ''} onChange={(e) => set('urgnom', e.target.value)} className={inCls} />
          </Field>
          <Field label="Parenté">
            <input value={form.urglien || ''} onChange={(e) => set('urglien', e.target.value)} className={inCls} />
          </Field>
          <Field label="Tél">
            <input value={form.urgtel || ''} onChange={(e) => set('urgtel', e.target.value)} className={inCls} />
          </Field>
        </Row>
      </Section>

      {/* EMBAUCHE */}
      <Section title="Infos embauche">
        <Row>
          <Field label="Date début">
            <input type="date" value={form.date_debut || ''} onChange={(e) => set('date_debut', e.target.value)} className={inCls} />
          </Field>
          <Check label="Adhère à la mutuelle" checked={!!form.mutuelle} onChange={(v) => set('mutuelle', v)} />
          <Field label="Date adhésion mutuelle">
            <input type="date" value={form.mutdate || ''} onChange={(e) => set('mutdate', e.target.value)} disabled={!form.mutuelle} className={inCls} />
          </Field>
        </Row>
        <Row>
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
        </Row>
        <Row>
          <PickerBtn
            icon={<Users className="w-4 h-4 text-c-brand" />}
            label={form.lib_equipe || "Choisir l'équipe"}
            onClick={() => setPicker('equipe')}
          />
        </Row>
      </Section>

      {/* DOCUMENTS */}
      <Section title="Documents">
        {(form.documents || []).length === 0 ? (
          <div className="text-sm text-c-ink-faint">Aucun document.</div>
        ) : (
          <div className="flex gap-4">
            <ul className="w-72 shrink-0 border border-c-line rounded-lg divide-y divide-c-line-soft overflow-hidden">
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
            <div className="flex-1 min-h-[480px] border border-c-line rounded-lg bg-c-surface-soft overflow-hidden">
              {docLoading ? (
                <div className="h-full flex items-center justify-center">
                  <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
                </div>
              ) : !docUrl ? (
                <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
                  Sélectionne un document pour l'aperçu.
                </div>
              ) : docMime.startsWith('image/') ? (
                <img
                  src={docUrl}
                  alt={docName}
                  className="w-full h-full object-contain"
                />
              ) : (
                <iframe
                  src={docUrl}
                  title={docName}
                  className="w-full h-[480px]"
                />
              )}
            </div>
          </div>
        )}
      </Section>

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
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-wrap gap-4 items-end">{children}</div>
}

function Field({
  label,
  children,
  wide,
}: {
  label: string
  children: React.ReactNode
  wide?: boolean
}) {
  return (
    <div className={`flex flex-col gap-1 ${wide ? 'flex-1 min-w-[300px]' : 'w-52'}`}>
      <span className="text-xs text-c-ink-soft">{label}</span>
      {children}
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
      className="flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-sm text-c-ink hover:bg-c-brand-soft transition-colors max-w-xs"
    >
      {icon}
      <span className="truncate">{label}</span>
    </button>
  )
}

function cap(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : ''
}
