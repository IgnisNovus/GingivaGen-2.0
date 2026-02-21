import { useState, useMemo, useEffect, Suspense, useRef } from 'react'
import { Canvas, useLoader, useThree } from '@react-three/fiber'
import { OrbitControls, Center, Html } from '@react-three/drei'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import * as THREE from 'three'
import { motion, useInView } from 'framer-motion'

function extractAndPrepare(obj: THREE.Group): THREE.BufferGeometry | null {
  let geo: THREE.BufferGeometry | null = null
  obj.traverse((child) => {
    if (child instanceof THREE.Mesh && child.geometry) {
      geo = child.geometry
    }
  })
  if (geo) (geo as THREE.BufferGeometry).computeVertexNormals()
  return geo
}

function JawScene({
  showOriginal,
  showTeeth,
  showGingiva,
  showDefect,
  showScaffold,
}: {
  showOriginal: boolean
  showTeeth: boolean
  showGingiva: boolean
  showDefect: boolean
  showScaffold: boolean
}) {
  // Preload ALL meshes upfront so toggles are instant
  const originalObj = useLoader(OBJLoader, '/models/jaw_parts/original_scan.obj')
  const teethObj = useLoader(OBJLoader, '/models/jaw_parts/teeth.obj')
  const gingivaObj = useLoader(OBJLoader, '/models/jaw_parts/gingiva.obj')
  const healthyObj = useLoader(OBJLoader, '/models/jaw_parts/gingiva_healthy.obj')
  const defectObj = useLoader(OBJLoader, '/models/jaw_parts/defect.obj')
  const idealObj = useLoader(OBJLoader, '/models/jaw_parts/ideal_volume.obj')
  const { camera } = useThree()

  const originalGeo = useMemo(() => extractAndPrepare(originalObj), [originalObj])
  const teethGeo = useMemo(() => extractAndPrepare(teethObj), [teethObj])
  const gingivaGeo = useMemo(() => extractAndPrepare(gingivaObj), [gingivaObj])
  const healthyGeo = useMemo(() => extractAndPrepare(healthyObj), [healthyObj])
  const defectGeo = useMemo(() => extractAndPrepare(defectObj), [defectObj])
  const idealGeo = useMemo(() => extractAndPrepare(idealObj), [idealObj])

  // Auto-frame camera on load
  useEffect(() => {
    const geo = teethGeo || gingivaGeo
    if (!geo) return
    geo.computeBoundingBox()
    const center = new THREE.Vector3()
    const size = new THREE.Vector3()
    geo.boundingBox!.getCenter(center)
    geo.boundingBox!.getSize(size)
    const maxDim = Math.max(size.x, size.y, size.z)
    camera.position.set(center.x, center.y - maxDim * 0.3, center.z + maxDim * 1.1)
    camera.lookAt(center)
    camera.updateProjectionMatrix()
  }, [teethGeo, gingivaGeo, camera])

  return (
    <Center>
      <group rotation={[Math.PI * 0.55, 0, 0]}>
        {/* Original unsegmented scan */}
        {showOriginal && originalGeo && (
          <mesh geometry={originalGeo}>
            <meshStandardMaterial
              color="#d9d2cc"
              roughness={0.4}
              metalness={0.05}
              side={THREE.DoubleSide}
            />
          </mesh>
        )}

        {/* Teeth — white enamel */}
        {showTeeth && !showOriginal && teethGeo && (
          <mesh geometry={teethGeo}>
            <meshStandardMaterial
              color="#f5f5f0"
              roughness={0.2}
              metalness={0.05}
              side={THREE.DoubleSide}
            />
          </mesh>
        )}

        {/* Gingiva — shown as one piece when defect overlay is OFF */}
        {showGingiva && !showDefect && !showOriginal && gingivaGeo && (
          <mesh geometry={gingivaGeo}>
            <meshStandardMaterial
              color="#d46a8a"
              roughness={0.6}
              metalness={0.0}
              side={THREE.DoubleSide}
            />
          </mesh>
        )}

        {/* When defect is ON: healthy gingiva + glowing defect */}
        {showGingiva && showDefect && !showOriginal && (
          <>
            {healthyGeo && (
              <mesh geometry={healthyGeo}>
                <meshStandardMaterial
                  color="#d46a8a"
                  roughness={0.6}
                  metalness={0.0}
                  side={THREE.DoubleSide}
                />
              </mesh>
            )}
            {defectGeo && (
              <mesh geometry={defectGeo}>
                <meshStandardMaterial
                  color="#00d4ff"
                  roughness={0.1}
                  metalness={0.3}
                  side={THREE.DoubleSide}
                  transparent
                  opacity={0.7}
                  emissive="#00d4ff"
                  emissiveIntensity={0.5}
                  depthWrite={false}
                />
              </mesh>
            )}
          </>
        )}

        {/* Defect visible even without gingiva (solo) */}
        {!showGingiva && showDefect && defectGeo && (
          <mesh geometry={defectGeo}>
            <meshStandardMaterial
              color="#00d4ff"
              roughness={0.1}
              metalness={0.3}
              side={THREE.DoubleSide}
              emissive="#00d4ff"
              emissiveIntensity={0.6}
            />
          </mesh>
        )}

        {/* RBF-reconstructed scaffold surface */}
        {showScaffold && idealGeo && (
          <mesh geometry={idealGeo}>
            <meshStandardMaterial
              color="#33e688"
              roughness={0.2}
              metalness={0.1}
              side={THREE.DoubleSide}
              transparent
              opacity={0.75}
              emissive="#33e688"
              emissiveIntensity={0.4}
              depthWrite={false}
            />
          </mesh>
        )}
      </group>
    </Center>
  )
}

function LoadingIndicator() {
  return (
    <Html center>
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-[#00d4ff]/30 border-t-[#00d4ff] rounded-full animate-spin" />
        <span className="text-sm text-[#8888aa]">Loading 3D scan…</span>
      </div>
    </Html>
  )
}

function ToggleButton({
  active,
  onClick,
  color,
  label,
}: {
  active: boolean
  onClick: () => void
  color: string
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm transition-all ${
        active
          ? 'bg-[#1a1a2e] border border-[#00d4ff]/30 text-[#f0f0f5]'
          : 'bg-[#12121a] border border-[#ffffff08] text-[#8888aa] opacity-60'
      } hover:border-[#00d4ff]/40`}
    >
      <span
        className="w-3 h-3 rounded-full"
        style={{
          backgroundColor: active ? color : '#333',
          boxShadow: active ? `0 0 8px ${color}40` : 'none',
        }}
      />
      {label}
    </button>
  )
}

export default function ScanViewer() {
  const [showOriginal, setShowOriginal] = useState(false)
  const [showTeeth, setShowTeeth] = useState(true)
  const [showGingiva, setShowGingiva] = useState(true)
  const [showDefect, setShowDefect] = useState(false)
  const [showScaffold, setShowScaffold] = useState(false)
  const sectionRef = useRef(null)
  const inView = useInView(sectionRef, { once: true, margin: '-100px' })

  return (
    <section id="scanner" className="py-32 relative">
      <div className="max-w-7xl mx-auto px-6">
        <motion.div
          ref={sectionRef}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-12"
        >
          <span className="text-xs text-[#00d4ff] tracking-widest uppercase font-medium">
            Interactive Viewer
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-[#f0f0f5] mt-3 mb-4">
            3D Intraoral Scan
          </h2>
          <p className="text-[#8888aa] max-w-xl mx-auto">
            Explore the patient's upper jaw with AI-driven segmentation.
            Toggle tissue layers and highlight the recession defect where
            the scaffold will be placed.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2 }}
          className="relative"
        >
          <div className="flex flex-wrap justify-center gap-3 mb-6">
            <ToggleButton
              active={showOriginal}
              onClick={() => setShowOriginal(!showOriginal)}
              color="#d9d2cc"
              label="Original Scan"
            />
            <ToggleButton
              active={showTeeth}
              onClick={() => setShowTeeth(!showTeeth)}
              color="#f5f5f0"
              label="Teeth"
            />
            <ToggleButton
              active={showGingiva}
              onClick={() => setShowGingiva(!showGingiva)}
              color="#d46a8a"
              label="Gingiva"
            />
            <ToggleButton
              active={showDefect}
              onClick={() => setShowDefect(!showDefect)}
              color="#00d4ff"
              label="Defect Region"
            />
            <ToggleButton
              active={showScaffold}
              onClick={() => setShowScaffold(!showScaffold)}
              color="#33e688"
              label="Scaffold"
            />
          </div>

          <div
            className="relative rounded-2xl overflow-hidden border border-[#ffffff08] bg-[#12121a] glow-border"
            style={{ height: '600px' }}
          >
            <Canvas
              camera={{ fov: 45, near: 0.1, far: 2000 }}
              gl={{ antialias: true, alpha: true }}
              dpr={[1, 2]}
            >
              <color attach="background" args={['#0d0d14']} />
              <ambientLight intensity={0.5} />
              <directionalLight position={[10, 10, 10]} intensity={0.9} />
              <directionalLight position={[-10, -5, -10]} intensity={0.3} />
              <pointLight position={[0, 20, 0]} intensity={0.3} color="#ffffff" />

              <Suspense fallback={<LoadingIndicator />}>
                <JawScene
                  showOriginal={showOriginal}
                  showTeeth={showTeeth}
                  showGingiva={showGingiva}
                  showDefect={showDefect}
                  showScaffold={showScaffold}
                />
              </Suspense>

              <OrbitControls
                enableDamping
                dampingFactor={0.05}
                minDistance={10}
                maxDistance={200}
                enablePan
              />
            </Canvas>

            <div className="absolute bottom-4 left-4 flex items-center gap-2 text-xs text-[#8888aa]/50">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
              </svg>
              Drag to rotate · Scroll to zoom · Shift+drag to pan
            </div>

            <div className="absolute top-4 right-4 bg-[#0a0a0f]/80 backdrop-blur-sm rounded-xl p-3 border border-[#ffffff08]">
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-[#d9d2cc]" />
                  <span className="text-[#8888aa]">Original Scan</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-[#f5f5f0]" />
                  <span className="text-[#8888aa]">Teeth (AI segmented)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-[#d46a8a]" />
                  <span className="text-[#8888aa]">Healthy Gingiva</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-[#00d4ff]" />
                  <span className="text-[#8888aa]">Recession Defect</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-[#33e688]" />
                  <span className="text-[#8888aa]">RBF Scaffold</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
