import { motion } from 'framer-motion'

interface ClusterDonutProps {
  ratio: number       // 0..1 (écrêté à 1 pour l'arc)
  ratioReel: number   // valeur non écrêtée (peut dépasser 100%)
  color: string       // hex #RRGGBB
  size?: number       // px (par défaut 100)
  strokeWidth?: number // px (par défaut 10)
}

export default function ClusterDonut({
  ratio,
  ratioReel,
  color,
  size = 100,
  strokeWidth = 10,
}: ClusterDonutProps) {
  const r = (size - strokeWidth) / 2
  const c = 2 * Math.PI * r
  const cx = size / 2
  const cy = size / 2

  const pct = Math.max(0, Math.min(1, ratio))
  const dash = pct * c
  const pctLabel = Math.round(ratioReel * 1000) / 10  // 1 décimale

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={strokeWidth}
        />
        <motion.circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c - dash }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </svg>
      <div
        className="absolute inset-0 flex items-center justify-center text-sm font-semibold"
        style={{ color }}
      >
        {pctLabel}%
      </div>
    </div>
  )
}
