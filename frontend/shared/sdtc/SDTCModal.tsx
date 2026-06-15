/**
 * SDTCModal : popup partagee Solde De Tout Compte (transposition Fen_SDTC).
 *
 * Composant utilisable depuis n'importe quel intranet :
 *   <SDTCModal
 *     open={open}
 *     onClose={() => setOpen(false)}
 *     getToken={getToken}
 *     idSalarie="123456"
 *   />
 *
 * Scaffold pour cette etape : chargement des donnees de base + onglet
 * 'Resume' fonctionnel (bloc HTML façon WinDev avec nom / societe /
 * adresse / date naiss / num SS / sortie / mutuelle).
 *
 * Onglets restants en placeholder, branches dans des commits dedies :
 *   - Contrats deja traites (grille selection mois + qte)
 *   - Contrats SDTC (selection + valider)
 *   - Resume Solde de tout compte (NB Pts / Comm Pts / Bareme / Total)
 *   - Contrats a editer pour le salarie (grille)
 *   - Recap Ctts pour le BO (recap par produit)
 */

import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Check, CheckSquare, FileSpreadsheet, FileText, Loader2, Send, Square, Wallet, X } from 'lucide-react'

import SendEmailModal from '../email/SendEmailModal'
import { showToast } from '../ui/dialog'

const COLOR_PRIMARY = '#17494E'
const COLOR_BRUN = '#4E1D17'
const COLOR_BG_SOFT = '#EFE9E7'

interface SalarieInfo {
  civilite?: number
  nom: string
  prenom: string
  lib_nom: string
  num_ss: string
  date_naiss: string
  lieu_naiss: string
  dep_naiss: string
  adresse1: string
  adresse2: string
  cp: string
  ville: string
  mail?: string
  tel_mob?: string
  tel_fixe?: string
  date_embauche: string
  date_anciennete: string
  date_anciennete_yyyymmdd?: string
  id_ste: string
  lib_societe: string
}

interface SortieInfo {
  date_sortie_reelle: string
  date_sortie_demandee?: string
  lib_sortie_raw: string
  titre_sortie: string
  kind: string
  courrier_info: string
  mail_objet: string
  mail_contenu: string
}

interface SDTCData {
  found: boolean
  id_salarie: string
  salarie: SalarieInfo
  sortie: SortieInfo
  info_mutuelle: string
  date_dernier_ctt: string
  /** Bloc HTML mesInfos genere cote backend avec placeholders
   *  MONTANT_COMM/CP/DECO/AVANCE/NB_TR/DATEABS - cf. WinDev `mesInfos`. */
  info_salarie_html?: string
}

interface ContratItem {
  id_contrat: string
  partenaire: string
  num_bs: string
  info_interne: string
  lib_produit: string
  famille?: string
  sous_fam?: string
  type_prod: string
  date_signature: string
  mois_paiement: string
  id_etat_contrat: number
  etat_contrat_lib: string
  etat_contrat_lib_op?: string
  id_type_etat: number
  type_etat_lib: string
  couleur_fond: string
  nb_points: number
  client_nom: string
  client_adresse: string
  client_cp: string
  client_ville: string
  client_mail: string
  client_gsm: string
  /** Colonnes specifiques SFR (cf. afficherContrat WinDev) */
  sfr?: {
    box8: boolean
    box8_verif: boolean
    id_sfr_cluster: string
    date_portabilite: string
    date_racc_activ: string
    date_rdv_tech: string
    date_resil: string
    date_validation: string
    id_etat_sfr: number
    internet_garanti: boolean
    type_vente: number
    remise: boolean
    self_install: boolean
    technologie: number
  }
  /** Colonnes specifiques ENI */
  eni?: {
    gaz_car_declaree: number
    gaz_car_relevee: number
    elec_puissance: number
    gaz_actif: boolean
    elec_actif: boolean
  }
  /** Colonnes specifiques OEN */
  oen?: {
    gaz_car_relevee: number
    elec_puissance: number
    id_etat_oen: number
  }
}

interface TableEtatRow {
  lib_type: string
  qte: number
}

interface TableValideDecommRow {
  mois_p: string
  mois_aff: string
  partenaire: string
  valides: number
  decomm: number
}

interface ContratsData {
  traites: ContratItem[]
  a_traiter: ContratItem[]
  type_etats: Record<string, { lib_type: string; couleur: string }>
  table_etat?: TableEtatRow[]
  table_valide_decomm?: TableValideDecommRow[]
}

interface ProduitSTC {
  lib_produit: string
  qte: number
  nb_pts: number
  valeur: number
}

interface BaremeResult {
  nb_selectionnes: number
  selection_ids: string[]
  produits: ProduitSTC[]
  nb_tot_pts: number
  nb_tot_ctts: number
  total_valeurs: number
  bareme: number
  comm_pts_ctts: number
  comm_tot_stc: number
}

type Tab =
  | 'resume'
  | 'deja_traites'
  | 'contrats_sdtc'
  | 'resume_stc'
  | 'a_editer'
  | 'recap_bo'

const TABS: { key: Tab; label: string }[] = [
  { key: 'resume',        label: 'Résumé' },
  { key: 'deja_traites',  label: 'Contrats déjà traités' },
  { key: 'contrats_sdtc', label: 'Contrats SDTC' },
  { key: 'resume_stc',    label: 'Résumé Solde de tout compte' },
  { key: 'a_editer',      label: 'Contrats à éditer pour le salarié' },
  { key: 'recap_bo',      label: 'Récap Ctts pour le BO' },
]

interface Props {
  open: boolean
  onClose: () => void
  getToken: () => string | null
  idSalarie: string
}

export default function SDTCModal({ open, onClose, getToken, idSalarie }: Props) {
  const [data, setData] = useState<SDTCData | null>(null)
  const [contrats, setContrats] = useState<ContratsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingContrats, setLoadingContrats] = useState(false)
  const [tab, setTab] = useState<Tab>('resume')
  const [selectedSdtc, setSelectedSdtc] = useState<Set<string>>(new Set())
  const [selectedTraites, setSelectedTraites] = useState<Set<string>>(new Set())
  const [bareme, setBareme] = useState<BaremeResult | null>(null)
  const [computing, setComputing] = useState(false)
  const [mailOpen, setMailOpen] = useState(false)
  const [mailPj, setMailPj] = useState<
    { name: string; size: number; contentB64: string }[]
  >([])
  const [mailPayload, setMailPayload] = useState<{
    objet: string
    html: string
    a: string[]
    cc: string[]
    expediteur: string
  } | null>(null)
  const [preparingMail, setPreparingMail] = useState(false)
  const [commentaires, setCommentaires] = useState('')
  const [nbTr, setNbTr] = useState(0)
  const [calculatingNbTr, setCalculatingNbTr] = useState(false)
  /** Résultat de /generer-tableau (contrat_tot + recap_prod + recap_prod_pts + nb_tr) */
  const [recapData, setRecapData] = useState<{
    contrat_tot: unknown[]
    recap_prod: { lib_produit: string; en_attente_contrat: number; envoye_chez_ope: number; rejets_bo: number; resiliation: number; valide_paye: number; decommision: number }[]
    recap_prod_pts: { lib_produit: string; en_attente_contrat: number; envoye_chez_ope: number; rejets_bo: number; resiliation: number; valide_paye: number; decommision: number }[]
    nb_tr: number
  } | null>(null)

  useEffect(() => {
    if (!open || !idSalarie) return
    let cancelled = false
    setLoading(true)
    setLoadingContrats(true)
    setData(null)
    setContrats(null)
    setSelectedSdtc(new Set())
    setSelectedTraites(new Set())
    setBareme(null)
    setTab('resume')
    const auth = { Authorization: `Bearer ${getToken()}` }

    fetch(`/api/shared/sdtc/${idSalarie}/load`, { headers: auth })
      .then(async (r) => {
        if (!r.ok) {
          const j = await r.json().catch(() => ({}))
          throw new Error((j as { detail?: string })?.detail || String(r.status))
        }
        return r.json()
      })
      .then((j) => {
        if (cancelled) return
        setData(j as SDTCData)
      })
      .catch((e) => {
        if (cancelled) return
        showToast(`Échec chargement SDTC : ${e?.message || e}`, 'error')
      })
      .finally(() => !cancelled && setLoading(false))

    fetch(`/api/shared/sdtc/${idSalarie}/contrats`, { headers: auth })
      .then(async (r) => {
        if (!r.ok) {
          const j = await r.json().catch(() => ({}))
          throw new Error((j as { detail?: string })?.detail || String(r.status))
        }
        return r.json()
      })
      .then((j) => {
        if (cancelled) return
        setContrats(j as ContratsData)
      })
      .catch((e) => {
        if (cancelled) return
        showToast(`Échec chargement contrats SDTC : ${e?.message || e}`, 'error')
      })
      .finally(() => !cancelled && setLoadingContrats(false))

    return () => {
      cancelled = true
    }
  }, [open, idSalarie, getToken])

  // --- Helpers Mail / XLS / PDF -------------------------------------------

  const fetchAsAttachment = async (
    endpoint: 'xls' | 'pdf',
  ): Promise<{ name: string; size: number; contentB64: string } | null> => {
    if (selectedSdtc.size === 0 && selectedTraites.size === 0) {
      showToast('Aucun contrat sélectionné.', 'error')
      return null
    }
    const body: Record<string, unknown> = {
      contrat_ids_traites: Array.from(selectedTraites),
      contrat_ids_sdtc: Array.from(selectedSdtc),
    }
    if (endpoint === 'pdf') {
      body.commentaires = commentaires
      body.nb_tr = nbTr || 0
    }
    const r = await fetch(`/api/shared/sdtc/${idSalarie}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      const j = await r.json().catch(() => ({}))
      throw new Error((j as { detail?: string })?.detail || String(r.status))
    }
    const blob = await r.blob()
    const arrayBuf = await blob.arrayBuffer()
    const bytes = new Uint8Array(arrayBuf)
    let bin = ''
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i])
    const b64 = btoa(bin)
    const lib = (data?.salarie.lib_nom || idSalarie).replace(/\s+/g, '_')
    const ext = endpoint === 'xls' ? 'xlsx' : 'pdf'
    return { name: `SDTC_${lib}.${ext}`, size: bytes.length, contentB64: b64 }
  }

  const triggerDownload = (
    pj: { name: string; contentB64: string },
    mime: string,
  ) => {
    const bin = atob(pj.contentB64)
    const arr = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i)
    const blob = new Blob([arr], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = pj.name
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDownloadXls = async () => {
    try {
      const pj = await fetchAsAttachment('xls')
      if (!pj) return
      triggerDownload(
        pj,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      )
    } catch (e) {
      showToast(`Échec génération XLS : ${(e as Error).message}`, 'error')
    }
  }

  const handleDownloadPdf = async () => {
    try {
      const pj = await fetchAsAttachment('pdf')
      if (!pj) return
      triggerDownload(pj, 'application/pdf')
    } catch (e) {
      showToast(`Échec génération PDF : ${(e as Error).message}`, 'error')
    }
  }

  const handleCalculNbTrAuto = async () => {
    if (!data) return
    setCalculatingNbTr(true)
    try {
      // Date de reference = date_dernier_ctt ou date_embauche par defaut
      const dateRef = data.date_dernier_ctt || data.salarie.date_embauche || ''
      const r = await fetch(
        `/api/shared/sdtc/${idSalarie}/generer-tableau`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            contrat_ids_traites: Array.from(selectedTraites),
            contrat_ids_a_traiter: Array.from(selectedSdtc),
            date_ref: dateRef,
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as {
        contrat_tot: unknown[]
        recap_prod: typeof recapData extends { recap_prod: infer R } ? R : never[]
        recap_prod_pts: typeof recapData extends { recap_prod_pts: infer R } ? R : never[]
        nb_tr: number
      }
      setRecapData(j as typeof recapData)
      setNbTr(j.nb_tr || 0)
      showToast(
        `NB_TR calculé : ${j.nb_tr} jour(s) travaillé(s) depuis ${dateRef.slice(0, 10) || '?'}`,
        'success',
      )
    } catch (e) {
      showToast(`Échec calcul NB_TR : ${(e as Error).message}`, 'error')
    } finally {
      setCalculatingNbTr(false)
    }
  }

  const handleOpenMailSdtc = async () => {
    if (!data) return
    setPreparingMail(true)
    try {
      // 1) Prepare-mail (substitue placeholders + sauvegarde + payload)
      const idsTraites = Array.from(selectedTraites)
      const idsSdtc = Array.from(selectedSdtc)
      const prep = await fetch(
        `/api/shared/sdtc/${idSalarie}/prepare-mail`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            contrat_ids_traites: idsTraites,
            contrat_ids_a_traiter: idsSdtc,
            nb_tr: nbTr,
            deco: 0,
            avance: 0,
          }),
        },
      )
      if (!prep.ok) {
        const j = await prep.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(prep.status))
      }
      const mailPayload = await prep.json() as {
        objet: string
        html: string
        a: string[]
        cc: string[]
        expediteur: string
      }
      // Stocke pour pre-remplir la modal email
      setMailPayload(mailPayload)

      // 2) PJ XLS + PDF
      const [xlsPj, pdfPj] = await Promise.all([
        fetchAsAttachment('xls'),
        fetchAsAttachment('pdf'),
      ])
      const pjs = [xlsPj, pdfPj].filter(Boolean) as {
        name: string
        size: number
        contentB64: string
      }[]
      setMailPj(pjs)
      setMailOpen(true)
    } catch (e) {
      showToast(`Échec préparation mail : ${(e as Error).message}`, 'error')
    } finally {
      setPreparingMail(false)
    }
  }

  if (!open) return null

  const sortieInfo = data?.sortie
  // Priorite : payload fraichement prepare (substitue + sauvegarde) > sortieInfo deja stocke > defaut
  const defaultMailSubject = (
    mailPayload?.objet
    || sortieInfo?.mail_objet
    || `Solde de tout compte — ${data?.salarie.lib_nom || ''}`
  )
  const defaultMailHtml = mailPayload?.html || sortieInfo?.mail_contenu || ''
  const defaultMailTo = mailPayload?.a || []
  const defaultMailCc = mailPayload?.cc || []

  return (
    <>
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-[1300px] max-w-[97vw] h-[88vh] flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: COLOR_BG_SOFT }}>
          <div className="flex items-center gap-2">
            <Wallet className="w-5 h-5" style={{ color: COLOR_PRIMARY }} />
            <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
              Solde de tout compte
            </h2>
            {data && (
              <span className="text-sm" style={{ color: COLOR_BRUN }}>
                — {data.salarie.lib_nom}
                {data.salarie.lib_societe && (
                  <span style={{ opacity: 0.7 }}> ({data.salarie.lib_societe})</span>
                )}
              </span>
            )}
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

        {/* Tabs */}
        <div className="flex items-center gap-1 px-3 pt-2 border-b" style={{ borderColor: COLOR_BG_SOFT }}>
          {TABS.map((t) => {
            const active = t.key === tab
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className="px-3 py-1.5 text-sm rounded-t transition"
                style={{
                  color: active ? COLOR_PRIMARY : COLOR_BRUN,
                  backgroundColor: active ? '#ECF1F2' : 'transparent',
                  borderBottom: active ? `2px solid ${COLOR_PRIMARY}` : '2px solid transparent',
                  fontWeight: active ? 600 : 400,
                }}
              >
                {t.label}
              </button>
            )
          })}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading && (
            <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
              <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
            </div>
          )}
          {!loading && data && tab === 'resume' && (
            <ResumeTab contrats={contrats} />
          )}
          {!loading && data && tab === 'deja_traites' && (
            <DejaTraitesTab
              contrats={contrats}
              loading={loadingContrats}
              selected={selectedTraites}
              setSelected={setSelectedTraites}
            />
          )}
          {!loading && data && tab === 'contrats_sdtc' && (
            <ContratsSDTCTab
              contrats={contrats}
              loading={loadingContrats}
              selected={selectedSdtc}
              setSelected={setSelectedSdtc}
              computing={computing}
              onValidate={async () => {
                // Toujours appeler /compute-bareme, meme avec selection
                // vide (backend retournera un bareme a 0).
                setComputing(true)
                try {
                  const r = await fetch(
                    `/api/shared/sdtc/${idSalarie}/compute-bareme`,
                    {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${getToken()}`,
                      },
                      body: JSON.stringify({
                        contrat_ids: Array.from(selectedSdtc),
                      }),
                    },
                  )
                  if (!r.ok) {
                    const j = await r.json().catch(() => ({}))
                    throw new Error(
                      (j as { detail?: string })?.detail || String(r.status),
                    )
                  }
                  const j = (await r.json()) as BaremeResult
                  setBareme(j)
                  setTab('resume_stc')
                  showToast(
                    `${j.nb_selectionnes} contrat(s) — ${j.comm_tot_stc.toFixed(2)} €`,
                    'success',
                  )
                } catch (e) {
                  showToast(
                    `Échec calcul barème : ${(e as Error).message}`,
                    'error',
                  )
                } finally {
                  setComputing(false)
                }
              }}
            />
          )}
          {!loading && data && tab === 'resume_stc' && (
            <ResumeSTCTab
              bareme={bareme}
              onGoToSelection={() => setTab('contrats_sdtc')}
              onDownloadXls={handleDownloadXls}
              onDownloadPdf={handleDownloadPdf}
              onMailSdtc={handleOpenMailSdtc}
              preparingMail={preparingMail}
              commentaires={commentaires}
              setCommentaires={setCommentaires}
              nbTr={nbTr}
              setNbTr={setNbTr}
              infoSalarieHtml={data?.info_salarie_html}
              onCalcNbTr={handleCalculNbTrAuto}
              calculatingNbTr={calculatingNbTr}
            />
          )}
          {!loading && data && tab === 'a_editer' && (
            <AEditerTab
              contrats={contrats}
              selectedTraites={selectedTraites}
              selectedSdtc={selectedSdtc}
              computing={computing}
              onRecalculate={async () => {
                if (selectedSdtc.size === 0) {
                  showToast('Aucun contrat SDTC sélectionné', 'info')
                  return
                }
                setComputing(true)
                try {
                  const r = await fetch(
                    `/api/shared/sdtc/${idSalarie}/compute-bareme`,
                    {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${getToken()}`,
                      },
                      body: JSON.stringify({
                        contrat_ids: Array.from(selectedSdtc),
                      }),
                    },
                  )
                  if (!r.ok) {
                    const j = await r.json().catch(() => ({}))
                    throw new Error(
                      (j as { detail?: string })?.detail || String(r.status),
                    )
                  }
                  const j = (await r.json()) as BaremeResult
                  setBareme(j)
                  showToast(
                    `STC recalculé : ${j.comm_tot_stc.toFixed(2)} €`,
                    'success',
                  )
                } catch (e) {
                  showToast(
                    `Échec recalcul STC : ${(e as Error).message}`,
                    'error',
                  )
                } finally {
                  setComputing(false)
                }
              }}
            />
          )}
          {!loading && data && tab === 'recap_bo' && (
            <RecapBOTab
              contrats={contrats}
              selectedTraites={selectedTraites}
              selectedSdtc={selectedSdtc}
              backendRecap={recapData}
              onCalcRecap={handleCalculNbTrAuto}
              calculating={calculatingNbTr}
            />
          )}
        </div>
      </motion.div>
    </motion.div>
    <SendEmailModal
      open={mailOpen}
      onClose={() => setMailOpen(false)}
      getToken={getToken}
      expediteur={mailPayload?.expediteur || 'fpe@exosphere.fr'}
      to={defaultMailTo.length > 0 ? defaultMailTo : ['service_paie@cneidf.cerfrance.fr']}
      cc={defaultMailCc.length > 0 ? defaultMailCc : ['a.dubois@exosphere.fr', 'm.doineau@exosphere.fr', 'fpe@exosphere.fr']}
      subject={defaultMailSubject}
      html={defaultMailHtml}
      initialAttachments={mailPj}
    />
    </>
  )
}

// --- Onglet "Resume" ----------------------------------------------------

function ResumeTab({
  contrats,
}: {
  contrats: ContratsData | null
}) {
  // Cf. WinDev onglet 'Résumé' : 2 tableaux côte à côte
  //   1. TableEtat : Etat / QTE (compteur par type d'état)
  //   2. TableValidéDécomm : Mois Paiement / Partenaire / Validés / Décomm
  // (cf. agréges retournés par /contrats : table_etat + table_valide_decomm)
  const tableEtat = contrats?.table_etat || []
  const tableVD = contrats?.table_valide_decomm || []

  // Couleurs RVB par type d'état (cf. pgt_type_etat_contrat)
  const colorByEtat: Record<string, string> = {}
  for (const [, meta] of Object.entries(contrats?.type_etats || {})) {
    colorByEtat[meta.lib_type] = meta.couleur
  }

  if (!contrats) {
    return (
      <div className="flex items-center gap-2 text-sm p-4" style={{ color: COLOR_BRUN }}>
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement des contrats…
      </div>
    )
  }

  return (
    <div className="grid grid-cols-[260px_1fr] gap-4 h-full">
      {/* TableEtat : compteur par type d'état */}
      <div
        className="flex flex-col rounded-lg border overflow-hidden"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
      >
        <div
          className="grid items-center px-3 py-2 text-xs font-semibold border-b text-center"
          style={{
            gridTemplateColumns: '1fr 70px',
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Etat</div>
          <div className="text-right">QTE</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {tableEtat.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun contrat
            </div>
          )}
          {tableEtat.map((r) => (
            <div
              key={r.lib_type}
              className="grid items-center px-3 py-1.5 text-xs border-b"
              style={{
                gridTemplateColumns: '1fr 70px',
                borderColor: COLOR_BG_SOFT,
                color: COLOR_BRUN,
                backgroundColor: colorByEtat[r.lib_type] || 'white',
              }}
            >
              <div className="truncate font-medium" title={r.lib_type}>
                {r.lib_type}
              </div>
              <div className="text-right font-semibold">{r.qte}</div>
            </div>
          ))}
        </div>
      </div>

      {/* TableValideDecomm : Mois Paiement x Partenaire avec compteur Validés/Décomm */}
      <div
        className="flex flex-col rounded-lg border overflow-hidden"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
      >
        <div
          className="grid items-center px-3 py-2 text-xs font-semibold border-b text-center"
          style={{
            gridTemplateColumns: '120px 100px 1fr 1fr',
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Mois de paiement</div>
          <div>Partenaire</div>
          <div className="text-right">Validés</div>
          <div className="text-right">Décomm</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {tableVD.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun contrat validé/décommissionné avec un mois de paiement.
            </div>
          )}
          {tableVD.map((r, i) => (
            <div
              key={`${r.mois_p}-${r.partenaire}-${i}`}
              className="grid items-center px-3 py-1.5 text-xs border-b"
              style={{
                gridTemplateColumns: '120px 100px 1fr 1fr',
                borderColor: COLOR_BG_SOFT,
                color: COLOR_BRUN,
              }}
            >
              <div>{r.mois_aff}</div>
              <div>{r.partenaire}</div>
              <div className="text-right">{r.valides || ''}</div>
              <div className="text-right">{r.decomm || ''}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// --- Helpers communs aux grilles contrats -------------------------------

function fmtFrenchDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function fmtMoisFr(iso: string): string {
  // 'YYYY-MM' -> 'MM/YYYY'
  if (!iso || iso.length < 7) return ''
  return `${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

const COLS_WIDTHS = {
  select: '38px',
  partenaire: '70px',
  produit: '1fr',
  type_prod: '110px',
  num_bs: '120px',
  date: '90px',
  type_etat: '120px',
  etat: '160px',
  mois: '80px',
} as const

const GRID_TEMPLATE = `${COLS_WIDTHS.select} ${COLS_WIDTHS.partenaire} ${COLS_WIDTHS.produit} ${COLS_WIDTHS.type_prod} ${COLS_WIDTHS.num_bs} ${COLS_WIDTHS.date} ${COLS_WIDTHS.type_etat} ${COLS_WIDTHS.etat}`
const GRID_TEMPLATE_TRAITES = `${GRID_TEMPLATE} ${COLS_WIDTHS.mois}`

interface RowProps {
  ct: ContratItem
  checked: boolean
  onToggle: (id: string) => void
  showMois?: boolean
}

function ContratRow({ ct, checked, onToggle, showMois }: RowProps) {
  return (
    <div
      className="grid items-center gap-2 px-2 py-1 text-xs border-b cursor-pointer"
      style={{
        gridTemplateColumns: showMois ? GRID_TEMPLATE_TRAITES : GRID_TEMPLATE,
        backgroundColor: ct.couleur_fond || '#FFFFFF',
        borderColor: COLOR_BG_SOFT,
        color: COLOR_BRUN,
      }}
      onClick={() => onToggle(ct.id_contrat)}
    >
      <div className="flex justify-center">
        {checked ? (
          <CheckSquare className="w-4 h-4" style={{ color: COLOR_PRIMARY }} />
        ) : (
          <Square className="w-4 h-4" style={{ opacity: 0.4 }} />
        )}
      </div>
      <div className="font-semibold truncate" title={ct.partenaire}>
        {ct.partenaire}
      </div>
      <div className="truncate" title={ct.lib_produit}>
        {ct.lib_produit}
      </div>
      <div className="truncate" title={ct.type_prod}>
        {ct.type_prod}
      </div>
      <div className="truncate" title={ct.num_bs}>
        {ct.num_bs}
      </div>
      <div>{fmtFrenchDate(ct.date_signature)}</div>
      <div className="truncate" title={ct.type_etat_lib}>
        {ct.type_etat_lib}
      </div>
      <div className="truncate" title={ct.etat_contrat_lib}>
        {ct.etat_contrat_lib}
      </div>
      {showMois && <div>{fmtMoisFr(ct.mois_paiement)}</div>}
    </div>
  )
}

function GridHeader({ showMois }: { showMois?: boolean }) {
  return (
    <div
      className="grid items-center gap-2 px-2 py-2 text-xs font-semibold border-b sticky top-0 z-10"
      style={{
        gridTemplateColumns: showMois ? GRID_TEMPLATE_TRAITES : GRID_TEMPLATE,
        color: COLOR_BRUN,
        backgroundColor: COLOR_BG_SOFT,
        borderColor: COLOR_BG_SOFT,
      }}
    >
      <div></div>
      <div>Part.</div>
      <div>Libellé Produit</div>
      <div>Type Prod.</div>
      <div>N° BS</div>
      <div>Date Sign.</div>
      <div>Type État</div>
      <div>État Contrat</div>
      {showMois && <div>Mois Pmt</div>}
    </div>
  )
}

// --- Onglet "Contrats déjà traités" -------------------------------------

interface TabProps {
  contrats: ContratsData | null
  loading: boolean
  selected: Set<string>
  setSelected: (s: Set<string>) => void
}

function DejaTraitesTab({ contrats, loading, selected, setSelected }: TabProps) {
  // Liste distincte des mois de paiement présents (descendant)
  const moisDispos = useMemo(() => {
    if (!contrats) return [] as string[]
    const set = new Set<string>()
    for (const c of contrats.traites) {
      if (c.mois_paiement) set.add(c.mois_paiement)
    }
    return Array.from(set).sort((a, b) => b.localeCompare(a))
  }, [contrats])

  const [moisFiltre, setMoisFiltre] = useState<string>('')

  useEffect(() => {
    if (moisDispos.length > 0 && !moisFiltre) setMoisFiltre(moisDispos[0])
  }, [moisDispos, moisFiltre])

  const filtered = useMemo(() => {
    if (!contrats) return [] as ContratItem[]
    if (!moisFiltre) return contrats.traites
    return contrats.traites.filter((c) => c.mois_paiement === moisFiltre)
  }, [contrats, moisFiltre])

  const toggle = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  // "Valider" WinDev : coche toutes les lignes "VALID*" du mois sélectionné
  const validerMois = () => {
    if (!contrats || !moisFiltre) return
    const next = new Set(selected)
    let added = 0
    for (const c of contrats.traites) {
      if (
        c.mois_paiement === moisFiltre &&
        c.type_etat_lib.toUpperCase().includes('VALID')
      ) {
        if (!next.has(c.id_contrat)) {
          next.add(c.id_contrat)
          added++
        }
      }
    }
    setSelected(next)
    showToast(`${added} contrat(s) ajouté(s) à la sélection`, 'info')
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement des contrats…
      </div>
    )
  }
  if (!contrats || contrats.traites.length === 0) {
    return (
      <div className="text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        Aucun contrat déjà traité pour ce salarié.
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 pb-2">
        <label className="text-sm" style={{ color: COLOR_BRUN }}>
          Mois de paiement :
        </label>
        <select
          value={moisFiltre}
          onChange={(e) => setMoisFiltre(e.target.value)}
          className="text-sm px-2 py-1 border rounded"
          style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
        >
          <option value="">(tous)</option>
          {moisDispos.map((m) => (
            <option key={m} value={m}>
              {fmtMoisFr(m)}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={validerMois}
          disabled={!moisFiltre}
          className="ml-auto inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          <Check className="w-4 h-4" /> Valider (lignes VALID du mois)
        </button>
      </div>
      <div className="text-xs pb-2" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        {filtered.length} contrat(s) — {selected.size} sélectionné(s)
      </div>
      <div className="flex-1 overflow-y-auto border rounded" style={{ borderColor: COLOR_BG_SOFT }}>
        <GridHeader showMois />
        {filtered.map((c) => (
          <ContratRow
            key={c.id_contrat}
            ct={c}
            checked={selected.has(c.id_contrat)}
            onToggle={toggle}
            showMois
          />
        ))}
      </div>
    </div>
  )
}

// --- Onglet "Contrats SDTC" --------------------------------------------

interface TabSDTCProps extends TabProps {
  onValidate: () => void
  computing: boolean
}

function ContratsSDTCTab({ contrats, loading, selected, setSelected, onValidate, computing }: TabSDTCProps) {
  const toggle = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  const toggleAll = () => {
    if (!contrats) return
    if (selected.size === contrats.a_traiter.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(contrats.a_traiter.map((c) => c.id_contrat)))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement des contrats…
      </div>
    )
  }
  if (!contrats || contrats.a_traiter.length === 0) {
    return (
      <div className="text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        Aucun contrat éligible au SDTC pour ce salarié.
      </div>
    )
  }

  const allSelected = selected.size === contrats.a_traiter.length

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 pb-2">
        <button
          type="button"
          onClick={toggleAll}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded border"
          style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
        >
          {allSelected ? <Square className="w-4 h-4" /> : <CheckSquare className="w-4 h-4" />}
          {allSelected ? 'Tout désélectionner' : 'Tout sélectionner'}
        </button>
        <div className="text-xs" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
          {contrats.a_traiter.length} contrat(s) à traiter — {selected.size} sélectionné(s)
        </div>
        <button
          type="button"
          onClick={onValidate}
          disabled={computing}
          className="ml-auto inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          {computing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Check className="w-4 h-4" />
          )}
          Valider la sélection et passer à l'étape suivante
        </button>
      </div>
      <div className="flex-1 overflow-y-auto border rounded" style={{ borderColor: COLOR_BG_SOFT }}>
        <GridHeader />
        {contrats.a_traiter.map((c) => (
          <ContratRow
            key={c.id_contrat}
            ct={c}
            checked={selected.has(c.id_contrat)}
            onToggle={toggle}
          />
        ))}
      </div>
    </div>
  )
}

// --- Onglet "Résumé Solde de tout compte" -------------------------------

function fmtEur(n: number): string {
  return `${n.toFixed(2).replace('.', ',')} €`
}

function ResumeSTCTab({
  bareme,
  onGoToSelection,
  onDownloadXls,
  onDownloadPdf,
  onMailSdtc,
  preparingMail,
  commentaires,
  setCommentaires,
  nbTr,
  setNbTr,
  infoSalarieHtml,
  onCalcNbTr,
  calculatingNbTr,
}: {
  bareme: BaremeResult | null
  onGoToSelection: () => void
  onDownloadXls: () => void | Promise<void>
  onDownloadPdf: () => void | Promise<void>
  onMailSdtc: () => void | Promise<void>
  preparingMail: boolean
  commentaires: string
  setCommentaires: (v: string) => void
  nbTr: number
  setNbTr: (v: number) => void
  /** HTML mesInfos genere cote backend (avec placeholders) */
  infoSalarieHtml?: string
  /** Calcule NB_TR via /generer-tableau */
  onCalcNbTr?: () => void | Promise<void>
  calculatingNbTr?: boolean
}) {
  if (!bareme) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-sm" style={{ color: COLOR_BRUN }}>
        <p style={{ opacity: 0.7 }}>
          Aucun calcul disponible — valider d'abord une sélection dans l'onglet « Contrats SDTC ».
        </p>
        <button
          type="button"
          onClick={onGoToSelection}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded border"
          style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
        >
          Aller à la sélection
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="grid grid-cols-4 gap-3 pb-3">
        <SummaryCard label="Nb contrats" value={String(bareme.nb_tot_ctts)} />
        <SummaryCard label="Nb points" value={String(bareme.nb_tot_pts)} />
        <SummaryCard label="Barème" value={fmtEur(bareme.bareme)} />
        <SummaryCard label="Total STC" value={fmtEur(bareme.comm_tot_stc)} highlight />
      </div>
      <div className="grid grid-cols-3 gap-3 pb-3 text-xs" style={{ color: COLOR_BRUN }}>
        <Detail label="Comm. par points" value={fmtEur(bareme.comm_pts_ctts)} />
        <Detail label="Total valeurs (forfait)" value={fmtEur(bareme.total_valeurs)} />
        <Detail label="Sélection" value={`${bareme.nb_selectionnes} ctt(s)`} />
      </div>

      <div className="flex-1 overflow-y-auto border rounded" style={{ borderColor: COLOR_BG_SOFT }}>
        <div
          className="grid items-center gap-2 px-2 py-2 text-xs font-semibold border-b sticky top-0 z-10"
          style={{
            gridTemplateColumns: '1fr 80px 100px 100px',
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Libellé Produit</div>
          <div className="text-right">Qté</div>
          <div className="text-right">Nb Pts</div>
          <div className="text-right">Valeur</div>
        </div>
        {bareme.produits.map((p) => (
          <div
            key={p.lib_produit}
            className="grid items-center gap-2 px-2 py-1 text-xs border-b"
            style={{
              gridTemplateColumns: '1fr 80px 100px 100px',
              borderColor: COLOR_BG_SOFT,
              color: COLOR_BRUN,
            }}
          >
            <div className="truncate font-medium" title={p.lib_produit}>
              {p.lib_produit}
            </div>
            <div className="text-right">{p.qte}</div>
            <div className="text-right">{p.nb_pts}</div>
            <div className="text-right">{fmtEur(p.valeur)}</div>
          </div>
        ))}
      </div>

      {/* Bloc HTML mesInfos (cf. WinDev InfoSalarie) — affiche tel quel.
          Les placeholders MONTANT_COMM/CP/DECO/AVANCE/NB_TR/DATEABS sont
          remplaces uniquement a la generation PDF/Mail cote backend. */}
      {infoSalarieHtml && (
        <div
          className="mt-4 p-3 border rounded text-xs"
          style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FBF6F4', color: COLOR_BRUN }}
          dangerouslySetInnerHTML={{ __html: infoSalarieHtml }}
        />
      )}

      <div className="mt-3 grid grid-cols-[120px_1fr] gap-3 items-start">
        <label className="text-sm pt-1" style={{ color: COLOR_BRUN }}>
          Nombre de TR :
        </label>
        <input
          type="number"
          min={0}
          value={nbTr}
          onChange={(e) => setNbTr(Number(e.target.value) || 0)}
          className="w-32 px-2 py-1 border rounded text-sm"
          style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
        />
        <div />
        {onCalcNbTr && (
          <button
            type="button"
            onClick={() => void onCalcNbTr()}
            disabled={calculatingNbTr}
            className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded border w-fit disabled:opacity-40"
            style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
            title="Calcule NB_TR via /generer-tableau (>=3 ctts/jour ENI/IAG/OEN, >=1 SFR)"
          >
            {calculatingNbTr ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : null}
            Calculer auto depuis la sélection
          </button>
        )}
        <label className="text-sm pt-1" style={{ color: COLOR_BRUN }}>
          Commentaires :
        </label>
        <textarea
          value={commentaires}
          onChange={(e) => setCommentaires(e.target.value)}
          rows={3}
          className="w-full px-2 py-1 border rounded text-sm"
          style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, resize: 'vertical' }}
          placeholder="(zone reprise dans le PDF EtatSTC_RecapPROD)"
        />
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={onDownloadXls}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded border"
          style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
        >
          <FileSpreadsheet className="w-4 h-4" /> Télécharger XLS
        </button>
        <button
          type="button"
          onClick={onDownloadPdf}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded border"
          style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
        >
          <FileText className="w-4 h-4" /> Télécharger PDF
        </button>
        <button
          type="button"
          onClick={onMailSdtc}
          disabled={preparingMail}
          className="ml-auto inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          {preparingMail ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          Mail SDTC
        </button>
      </div>
    </div>
  )
}

function SummaryCard({
  label,
  value,
  highlight,
}: {
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div
      className="border rounded p-3"
      style={{
        borderColor: COLOR_BG_SOFT,
        backgroundColor: highlight ? COLOR_PRIMARY : 'white',
        color: highlight ? 'white' : COLOR_BRUN,
      }}
    >
      <div className="text-xs" style={{ opacity: highlight ? 0.85 : 0.7 }}>
        {label}
      </div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2 px-3 py-2 border rounded" style={{ borderColor: COLOR_BG_SOFT }}>
      <span style={{ opacity: 0.7 }}>{label}</span>
      <span className="font-semibold">{value}</span>
    </div>
  )
}

// --- Onglet "Contrats à éditer pour le salarié" -------------------------
// Transposition WinDev TableContratTOT : concatenation des contrats deja
// traites + selection SDTC, avec flag STC=true pour la selection.

interface AEditerProps {
  contrats: ContratsData | null
  selectedTraites: Set<string>
  selectedSdtc: Set<string>
  computing: boolean
  onRecalculate: () => void
}

function AEditerTab({
  contrats,
  selectedTraites,
  selectedSdtc,
  computing,
  onRecalculate,
}: AEditerProps) {
  const rows = useMemo(() => {
    if (!contrats) return [] as Array<ContratItem & { stc: boolean }>
    const t = (contrats.traites || [])
      .filter((c) => selectedTraites.has(c.id_contrat))
      .map((c) => ({ ...c, stc: false }))
    const s = (contrats.a_traiter || [])
      .filter((c) => selectedSdtc.has(c.id_contrat))
      .map((c) => ({ ...c, stc: true }))
    return [...t, ...s]
  }, [contrats, selectedTraites, selectedSdtc])

  if (!contrats) {
    return (
      <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
      </div>
    )
  }
  if (rows.length === 0) {
    return (
      <div className="text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        Aucun contrat sélectionné. Cocher des lignes dans « Contrats déjà traités » ou « Contrats SDTC ».
      </div>
    )
  }

  const template = '40px 70px 1fr 130px 90px 110px 70px 70px 60px'
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 pb-2">
        <div className="text-xs" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
          {rows.length} contrat(s) au tableau — {rows.filter((r) => r.stc).length} marqué(s) STC
        </div>
        <button
          type="button"
          onClick={onRecalculate}
          disabled={computing || selectedSdtc.size === 0}
          className="ml-auto inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          {computing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
          Recalculer STC
        </button>
      </div>
      <div className="flex-1 overflow-y-auto border rounded" style={{ borderColor: COLOR_BG_SOFT }}>
        <div
          className="grid items-center gap-2 px-2 py-2 text-xs font-semibold border-b sticky top-0 z-10"
          style={{
            gridTemplateColumns: template,
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div className="text-center">STC</div>
          <div>Part.</div>
          <div>Client / Ville</div>
          <div>Lib Produit</div>
          <div>N° BS</div>
          <div>Date Sign.</div>
          <div>Mois P.</div>
          <div>Type État</div>
          <div className="text-right">Pts</div>
        </div>
        {rows.map((r) => (
          <div
            key={`${r.id_contrat}-${r.stc ? 'stc' : 'tr'}`}
            className="grid items-center gap-2 px-2 py-1 text-xs border-b"
            style={{
              gridTemplateColumns: template,
              backgroundColor: r.couleur_fond || '#FFFFFF',
              borderColor: COLOR_BG_SOFT,
              color: COLOR_BRUN,
            }}
          >
            <div className="flex justify-center">
              {r.stc ? (
                <CheckSquare className="w-4 h-4" style={{ color: COLOR_PRIMARY }} />
              ) : (
                <Square className="w-4 h-4" style={{ opacity: 0.4 }} />
              )}
            </div>
            <div className="font-semibold truncate">{r.partenaire}</div>
            <div className="truncate" title={`${r.client_nom} ${r.client_ville} (${r.client_cp})`}>
              {r.client_nom} <span style={{ opacity: 0.6 }}>{r.client_ville}</span>
            </div>
            <div className="truncate" title={r.lib_produit}>
              {r.lib_produit}
            </div>
            <div className="truncate">{r.num_bs}</div>
            <div>{fmtFrenchDate(r.date_signature)}</div>
            <div>{fmtMoisFr(r.mois_paiement)}</div>
            <div className="truncate">{r.type_etat_lib}</div>
            <div className="text-right">{r.nb_points}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// --- Onglet "Récap Ctts pour le BO" --------------------------------------
// Transposition WinDev TableRecapProd + TableRecapProdPts : agrege par produit
// (regroupement Hachette) selon le Type_Etat de chaque contrat.

const COL_ETATS = [
  { key: 'temporaire', label: 'En attente CONTRAT', match: ['TEMPORAIRE'] },
  { key: 'attente_ope', label: 'Envoyé chez OPE', match: ['EN ATTENTE OP'] },
  { key: 'rejets', label: 'Rejets BO', match: ['REJET', 'ANOMALIE'] },
  { key: 'resiliation', label: 'Résiliation', match: ['RESILIATION', 'RÉSILIATION'] },
  { key: 'valide_paye', label: 'Validé-Payé', match: ['VALID'] },
  { key: 'decommission', label: 'Décommission', match: ['DECOMMISSION', 'DÉCOMMISSION'] },
] as const

type EtatKey = (typeof COL_ETATS)[number]['key']

interface RecapRow {
  lib_produit: string
  counts: Record<EtatKey, number>
  pts: Record<EtatKey, number>
}

function matchEtat(type_etat_lib: string): EtatKey | null {
  const up = (type_etat_lib || '').toUpperCase()
  for (const c of COL_ETATS) {
    for (const m of c.match) if (up.includes(m)) return c.key
  }
  return null
}

interface RecapBOBackendRow {
  lib_produit: string
  en_attente_contrat: number
  envoye_chez_ope: number
  rejets_bo: number
  resiliation: number
  valide_paye: number
  decommision: number
}

interface RecapBOProps {
  contrats: ContratsData | null
  selectedTraites: Set<string>
  selectedSdtc: Set<string>
  /** Si fourni, prefere les valeurs backend (cf. /generer-tableau) au lieu
   *  du calcul cote frontend. */
  backendRecap?: {
    recap_prod: RecapBOBackendRow[]
    recap_prod_pts: RecapBOBackendRow[]
    nb_tr: number
  } | null
  /** Callback pour declencher /generer-tableau et remplir backendRecap. */
  onCalcRecap?: () => void | Promise<void>
  calculating?: boolean
}

function RecapBOTab({
  contrats,
  selectedTraites,
  selectedSdtc,
  backendRecap,
  onCalcRecap,
  calculating,
}: RecapBOProps) {
  const { rows, totals } = useMemo(() => {
    const empty = () => ({
      temporaire: 0,
      attente_ope: 0,
      rejets: 0,
      resiliation: 0,
      valide_paye: 0,
      decommission: 0,
    }) as Record<EtatKey, number>

    // Si on a backendRecap, on prefere ces valeurs (cf. /generer-tableau
    // qui inclut TOUS les contrats, pas seulement la selection - fidele
    // WinDev TableRecapProd).
    if (backendRecap && backendRecap.recap_prod.length > 0) {
      const noms = Array.from(
        new Set([
          ...backendRecap.recap_prod.map((r) => r.lib_produit),
          ...backendRecap.recap_prod_pts.map((r) => r.lib_produit),
        ]),
      )
      const byNomCount = new Map(backendRecap.recap_prod.map((r) => [r.lib_produit, r]))
      const byNomPts = new Map(backendRecap.recap_prod_pts.map((r) => [r.lib_produit, r]))
      const arr: RecapRow[] = noms.map((nom) => {
        const c = byNomCount.get(nom)
        const p = byNomPts.get(nom)
        return {
          lib_produit: nom,
          counts: {
            temporaire: c?.en_attente_contrat || 0,
            attente_ope: c?.envoye_chez_ope || 0,
            rejets: c?.rejets_bo || 0,
            resiliation: c?.resiliation || 0,
            valide_paye: c?.valide_paye || 0,
            decommission: c?.decommision || 0,
          },
          pts: {
            temporaire: p?.en_attente_contrat || 0,
            attente_ope: p?.envoye_chez_ope || 0,
            rejets: p?.rejets_bo || 0,
            resiliation: p?.resiliation || 0,
            valide_paye: p?.valide_paye || 0,
            decommission: p?.decommision || 0,
          },
        }
      })
      arr.sort((a, b) => a.lib_produit.localeCompare(b.lib_produit))
      const t = { counts: empty(), pts: empty() }
      for (const r of arr) {
        for (const c of COL_ETATS) {
          t.counts[c.key] += r.counts[c.key]
          t.pts[c.key] += r.pts[c.key]
        }
      }
      return { rows: arr, totals: t }
    }

    const map = new Map<string, RecapRow>()
    if (!contrats) return { rows: [], totals: { counts: empty(), pts: empty() } }

    const considere = [
      ...contrats.traites.filter((c) => selectedTraites.has(c.id_contrat)),
      ...contrats.a_traiter.filter((c) => selectedSdtc.has(c.id_contrat)),
    ]

    for (const c of considere) {
      let nom = (c.lib_produit || '').split('(')[0].trim()
      const up = nom.toUpperCase()
      if (up === 'TELE 7 JOUR' || up === 'ELLE' || up === 'PARIS MATCH') {
        nom = 'HACHETTE'
      }
      if (!nom) continue
      let row = map.get(nom)
      if (!row) {
        row = { lib_produit: nom, counts: empty(), pts: empty() }
        map.set(nom, row)
      }
      const k = matchEtat(c.type_etat_lib)
      if (k) {
        row.counts[k] += 1
        row.pts[k] += c.nb_points || 0
      }
    }

    const arr = Array.from(map.values()).sort((a, b) =>
      a.lib_produit.localeCompare(b.lib_produit),
    )
    const totals = { counts: empty(), pts: empty() }
    for (const r of arr) {
      for (const c of COL_ETATS) {
        totals.counts[c.key] += r.counts[c.key]
        totals.pts[c.key] += r.pts[c.key]
      }
    }
    return { rows: arr, totals }
  }, [contrats, selectedTraites, selectedSdtc, backendRecap])

  if (!contrats) {
    return (
      <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
      </div>
    )
  }
  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-start gap-3 text-sm" style={{ color: COLOR_BRUN }}>
        <p className="italic" style={{ opacity: 0.7 }}>
          Aucun contrat à afficher. Cocher des lignes dans « Contrats déjà traités » ou « Contrats SDTC », ou recalculer depuis la sélection.
        </p>
        {onCalcRecap && (
          <button
            type="button"
            onClick={() => void onCalcRecap()}
            disabled={calculating}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
            style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
          >
            {calculating ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Recalculer depuis le backend
          </button>
        )}
      </div>
    )
  }

  const template = `1fr ${COL_ETATS.map(() => '110px').join(' ')}`

  return (
    <div className="flex flex-col h-full gap-3">
      {onCalcRecap && (
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => void onCalcRecap()}
            disabled={calculating}
            className="inline-flex items-center gap-1 px-3 py-1 text-xs rounded border disabled:opacity-40"
            style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
            title="Calcule TableRecapProd + TableRecapProdPts cote backend"
          >
            {calculating ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
            Recalculer depuis le backend
          </button>
        </div>
      )}
      <RecapTable
        title="Nombre de contrats"
        template={template}
        rows={rows}
        totals={totals.counts}
        kind="counts"
      />
      <RecapTable
        title="Nombre de points"
        template={template}
        rows={rows}
        totals={totals.pts}
        kind="pts"
      />
    </div>
  )
}

function RecapTable({
  title,
  template,
  rows,
  totals,
  kind,
}: {
  title: string
  template: string
  rows: RecapRow[]
  totals: Record<EtatKey, number>
  kind: 'counts' | 'pts'
}) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden border rounded" style={{ borderColor: COLOR_BG_SOFT }}>
      <div
        className="px-3 py-2 text-xs font-semibold border-b"
        style={{ backgroundColor: COLOR_PRIMARY, color: 'white' }}
      >
        {title}
      </div>
      <div
        className="grid items-center gap-2 px-2 py-2 text-xs font-semibold border-b"
        style={{
          gridTemplateColumns: template,
          color: COLOR_BRUN,
          backgroundColor: COLOR_BG_SOFT,
          borderColor: COLOR_BG_SOFT,
        }}
      >
        <div>Produit</div>
        {COL_ETATS.map((c) => (
          <div key={c.key} className="text-right">
            {c.label}
          </div>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {rows.map((r) => (
          <div
            key={r.lib_produit}
            className="grid items-center gap-2 px-2 py-1 text-xs border-b"
            style={{ gridTemplateColumns: template, borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
          >
            <div className="font-medium truncate" title={r.lib_produit}>
              {r.lib_produit}
            </div>
            {COL_ETATS.map((c) => {
              const v = (kind === 'counts' ? r.counts[c.key] : r.pts[c.key]) as number
              return (
                <div
                  key={c.key}
                  className="text-right"
                  style={{ opacity: v === 0 ? 0.3 : 1 }}
                >
                  {v}
                </div>
              )
            })}
          </div>
        ))}
      </div>
      <div
        className="grid items-center gap-2 px-2 py-2 text-xs font-semibold border-t"
        style={{
          gridTemplateColumns: template,
          color: COLOR_BRUN,
          backgroundColor: COLOR_BG_SOFT,
          borderColor: COLOR_BG_SOFT,
        }}
      >
        <div>Total</div>
        {COL_ETATS.map((c) => (
          <div key={c.key} className="text-right">
            {totals[c.key]}
          </div>
        ))}
      </div>
    </div>
  )
}
