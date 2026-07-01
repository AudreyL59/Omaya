/**
 * Fen_FicheSociete - fiche societe (creation / modification).
 *
 * Modal ouvert depuis ListeSocietePage (boutons Nouveau + Modifier).
 * 3 blocs :
 *   - Infos juridiques : type_orga (Interne/Distrib) + is_actif
 *     (Archivée/Active), forme_juri (combo), raison_sociale,
 *     rs_interne, date_creation, siren, siret, num_orias, rcs,
 *     code_ape, capital, num_tva
 *   - Infos chef d'entreprise : prenom/nom + titre + id_gerant
 *   - Coordonnées postales + téléphone + web
 *   - Coordonnées bancaires : IBAN, BIC
 *
 * Overlays Identite Visuelle / Signature Demat : placeholders
 * (uploads d'images pas encore implementes).
 */
import { useEffect, useState } from 'react'
import {
  X, Save, Loader2, Building2, ImageIcon, PenTool, FileText,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import SocieteImageSlot from './SocieteImageSlot'
import DocsDematerModal from './DocsDematerModal'
import PersonnePicker from '@/components/PersonnePicker'
import OrgaPicker from '@/components/OrgaPicker'

const API_BASE = '/api/adm'

interface FormeJuri { id_societe_form_juri: number; lib_form_juri: string }

interface SocieteDetail {
  id_societe_auto: string; id_ste: string
  id_type_orga: number; is_actif: boolean
  raison_sociale: string; rs_interne: string
  forme_juri: string; date_creation: string
  siren: string; siret: string; num_orias: string; rcs: string
  code_ape: string; capital: number; num_tva: string
  id_gerant: number; gerant_nom: string; gerant_type: string
  adresse1: string; adresse2: string; cp: string; ville: string
  tel: string; mail: string; url: string
  iban: string; bic: string; idorganigramme: number
  orga_lib: string; gerant_display: string
  has_logo: boolean; has_guimmick: boolean; has_cachet_cial: boolean
  has_gerant_paraphe: boolean; has_gerant_signature: boolean
}

interface Props {
  // string plutot que number : id_societe_auto est un bigint WinDev
  // (timestamp 17 chiffres) qui depasse Number.MAX_SAFE_INTEGER (2^53).
  // parseInt() perd de la precision et ouvre la mauvaise fiche.
  idSocieteAuto: string | null    // null = nouveau
  onClose: () => void
  onSaved?: () => void
}

const EMPTY: SocieteDetail = {
  id_societe_auto: '0', id_ste: '0',
  id_type_orga: 1, is_actif: true,
  raison_sociale: '', rs_interne: '',
  forme_juri: '', date_creation: '',
  siren: '', siret: '', num_orias: '', rcs: '',
  code_ape: '', capital: 0, num_tva: '',
  id_gerant: 0, gerant_nom: '', gerant_type: '',
  adresse1: '', adresse2: '', cp: '', ville: '',
  tel: '', mail: '', url: '',
  iban: '', bic: '', idorganigramme: 0,
  orga_lib: '', gerant_display: '',
  has_logo: false, has_guimmick: false, has_cachet_cial: false,
  has_gerant_paraphe: false, has_gerant_signature: false,
}

export default function FicheSocieteModal({
  idSocieteAuto, onClose, onSaved,
}: Props) {
  const isNew = idSocieteAuto == null
  const [d, setD] = useState<SocieteDetail>(EMPTY)
  const [formes, setFormes] = useState<FormeJuri[]>([])
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [showIdentite, setShowIdentite] = useState(false)
  const [showSignature, setShowSignature] = useState(false)
  const [showGerantPicker, setShowGerantPicker] = useState(false)
  const [showOrgaPicker, setShowOrgaPicker] = useState(false)
  const [showDocsDemater, setShowDocsDemater] = useState(false)

  const reloadImages = () => {
    if (isNew || !idSocieteAuto) return
    fetch(`${API_BASE}/societes/${idSocieteAuto}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then((f: SocieteDetail | null) => {
        if (!f) return
        setD(prev => ({
          ...prev,
          has_logo: f.has_logo, has_guimmick: f.has_guimmick,
          has_cachet_cial: f.has_cachet_cial,
          has_gerant_paraphe: f.has_gerant_paraphe,
          has_gerant_signature: f.has_gerant_signature,
        }))
      })
  }

  useEffect(() => {
    // Charge combo formes juri
    fetch(`${API_BASE}/societes/formes-juri`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((f: FormeJuri[]) => setFormes(Array.isArray(f) ? f : []))
  }, [])

  useEffect(() => {
    if (isNew) { setD(EMPTY); setLoading(false); return }
    setLoading(true)
    fetch(`${API_BASE}/societes/${idSocieteAuto}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(async r => {
        if (!r.ok) throw new Error(String(r.status))
        return r.json() as Promise<SocieteDetail>
      })
      .then(setD)
      .catch(e => showToast(`Erreur : ${(e as Error).message}`, 'error'))
      .finally(() => setLoading(false))
  }, [idSocieteAuto, isNew])

  const update = (patch: Partial<SocieteDetail>) => setD(p => ({ ...p, ...patch }))

  const enregistrer = async () => {
    setSaving(true)
    try {
      const url = isNew
        ? `${API_BASE}/societes`
        : `${API_BASE}/societes/${idSocieteAuto}`
      const method = isNew ? 'POST' : 'PUT'
      // Payload sans les champs auto/id_ste (backend les gère)
      const payload = {
        id_type_orga: d.id_type_orga, is_actif: d.is_actif,
        raison_sociale: d.raison_sociale, rs_interne: d.rs_interne,
        forme_juri: d.forme_juri,
        date_creation: d.date_creation ? d.date_creation.slice(0, 10) : null,
        siren: d.siren, siret: d.siret, num_orias: d.num_orias, rcs: d.rcs,
        code_ape: d.code_ape, capital: d.capital, num_tva: d.num_tva,
        id_gerant: d.id_gerant, gerant_nom: d.gerant_nom, gerant_type: d.gerant_type,
        adresse1: d.adresse1, adresse2: d.adresse2, cp: d.cp, ville: d.ville,
        tel: d.tel, mail: d.mail, url: d.url,
        iban: d.iban, bic: d.bic, idorganigramme: d.idorganigramme,
      }
      const r = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast(isNew ? 'Société créée' : 'Société enregistrée', 'success')
      onSaved?.()
      onClose()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[1100px] max-w-full max-h-[95vh] flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h2 className="text-sm font-bold flex items-center gap-2">
            <Building2 className="w-4 h-4 text-c-brand" />
            Fiche Société
            <span className="text-xs text-c-ink-faint-2 font-normal">
              ID {d.id_societe_auto || '(nouveau)'}
            </span>
          </h2>
          <button onClick={onClose}
            className="p-1 hover:bg-c-surface-soft rounded text-c-ink-faint">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-c-brand" />
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {/* Toggles type / actif */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex gap-0">
                {([[1, 'Interne'], [3, 'Distributeur']] as const).map(([v, l], i) => (
                  <button key={v} type="button"
                    onClick={() => update({ id_type_orga: v })}
                    className={`px-3 h-7 text-xs border border-c-line ${
                      i === 0 ? 'rounded-l' : 'rounded-r'
                    } ${
                      d.id_type_orga === v
                        ? 'bg-c-brand text-white border-c-brand'
                        : 'bg-white text-c-ink-soft'
                    }`}>
                    {l}
                  </button>
                ))}
              </div>
              <div className="flex gap-0">
                {([[false, 'Archivée'], [true, 'Active']] as const).map(([v, l], i) => (
                  <button key={String(v)} type="button"
                    onClick={() => update({ is_actif: v })}
                    className={`px-3 h-7 text-xs border border-c-line ${
                      i === 0 ? 'rounded-l' : 'rounded-r'
                    } ${
                      d.is_actif === v
                        ? 'bg-c-brand text-white border-c-brand'
                        : 'bg-white text-c-ink-soft'
                    }`}>
                    {l}
                  </button>
                ))}
              </div>
              <div className="flex-1" />
              <button type="button" disabled={isNew}
                onClick={() => { setShowIdentite(v => !v); setShowSignature(false) }}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs disabled:opacity-30 disabled:cursor-not-allowed ${
                  showIdentite ? 'bg-c-brand text-white border-c-brand'
                                : 'border-c-line text-c-ink-soft hover:bg-c-surface-soft'
                }`}
                title={isNew ? 'Enregistrez la société d\'abord' : ''}>
                <ImageIcon className="w-3.5 h-3.5" /> Identité visuelle
              </button>
              <button type="button" disabled={isNew}
                onClick={() => { setShowSignature(v => !v); setShowIdentite(false) }}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs disabled:opacity-30 disabled:cursor-not-allowed ${
                  showSignature ? 'bg-c-brand text-white border-c-brand'
                                 : 'border-c-line text-c-ink-soft hover:bg-c-surface-soft'
                }`}
                title={isNew ? 'Enregistrez la société d\'abord' : ''}>
                <PenTool className="w-3.5 h-3.5" /> Signature Démat
              </button>
              {!isNew && d.id_ste && d.id_ste !== '0' && (
                <button type="button"
                  onClick={() => setShowDocsDemater(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
                  <FileText className="w-3.5 h-3.5" /> Docs
                </button>
              )}
            </div>

            {/* Overlays uploads d'images */}
            {showIdentite && !isNew && idSocieteAuto && (
              <section className="border border-c-brand bg-c-brand/5 rounded-lg p-3 flex gap-3">
                <SocieteImageSlot idSociete={idSocieteAuto} champ="logo"
                  label="Logo" hasImage={d.has_logo} onChanged={reloadImages} />
                <SocieteImageSlot idSociete={idSocieteAuto} champ="guimmick"
                  label="Guimmick" hasImage={d.has_guimmick} onChanged={reloadImages} />
              </section>
            )}
            {showSignature && !isNew && idSocieteAuto && (
              <section className="border border-c-brand bg-c-brand/5 rounded-lg p-3 flex gap-3">
                <SocieteImageSlot idSociete={idSocieteAuto} champ="cachet_cial"
                  label="Cachet Cial" hasImage={d.has_cachet_cial} onChanged={reloadImages} />
                <SocieteImageSlot idSociete={idSocieteAuto} champ="gerant_paraphe"
                  label="Paraphe" hasImage={d.has_gerant_paraphe} onChanged={reloadImages} />
                <SocieteImageSlot idSociete={idSocieteAuto} champ="gerant_signature"
                  label="Signature" hasImage={d.has_gerant_signature} onChanged={reloadImages} />
              </section>
            )}

            {/* Bloc INFOS JURIDIQUES */}
            <section className="border border-c-line rounded-lg p-3">
              <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2">
                Infos juridiques
              </h3>
              <div className="grid grid-cols-4 gap-3 text-xs">
                <Field label="Forme juridique">
                  <select value={d.forme_juri}
                    onChange={e => update({ forme_juri: e.target.value })}
                    className="w-full px-2 py-1 border border-c-line rounded text-xs h-7">
                    <option value="">—</option>
                    {formes.map(f => (
                      <option key={f.id_societe_form_juri} value={String(f.id_societe_form_juri)}>
                        {f.lib_form_juri}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Raison Sociale" cols={2}>
                  <Input value={d.raison_sociale}
                    onChange={v => update({ raison_sociale: v })} />
                </Field>
                <Field label="Date Création">
                  <input type="date" value={d.date_creation ? d.date_creation.slice(0, 10) : ''}
                    onChange={e => update({ date_creation: e.target.value })}
                    className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
                </Field>
                <Field label="RS Interne" cols={4}>
                  <Input value={d.rs_interne}
                    onChange={v => update({ rs_interne: v })} />
                </Field>
                <Field label="SIREN">
                  <Input value={d.siren} onChange={v => update({ siren: v })} />
                </Field>
                <Field label="SIRET">
                  <Input value={d.siret} onChange={v => update({ siret: v })} />
                </Field>
                <Field label="Num Orias">
                  <Input value={d.num_orias} onChange={v => update({ num_orias: v })} />
                </Field>
                <Field label="RCS">
                  <Input value={d.rcs} onChange={v => update({ rcs: v })} />
                </Field>
                <Field label="APE">
                  <Input value={d.code_ape} onChange={v => update({ code_ape: v })} />
                </Field>
                <Field label="CAPITAL">
                  <input type="number" step="0.01" value={d.capital || ''}
                    onChange={e => update({ capital: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 text-right tabular-nums" />
                </Field>
                <Field label="TVA intra." cols={2}>
                  <Input value={d.num_tva} onChange={v => update({ num_tva: v })} />
                </Field>
              </div>
            </section>

            {/* Bloc CHEF D'ENTREPRISE */}
            <section className="border border-c-line rounded-lg p-3">
              <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2">
                Infos chef d'entreprise
              </h3>
              <div className="grid grid-cols-4 gap-3 text-xs">
                <Field label="Nom / Prénom" cols={2}>
                  <Input value={d.gerant_nom} onChange={v => update({ gerant_nom: v })} />
                </Field>
                <Field label="Titre">
                  <Input value={d.gerant_type} onChange={v => update({ gerant_type: v })}
                    placeholder="Président, Gérant..." />
                </Field>
                <Field label="Choisir le gérant">
                  <button type="button" onClick={() => setShowGerantPicker(true)}
                    className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 text-left truncate hover:bg-c-surface-soft flex items-center gap-1">
                    <span className="flex-1 truncate">
                      {d.gerant_display || (d.id_gerant ? `ID ${d.id_gerant}` : '— aucun —')}
                    </span>
                  </button>
                </Field>
                <Field label="Choisir l'équipe" cols={2}>
                  <button type="button" onClick={() => setShowOrgaPicker(true)}
                    className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 text-left truncate hover:bg-c-surface-soft flex items-center gap-1">
                    <span className="flex-1 truncate">
                      {d.orga_lib || (d.idorganigramme ? `ID ${d.idorganigramme}` : '— aucune —')}
                    </span>
                  </button>
                </Field>
              </div>
            </section>

            {/* Bloc COORDONNÉES POSTALES + BANCAIRES */}
            <div className="grid grid-cols-2 gap-3">
              <section className="border border-c-line rounded-lg p-3">
                <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2">
                  Coordonnées postales et téléphoniques
                </h3>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <Field label="Adresse 1" cols={2}>
                    <Input value={d.adresse1} onChange={v => update({ adresse1: v })} />
                  </Field>
                  <Field label="Adresse 2" cols={2}>
                    <Input value={d.adresse2} onChange={v => update({ adresse2: v })} />
                  </Field>
                  <Field label="CP">
                    <Input value={d.cp} onChange={v => update({ cp: v })} />
                  </Field>
                  <Field label="Ville">
                    <Input value={d.ville} onChange={v => update({ ville: v })} />
                  </Field>
                  <Field label="Tél">
                    <Input value={d.tel} onChange={v => update({ tel: v })} />
                  </Field>
                  <Field label="Courriel">
                    <Input value={d.mail} onChange={v => update({ mail: v })} />
                  </Field>
                  <Field label="Site Web" cols={2}>
                    <Input value={d.url} onChange={v => update({ url: v })} />
                  </Field>
                </div>
              </section>
              <section className="border border-c-line rounded-lg p-3">
                <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2">
                  Coordonnées bancaires
                </h3>
                <div className="grid grid-cols-1 gap-3 text-xs">
                  <Field label="IBAN">
                    <Input value={d.iban} onChange={v => update({ iban: v })} />
                  </Field>
                  <Field label="BIC">
                    <Input value={d.bic} onChange={v => update({ bic: v })} />
                  </Field>
                </div>
              </section>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-c-line">
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
            Annuler
          </button>
          <button type="button" onClick={enregistrer} disabled={saving || loading}
            className="flex items-center gap-2 px-4 py-1.5 rounded bg-c-brand text-white text-xs font-medium hover:opacity-90 disabled:opacity-50">
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                     : <Save className="w-3.5 h-3.5" />}
            Enregistrer
          </button>
        </div>
      </div>

      {showGerantPicker && (
        <PersonnePicker
          title="Choisir le gérant"
          onClose={() => setShowGerantPicker(false)}
          onSelect={(s) => {
            const id = parseInt(s.id_salarie, 10) || 0
            const nom = (s.nom || '').toUpperCase()
            const prenom = s.prenom ? s.prenom[0].toUpperCase() + s.prenom.slice(1).toLowerCase() : ''
            update({
              id_gerant: id,
              gerant_display: `${nom} ${prenom}`.trim(),
              gerant_nom: `${nom} ${prenom}`.trim(),
            })
            setShowGerantPicker(false)
          }}
        />
      )}
      {showOrgaPicker && (
        <OrgaPicker
          title="Choisir l'équipe"
          onClose={() => setShowOrgaPicker(false)}
          onSelect={(orgas) => {
            const o = orgas[0]
            if (o) {
              update({
                idorganigramme: parseInt(o.id_orga, 10) || 0,
                orga_lib: o.lib_orga,
              })
            }
            setShowOrgaPicker(false)
          }}
        />
      )}
      {showDocsDemater && d.id_ste && d.id_ste !== '0' && (
        <DocsDematerModal idSte={d.id_ste}
          onClose={() => setShowDocsDemater(false)} />
      )}
    </div>
  )
}

function Field({ label, children, cols = 1 }: {
  label: string; children: React.ReactNode; cols?: number
}) {
  return (
    <div className={cols === 4 ? 'col-span-4' : cols === 3 ? 'col-span-3' : cols === 2 ? 'col-span-2' : ''}>
      <label className="text-[10px] text-c-ink-faint block">{label}</label>
      {children}
    </div>
  )
}

function Input({
  value, onChange, placeholder,
}: {
  value: string; onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <input type="text" value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
  )
}
