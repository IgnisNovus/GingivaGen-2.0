import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const navLinks = [
  { label: 'Process', href: '#process' },
  { label: '3D Scanner', href: '#scanner' },
  { label: 'Scaffold', href: '#scaffold' },
  { label: 'Gyroid', href: '#gyroid' },
  { label: 'Tech Stack', href: '#tech' },
  { label: 'Data', href: '#data' },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-[#00d4ff]/10'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <a href="#" className="flex items-center gap-3 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00d4ff] to-[#00ffd5] flex items-center justify-center">
            <span className="text-[#0a0a0f] font-bold text-sm">G</span>
          </div>
          <span className="text-lg font-semibold text-[#f0f0f5] group-hover:text-[#00d4ff] transition-colors">
            GingivaGen
          </span>
        </a>

        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-[#8888aa] hover:text-[#00d4ff] transition-colors relative group"
            >
              {link.label}
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-[#00d4ff] transition-all group-hover:w-full" />
            </a>
          ))}
        </div>

        <button
          className="md:hidden text-[#8888aa] hover:text-[#00d4ff]"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
            {mobileOpen ? (
              <path d="M6 6l12 12M6 18L18 6" />
            ) : (
              <path d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden bg-[#0a0a0f]/95 backdrop-blur-xl border-b border-[#00d4ff]/10 overflow-hidden"
          >
            <div className="px-6 py-4 flex flex-col gap-4">
              {navLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="text-[#8888aa] hover:text-[#00d4ff] transition-colors"
                  onClick={() => setMobileOpen(false)}
                >
                  {link.label}
                </a>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  )
}
