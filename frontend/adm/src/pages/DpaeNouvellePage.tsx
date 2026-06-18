/**
 * Fen_DPAE_Nouvelle (transposition WinDev Plan 1).
 *
 * Ouverture depuis Fen_DPAE_Recherche avec query :
 *   ?id_ticket=N&type_dpae=0|1|2|3|4&id_elem=N&id_cv_suivi=N
 *
 * Au mount :
 *   1. GET /api/adm/dpae/lookups          -> combos societes/mutuelles/...
 *   2. GET /api/adm/dpae/preremplir?...   -> remplit l'etat selon TypeDpae
 *
 * Btn Enregistrer :
 *   POST /api/adm/dpae/enregistrer (cf. Plan 1)
 *   -> renvoie {id_salarie, matricule_tr}, bascule en Plan 2 (codes
 *      partenaires - V2 a venir)
 */

import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  Save,
  UserCog,
} from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import SearchPicker, {
  type PickerItem,
} from '@shared/tickets/forms/SearchPicker'
import {
  fillPartenaire,
  isExtensionInstalled,
} from '@/lib/dpae-extension'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

const cap = (s: string): string =>
  s ? s[0].toUpperCase() + s.slice(1).toLowerCase() : ''

interface Lookups {
  societes: { id_ste: string; lib: string }[]
  mutuelles: { id_mutuelle: number; lib: string; is_actif: boolean }[]
  postes: { id_type_poste: number; lib: string; categorie: string }[]
  types_ctt: { id_type_ctt: number; lib: string }[]
  types_horaire: { id_type_horaire: number; lib: string }[]
}

interface DpaePayload {
  // IDs 8 octets (timestamp) : DOIVENT etre en string pour preserver
  // la precision JS (Number max safe = 2^53-1 < 20260616110127323).
  type_dpae: number
  id_elem: string
  id_cv_suivi: string
  id_ticket: string
  id_cvtheque: string
  idorganigramme: string
  id_ste: string
  coopteur: string
  jo_coopteur: string

  civilite: number
  sexe: string
  nom: string
  nom_marital: string
  prenom: string
  nationalite: string
  date_naiss: string
  lieu_naiss: string
  dep_naiss: number
  num_ss: string
  cpam: string
  num_cin: string
  situation_fam: number
  avec_enfant: boolean
  nb_enfants: number
  travailleur_handi: boolean

  adresse1: string
  adresse2: string
  cp: string
  ville: string
  tel_mob: string
  tel_fixe: string
  mail: string
  urg_nom: string
  urg_lien: string
  urg_tel: string
  iban: string
  bic: string

  // Petits entiers (PK simples) : OK en number
  id_type_poste: number
  id_type_ctt: number
  id_type_horaire: number
  date_debut: string

  coopte: boolean
  jodirecte: boolean

  id_mutuelle: number
  adhesion: boolean
  adhesion_date: string
  mutuelle_dossier: boolean
  mutuelle_att_ss: boolean
  mutuelle_rib: boolean
}

const EMPTY_PAYLOAD: DpaePayload = {
  type_dpae: 0,
  id_elem: '',
  id_cv_suivi: '',
  id_ticket: '',
  id_cvtheque: '',
  idorganigramme: '',
  id_ste: '',
  coopteur: '',
  jo_coopteur: '',
  civilite: 0,
  sexe: '',
  nom: '',
  nom_marital: '',
  prenom: '',
  nationalite: 'Française',
  date_naiss: '',
  lieu_naiss: '',
  dep_naiss: 0,
  num_ss: '',
  cpam: '',
  num_cin: '',
  situation_fam: 0,
  avec_enfant: false,
  nb_enfants: 0,
  travailleur_handi: false,
  adresse1: '',
  adresse2: '',
  cp: '',
  ville: '',
  tel_mob: '',
  tel_fixe: '',
  mail: '',
  urg_nom: '',
  urg_lien: '',
  urg_tel: '',
  iban: '',
  bic: '',
  id_type_poste: 0,
  id_type_ctt: 1,
  id_type_horaire: 1,
  date_debut: '',
  coopte: false,
  jodirecte: false,
  id_mutuelle: 0,
  adhesion: false,
  adhesion_date: '',
  mutuelle_dossier: false,
  mutuelle_att_ss: false,
  mutuelle_rib: false,
}

export default function DpaeNouvellePage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()

  // IDs gardes en string : > 2^53 perd la precision sinon
  const idTicket = params.get('id_ticket') || ''
  const typeDpae = Number(params.get('type_dpae') || '0')
  const idElem = params.get('id_elem') || ''
  const idCvSuivi = params.get('id_cv_suivi') || ''

  const [lookups, setLookups] = useState<Lookups | null>(null)
  const [data, setData] = useState<DpaePayload>({
    ...EMPTY_PAYLOAD,
    type_dpae: typeDpae,
    id_elem: idElem,
    id_cv_suivi: idCvSuivi,
    id_ticket: idTicket,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [phase, setPhase] = useState<'form' | 'codes'>('form')
  const [savedId, setSavedId] = useState<string>('')
  const [savedMatricule, setSavedMatricule] = useState<string>('')

  const [orgaLib, setOrgaLib] = useState('Choisir une équipe')
  const [coopteurLib, setCoopteurLib] = useState('Choisir le coopteur')
  const [joCoopteurLib, setJoCoopteurLib] = useState('Choisir le coopteur JO')

  const [orgaPickerOpen, setOrgaPickerOpen] = useState(false)
  const [coopteurPickerOpen, setCoopteurPickerOpen] = useState(false)
  const [joCoopteurPickerOpen, setJoCoopteurPickerOpen] = useState(false)

  const update = (patch: Partial<DpaePayload>) =>
    setData((d) => ({ ...d, ...patch }))

  // ---- Init ---------------------------------------------------------------
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const [lkR, prR] = await Promise.all([
          fetch('/api/adm/dpae/lookups', {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
          fetch(
            `/api/adm/dpae/preremplir?type_dpae=${typeDpae}&id_elem=${idElem}&id_cv_suivi=${idCvSuivi}&id_ticket=${idTicket}`,
            { headers: { Authorization: `Bearer ${getToken()}` } },
          ),
        ])
        if (cancelled) return
        const lk = (await lkR.json()) as Lookups
        const pr = (await prR.json()) as Partial<DpaePayload> & {
          orga_lib?: string
          coopteur_lib?: string
          jo_coopteur_lib?: string
        }
        setLookups(lk)
        // Auto-selection de la mutuelle active uniquement si rien deja choisi
        const activeMut = lk.mutuelles.find((m) => m.is_actif)
        const merged: DpaePayload = {
          ...EMPTY_PAYLOAD,
          ...(pr as Partial<DpaePayload>),
          type_dpae: typeDpae,
          id_elem: idElem,
          id_cv_suivi: idCvSuivi,
          id_ticket: idTicket,
          id_mutuelle:
            (pr as DpaePayload).id_mutuelle ||
            (activeMut ? activeMut.id_mutuelle : 0),
        }
        setData(merged)
        // Libelles des boutons (renvoyes par /preremplir)
        if (pr.orga_lib) setOrgaLib(pr.orga_lib)
        if (pr.coopteur_lib) setCoopteurLib(pr.coopteur_lib)
        if (pr.jo_coopteur_lib) setJoCoopteurLib(pr.jo_coopteur_lib)
        // TypeDpae=3 : salarie deja en activite -> on saute le form Plan 1
        // et on bascule directement en Plan 2 (codes partenaires).
        // Cf. WinDev cas TypeDpae=3 -> PoursuivreDPAE() qui fait
        // MaFenêtre..Plan = 2.
        if (typeDpae === 3 && idElem) {
          setSavedId(idElem)
          setSavedMatricule(`${merged.nom} ${merged.prenom}`.trim())
          setPhase('codes')
        }
      } catch (e) {
        showToast(`Échec chargement DPAE : ${(e as Error).message}`, 'error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [typeDpae, idElem, idCvSuivi, idTicket])

  // ---- Save ---------------------------------------------------------------
  const handleSave = async () => {
    setSaving(true)
    try {
      const r = await fetch('/api/adm/dpae/enregistrer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(data),
      })
      const j = await r.json()
      if (!r.ok) {
        // detail peut etre soit une string (HTTPException), soit un array
        // de validation Pydantic [{loc, msg, type, ...}].
        const d = (j as { detail?: unknown })?.detail
        let msg: string
        if (typeof d === 'string') msg = d
        else if (Array.isArray(d))
          msg = d
            .map((e) =>
              e && typeof e === 'object' && 'msg' in e
                ? `${(e as { loc?: unknown[] }).loc?.slice(1).join('.') || ''}: ${(e as { msg: string }).msg}`
                : JSON.stringify(e),
            )
            .join(' ; ')
        else msg = String(r.status)
        throw new Error(msg)
      }
      setSavedId(String(j.id_salarie))
      setSavedMatricule(String(j.matricule_tr))
      setPhase('codes')
      showToast('Informations salarié enregistrées.', 'success')
    } catch (e) {
      showToast(`Échec enregistrement : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !lookups) {
    return (
      <div className="p-10 flex items-center justify-center gap-3 text-[#A68D8A]">
        <Loader2 className="w-5 h-5 animate-spin" />
        Chargement de la DPAE...
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto font-normal">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm mb-3 hover:underline"
        style={{ color: COL_PRIMARY }}
      >
        <ArrowLeft className="w-4 h-4" />
        Retour à la recherche
      </button>

      <div className="flex items-center gap-3 mb-5">
        <UserCog className="w-6 h-6" style={{ color: COL_BRUN }} />
        <h1 className="text-xl font-bold" style={{ color: COL_BRUN }}>
          {phase === 'form'
            ? 'Nouvelle DPAE'
            : `Ajout des codes partenaires - ${data.nom} ${data.prenom}`}
        </h1>
        {savedMatricule && (
          <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: COL_BG_SOFT, color: COL_BRUN }}>
            Matricule : {savedMatricule}
          </span>
        )}
      </div>

      {phase === 'form' ? (
        <FormPlan1
          data={data}
          update={update}
          lookups={lookups}
          orgaLib={orgaLib}
          coopteurLib={coopteurLib}
          joCoopteurLib={joCoopteurLib}
          openOrgaPicker={() => setOrgaPickerOpen(true)}
          openCoopteurPicker={() => setCoopteurPickerOpen(true)}
          openJoCoopteurPicker={() => setJoCoopteurPickerOpen(true)}
          onSave={handleSave}
          saving={saving}
        />
      ) : (
        <CodesPlan2
          savedId={savedId}
          idTicket={idTicket}
          data={data}
          navigate={navigate}
        />
      )}

      {orgaPickerOpen && (
        <SearchPicker
          apiBase="/api/adm"
          getToken={getToken}
          title="Choisir l'équipe"
          path="/tickets/organigrammes/search"
          mapItem={(o: { id_organigramme: string; lib_orga: string }) => ({
            id: o.id_organigramme,
            label: o.lib_orga,
          })}
          onClose={() => setOrgaPickerOpen(false)}
          onPick={(it: PickerItem) => {
            setOrgaPickerOpen(false)
            update({ idorganigramme: it.id })
            setOrgaLib(it.label)
          }}
        />
      )}
      {coopteurPickerOpen && (
        <SearchPicker
          apiBase="/api/adm"
          getToken={getToken}
          title="Choisir le coopteur"
          path="/tickets/salaries/search"
          mapItem={(s: {
            id_salarie: string
            nom: string
            prenom: string
            poste?: string
            lib_societe?: string
          }) => ({
            id: s.id_salarie,
            label: `${s.nom} ${cap(s.prenom)}`,
            sublabel: [s.poste, s.lib_societe].filter(Boolean).join(' · '),
          })}
          onClose={() => setCoopteurPickerOpen(false)}
          onPick={(it: PickerItem) => {
            setCoopteurPickerOpen(false)
            update({ coopteur: it.id })
            setCoopteurLib(it.label)
          }}
        />
      )}
      {joCoopteurPickerOpen && (
        <SearchPicker
          apiBase="/api/adm"
          getToken={getToken}
          title="Choisir le coopteur JO"
          path="/tickets/salaries/search"
          mapItem={(s: {
            id_salarie: string
            nom: string
            prenom: string
            poste?: string
            lib_societe?: string
          }) => ({
            id: s.id_salarie,
            label: `${s.nom} ${cap(s.prenom)}`,
            sublabel: [s.poste, s.lib_societe].filter(Boolean).join(' · '),
          })}
          onClose={() => setJoCoopteurPickerOpen(false)}
          onPick={(it: PickerItem) => {
            setJoCoopteurPickerOpen(false)
            update({ jo_coopteur: it.id })
            setJoCoopteurLib(it.label)
          }}
        />
      )}
    </div>
  )
}

// ============================================================================
// Plan 1 - Form de saisie
// ============================================================================

interface FormProps {
  data: DpaePayload
  update: (patch: Partial<DpaePayload>) => void
  lookups: Lookups
  orgaLib: string
  coopteurLib: string
  joCoopteurLib: string
  openOrgaPicker: () => void
  openCoopteurPicker: () => void
  openJoCoopteurPicker: () => void
  onSave: () => void
  saving: boolean
}

function FormPlan1({
  data,
  update,
  lookups,
  orgaLib,
  coopteurLib,
  joCoopteurLib,
  openOrgaPicker,
  openCoopteurPicker,
  openJoCoopteurPicker,
  onSave,
  saving,
}: FormProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {/* Colonne 1 : Identité */}
      <Card title="Identité">
        <div className="flex gap-2">
          <RadioCiv
            value={data.civilite}
            onChange={(v) =>
              update({ civilite: v, sexe: v === 1 ? 'H' : 'F' })
            }
          />
        </div>
        <Field label="Nom">
          <input
            type="text"
            value={data.nom}
            onChange={(e) => update({ nom: e.target.value.toUpperCase() })}
            className={inputCls}
          />
        </Field>
        <Field label="Épouse (le cas échéant)">
          <input
            type="text"
            value={data.nom_marital}
            onChange={(e) => update({ nom_marital: e.target.value })}
            className={inputCls}
          />
        </Field>
        <Field label="Prénom">
          <input
            type="text"
            value={data.prenom}
            onChange={(e) => update({ prenom: e.target.value })}
            className={inputCls}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Sexe (H/F)">
            <input
              type="text"
              value={data.sexe}
              onChange={(e) => update({ sexe: e.target.value.toUpperCase() })}
              maxLength={1}
              className={inputCls}
            />
          </Field>
          <Field label="Nationalité">
            <input
              type="text"
              value={data.nationalite}
              onChange={(e) => update({ nationalite: e.target.value })}
              className={inputCls}
            />
          </Field>
        </div>
        <Field label="Né(e) le">
          <input
            type="date"
            value={data.date_naiss}
            onChange={(e) => update({ date_naiss: e.target.value })}
            className={inputCls}
          />
        </Field>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Lieu de naissance" wide>
            <input
              type="text"
              value={data.lieu_naiss}
              onChange={(e) => update({ lieu_naiss: e.target.value })}
              className={inputCls}
            />
          </Field>
          <Field label="Dép">
            <input
              type="number"
              value={data.dep_naiss || ''}
              onChange={(e) => update({ dep_naiss: Number(e.target.value) })}
              className={inputCls}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="N° Sécu Sociale">
            <input
              type="text"
              value={data.num_ss}
              onChange={(e) => update({ num_ss: e.target.value })}
              className={inputCls}
            />
          </Field>
          <Field label="CPAM">
            <input
              type="text"
              value={data.cpam}
              onChange={(e) => update({ cpam: e.target.value })}
              className={inputCls}
            />
          </Field>
        </div>
        <Field label="N° CIN ou passeport">
          <input
            type="text"
            value={data.num_cin}
            onChange={(e) => update({ num_cin: e.target.value })}
            className={inputCls}
          />
        </Field>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Situation Familiale" wide>
            <select
              value={data.situation_fam || ''}
              onChange={(e) =>
                update({ situation_fam: Number(e.target.value) })
              }
              className={inputCls}
            >
              <option value="">-</option>
              <option value="1">Célibataire</option>
              <option value="2">Marié(e)</option>
              <option value="3">Pacsé(e)</option>
              <option value="4">Divorcé(e)</option>
              <option value="5">Veuf/ve</option>
            </select>
          </Field>
          <Field label="Nb enfants">
            <input
              type="number"
              value={data.nb_enfants || ''}
              onChange={(e) => update({ nb_enfants: Number(e.target.value) })}
              className={inputCls}
            />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: COL_BRUN }}>
          <input
            type="checkbox"
            checked={data.avec_enfant}
            onChange={(e) => update({ avec_enfant: e.target.checked })}
          />
          Avec enfant à charge
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: COL_BRUN }}>
          <input
            type="checkbox"
            checked={data.travailleur_handi}
            onChange={(e) => update({ travailleur_handi: e.target.checked })}
          />
          Travailleur Handicapé
        </label>

        <Section>Personne à contacter en cas d'urgence</Section>
        <Field label="Nom du contact">
          <input
            type="text"
            value={data.urg_nom}
            onChange={(e) => update({ urg_nom: e.target.value })}
            className={inputCls}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Lien de parenté">
            <input
              type="text"
              value={data.urg_lien}
              onChange={(e) => update({ urg_lien: e.target.value })}
              className={inputCls}
            />
          </Field>
          <Field label="Tél du contact">
            <input
              type="text"
              value={data.urg_tel}
              onChange={(e) => update({ urg_tel: e.target.value })}
              className={inputCls}
            />
          </Field>
        </div>
      </Card>

      {/* Colonne 2 : Coordonnées + bancaires */}
      <Card title="Coordonnées postales & téléphoniques">
        <Field label="Adresse">
          <input
            type="text"
            value={data.adresse1}
            onChange={(e) => update({ adresse1: e.target.value })}
            className={inputCls}
          />
        </Field>
        <Field label="Complément d'adresse">
          <input
            type="text"
            value={data.adresse2}
            onChange={(e) => update({ adresse2: e.target.value })}
            className={inputCls}
          />
        </Field>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Code postal">
            <input
              type="text"
              value={data.cp}
              onChange={(e) => update({ cp: e.target.value })}
              className={inputCls}
            />
          </Field>
          <Field label="Ville" wide>
            <input
              type="text"
              value={data.ville}
              onChange={(e) => update({ ville: e.target.value })}
              className={inputCls}
            />
          </Field>
        </div>
        <Field label="Tél Mobile">
          <input
            type="text"
            value={data.tel_mob}
            onChange={(e) => update({ tel_mob: e.target.value })}
            className={inputCls}
          />
        </Field>
        <Field label="Courriel">
          <input
            type="email"
            value={data.mail}
            onChange={(e) => update({ mail: e.target.value })}
            className={inputCls}
          />
        </Field>

        <Section>Coordonnées bancaires</Section>
        <Field label="IBAN">
          <input
            type="text"
            value={data.iban}
            onChange={(e) => update({ iban: e.target.value.toUpperCase() })}
            placeholder="TOUT EN MAJUSCULES"
            className={inputCls}
          />
        </Field>
        <Field label="BIC">
          <input
            type="text"
            value={data.bic}
            onChange={(e) => update({ bic: e.target.value.toUpperCase() })}
            placeholder="TOUT EN MAJUSCULES"
            className={inputCls}
          />
        </Field>

        {data.id_cvtheque && data.id_cvtheque !== '' && (
          <div className="mt-3">
            <button
              type="button"
              onClick={() =>
                showToast('Voir Fiche CV : module à venir.', 'info')
              }
              className="flex items-center gap-2 text-sm"
              style={{ color: COL_PRIMARY }}
            >
              <ExternalLink className="w-4 h-4" />
              Voir la fiche CV
            </button>
          </div>
        )}
      </Card>

      {/* Colonne 3 : Info embauche + mutuelle */}
      <Card title="Information embauche">
        <Field label="Début le">
          <input
            type="date"
            value={data.date_debut}
            onChange={(e) => update({ date_debut: e.target.value })}
            className={inputCls}
          />
        </Field>
        <Field label="Équipe">
          <button
            type="button"
            onClick={openOrgaPicker}
            className="w-full px-3 py-2 text-left rounded-md text-sm hover:bg-[#EFE9E7]"
            style={{
              backgroundColor: COL_BG_SOFT,
              color: COL_BRUN,
              border: `1px solid ${COL_BORDER}`,
            }}
          >
            {orgaLib}
          </button>
        </Field>
        <Field label="Société">
          <select
            value={data.id_ste || ''}
            onChange={(e) => update({ id_ste: e.target.value })}
            className={inputCls}
          >
            <option value="">-</option>
            {lookups.societes.map((s) => (
              <option key={s.id_ste} value={s.id_ste}>
                {s.lib}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Poste">
          <select
            value={data.id_type_poste || ''}
            onChange={(e) =>
              update({ id_type_poste: Number(e.target.value) })
            }
            className={inputCls}
          >
            <option value="">-</option>
            {lookups.postes.map((p) => (
              <option key={p.id_type_poste} value={p.id_type_poste}>
                {p.lib}
              </option>
            ))}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Type Ctt">
            <select
              value={data.id_type_ctt || ''}
              onChange={(e) =>
                update({ id_type_ctt: Number(e.target.value) })
              }
              className={inputCls}
            >
              {lookups.types_ctt.map((t) => (
                <option key={t.id_type_ctt} value={t.id_type_ctt}>
                  {t.lib}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Horaires">
            <select
              value={data.id_type_horaire || ''}
              onChange={(e) =>
                update({ id_type_horaire: Number(e.target.value) })
              }
              className={inputCls}
            >
              {lookups.types_horaire.map((h) => (
                <option key={h.id_type_horaire} value={h.id_type_horaire}>
                  {h.lib}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Section>Cooptation</Section>
        <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: COL_BRUN }}>
          <input
            type="checkbox"
            checked={data.coopte}
            onChange={(e) => update({ coopte: e.target.checked })}
          />
          Coopté
        </label>
        {data.coopte && (
          <button
            type="button"
            onClick={openCoopteurPicker}
            className="w-full px-3 py-2 text-left rounded-md text-sm hover:bg-[#EFE9E7] mb-2"
            style={{
              backgroundColor: COL_BG_SOFT,
              color: COL_BRUN,
              border: `1px solid ${COL_BORDER}`,
            }}
          >
            {coopteurLib}
          </button>
        )}
        <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: COL_BRUN }}>
          <input
            type="checkbox"
            checked={data.jodirecte}
            onChange={(e) => update({ jodirecte: e.target.checked })}
          />
          JO Directe
        </label>
        {data.jodirecte && (
          <button
            type="button"
            onClick={openJoCoopteurPicker}
            className="w-full px-3 py-2 text-left rounded-md text-sm hover:bg-[#EFE9E7] mb-2"
            style={{
              backgroundColor: COL_BG_SOFT,
              color: COL_BRUN,
              border: `1px solid ${COL_BORDER}`,
            }}
          >
            {joCoopteurLib}
          </button>
        )}
        {data.jodirecte && !data.jo_coopteur && (
          <p className="text-xs italic mt-1" style={{ color: COL_BRUN }}>
            Attention, JO Directe car pas de RDV pris, merci de renseigner le
            coopteur.
          </p>
        )}

        <Section>Mutuelle entreprise</Section>
        <Field label="Mutuelle">
          <select
            value={data.id_mutuelle || ''}
            onChange={(e) =>
              update({ id_mutuelle: Number(e.target.value) })
            }
            className={inputCls}
          >
            <option value="">-</option>
            {lookups.mutuelles.map((m) => (
              <option key={m.id_mutuelle} value={m.id_mutuelle}>
                {m.lib}
              </option>
            ))}
          </select>
        </Field>
        <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: COL_BRUN }}>
          <input
            type="checkbox"
            checked={data.adhesion}
            onChange={(e) => update({ adhesion: e.target.checked })}
          />
          Adhésion à la mutuelle
        </label>
        {data.adhesion && (
          <Field label="Depuis le">
            <input
              type="date"
              value={data.adhesion_date}
              onChange={(e) => update({ adhesion_date: e.target.value })}
              className={inputCls}
            />
          </Field>
        )}
        <div className="flex flex-wrap gap-3">
          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: COL_BRUN }}>
            <input
              type="checkbox"
              checked={data.mutuelle_dossier}
              onChange={(e) => update({ mutuelle_dossier: e.target.checked })}
            />
            Dossier
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: COL_BRUN }}>
            <input
              type="checkbox"
              checked={data.mutuelle_rib}
              onChange={(e) => update({ mutuelle_rib: e.target.checked })}
            />
            RIB
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: COL_BRUN }}>
            <input
              type="checkbox"
              checked={data.mutuelle_att_ss}
              onChange={(e) => update({ mutuelle_att_ss: e.target.checked })}
            />
            Att. Sécu. Sociale
          </label>
        </div>

        <div className="mt-5 pt-4 border-t" style={{ borderColor: COL_BORDER }}>
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-md text-white text-sm font-medium disabled:opacity-60"
            style={{ backgroundColor: COL_PRIMARY }}
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Enregistrer
          </button>
        </div>
      </Card>
    </div>
  )
}

// ============================================================================
// Plan 2 - Codes partenaires (placeholder V2)
// ============================================================================

interface PartenairePortail {
  id_partenaire: string
  lib_partenaire: string
}

interface CodeFait {
  id_partenaire: string
  lib_partenaire: string
  code: string
  login: string
  mdp: string
}

function CodesPlan2({
  savedId,
  idTicket,
  data,
  navigate,
}: {
  savedId: string
  idTicket: string
  data: DpaePayload
  navigate: (path: string) => void
}) {
  const [partenaires, setPartenaires] = useState<PartenairePortail[]>([])
  const [selPartId, setSelPartId] = useState('')
  const [portail, setPortail] = useState({
    lien: '',
    login: '',
    mdp: '',
  })
  const [societe, setSociete] = useState({ raison_sociale: '', siret: '' })
  const [extInstalled, setExtInstalled] = useState<boolean | null>(null)
  const [dpaeNum, setDpaeNum] = useState('')
  const [code, setCode] = useState('')
  const [login2, setLogin2] = useState('')
  const [mdp2, setMdp2] = useState('')
  const [elemsFaits, setElemsFaits] = useState<CodeFait[]>([])
  const [busy, setBusy] = useState(false)

  const selPart = partenaires.find((p) => p.id_partenaire === selPartId)
  const libUpper = (selPart?.lib_partenaire || '').toUpperCase()
  const isUrssaf = libUpper === 'URSSAF'
  const isIag = libUpper === 'IAG'
  const isOhm = libUpper.includes('OHM')

  // Init : charge la combo + les codes deja saisis
  useEffect(() => {
    fetch('/api/adm/dpae/partenaires-portail', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: PartenairePortail[]) => {
        setPartenaires(d)
        if (d.length > 0) setSelPartId(d[0].id_partenaire)
      })
    fetch(`/api/adm/dpae/codes/${savedId}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setElemsFaits)
    // Societe d'embauche du salarie (SIRET = login URSSAF cf. WinDev)
    fetch(`/api/adm/dpae/societe-salarie/${savedId}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: { raison_sociale?: string; siret?: string }) =>
        setSociete({
          raison_sociale: d.raison_sociale || '',
          siret: d.siret || '',
        }),
      )
    // Detection de l'extension Omaya DPAE Filler (ping/pong)
    isExtensionInstalled().then(setExtInstalled)
  }, [savedId])

  // Quand on change de partenaire : charge le portail
  useEffect(() => {
    if (!selPartId) return
    setCode('')
    setLogin2('')
    setMdp2('')
    fetch(`/api/adm/dpae/partenaire-portail/${selPartId}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: { lien_portail?: string; login?: string; mdp?: string }) =>
        setPortail({
          lien: d.lien_portail || '',
          login: d.login || '',
          mdp: d.mdp || '',
        }),
      )
  }, [selPartId])

  const reloadFaits = () =>
    fetch(`/api/adm/dpae/codes/${savedId}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setElemsFaits)

  const envoyerSmsCandidat = async () => {
    if (!selPart) return
    await fetch(`/api/adm/dpae/envoyer-infos/${savedId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({
        id_partenaire: Number(selPartId),
        lib_partenaire: selPart.lib_partenaire,
        code,
        login: login2,
        mdp: mdp2,
        dpae_num: dpaeNum,
      }),
    })
  }

  const validerUrssaf = async () => {
    if (!dpaeNum.trim()) {
      showToast('Saisis le N° DPAE.', 'info')
      return
    }
    setBusy(true)
    try {
      const r = await fetch(`/api/adm/dpae/urssaf/${savedId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ dpae_num: dpaeNum.trim() }),
      })
      if (!r.ok) throw new Error(String(r.status))
      await envoyerSmsCandidat()
      await reloadFaits()
      showToast('URSSAF validée + SMS envoyé.', 'success')
    } catch (e) {
      showToast(`Échec URSSAF : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const validerCodes = async () => {
    if (!selPartId) return
    setBusy(true)
    try {
      const r = await fetch(`/api/adm/dpae/codes/${savedId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_partenaire: Number(selPartId),
          code,
          login: login2,
          mdp: mdp2,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      await envoyerSmsCandidat()
      await reloadFaits()
      showToast('Codes validés + SMS envoyé.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const envoyerCharte = async () => {
    if (!selPartId) return
    setBusy(true)
    try {
      const r = await fetch(`/api/adm/dpae/charte-ethique/${savedId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ id_partenaire: Number(selPartId) }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Demande de code envoyée (ticket BO créé).', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const terminerDpae = async () => {
    setBusy(true)
    try {
      const r = await fetch(`/api/adm/dpae/terminer/${savedId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ id_ticket: idTicket ? Number(idTicket) : 0 }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('DPAE terminée. Ouverture de la fiche salarié...', 'success')
      navigate(`/salaries/registre`)
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const ouvrirPortail = () => {
    if (portail.lien) window.open(portail.lien, '_blank', 'noopener')
  }

  // Resout la cle partenaire pour l'extension (matche FILLERS dans
  // content-portail.js). On utilise des aliases sur le libelle.
  const extKey = (() => {
    const u = libUpper
    if (u === 'URSSAF') return 'urssaf'
    if (u === 'IAG') return 'iag'
    if (u === 'SFR') return 'sfr'
    if (u === 'ENI') return 'eni'
    if (u.includes('PLENITUDE')) return 'plenitude'
    if (u.includes('OHM')) return 'ohm'
    return ''
  })()

  const remplirPortail = async () => {
    if (!extKey) {
      showToast('Aucun mapping de remplissage pour ce partenaire.', 'info')
      return
    }
    if (extInstalled === false) {
      showToast(
        "L'extension Omaya DPAE Filler n'est pas installée. Voir browser-extension/omaya-dpae/README.md",
        'error',
      )
      return
    }
    const fillData = {
      siret: societe.siret,
      login: isUrssaf ? societe.siret : portail.login,
      mdp: portail.mdp,
      nom: data.nom,
      prenom: data.prenom,
      date_naiss: data.date_naiss,
      adresse: data.adresse1,
      cp: data.cp,
      ville: data.ville,
      tel_mob: data.tel_mob,
      mail: data.mail,
    }
    const res = await fillPartenaire(extKey, fillData)
    if (res.ok) {
      showToast(`Formulaire rempli (${res.tabs} onglet(s)).`, 'success')
    } else if (res.tabs === 0) {
      showToast(
        "Aucun onglet partenaire ouvert. Clique d'abord sur 'Ouvrir dans un nouvel onglet'.",
        'info',
      )
    } else {
      showToast(`Échec remplissage : ${res.error || 'inconnu'}`, 'error')
    }
  }

  // Infos salarie pour le copy/paste manuel vers le portail
  const infosSalarie =
    `${data.nom} ${data.prenom}\n` +
    `${data.adresse1}${data.adresse2 ? ' ' + data.adresse2 : ''}\n` +
    `${data.cp} ${data.ville}\n` +
    `${data.tel_mob}${data.mail ? '  ' + data.mail : ''}\n` +
    (data.date_naiss
      ? `Né(e) le ${data.date_naiss.slice(8, 10)}/${data.date_naiss.slice(5, 7)}/${data.date_naiss.slice(0, 4)}\n`
      : '') +
    (data.lieu_naiss ? `à ${data.lieu_naiss}\n` : '') +
    `${data.num_ss}${data.sexe ? '  Sexe : ' + data.sexe : ''}`

  return (
    <div className="grid grid-cols-[420px_1fr] gap-4">
      {/* Col 1 : forms + faits */}
      <div className="space-y-4">
        <Card title="Portail partenaire">
          <Field label="Société">
            <input
              type="text"
              value={
                societe.raison_sociale
                  ? societe.siret
                    ? `${societe.raison_sociale} (${societe.siret})`
                    : societe.raison_sociale
                  : ''
              }
              readOnly
              className={inputCls}
            />
          </Field>
          <Field label="Partenaire">
            <select
              value={selPartId}
              onChange={(e) => setSelPartId(e.target.value)}
              className={inputCls}
            >
              {partenaires.map((p) => (
                <option key={p.id_partenaire} value={p.id_partenaire}>
                  {p.lib_partenaire}
                </option>
              ))}
            </select>
          </Field>
          <Field label={isUrssaf ? 'Login (SIRET société)' : 'Login (portail)'}>
            <input
              type="text"
              value={isUrssaf ? societe.siret : portail.login}
              readOnly
              className={inputCls}
            />
          </Field>
          <Field label="MDP (portail)">
            <input
              type="text"
              value={portail.mdp}
              readOnly
              className={inputCls}
            />
          </Field>
          <button
            type="button"
            onClick={ouvrirPortail}
            disabled={!portail.lien}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-white text-sm disabled:opacity-50"
            style={{ backgroundColor: COL_PRIMARY }}
            title="Ouvre le portail dans un nouvel onglet (utile si le portail bloque l'embed iframe)"
          >
            <ExternalLink className="w-4 h-4" />
            Ouvrir dans un nouvel onglet
          </button>
          {extKey && (
            <button
              type="button"
              onClick={remplirPortail}
              disabled={extInstalled === false}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm border disabled:opacity-50"
              style={{
                borderColor: COL_PRIMARY,
                color: COL_PRIMARY,
              }}
              title="Nécessite l'extension Omaya DPAE Filler"
            >
              Remplir le formulaire (extension)
            </button>
          )}
          {extInstalled === false && (
            <p
              className="text-xs italic mt-1 p-2 rounded"
              style={{ backgroundColor: '#FEF3C7', color: '#92400E' }}
            >
              ⚠ Pour le remplissage auto, installe l'extension navigateur
              Omaya DPAE Filler. Voir <code>browser-extension/omaya-dpae/README.md</code>.
            </p>
          )}
        </Card>

        <Card
          title={
            isUrssaf
              ? 'Validation URSSAF'
              : isOhm
                ? 'Demande Ohm Énergie'
                : 'Codes partenaire'
          }
        >
          {isUrssaf ? (
            <>
              <Field label="N° DPAE">
                <input
                  type="text"
                  value={dpaeNum}
                  onChange={(e) => setDpaeNum(e.target.value)}
                  className={inputCls}
                />
              </Field>
              <button
                type="button"
                onClick={validerUrssaf}
                disabled={busy}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-white text-sm disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}
              >
                {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                Valider les infos URSSAF
              </button>
            </>
          ) : isOhm ? (
            <>
              <p className="text-xs italic mb-2" style={{ color: COL_BRUN }}>
                Crée une demande de code Ohm Énergie (ticket BO) à transmettre
                au service partenaires.
              </p>
              <button
                type="button"
                onClick={envoyerCharte}
                disabled={busy}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-white text-sm disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}
              >
                {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                Envoyer la charte éthique
              </button>
            </>
          ) : (
            <>
              <Field label="Code">
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className={inputCls}
                />
              </Field>
              <Field label="Login">
                <input
                  type="text"
                  value={login2}
                  onChange={(e) => setLogin2(e.target.value)}
                  className={inputCls}
                />
              </Field>
              <Field label="MDP">
                <input
                  type="text"
                  value={mdp2}
                  onChange={(e) => setMdp2(e.target.value)}
                  className={inputCls}
                />
              </Field>
              {isIag && (
                <p className="text-xs italic" style={{ color: COL_BRUN }}>
                  Remplis le formulaire IAG côté portail puis renseigne ici
                  le code et le login pour l'enregistrement local.
                </p>
              )}
              <button
                type="button"
                onClick={validerCodes}
                disabled={busy}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-white text-sm disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}
              >
                {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                Valider les codes Partenaires
              </button>
            </>
          )}
        </Card>

        <Card title="Infos salarié (à copier/coller)">
          <textarea
            readOnly
            value={infosSalarie}
            rows={7}
            className="w-full p-2 border rounded text-xs font-mono resize-none"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          />
        </Card>

        <Card title="Éléments faits">
          {elemsFaits.length === 0 ? (
            <p className="text-xs italic" style={{ color: COL_BRUN }}>
              Aucun partenaire validé pour l'instant.
            </p>
          ) : (
            <ul className="space-y-1.5 text-sm">
              {elemsFaits.map((e, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 p-2 rounded"
                  style={{ backgroundColor: COL_BG_SOFT, color: COL_BRUN }}
                >
                  <span style={{ color: '#16a34a' }}>✓</span>
                  <div className="flex-1">
                    <div className="font-semibold">{e.lib_partenaire}</div>
                    {(e.code || e.login) && (
                      <div className="text-xs opacity-75">
                        {e.code && `Code ${e.code}`}
                        {e.code && e.login && ' · '}
                        {e.login && `Login ${e.login}`}
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div
            className="mt-4 pt-3 border-t"
            style={{ borderColor: COL_BORDER }}
          >
            <button
              type="button"
              onClick={terminerDpae}
              disabled={busy}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-md text-white text-sm font-medium disabled:opacity-50"
              style={{ backgroundColor: COL_PRIMARY }}
            >
              {busy && <Loader2 className="w-4 h-4 animate-spin" />}
              Terminer ma DPAE
            </button>
          </div>
        </Card>
      </div>

      {/* Col 2 : iframe du portail (peut etre refuse par X-Frame-Options) */}
      <div
        className="bg-white rounded-lg shadow-sm border flex flex-col"
        style={{ borderColor: COL_BORDER, minHeight: '85vh' }}
      >
        <div
          className="flex items-center gap-2 px-3 py-2 border-b text-xs"
          style={{ borderColor: COL_BORDER, color: COL_BRUN }}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span className="font-mono truncate flex-1">
            {portail.lien || 'Aucun lien'}
          </span>
        </div>
        {portail.lien ? (
          <iframe
            src={portail.lien}
            title="Portail partenaire"
            className="flex-1 w-full"
            style={{ border: 'none', minHeight: '80vh' }}
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-top-navigation"
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm italic text-[#A68D8A]">
            Sélectionne un partenaire pour charger son portail.
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// UI helpers
// ============================================================================

const inputCls =
  'w-full px-2 py-1.5 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-[#17494E]'

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="bg-white rounded-lg shadow-sm p-4 border space-y-2.5"
      style={{ borderColor: COL_BORDER }}
    >
      <h2 className="text-sm font-bold uppercase tracking-wide" style={{ color: COL_BRUN }}>
        {title}
      </h2>
      {children}
    </div>
  )
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
    <div className={wide ? 'col-span-2' : ''}>
      <label className="block text-xs mb-0.5" style={{ color: COL_BRUN }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function Section({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="mt-3 pt-3 border-t text-xs font-bold uppercase tracking-wide"
      style={{ borderColor: COL_BORDER, color: COL_BRUN }}
    >
      {children}
    </div>
  )
}

function RadioCiv({
  value,
  onChange,
}: {
  value: number
  onChange: (v: number) => void
}) {
  // Glissiere M./Mme (memes styles que CiviliteToggle de FicheSalarieModal)
  return (
    <div
      className="flex items-center rounded overflow-hidden w-full"
      style={{ border: `1px solid ${COL_BORDER}` }}
    >
      {[
        { v: 1, l: 'M.' },
        { v: 2, l: 'Mme' },
      ].map((o) => {
        const active = value === o.v
        return (
          <button
            key={o.v}
            type="button"
            onClick={() => onChange(o.v)}
            className="flex-1 px-4 py-1.5 text-sm transition"
            style={{
              backgroundColor: active ? COL_PRIMARY : 'white',
              color: active ? 'white' : COL_BRUN,
              fontWeight: active ? 600 : 400,
            }}
          >
            {o.l}
          </button>
        )
      })}
    </div>
  )
}
