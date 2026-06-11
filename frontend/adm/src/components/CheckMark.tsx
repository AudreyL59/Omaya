/**
 * Coche standard ADM : ✓ en couleur primaire (#17494E, teal foncé des
 * boutons) si active, vide sinon.
 *
 * Utilise dans les tableaux des onglets de la fiche salarie ADM pour
 * uniformiser l'affichage des valeurs booleennes.
 */

export const ADM_CHECK_COLOR = '#17494E'

interface Props {
  active: boolean
}

export default function CheckMark({ active }: Props) {
  if (!active) return null
  return (
    <span className="font-bold" style={{ color: ADM_CHECK_COLOR }}>
      ✓
    </span>
  )
}
