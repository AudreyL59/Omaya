/**
 * Fen_EditionDocUlease : édition d'un modèle de document Ulease.
 *
 * Stub minimal pour l'instant. La vraie modale, clonée depuis
 * DocRHEditModal, viendra ensuite (WYSIWYG mammoth + WeasyPrint +
 * publipostage Salarié + Société + Véhicule).
 *
 * Variables Ulease (cf. WinDev Fen_EditionDocUlease) :
 *  - Salarié : S_TITRE, S_NOM, S_PRENOM, S_LNAISS, S_DEPNAISS, S_NUMSS,
 *    S_DNAISS, S_ADRESSE, S_CP, S_VILLE, FIN_PER_ESSAI, DATE_CTS,
 *    DATE_ANC, DATE_AVENANT, SECTEURAGENCE, S_MENTION, S_SIGN.
 *  - Société : STE_LOGO, DOCTITRE, STE_RS, STE_APE, STE_RCS, STE_CAPITAL,
 *    STE_ADR, STE_VILLE, STE_SIREN, STE_SIRET, STE_GERANT_NOM,
 *    STE_GERANT_TYPE, GER_SIGN, STE_CACHET, DATE_NOTE.
 *  - Véhicule (si idPC != 0) : AUTO_IMMA, AUTO_TYPE, AUTO_CV, AUTO_KM,
 *    DATE_DEB, DATE_FIN.
 */

import { motion, AnimatePresence } from 'framer-motion'
import { FileText, X } from 'lucide-react'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Props {
  idDocUlease: string  // '' = nouveau, sinon id
  onClose: () => void
  onSaved: () => void
}

export default function DocUleaseEditModal({ idDocUlease, onClose, onSaved: _onSaved }: Props) {
  return (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[80vh] flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: COL_BORDER, backgroundColor: COL_PRIMARY, color: 'white' }}>
            <h2 className="text-base font-semibold flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Édition Doc Ulease
            </h2>
            <button onClick={onClose} className="text-white/80 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="p-6 text-sm space-y-3" style={{ backgroundColor: COL_BG_SOFT, color: COL_BRUN }}>
            <p>
              <strong>{idDocUlease ? `Modification du doc #${idDocUlease}` : 'Nouveau document Ulease'}</strong>
            </p>
            <p className="italic">
              Modal complet à venir (WYSIWYG + publipostage + WeasyPrint), clonée
              depuis DocRHEditModal avec en plus les variables véhicule.
            </p>
          </div>
          <div className="flex justify-end gap-2 px-5 py-3 border-t"
            style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
            <button type="button" onClick={onClose}
              className="px-3 py-1.5 rounded text-sm border"
              style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
              Fermer
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
