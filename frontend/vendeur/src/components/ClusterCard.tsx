import { motion } from 'framer-motion'
import { Users } from 'lucide-react'
import ClusterDonut from '@/components/ClusterDonut'

export interface ClusterData {
  code_vad: string
  code_vad_full: string
  nom: string
  exp_lib: string
  exp_rs: string
  logo_ste: string
  obj_ctt: number
  nb_ctt_brut: number
  nb_s1: number
  nb_racc_sfr: number
  nb_fib_hors_att: number
  ratio: number
  ratio_reel: number
  tx_rac: number
  tx_s1: number
  couleur_jauge: string
  couleur_racc: string
}

interface ClusterCardProps {
  cluster: ClusterData
  onTeamClick?: (cluster: ClusterData) => void
}

export default function ClusterCard({ cluster, onTeamClick }: ClusterCardProps) {
  const {
    nom,
    exp_lib,
    obj_ctt,
    nb_ctt_brut,
    ratio,
    ratio_reel,
    tx_rac,
    tx_s1,
    couleur_jauge,
    couleur_racc,
  } = cluster

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.25 }}
      className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate" title={nom}>
            {nom}
          </h3>
          <button
            onClick={() => onTeamClick?.(cluster)}
            disabled={!onTeamClick}
            className="mt-2 flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 disabled:hover:text-gray-600 disabled:cursor-default transition-colors group"
          >
            <Users className="w-4 h-4 text-gray-400 group-hover:text-gray-700" />
            <span className={onTeamClick ? 'underline decoration-dotted underline-offset-4' : ''}>
              {exp_lib}
            </span>
          </button>
        </div>

        <ClusterDonut
          ratio={ratio}
          ratioReel={ratio_reel}
          color={couleur_jauge}
          size={84}
          strokeWidth={8}
        />
      </div>

      <div className="mt-4 flex items-baseline justify-between">
        <div
          className="font-semibold text-lg tabular-nums"
          style={{ color: couleur_jauge }}
        >
          {nb_ctt_brut} <span className="text-gray-400 font-normal">/</span> {obj_ctt}
        </div>
        <div className="text-xs tabular-nums" style={{ color: couleur_racc }}>
          Racc : {tx_rac.toFixed(tx_rac % 1 ? 2 : 0)}%
          {tx_s1 > 0 && <>, Racc S1 : {tx_s1.toFixed(tx_s1 % 1 ? 2 : 0)}%</>}
        </div>
      </div>
    </motion.div>
  )
}
