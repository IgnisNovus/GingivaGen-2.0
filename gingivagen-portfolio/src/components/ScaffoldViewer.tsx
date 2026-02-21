import { useState, useMemo, Suspense, useRef } from 'react'
import { Canvas, useLoader } from '@react-three/fiber'
import { OrbitControls, Center, Html } from '@react-three/drei'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import * as THREE from 'three'
import { motion, useInView } from 'framer-motion'

const MATERIALS = [
  {
    id: 'armor',
    label: 'PCL+BAG Armor',
    file: '/models/scaffold_preview/PCL_BAG_armor.stl',
    color: '#c8c8dc',
    opacity: 0.45,
    description:
      '0.5 mm protective shell — suture retention & mechanical defense',
  },
  {
    id: 'core',
    label: 'GelMA Gyroid Core',
    file: '/models/scaffold_preview/GelMA_core.stl',
    color: '#64c864',
    opacity: 0.7,
    description:
      'Anisotropic Schoen Gyroid lattice — 325 µm pores for fibroblast migration',
  },
  {
    id: 'pluronic',
    label: 'Pluronic Channels',
    file: '/models/scaffold_preview/Pluronic_channels.stl',
    color: '#6496ff',
    opacity: 0.9,
    description:
      'Sacrificial 400 µm channels — dissolved at 4°C for vascular perfusion',
  },
]

function MaterialMesh({
  file,
  color,
  opacity,
  visible,
}: {
  file: string
  color: string
  opacity: number
  visible: boolean
}) {
  const geometry = useLoader(STLLoader, file)

  const processedGeo = useMemo(() => {
    const g = geometry.clone()
    g.computeVertexNormals()
    return g
  }, [geometry])

  if (!visible) return null

  return (
    <mesh geometry={processedGeo}>
      <meshPhysicalMaterial
        color={color}
        transparent
        opacity={opacity}
        roughness={0.35}
        metalness={0.15}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  )
}

function LoadingIndicator() {
  return (
    <Html center>
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-[#00d4ff]/30 border-t-[#00d4ff] rounded-full animate-spin" />
        <span className="text-sm text-[#8888aa]">Loading scaffold meshes…</span>
      </div>
    </Html>
  )
}

function ScaffoldScene({ visibility }: { visibility: Record<string, boolean> }) {
  return (
    <Center>
      <group>
        {MATERIALS.map((mat) => (
          <MaterialMesh
            key={mat.id}
            file={mat.file}
            color={mat.color}
            opacity={mat.opacity}
            visible={visibility[mat.id]}
          />
        ))}
      </group>
    </Center>
  )
}

export default function ScaffoldViewer() {
  const [visibility, setVisibility] = useState<Record<string, boolean>>({
    armor: true,
    core: true,
    pluronic: true,
  })

  const sectionRef = useRef(null)
  const inView = useInView(sectionRef, { once: true, margin: '-100px' })

  const toggleMat = (id: string) => {
    setVisibility((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <section id="scaffold" className="py-32 relative">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          ref={sectionRef}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-4"
        >
          <span className="text-xs text-[#00d4ff] tracking-widest uppercase font-medium">
            Patient-Specific Output
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-[#f0f0f5] mt-3 mb-4">
            Multi-Material Scaffold
          </h2>
          <p className="text-[#8888aa] max-w-2xl mx-auto">
            The scaffold is contoured to the patient's defect geometry — not a
            generic block. Marching cubes extracts smooth, anatomically-fitted
            surfaces from the voxel grid, producing a shape that seats directly
            onto the exposed root without surgical trimming.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-[1fr_320px] gap-6 mt-10">
          {/* 3D Viewer */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.2 }}
            className="relative rounded-2xl overflow-hidden border border-[#ffffff08] bg-[#12121a] glow-border"
            style={{ height: '600px' }}
          >
            <Canvas
              camera={{
                fov: 45,
                near: 0.001,
                far: 500,
                position: [0, 0, 15],
              }}
              gl={{ antialias: true }}
              dpr={[1, 2]}
            >
              <color attach="background" args={['#0d0d14']} />
              <ambientLight intensity={0.5} />
              <directionalLight position={[20, 20, 20]} intensity={0.7} />
              <directionalLight position={[-10, -10, 10]} intensity={0.3} />
              <pointLight position={[0, 0, 30]} intensity={0.3} color="#64c864" />

              <Suspense fallback={<LoadingIndicator />}>
                <ScaffoldScene visibility={visibility} />
              </Suspense>

              <OrbitControls enableDamping dampingFactor={0.05} />
            </Canvas>

            <div className="absolute bottom-4 left-4 flex items-center gap-2 text-xs text-[#8888aa]/50">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
              </svg>
              Drag to rotate · Scroll to zoom
            </div>
          </motion.div>

          {/* Material controls sidebar */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.3 }}
            className="flex flex-col gap-4"
          >
            {MATERIALS.map((mat) => (
              <button
                key={mat.id}
                onClick={() => toggleMat(mat.id)}
                className={`text-left p-4 rounded-xl border transition-all duration-300 ${
                  visibility[mat.id]
                    ? 'bg-[#12121a] border-[#ffffff15]'
                    : 'bg-[#0a0a0f] border-[#ffffff08] opacity-50'
                } hover:border-[#00d4ff]/20`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className="w-4 h-4 rounded-full flex-shrink-0"
                    style={{
                      backgroundColor: visibility[mat.id] ? mat.color : '#333',
                      boxShadow: visibility[mat.id]
                        ? `0 0 10px ${mat.color}50`
                        : 'none',
                    }}
                  />
                  <span className="font-medium text-sm text-[#f0f0f5]">
                    {mat.label}
                  </span>
                  <span
                    className={`ml-auto text-xs px-2 py-0.5 rounded-full ${
                      visibility[mat.id]
                        ? 'bg-[#00d4ff]/10 text-[#00d4ff]'
                        : 'bg-[#333]/30 text-[#666]'
                    }`}
                  >
                    {visibility[mat.id] ? 'ON' : 'OFF'}
                  </span>
                </div>
                <p className="text-xs text-[#8888aa] leading-relaxed pl-7">
                  {mat.description}
                </p>
              </button>
            ))}

            <div className="mt-2 p-4 rounded-xl bg-[#12121a] border border-[#ffffff08]">
              <h4 className="text-sm font-medium text-[#f0f0f5] mb-3">
                Scaffold Specifications
              </h4>
              <div className="space-y-2">
                {[
                  ['Pore Size', '325 ± 25 µm'],
                  ['Armor Thickness', '0.5 mm'],
                  ['Channel Diameter', '400 µm'],
                  ['Voxel Resolution', '50 µm'],
                  ['Gyroid Cell Size', '2.0 mm'],
                  ['Stiffness Target', '< 15 KPa'],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between text-xs">
                    <span className="text-[#8888aa]">{label}</span>
                    <span className="text-[#00d4ff] font-mono">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
