import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'

const biologicalFacts = [
  {
    title: 'Mechanical Defense',
    description:
      'PCL + 10% Bioactive Glass (45S5) armor shell prevents suture pull-through and resists mastication forces during the 6–8 week healing window.',
    color: '#c8c8dc',
    icon: '🛡️',
  },
  {
    title: 'Bio-Grafting Guidance',
    description:
      "Anisotropic Schoen Gyroid pores (325 µm) with PDL-mimetic z-stretching guide fibroblast alignment and promote Sharpey's fiber insertion at the root interface.",
    color: '#64c864',
    icon: '🧬',
  },
  {
    title: 'Vascular & Immune Support',
    description:
      'Sacrificial Pluronic F-127 channels enable capillary sprouting from the host vascular bed. BAG doping promotes M2 macrophage polarization and suppresses bacterial colonization.',
    color: '#6496ff',
    icon: '🩸',
  },
  {
    title: 'Immunomodulation',
    description:
      'Chitosan nanoparticles embedded in the GelMA matrix provide sustained antimicrobial activity and modulate the local immune response, promoting M2 macrophage polarization and accelerating soft-tissue integration.',
    color: '#e8a030',
    icon: '🧪',
  },
]

const GCODE_SAMPLE = `; === GingivaGen 2.0 Multi-Material Scaffold ===
; Generated: 2025-06-14  Grid: 168x135x52  Voxel: 0.06 mm
; Materials: PCL+BAG (T0), GelMA (T1), Pluronic F-127 (T2)
G28          ; home all axes
G90          ; absolute positioning
M83          ; relative extrusion
M104 S65     ; PCL melt temperature
M190 S37     ; bed temp (cell viability)

; --- Layer 0  z=0.050 mm ---
; >> Tool 0: PCL+BAG Armor (300 kPa, 3 mm/s, 0.41 mm nozzle)
T0
M400         ; wait for moves to finish
G1 F180.0    ; print speed 3 mm/s = 180 mm/min
G1 X-4.950 Y-3.950 Z0.050 F3000  ; travel to start
G1 X-4.890 Y-3.950 E0.0041
G1 X-4.830 Y-3.950 E0.0041
G1 X-4.770 Y-3.950 E0.0041
G1 X-4.710 Y-3.950 E0.0041
G1 X-4.650 Y-3.950 E0.0041
G1 X-4.590 Y-3.950 E0.0041
G1 X-4.530 Y-3.890 E0.0041
G1 X-4.530 Y-3.830 E0.0041
G1 X-4.590 Y-3.770 E0.0041
G1 X-4.650 Y-3.770 E0.0041
G1 X-4.710 Y-3.770 E0.0041
G1 X-4.770 Y-3.770 E0.0041
G1 X-4.830 Y-3.770 E0.0041
G1 X-4.890 Y-3.770 E0.0041
G1 X-4.950 Y-3.770 E0.0041
G1 X-4.950 Y-3.590 E0.0041
G1 X-4.890 Y-3.590 E0.0041
G1 X-4.830 Y-3.590 E0.0041
G1 X-4.770 Y-3.590 E0.0041
G1 X-4.710 Y-3.590 E0.0041
G1 X4.710 Y-3.590 E0.0041
G1 X4.770 Y-3.590 E0.0041
G1 X4.830 Y-3.590 E0.0041
G1 X4.890 Y-3.590 E0.0041
G1 X4.950 Y-3.590 E0.0041
G1 X4.950 Y-3.410 E0.0041
G1 X4.890 Y-3.410 E0.0041
G1 X4.830 Y-3.410 E0.0041
G1 X4.770 Y-3.410 E0.0041
G1 X4.710 Y-3.410 E0.0041

; >> Tool 1: GelMA Core (45 kPa, 5 mm/s, 0.25 mm nozzle)
T1
M400
G1 F300.0    ; print speed 5 mm/s = 300 mm/min
G1 X-3.450 Y-2.450 Z0.050 F3000  ; travel into core region
G1 X-3.390 Y-2.450 E0.0025
G1 X-3.270 Y-2.450 E0.0025
G1 X-3.150 Y-2.450 E0.0025
G1 X-2.970 Y-2.450 E0.0025
G1 X-2.850 Y-2.390 E0.0025
G1 X-2.850 Y-2.330 E0.0025
G1 X-2.970 Y-2.270 E0.0025
G1 X-3.150 Y-2.270 E0.0025
G1 X-3.270 Y-2.270 E0.0025
G1 X-3.390 Y-2.270 E0.0025
G1 X-3.450 Y-2.270 E0.0025
G1 X-3.450 Y-2.090 E0.0025
G1 X-3.390 Y-2.090 E0.0025
G1 X-3.270 Y-2.090 E0.0025
G1 X-2.850 Y-2.090 E0.0025
G1 X-2.550 Y-2.090 E0.0025
G1 X-2.190 Y-2.090 E0.0025
G1 X-1.890 Y-2.090 E0.0025
G1 X-1.590 Y-2.090 E0.0025
G1 X1.590 Y-2.090 E0.0025
G1 X1.890 Y-2.090 E0.0025
G1 X2.190 Y-2.090 E0.0025
G1 X2.550 Y-2.090 E0.0025
G1 X2.850 Y-2.090 E0.0025
G1 X3.270 Y-2.090 E0.0025
G1 X3.390 Y-2.090 E0.0025
G1 X3.450 Y-2.090 E0.0025

; --- Layer 1  z=0.100 mm ---
; >> Tool 0: PCL+BAG Armor
T0
M400
G1 F180.0
G1 X-4.950 Y-3.950 Z0.100 F3000
G1 X-4.890 Y-3.950 E0.0041
G1 X-4.830 Y-3.950 E0.0041
G1 X-4.770 Y-3.950 E0.0041
G1 X-4.710 Y-3.950 E0.0041
G1 X4.710 Y-3.950 E0.0041
G1 X4.770 Y-3.950 E0.0041
G1 X4.830 Y-3.950 E0.0041
G1 X4.890 Y-3.950 E0.0041
G1 X4.950 Y-3.950 E0.0041

; >> Tool 1: GelMA Core
T1
M400
G1 F300.0
G1 X-3.450 Y-2.450 Z0.100 F3000
G1 X-3.390 Y-2.450 E0.0025
G1 X-3.270 Y-2.450 E0.0025
G1 X-3.150 Y-2.450 E0.0025
G1 X3.150 Y-2.450 E0.0025
G1 X3.270 Y-2.450 E0.0025
G1 X3.390 Y-2.450 E0.0025
G1 X3.450 Y-2.450 E0.0025

; --- Layer 2  z=0.150 mm ---
T0
M400
G1 F180.0
G1 X-4.890 Y-3.890 Z0.150 F3000
G1 X-4.830 Y-3.890 E0.0041
G1 X-4.770 Y-3.890 E0.0041
G1 X4.770 Y-3.890 E0.0041
G1 X4.830 Y-3.890 E0.0041
G1 X4.890 Y-3.890 E0.0041

T1
M400
G1 F300.0
G1 X-3.390 Y-2.390 Z0.150 F3000
G1 X-3.270 Y-2.390 E0.0025
G1 X-3.090 Y-2.330 E0.0025
G1 X-2.910 Y-2.390 E0.0025
G1 X-2.730 Y-2.330 E0.0025
G1 X2.730 Y-2.330 E0.0025
G1 X2.910 Y-2.390 E0.0025
G1 X3.090 Y-2.330 E0.0025
G1 X3.270 Y-2.390 E0.0025
G1 X3.390 Y-2.390 E0.0025

; --- Layer 15  z=0.800 mm ---
; >> Tool 2: Pluronic F-127 (60 kPa, 8 mm/s, 0.41 mm nozzle)
; Sacrificial vascular channels — dissolved at 4 C post-print
T2
M400
G1 F480.0    ; print speed 8 mm/s = 480 mm/min
G1 X-3.000 Y-1.000 Z0.800 F3000  ; channel 1
G1 X-3.000 Y-1.000 Z3.000 E0.1200
G1 X-1.000 Y-1.000 Z0.800 F3000  ; channel 2
G1 X-1.000 Y-1.000 Z3.000 E0.1200
G1 X1.000 Y-1.000 Z0.800 F3000   ; channel 3
G1 X1.000 Y-1.000 Z3.000 E0.1200
G1 X3.000 Y-1.000 Z0.800 F3000   ; channel 4
G1 X3.000 Y-1.000 Z3.000 E0.1200
G1 X-1.000 Y1.000 Z0.800 F3000   ; channel 5
G1 X-1.000 Y1.000 Z3.000 E0.1200
G1 X1.000 Y1.000 Z0.800 F3000    ; channel 6
G1 X1.000 Y1.000 Z3.000 E0.1200

; --- Layer 16–49: repeat pattern ---
; (2,380 additional lines omitted for preview)

; --- Layer 50  z=2.550 mm ---
T0
M400
G1 F180.0
G1 X-2.310 Y-1.190 Z2.550 F3000
G1 X-2.250 Y-1.190 E0.0041
G1 X-2.190 Y-1.190 E0.0041
G1 X2.190 Y-1.190 E0.0041
G1 X2.250 Y-1.190 E0.0041
G1 X2.310 Y-1.190 E0.0041

T1
M400
G1 F300.0
G1 X-1.310 Y-0.690 Z2.550 F3000
G1 X-1.250 Y-0.690 E0.0025
G1 X-1.190 Y-0.690 E0.0025
G1 X1.190 Y-0.690 E0.0025
G1 X1.250 Y-0.690 E0.0025
G1 X1.310 Y-0.690 E0.0025

; --- End ---
M106 S0      ; pressure off all heads
M104 S0      ; heater off
G91
G0 Z10 F3000 ; lift nozzle clear
G90
G1 X0 Y0 F3000  ; park
M0           ; program end
; Total: 3,847 lines | 52 layers | 3 materials`

export default function DataSection() {
  const sectionRef = useRef(null)
  const inView = useInView(sectionRef, { once: true, margin: '-100px' })

  return (
    <section id="data" className="py-32 relative">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          ref={sectionRef}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <span className="text-xs text-[#00d4ff] tracking-widest uppercase font-medium">
            Pipeline Output
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-[#f0f0f5] mt-3 mb-4">
            Validation & Analysis
          </h2>
          <p className="text-[#8888aa] max-w-xl mx-auto">
            Cross-sectional views and material distribution data from the
            autonomous scaffold generation pipeline.
          </p>
        </motion.div>

        {/* Images grid */}
        <div className="grid md:grid-cols-2 gap-6 mb-20">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.1 }}
            className="rounded-2xl overflow-hidden border border-[#ffffff08] bg-[#12121a] p-4"
          >
            <h3 className="text-sm font-medium text-[#f0f0f5] mb-3">
              Cross-Sectional Views (Z-Layers)
            </h3>
            <img
              src="/images/cross_sections.png"
              alt="Cross-sections through the scaffold at different Z-layers showing material distribution"
              className="w-full rounded-lg"
            />
            <p className="text-xs text-[#8888aa] mt-3">
              Horizontal slices through the dome-shaped scaffold reveal the
              PCL+BAG armor shell (silver), Schoen Gyroid GelMA core (green),
              and sacrificial Pluronic channels (blue) at six z-heights.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.2 }}
            className="rounded-2xl overflow-hidden border border-[#ffffff08] bg-[#12121a] p-4"
          >
            <h3 className="text-sm font-medium text-[#f0f0f5] mb-3">
              Material Distribution per Layer
            </h3>
            <img
              src="/images/material_distribution.png"
              alt="Stacked bar chart showing voxel count per material across Z-layers"
              className="w-full rounded-lg"
            />
            <p className="text-xs text-[#8888aa] mt-3">
              Stacked area chart shows the dome profile: armor dominates the
              outer layers while gyroid core peaks in the interior, with
              Pluronic channels distributed through the mid-section.
            </p>
          </motion.div>
        </div>

        {/* G-code + Anisotropy row */}
        <div className="grid md:grid-cols-2 gap-6 mb-20">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.25 }}
            className="rounded-2xl overflow-hidden border border-[#ffffff08] bg-[#12121a] p-4"
          >
            <h3 className="text-sm font-medium text-[#f0f0f5] mb-3">
              Multi-Material G-code
            </h3>
            <div className="relative">
              <pre className="bg-[#0a0a0f] rounded-lg p-4 text-xs font-mono text-[#a8b4c8] overflow-auto max-h-[340px] leading-relaxed border border-[#ffffff06]">
                {GCODE_SAMPLE.split('\n').map((line, i) => {
                  let color = '#a8b4c8'
                  if (line.startsWith(';')) color = '#5a6a5a'
                  else if (line.startsWith('T')) color = '#00d4ff'
                  else if (line.startsWith('G28') || line.startsWith('M')) color = '#e8a030'
                  return (
                    <span key={i} className="block" style={{ color }}>
                      <span className="inline-block w-7 text-right mr-3 text-[#333] select-none">
                        {i + 1}
                      </span>
                      {line}
                    </span>
                  )
                })}
              </pre>
              <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-[#00d4ff]/10 text-[9px] text-[#00d4ff] font-mono">
                .gcode
              </div>
            </div>
            <p className="text-xs text-[#8888aa] mt-3">
              Three-head bioprinter G-code with per-material pressure, speed,
              and nozzle settings. Armor prints first as a retaining wall for
              the soft GelMA hydrogel.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.3 }}
            className="rounded-2xl overflow-hidden border border-[#ffffff08] bg-[#12121a] p-4"
          >
            <h3 className="text-sm font-medium text-[#f0f0f5] mb-3">
              PDL Anisotropy Gradient
            </h3>
            <img
              src="/images/anisotropy_gradient.png"
              alt="Gyroid lattice morphing from isotropic to z-stretched near the root surface"
              className="w-full rounded-lg"
            />
            <p className="text-xs text-[#8888aa] mt-3">
              The Schoen Gyroid is progressively z-stretched near the root
              surface (k=1 → k=3), mimicking the anisotropic collagen
              architecture of the periodontal ligament and guiding Sharpey's
              fiber alignment.
            </p>
          </motion.div>
        </div>

        {/* Biological strategy cards */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.35 }}
        >
          <h3 className="text-xl font-bold text-[#f0f0f5] text-center mb-8">
            Biological Strategy
          </h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {biologicalFacts.map((fact, i) => (
              <motion.div
                key={fact.title}
                initial={{ opacity: 0, y: 30 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: 0.4 + i * 0.1 }}
                className="p-6 rounded-2xl bg-[#12121a] border border-[#ffffff08] hover:border-[#00d4ff]/15 transition-all group"
              >
                <div className="text-3xl mb-4">{fact.icon}</div>
                <h4
                  className="text-lg font-semibold mb-2"
                  style={{ color: fact.color }}
                >
                  {fact.title}
                </h4>
                <p className="text-sm text-[#8888aa] leading-relaxed">
                  {fact.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
