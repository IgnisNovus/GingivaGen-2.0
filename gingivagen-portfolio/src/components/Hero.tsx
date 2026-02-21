import { motion } from 'framer-motion'

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated background grid */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(0,212,255,0.3) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(0,212,255,0.3) 1px, transparent 1px)`,
          backgroundSize: '60px 60px',
        }}
      />

      {/* Gradient orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-[#00d4ff]/10 rounded-full blur-[120px] animate-float" />
      <div
        className="absolute bottom-1/4 -right-32 w-96 h-96 bg-[#00ffd5]/8 rounded-full blur-[120px] animate-float"
        style={{ animationDelay: '3s' }}
      />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#ff4d8d]/5 rounded-full blur-[150px]" />

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[#00d4ff]/20 bg-[#00d4ff]/5 mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-[#00ffd5] animate-pulse" />
          <span className="text-xs text-[#00d4ff] tracking-wider uppercase font-medium">
            Regenerative Bioprinting Platform
          </span>
        </motion.div>

        {/* Title */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-6"
        >
          <span className="text-[#f0f0f5]">Gingiva</span>
          <span className="gradient-text">Gen</span>
          <span className="text-[#8888aa] text-3xl md:text-4xl lg:text-5xl ml-3 font-light">
            2.0
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="text-lg md:text-xl text-[#8888aa] max-w-2xl mx-auto mb-4 leading-relaxed"
        >
          AI-driven pipeline converting intraoral 3D scans into multi-material,
          implantable gingival scaffolds for
          <span className="text-[#00d4ff]"> gum recession treatment</span>.
        </motion.p>

        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="text-sm text-[#8888aa]/60 max-w-xl mx-auto mb-12"
        >
          Triple-threat biological strategy: mechanical defense, bio-grafting
          guidance, and vascular support — all in one bioprinted scaffold.
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <a
            href="#scanner"
            className="px-8 py-3.5 rounded-xl bg-gradient-to-r from-[#00d4ff] to-[#00ffd5] text-[#0a0a0f] font-semibold text-sm hover:shadow-[0_0_30px_rgba(0,212,255,0.3)] transition-shadow"
          >
            Explore 3D Scan →
          </a>
          <a
            href="#process"
            className="px-8 py-3.5 rounded-xl border border-[#8888aa]/20 text-[#f0f0f5] text-sm hover:border-[#00d4ff]/40 hover:bg-[#00d4ff]/5 transition-all"
          >
            View Process
          </a>
        </motion.div>

        {/* Stats bar */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
          className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto"
        >
          {[
            { value: '325 µm', label: 'Pore Size' },
            { value: '50 µm', label: 'Resolution' },
            { value: '4', label: 'Bio-Materials' },
            { value: '< 15 KPa', label: 'Scaffold Stiffness' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-xl md:text-2xl font-bold text-[#00d4ff]">
                {stat.value}
              </div>
              <div className="text-xs text-[#8888aa] mt-1">{stat.label}</div>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <span className="text-xs text-[#8888aa]/50 tracking-widest uppercase">
          Scroll
        </span>
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className="w-5 h-8 rounded-full border border-[#8888aa]/30 flex items-start justify-center p-1.5"
        >
          <div className="w-1 h-2 rounded-full bg-[#00d4ff]" />
        </motion.div>
      </motion.div>
    </section>
  )
}
