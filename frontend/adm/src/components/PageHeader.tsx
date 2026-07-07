/**
 * Header standard des pages ouvertes via le menu principal :
 * fleche retour + icone + titre en vert fonce OMAYA (#17494E).
 *
 * Usage :
 *   <PageHeader icon={Table2} title="Génération de tableaux divers" />
 *
 * Optionnellement :
 *   <PageHeader
 *     icon={Send}
 *     title="Envoi des fiches de salaires"
 *     right={<span className="text-xs">Plan 2/2</span>}
 *   />
 */
import type { LucideIcon } from 'lucide-react'
import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

interface PageHeaderProps {
  icon: LucideIcon
  title: string
  right?: React.ReactNode
  backTo?: string
}

export default function PageHeader({
  icon: Icon,
  title,
  right,
  backTo = '/',
}: PageHeaderProps) {
  return (
    <div className="flex items-center gap-4 mb-6">
      <Link
        to={backTo}
        className="p-2 rounded hover:bg-white/50 text-[#17494E]"
        title="Retour"
      >
        <ArrowLeft className="w-5 h-5" />
      </Link>
      <Icon className="w-6 h-6 text-[#17494E]" />
      <h1 className="text-2xl font-semibold text-[#17494E]">{title}</h1>
      {right && <div className="ml-auto">{right}</div>}
    </div>
  )
}
