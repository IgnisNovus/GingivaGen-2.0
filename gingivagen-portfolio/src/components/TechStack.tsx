import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'

const pipelineSteps = [
  {
    id: 'input',
    label: 'Intraoral Scan',
    detail: '.OBJ / .STL mesh',
    color: '#8888aa',
    tools: ['3Shape TRIOS', 'iTero'],
  },
  {
    id: 'seg',
    label: 'AI Segmentation',
    detail: 'Phase 1',
    color: '#00d4ff',
    tools: ['3DTeethSAM', 'Teeth3DS+ dataset', 'PyTorch'],
  },
  {
    id: 'vol',
    label: 'Volume Reconstruction',
    detail: 'Phase 2',
    color: '#00ffd5',
    tools: ['SciPy RBF Interpolator', 'NumPy'],
  },
  {
    id: 'armor',
    label: 'Armor Shell',
    detail: 'Phase 3',
    color: '#c8c8dc',
    tools: ['SciPy ndimage', 'MeshLib (optional)'],
  },
  {
    id: 'core',
    label: 'Gyroid Core',
    detail: 'Phase 4',
    color: '#64c864',
    tools: ['LisbonTPMS tool', 'Schoen Gyroid TPMS'],
  },
  {
    id: 'vasc',
    label: 'Vascular Channels',
    detail: 'Phase 5',
    color: '#6496ff',
    tools: ['NumPy boolean operations'],
  },
  {
    id: 'gcode',
    label: 'G-code Export',
    detail: 'Phase 6',
    color: '#ff4d8d',
    tools: ['FullControl GCode Designer'],
  },
  {
    id: 'output',
    label: 'Bioprinter Ready',
    detail: 'Multi-head G-code',
    color: '#00d4ff',
    tools: ['3-head bioprinter', 'PCL + GelMA + Pluronic'],
  },
]

const openSourceTools = [
  {
    name: 'Teeth3DS+',
    url: 'https://github.com/abenhamadou/3DTeethSeg22_challenge',
    description: 'Benchmark dataset for 3D dental segmentation',
    category: 'Data',
  },
  {
    name: '3DTeethSAM',
    url: 'https://github.com/Crisitofy/3DTeethSAM',
    description: 'SAM-based 3D tooth segmentation model',
    category: 'AI',
  },
  {
    name: 'LisbonTPMS',
    url: 'https://github.com/SoftwareImpacts/SIMPAC-2025-26',
    description: 'TPMS lattice generation for tissue engineering',
    category: 'Geometry',
  },
  {
    name: 'FullControl',
    url: 'https://github.com/FullControlXYZ/fullcontrol',
    description: 'Parametric G-code design for additive manufacturing',
    category: 'Fabrication',
  },
  {
    name: 'Trimesh',
    url: 'https://github.com/mikedh/trimesh',
    description: 'Python library for 3D mesh processing',
    category: 'Geometry',
  },
  {
    name: 'scikit-image',
    url: 'https://scikit-image.org/',
    description: 'Marching cubes, morphology, and image analysis',
    category: 'Analysis',
  },
  {
    name: 'PoreSpy',
    url: 'https://github.com/PMEAL/porespy',
    description: 'Pore network analysis for scaffold validation',
    category: 'Validation',
  },
  {
    name: 'SciPy',
    url: 'https://scipy.org/',
    description: 'RBF interpolation, spatial algorithms, morphology',
    category: 'Core',
  },
]

const categoryColors: Record<string, string> = {
  Data: '#00d4ff',
  AI: '#ff4d8d',
  Geometry: '#64c864',
  Fabrication: '#ffb432',
  Analysis: '#6496ff',
  Validation: '#c8c8dc',
  Core: '#8888aa',
}

export default function TechStack() {
  const sectionRef = useRef(null)
  const inView = useInView(sectionRef, { once: true, margin: '-100px' })

  return (
    <section id="tech" className="py-32 relative">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          ref={sectionRef}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <span className="text-xs text-[#00d4ff] tracking-widest uppercase font-medium">
            Technology
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-[#f0f0f5] mt-3 mb-4">
            Pipeline & Open-Source Stack
          </h2>
          <p className="text-[#8888aa] max-w-xl mx-auto">
            Built entirely on open-source tools and peer-reviewed methods.
            Every phase is reproducible and extensible.
          </p>
        </motion.div>

        {/* Pipeline flowchart */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.1 }}
          className="mb-20"
        >
          <h3 className="text-lg font-semibold text-[#f0f0f5] text-center mb-8">
            End-to-End Pipeline Flow
          </h3>

          {/* Horizontal flow on desktop, vertical on mobile */}
          <div className="relative">
            {/* Desktop: horizontal */}
            <div className="hidden lg:flex items-start gap-0 overflow-x-auto pb-4">
              {pipelineSteps.map((step, i) => (
                <div key={step.id} className="flex items-start flex-shrink-0">
                  <div className="flex flex-col items-center w-[140px]">
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold text-[#0a0a0f] mb-2"
                      style={{ backgroundColor: step.color }}
                    >
                      {i === 0
                        ? '📷'
                        : i === pipelineSteps.length - 1
                        ? '🖨️'
                        : i}
                    </div>
                    <span className="text-xs font-medium text-[#f0f0f5] text-center">
                      {step.label}
                    </span>
                    <span className="text-[10px] text-[#8888aa] text-center mt-0.5">
                      {step.detail}
                    </span>
                    <div className="mt-2 flex flex-wrap justify-center gap-1">
                      {step.tools.map((tool) => (
                        <span
                          key={tool}
                          className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a2e] text-[#8888aa] border border-[#ffffff08]"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                  {i < pipelineSteps.length - 1 && (
                    <div className="flex items-center h-12 px-1">
                      <svg
                        width="24"
                        height="12"
                        viewBox="0 0 24 12"
                        fill="none"
                      >
                        <path
                          d="M0 6h20M16 2l4 4-4 4"
                          stroke="#00d4ff"
                          strokeWidth="1.5"
                          opacity="0.4"
                        />
                      </svg>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Mobile: vertical */}
            <div className="lg:hidden flex flex-col gap-3">
              {pipelineSteps.map((step, i) => (
                <div key={step.id} className="flex items-center gap-4">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold text-[#0a0a0f] flex-shrink-0"
                    style={{ backgroundColor: step.color }}
                  >
                    {i === 0
                      ? '📷'
                      : i === pipelineSteps.length - 1
                      ? '🖨️'
                      : i}
                  </div>
                  <div>
                    <span className="text-sm font-medium text-[#f0f0f5]">
                      {step.label}
                    </span>
                    <span className="text-xs text-[#8888aa] ml-2">
                      {step.detail}
                    </span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {step.tools.map((tool) => (
                        <span
                          key={tool}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-[#1a1a2e] text-[#8888aa]"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Open-source tools grid */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2 }}
        >
          <h3 className="text-lg font-semibold text-[#f0f0f5] text-center mb-8">
            Open-Source Dependencies
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {openSourceTools.map((tool) => (
              <a
                key={tool.name}
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group p-4 rounded-xl bg-[#12121a] border border-[#ffffff08] hover:border-[#00d4ff]/20 transition-all"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                    style={{
                      backgroundColor: `${categoryColors[tool.category]}15`,
                      color: categoryColors[tool.category],
                    }}
                  >
                    {tool.category}
                  </span>
                </div>
                <h4 className="text-sm font-semibold text-[#f0f0f5] group-hover:text-[#00d4ff] transition-colors mb-1">
                  {tool.name}
                  <span className="text-[#8888aa] ml-1 text-xs">↗</span>
                </h4>
                <p className="text-xs text-[#8888aa] leading-relaxed">
                  {tool.description}
                </p>
              </a>
            ))}
          </div>
        </motion.div>

        {/* Methods summary */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.3 }}
          className="mt-16 p-6 rounded-2xl bg-[#12121a] border border-[#ffffff08]"
        >
          <h3 className="text-lg font-semibold text-[#f0f0f5] mb-4">
            Key Methods & References
          </h3>
          <div className="grid md:grid-cols-2 gap-4 text-xs text-[#8888aa]">
            <div>
              <h4 className="text-[#00d4ff] font-medium mb-1">
                Segmentation
              </h4>
              <p>
                3DTeethSAM (multi-view SAM adaptation for dental meshes) with
                geometric fallback using z-height percentile analysis.
              </p>
            </div>
            <div>
              <h4 className="text-[#00ffd5] font-medium mb-1">
                Gap Interpolation
              </h4>
              <p>
                Thin-plate-spline RBF interpolation through healthy margin
                points reconstructs the ideal tissue surface over the recession
                gap.
              </p>
            </div>
            <div>
              <h4 className="text-[#c8c8dc] font-medium mb-1">
                Morphological Armor
              </h4>
              <p>
                Binary erosion of the scaffold volume generates the 0.5 mm PCL
                shell. SciPy ndimage or MeshLib handles the distance-field
                computation.
              </p>
            </div>
            <div>
              <h4 className="text-[#64c864] font-medium mb-1">
                TPMS Lattice
              </h4>
              <p>
                LisbonTPMS tool generates the Schoen Gyroid field. An iterative
                solver tunes the isovalue t to hit the 325 µm target pore
                size (Zeltinger 2001).
              </p>
            </div>
            <div>
              <h4 className="text-[#6496ff] font-medium mb-1">
                Vascularisation
              </h4>
              <p>
                Boolean-OR of 400 µm Pluronic F-127 cylinders into the core
                (Miller 2012 pre-vascularisation strategy).
              </p>
            </div>
            <div>
              <h4 className="text-[#ff4d8d] font-medium mb-1">
                G-code Generation
              </h4>
              <p>
                FullControl serpentine raster slicing with automatic tool
                changes. Armor prints first to contain soft GelMA hydrogel.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
