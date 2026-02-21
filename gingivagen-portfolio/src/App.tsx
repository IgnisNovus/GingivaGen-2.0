import Navbar from './components/Navbar'
import Hero from './components/Hero'
import ProcessSection from './components/ProcessSection'
import ScanViewer from './components/ScanViewer'
import ScaffoldViewer from './components/ScaffoldViewer'
import GyroidViewer from './components/GyroidViewer'
import TechStack from './components/TechStack'
import DataSection from './components/DataSection'
import Footer from './components/Footer'

export default function App() {
  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <Navbar />
      <Hero />
      <ProcessSection />
      <ScanViewer />
      <ScaffoldViewer />
      <GyroidViewer />
      <TechStack />
      <DataSection />
      <Footer />
    </div>
  )
}
