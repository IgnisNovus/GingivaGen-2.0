import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'

const phases = [
  {
    phase: 1,
    title: 'Neural Segmentation',
    description:
      'AI-powered 3DTeethSAM segments the intraoral scan, isolating teeth from gingival tissue and identifying the recession defect boundary.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
    color: '#00d4ff',
  },
  {
    phase: 2,
    title: 'Ideal Volume',
    description:
      'RBF interpolation through healthy margin points reconstructs the missing tissue contour, defining the exact scaffold geometry.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z" />
      </svg>
    ),
    color: '#00ffd5',
  },
  {
    phase: 3,
    title: 'PCL+BAG Armor',
    description:
      '0.5 mm polycaprolactone shell with 10% bioactive glass provides suture retention and protects against mastication forces.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    color: '#c8c8dc',
  },
  {
    phase: 4,
    title: 'Anisotropic Gyroid Core',
    description:
      "Schoen Gyroid TPMS lattice with PDL-mimetic anisotropy. 325 µm pores guide fibroblast migration and Sharpey's fiber alignment.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
      </svg>
    ),
    color: '#64c864',
  },
  {
    phase: 5,
    title: 'Vascular Channels',
    description:
      'Sacrificial Pluronic F-127 cylinders (400 µm) create perfusable lumens for angiogenesis after dissolution at 4°C.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
      </svg>
    ),
    color: '#6496ff',
  },
  {
    phase: 6,
    title: 'G-code Export',
    description:
      'Multi-material slicing via FullControl generates 3-head bioprinter instructions. Armor prints first to contain soft hydrogel.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6">
        <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    color: '#ff4d8d',
  },
]

function PhaseCard({
  phase,
  index,
}: {
  phase: (typeof phases)[0]
  index: number
}) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: index * 0.1, duration: 0.6 }}
      className="relative group"
    >
      <div className="relative bg-[#12121a] border border-[#ffffff08] rounded-2xl p-6 hover:border-[#00d4ff]/20 transition-all duration-300 h-full">
        <div
          className="absolute -top-3 -left-3 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-[#0a0a0f]"
          style={{ backgroundColor: phase.color }}
        >
          {phase.phase}
        </div>
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 mt-2"
          style={{ backgroundColor: `${phase.color}15`, color: phase.color }}
        >
          {phase.icon}
        </div>
        <h3 className="text-lg font-semibold text-[#f0f0f5] mb-2">
          {phase.title}
        </h3>
        <p className="text-sm text-[#8888aa] leading-relaxed">
          {phase.description}
        </p>
        <div
          className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
          style={{
            boxShadow: `inset 0 0 30px ${phase.color}08, 0 0 20px ${phase.color}05`,
          }}
        />
      </div>
    </motion.div>
  )
}

export default function ProcessSection() {
  const headerRef = useRef(null)
  const headerInView = useInView(headerRef, { once: true, margin: '-100px' })

  return (
    <section id="process" className="py-32 relative">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          ref={headerRef}
          initial={{ opacity: 0, y: 30 }}
          animate={headerInView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <span className="text-xs text-[#00d4ff] tracking-widest uppercase font-medium">
            Pipeline Architecture
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-[#f0f0f5] mt-3 mb-4">
            From Scan to Scaffold
          </h2>
          <p className="text-[#8888aa] max-w-xl mx-auto">
            Six autonomous phases transform a raw intraoral 3D scan into
            bioprinter-ready G-code for a patient-specific gingival scaffold.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {phases.map((phase, i) => (
            <PhaseCard key={phase.phase} phase={phase} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
