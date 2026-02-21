export default function Footer() {
  return (
    <footer className="py-12 border-t border-[#ffffff08]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#00d4ff] to-[#00ffd5] flex items-center justify-center">
              <span className="text-[#0a0a0f] font-bold text-xs">G</span>
            </div>
            <span className="text-sm text-[#8888aa]">
              GingivaGen 2.0 — Regenerative Bioprinting Platform
            </span>
          </div>

          <div className="flex items-center gap-6 text-xs text-[#8888aa]/60">
            <span>AI-Driven Scaffold Design</span>
            <span className="w-1 h-1 rounded-full bg-[#8888aa]/30" />
            <span>Multi-Material Bioprinting</span>
            <span className="w-1 h-1 rounded-full bg-[#8888aa]/30" />
            <span>Gum Recession Treatment</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
