import { useCallback, useEffect, useState } from 'react'
import {
  FileText, Loader2, RefreshCw, Save, Trash2, Users,
} from 'lucide-react'

import type { FIProps } from './index'
import SearchPicker from './SearchPicker'
import { showConfirm, showToast } from '../../ui/dialog'

// FI_DPAEDistrib (types 29 Nouveau Vendeur Distrib + 30 Intégration Distrib).
export default function FIDPAEDistrib({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [pickEquipe, setPickEquipe] = useState(false)

  // Champs éditables
  const [civilite, setCivilite] = useState(1)
  const [nom, setNom] = useState('')
  const [nomMarital, setNomMarital] = useState('')
  const [prenom, setPrenom] = useState('')
  const [dateNaiss, setDateNaiss] = useState('')
  const [adresse, setAdresse] = useState('')
  const [cp, setCp] = useState('')
  const [ville, setVille] = useState('')
  const [gsm, setGsm] = useState('')
  const [mail, setMail] = useState('')
  const [produits, setProduits] = useState<boolean[]>([])
  const [idEquipe, setIdEquipe] = useState('')
  const [equipeLabel, setEquipeLabel] = useState('')
  const [idPartenaire, setIdPartenaire] = useState('')

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const dd = d?.data?.found ? d.data : null
        setData(dd)
        if (dd) {
          setCivilite(Number(dd.civilite || 1))
          setNom(dd.nom || '')
          setNomMarital(dd.nom_marital || '')
          setPrenom(dd.prenom || '')
          setDateNaiss(dd.date_naiss || '')
          setAdresse(dd.adresse || '')
          setCp(dd.cp || '')
          setVille(dd.ville || '')
          setGsm(dd.gsm || '')
          setMail(dd.mail || '')
          setProduits((dd.produits || []).map((p: any) => !!p.actif))
          setIdEquipe(dd.id_equipe || '')
          setEquipeLabel(dd.equipe_label || '')
        }
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, idTicket])

  useEffect(() => {
    reload()
  }, [reload])

  const post = async (body: any): Promise<any> => {
    setSaving(true)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(body),
      })
      const j = await resp.json().catch(() => null)
      if (!resp.ok) {
        showToast(`Erreur : ${j?.detail || resp.status}`, 'error')
        return null
      }
      return j ?? {}
    } catch {
      showToast('Erreur réseau.', 'error')
      return null
    } finally {
      setSaving(false)
    }
  }

  const openDoc = async (nomFichier: string) => {
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(nomFichier)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!resp.ok) {
        showToast('Document introuvable.', 'error')
        return
      }
      const blob = await resp.blob()
      window.open(URL.createObjectURL(blob), '_blank')
    } catch {
      showToast('Erreur réseau (document).', 'error')
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }
  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
        Aucune demande d'intégration distrib pour ce ticket.
      </div>
    )
  }

  const documents: any[] = data.documents || []
  const demandesCode: any[] = data.demandes_code || []
  const partenaires: any[] = data.partenaires || []
  const noms: string[] = (data.produits || []).map((p: any) => p.nom)
  const fmtDate = (iso: string) => {
    if (!iso) return ''
    const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/)
    return m ? `${m[3]}/${m[2]}/${m[1]}` : iso
  }

  const enregistrer = async () => {
    const r = await post({
      action: 'enregistrer',
      civilite, nom, nom_marital: nomMarital, prenom,
      date_naiss: dateNaiss, adresse, cp, ville, gsm, mail,
      produits, id_equipe: idEquipe,
    })
    if (r) showToast('Informations enregistrées', 'success')
  }

  // Cf. WinDev cas TypeDpae=4 : ouvre directement Fen_DPAE_Nouvelle
  // (pas de recherche, la fiche distributeur est unique). Navigation
  // absolue vers /adm car le module DPAE = ADM only.
  const convertirEnSalarie = () => {
    const url = new URL('/adm/salaries/dpae/nouvelle', window.location.origin)
    url.searchParams.set('id_ticket', String(idTicket))
    url.searchParams.set('type_dpae', '4')
    url.searchParams.set('id_elem', '0')
    url.searchParams.set('id_cv_suivi', '0')
    window.location.href = url.toString()
  }

  const docNonConforme = async (idDoc: string) => {
    if (
      !(await showConfirm({
        message:
          'Vous êtes sur le point de supprimer ce document pour non-conformité.\n' +
          'Le candidat recevra un SMS. Continuer ?',
        confirmLabel: 'Supprimer',
        variant: 'danger',
      }))
    )
      return
    const r = await post({ action: 'doc_non_conforme', id_doc: idDoc })
    if (r) {
      setData((d: any) => ({ ...d, documents: r.documents || d.documents }))
      if (r.sms_result) showToast('SMS : ' + r.sms_result, 'success')
    }
  }

  const champ = (
    label: string,
    value: string,
    setter: (v: string) => void,
    type = 'text',
  ) => (
    <label className="block text-sm">
      <span className="text-c-ink-soft">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => setter(e.target.value)}
        className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
      />
    </label>
  )

  return (
    <div className="space-y-4">
      {/* INFOS ÉTAT CIVIL */}
      <div>
        <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide mb-2">
          Infos état civil
        </h3>
        <div className="flex gap-1 mb-2">
          {[[1, 'M.'], [2, 'Mme']].map(([v, lib]) => (
            <button
              key={v as number}
              onClick={() => setCivilite(v as number)}
              className={
                'px-3 py-1 rounded-md text-sm border ' +
                (civilite === v
                  ? 'bg-c-brand text-white border-c-brand'
                  : 'border-c-line-strong text-c-ink hover:bg-c-surface-soft')
              }
            >
              {lib}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3">
          {champ('Nom', nom, setNom)}
          {champ('Époux(se)', nomMarital, setNomMarital)}
          {champ('Prénom', prenom, setPrenom)}
          {champ('Né(e) le', dateNaiss, setDateNaiss, 'date')}
        </div>
      </div>

      {/* COORDONNÉES */}
      <div className="border-t border-c-line pt-3">
        <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide mb-2">
          Coordonnées postales et téléphoniques
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">{champ('Adresse', adresse, setAdresse)}</div>
          {champ('CP', cp, setCp)}
          {champ('Ville', ville, setVille)}
          {champ('Mobile', gsm, setGsm)}
          {champ('Mail', mail, setMail, 'email')}
        </div>
      </div>

      {/* Produits proposés */}
      <div className="border-t border-c-line pt-3">
        <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide mb-2">
          Produits proposés
        </h3>
        <div className="flex flex-wrap gap-3">
          {noms.map((n, i) => (
            <label key={n} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={!!produits[i]}
                onChange={(e) =>
                  setProduits((prev) => {
                    const copy = [...prev]
                    copy[i] = e.target.checked
                    return copy
                  })
                }
              />
              {n}
            </label>
          ))}
        </div>
      </div>

      {/* Équipe */}
      <div className="border-t border-c-line pt-3">
        <button
          onClick={() => setPickEquipe(true)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm hover:bg-c-brand-soft"
        >
          <Users className="w-4 h-4 text-c-brand" />
          {equipeLabel || "Choisir l'équipe"}
        </button>
      </div>

      {/* Partenaire + Générer code (bouton Générer = TODO) */}
      <div className="border-t border-c-line pt-3">
        <div className="flex items-center gap-2">
          <select
            value={idPartenaire}
            onChange={(e) => setIdPartenaire(e.target.value)}
            className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
          >
            <option value="">--- Choisir un partenaire ---</option>
            {partenaires.map((p) => (
              <option key={p.id} value={p.id}>
                {p.lib}
              </option>
            ))}
          </select>
          <button
            disabled
            title="À venir (génération du ticket Demande de Code, type 38)"
            className="px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold opacity-50 cursor-not-allowed"
          >
            Générer Tk Demande de Code
          </button>
        </div>
        {demandesCode.length > 0 && (
          <div className="border border-c-line rounded-lg overflow-auto mt-2">
            <table className="w-full text-sm">
              <thead className="bg-c-surface-soft text-c-ink-soft text-left">
                <tr>
                  <th className="px-2 py-2">Partenaire</th>
                  <th className="px-2 py-2">Statut</th>
                  <th className="px-2 py-2 w-32">Date</th>
                </tr>
              </thead>
              <tbody>
                {demandesCode.map((d, i) => (
                  <tr key={i} className="border-t border-c-line">
                    <td className="px-2 py-1.5">{d.partenaire}</td>
                    <td className="px-2 py-1.5">{d.statut}</td>
                    <td className="px-2 py-1.5">{fmtDate(d.date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Enregistrer + Convertir */}
      <div className="flex flex-col gap-2 border-t border-c-line pt-3">
        <button
          onClick={enregistrer}
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          Enregistrer le ticket
        </button>
        <button
          onClick={convertirEnSalarie}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand-strong text-white text-sm font-semibold hover:brightness-110 transition-all"
        >
          <FileText className="w-4 h-4" />
          Convertir en fiche salarié
        </button>
      </div>

      {/* Documents */}
      <div className="border-t border-c-line pt-3">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide flex-1">
            Documents
          </h3>
          <button
            onClick={reload}
            className="flex items-center gap-1 text-xs text-c-brand hover:underline"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Actualiser
          </button>
        </div>
        <div className="border border-c-line rounded-lg overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft text-c-ink-soft text-left">
              <tr>
                <th className="px-2 py-2">Nom</th>
                <th className="px-2 py-2">NomFichier</th>
                <th className="px-2 py-2 w-10" />
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-2 py-3 text-center text-c-ink-faint">
                    Aucun document.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-t border-c-line hover:bg-c-surface-soft"
                  >
                    <td className="px-2 py-1.5">{doc.nom}</td>
                    <td
                      className="px-2 py-1.5 cursor-pointer text-c-brand hover:underline"
                      onClick={() => openDoc(doc.nom_fichier)}
                    >
                      {doc.nom_fichier}
                    </td>
                    <td className="px-2 py-1.5">
                      <button
                        onClick={() => docNonConforme(doc.id)}
                        disabled={saving}
                        title="Document non conforme (suppression + SMS)"
                        className="text-c-ink-faint hover:text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <p className="mt-1 text-[11px] text-c-ink-faint">
          Clique sur un nom de fichier pour l'ouvrir. La corbeille marque le
          document non conforme (suppression + SMS au candidat).
        </p>
      </div>

      {pickEquipe && (
        <SearchPicker
          apiBase={apiBase}
          getToken={getToken}
          title="Choisir l'équipe"
          path="/tickets/organigrammes/search"
          mapItem={(o) => ({ id: o.id_organigramme, label: o.lib_orga })}
          onPick={(it) => {
            setIdEquipe(it.id)
            setEquipeLabel(it.label)
            setPickEquipe(false)
          }}
          onClose={() => setPickEquipe(false)}
        />
      )}
    </div>
  )
}
