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
  type_dpae: number
  id_elem: number
  id_cv_suivi: number
  id_ticket: number
  id_cvtheque: number

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

  idorganigramme: number
  id_ste: number
  id_type_poste: number
  id_type_ctt: number
  id_type_horaire: number
  date_debut: string

  coopte: boolean
  coopteur: number
  jodirecte: boolean
  jo_coopteur: number

  id_mutuelle: number
  adhesion: boolean
  adhesion_date: string
  mutuelle_dossier: boolean
  mutuelle_att_ss: boolean
  mutuelle_rib: boolean
}

const EMPTY_PAYLOAD: DpaePayload = {
  type_dpae: 0,
  id_elem: 0,
  id_cv_suivi: 0,
  id_ticket: 0,
  id_cvtheque: 0,
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
  idorganigramme: 0,
  id_ste: 0,
  id_type_poste: 0,
  id_type_ctt: 1,
  id_type_horaire: 1,
  date_debut: '',
  coopte: false,
  coopteur: 0,
  jodirecte: false,
  jo_coopteur: 0,
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

  const idTicket = Number(params.get('id_ticket') || '0')
  const typeDpae = Number(params.get('type_dpae') || '0')
  const idElem = Number(params.get('id_elem') || '0')
  const idCvSuivi = Number(params.get('id_cv_suivi') || '0')

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
        const pr = (await prR.json()) as Partial<DpaePayload>
        setLookups(lk)
        // Auto-selection de la mutuelle active
        const activeMut = lk.mutuelles.find((m) => m.is_actif)
        const merged: DpaePayload = {
          ...EMPTY_PAYLOAD,
          ...pr,
          type_dpae: typeDpae,
          id_elem: idElem,
          id_cv_suivi: idCvSuivi,
          id_ticket: idTicket,
          id_mutuelle:
            (pr as DpaePayload).id_mutuelle ||
            (activeMut ? activeMut.id_mutuelle : 0),
        }
        setData(merged)
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
        throw new Error((j as { detail?: string })?.detail || String(r.status))
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
        <CodesPlan2 savedId={savedId} navigate={navigate} />
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
            update({ idorganigramme: Number(it.id) })
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
            update({ coopteur: Number(it.id) })
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
            update({ jo_coopteur: Number(it.id) })
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

        {data.id_cvtheque > 0 && (
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
            onChange={(e) => update({ id_ste: Number(e.target.value) })}
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
        {data.jodirecte && data.jo_coopteur === 0 && (
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

function CodesPlan2({
  savedId,
  navigate,
}: {
  savedId: string
  navigate: (path: string) => void
}) {
  return (
    <div
      className="bg-white rounded-lg shadow-sm p-6 border"
      style={{ borderColor: COL_BORDER }}
    >
      <p className="text-sm mb-3" style={{ color: COL_BRUN }}>
        Le salarié <strong>#{savedId}</strong> a été créé. Le Plan 2 (ajout
        des codes partenaires URSSAF / IAG / SFR / ENI / etc., envoi mail/SMS
        au candidat, charte éthique Ohm, Terminer ma DPAE) sera implémenté en
        V2.
      </p>
      <p className="text-xs italic mb-4" style={{ color: COL_BRUN }}>
        Tu peux dès à présent consulter la fiche salarié et compléter les
        codes manuellement.
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => navigate(`/salaries/registre`)}
          className="px-4 py-2 rounded-md text-white text-sm"
          style={{ backgroundColor: COL_PRIMARY }}
        >
          Retour au Registre RH
        </button>
        <button
          type="button"
          onClick={() => navigate('/salaries/dpae')}
          className="px-4 py-2 border rounded-md text-sm hover:bg-[#EFE9E7]"
          style={{ borderColor: COL_BORDER, color: COL_BRUN }}
        >
          Nouvelle DPAE
        </button>
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
