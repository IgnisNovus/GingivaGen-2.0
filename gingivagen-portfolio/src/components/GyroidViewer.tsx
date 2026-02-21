import { useRef, useMemo, Suspense } from 'react'
import { Canvas, useLoader, useFrame } from '@react-three/fiber'
import { OrbitControls, Center, Html } from '@react-three/drei'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import * as THREE from 'three'
import { motion, useInView } from 'framer-motion'

function GyroidMesh() {
  const geometry = useLoader(STLLoader, '/models/gyroid_gradient.stl')
  const meshRef = useRef<THREE.Mesh>(null)

  const geo = useMemo(() => {
    const g = geometry.clone()
    g.computeVertexNormals()

    // Color gradient: green (isotropic, left) → cyan (stretched, right)
    const pos = g.attributes.position
    const colors = new Float32Array(pos.count * 3)
    const bbox = new THREE.Box3().setFromBufferAttribute(pos)
    const xMin = bbox.min.x
    const xRange = bbox.max.x - bbox.min.x

    for (let i = 0; i < pos.count; i++) {
      const t = (pos.getX(i) - xMin) / xRange // 0=left(iso), 1=right(root)
      colors[i * 3] = 0.39 * (1 - t) + 0.0 * t      // R
      colors[i * 3 + 1] = 0.78 * (1 - t) + 0.83 * t  // G
      colors[i * 3 + 2] = 0.39 * (1 - t) + 1.0 * t   // B
    }
    g.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return g
  }, [geometry])

  useFrame(({ clock }) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = clock.getElapsedTime() * 0.15
    }
  })

  return (
    <mesh ref={meshRef} geometry={geo}>
      <meshPhysicalMaterial
        vertexColors
        roughness={0.25}
        metalness={0.15}
        side={THREE.DoubleSide}
        clearcoat={0.3}
        clearcoatRoughness={0.2}
      />
    </mesh>
  )
}

function LoadingIndicator() {
  return (
    <Html center>
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-[#64c864]/30 border-t-[#64c864] rounded-full animate-spin" />
        <span className="text-sm text-[#8888aa]">Loading gyroid…</span>
      </div>
    </Html>
  )
}

export default function GyroidViewer() {
  const sectionRef = useRef(null)
  const inView = useInView(sectionRef, { once: true, margin: '-100px' })

  return (
    <section id="gyroid" className="py-32 relative">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          ref={sectionRef}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-12"
        >
          <span className="text-xs text-[#00d4ff] tracking-widest uppercase font-medium">
            Microscopic Architecture
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-[#f0f0f5] mt-3 mb-4">
            Schoen Gyroid TPMS Lattice
          </h2>
          <p className="text-[#8888aa] max-w-2xl mx-auto">
            The scaffold's internal structure uses a Triply Periodic Minimal
            Surface (TPMS) — the Schoen Gyroid — with a{' '}
            <strong className="text-[#f0f0f5]">
              spatially varying anisotropy
            </strong>
            . Near the root surface, the lattice is z-stretched (k=3×) to guide
            Sharpey's fiber alignment; further away it relaxes to isotropic
            pores for uniform cell migration. Computed via the{' '}
            <a
              href="https://github.com/TPMS-Lisbon-Lab/LisbonTPMStool"
              target="_blank"
              rel="noopener"
              className="text-[#00d4ff] hover:underline"
            >
              LisbonTPMS tool
            </a>
            .
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-[1fr_380px] gap-6">
          {/* Gyroid 3D viewer */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.2 }}
            className="relative rounded-2xl overflow-hidden border border-[#ffffff08] bg-[#12121a] glow-border"
            style={{ height: '500px' }}
          >
            <Canvas
              camera={{ fov: 50, near: 0.01, far: 100, position: [5, 4, 5] }}
              gl={{ antialias: true }}
              dpr={[1, 2]}
            >
              <color attach="background" args={['#0d0d14']} />
              <ambientLight intensity={0.4} />
              <directionalLight position={[5, 8, 5]} intensity={0.8} />
              <directionalLight position={[-5, -3, -5]} intensity={0.3} />
              <pointLight position={[0, 5, 0]} intensity={0.3} color="#64c864" />

              <Suspense fallback={<LoadingIndicator />}>
                <Center>
                  <GyroidMesh />
                </Center>
              </Suspense>

              <OrbitControls enableDamping dampingFactor={0.05} />
            </Canvas>

            <div className="absolute top-4 left-4 bg-[#0a0a0f]/80 backdrop-blur-sm rounded-xl px-3 py-2 border border-[#ffffff08]">
              <span className="text-xs text-[#64c864] font-mono">
                cos(x)·sin(y) + cos(y)·sin(z/k) + cos(z/k)·sin(x) = t
              </span>
            </div>

            <div className="absolute bottom-4 left-4 flex items-center gap-3 bg-[#0a0a0f]/80 backdrop-blur-sm rounded-xl px-3 py-2 border border-[#ffffff08]">
              <span className="text-xs text-[#64c864]">Isotropic (k=1)</span>
              <div className="w-24 h-2 rounded-full" style={{
                background: 'linear-gradient(to right, #64c864, #00d4ff)'
              }} />
              <span className="text-xs text-[#00d4ff]">Root (k=3)</span>
            </div>
          </motion.div>

          {/* Info panel */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: 0.3 }}
            className="flex flex-col gap-4"
          >
            <div className="p-5 rounded-xl bg-[#12121a] border border-[#ffffff08]">
              <h4 className="text-sm font-semibold text-[#f0f0f5] mb-3">
                Why Gyroid TPMS?
              </h4>
              <ul className="space-y-3 text-xs text-[#8888aa] leading-relaxed">
                <li className="flex gap-2">
                  <span className="text-[#64c864] mt-0.5">●</span>
                  <span>
                    <strong className="text-[#f0f0f5]">
                      Zero mean curvature
                    </strong>{' '}
                    — minimises stress concentrations and provides uniform
                    mechanical load distribution
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-[#64c864] mt-0.5">●</span>
                  <span>
                    <strong className="text-[#f0f0f5]">
                      Full interconnectivity
                    </strong>{' '}
                    — every pore connects to every other, ensuring nutrient
                    perfusion and waste removal throughout the scaffold
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-[#64c864] mt-0.5">●</span>
                  <span>
                    <strong className="text-[#f0f0f5]">
                      Tunable porosity
                    </strong>{' '}
                    — adjusting the isovalue t controls pore size from 200–500 µm
                    while maintaining structural integrity
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-[#64c864] mt-0.5">●</span>
                  <span>
                    <strong className="text-[#f0f0f5]">PDL anisotropy</strong> —
                    z-axis stretching near the root surface mimics Sharpey's
                    fiber insertion angles for natural attachment
                  </span>
                </li>
              </ul>
            </div>

            <div className="p-5 rounded-xl bg-[#12121a] border border-[#ffffff08]">
              <h4 className="text-sm font-semibold text-[#f0f0f5] mb-3">
                TPMS Parameters
              </h4>
              <div className="space-y-2">
                {[
                  ['Surface Type', 'Schoen Gyroid'],
                  ['Cell Size', '2.0 mm'],
                  ['Target Pore', '325 µm'],
                  ['Tolerance', '± 25 µm'],
                  ['Isovalue (t)', '~0.35'],
                  ['PDL Stretch (k)', '3.0×'],
                  ['Decay Length', '2.0 mm'],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between text-xs">
                    <span className="text-[#8888aa]">{label}</span>
                    <span className="text-[#64c864] font-mono">{value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-5 rounded-xl bg-[#12121a] border border-[#00d4ff]/10">
              <h4 className="text-sm font-semibold text-[#f0f0f5] mb-2">
                Biological Target
              </h4>
              <p className="text-xs text-[#8888aa] leading-relaxed">
                325 µm mean pore size is the sweet spot for gingival fibroblast
                migration (Zeltinger 2001). Smaller pores restrict cell
                infiltration; larger pores reduce surface area for attachment and
                slow tissue ingrowth.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
