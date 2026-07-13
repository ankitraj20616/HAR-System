import { motion, Variants } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ChartLineUp, ShieldCheck, UserCircle, Heartbeat } from '@phosphor-icons/react';

export default function LandingPage() {
  const navigate = useNavigate();

  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
      },
    },
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 100, damping: 20 } },
  };

  return (
    <div className="min-h-[100dvh] bg-zinc-950 text-zinc-50 selection:bg-brand-500/30 overflow-x-hidden relative">
      {/* Full-screen Animated Ambient Background */}
      <div className="fixed inset-0 z-0 pointer-events-none opacity-60 overflow-hidden bg-zinc-950">
        <motion.div 
          animate={{ 
            rotate: [0, 45, 90, 135, 180, 225, 270, 315, 360],
            scale: [1, 1.1, 1, 1.2, 1],
            x: ["-5%", "5%", "0%", "-5%", "0%", "-5%"],
            y: ["0%", "-5%", "5%", "0%", "-5%", "0%"]
          }}
          transition={{ repeat: Infinity, duration: 30, ease: "linear" }}
          className="absolute inset-[-50%] w-[200%] h-[200%] mix-blend-screen"
        >
          <div className="absolute top-[30%] left-[20%] w-[40vw] h-[40vw] bg-brand-600/40 blur-[120px] rounded-full" />
          <div className="absolute bottom-[20%] right-[30%] w-[50vw] h-[50vw] bg-blue-900/40 blur-[150px] rounded-full" />
          <div className="absolute top-[40%] right-[20%] w-[35vw] h-[35vw] bg-emerald-600/30 blur-[100px] rounded-full" />
        </motion.div>
        {/* Soft noise/glass filter over the blobs */}
        <div className="absolute inset-0 bg-zinc-950/40 backdrop-blur-[60px]" />
      </div>

      <div className="relative z-10">
        {/* Navigation */}
        <nav className="flex justify-between items-center p-6 md:p-10 max-w-7xl mx-auto">
          <div className="flex items-center gap-2">
            <Heartbeat weight="fill" className="text-brand-500 w-8 h-8" />
            <span className="text-xl font-bold tracking-tight">HAR<span className="text-zinc-500">.sys</span></span>
          </div>
          <button 
            onClick={() => navigate('/auth')}
            className="px-6 py-2 rounded-full liquid-glass hover:bg-white/10 transition-colors font-medium text-sm"
          >
            Sign In
          </button>
        </nav>

        {/* Hero Section */}
        <motion.section 
          className="max-w-7xl mx-auto px-6 pt-32 pb-32 md:pt-52 md:pb-52 flex items-center"
          variants={containerVariants}
          initial="hidden"
          animate="show"
        >
          <div className="flex flex-col items-start space-y-8 max-w-3xl relative z-10">
            <motion.div variants={itemVariants} className="px-4 py-1.5 rounded-full border border-brand-500/30 bg-brand-500/10 text-xs font-semibold text-brand-400 tracking-wider uppercase backdrop-blur-md">
              Now with Live AI Vision
            </motion.div>
            
            <motion.h1 variants={itemVariants} className="text-6xl md:text-8xl font-bold tracking-tighter leading-[1.05] text-transparent bg-clip-text bg-gradient-to-br from-zinc-100 via-zinc-300 to-zinc-600 pb-2">
              Human Activity <br />
              <span className="text-brand-500 text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-emerald-400">Reimagined.</span>
            </motion.h1>
            
            <motion.p variants={itemVariants} className="text-xl md:text-2xl text-zinc-400 max-w-[45ch] leading-relaxed font-light">
              Real-time posture tracking, fall detection, and behavioral analysis powered by edge AI. Designed for modern caregiving facilities.
            </motion.p>
            
            <motion.div variants={itemVariants} className="pt-8">
              <button 
                onClick={() => navigate('/auth')}
                className="group relative px-10 py-5 bg-white text-zinc-950 rounded-full font-bold text-lg overflow-hidden transition-all hover:scale-105 active:scale-[0.98] shadow-[0_0_40px_rgba(255,255,255,0.1)]"
              >
                <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-brand-400 to-emerald-400 opacity-0 group-hover:opacity-20 transition-opacity" />
                Start your workspace
              </button>
            </motion.div>
          </div>
        </motion.section>

        {/* Roles / Features Scroll Section */}
        <section className="bg-zinc-900/50 border-t border-white/5 py-32">
          <div className="max-w-7xl mx-auto px-6">
            <motion.div 
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ type: 'spring', stiffness: 100 }}
              className="mb-20 text-center md:text-left"
            >
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight">Built for every care provider.</h2>
              <p className="text-zinc-400 mt-4 max-w-[60ch]">A unified platform that adapts to your exact role, filtering out the noise to show you exactly what matters.</p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  role: "Caregiver",
                  desc: "Live video feeds, instant fall alerts, and current posture status. Focus on immediate response.",
                  icon: <Heartbeat className="w-8 h-8 text-brand-500" />,
                  delay: 0
                },
                {
                  role: "Doctor",
                  desc: "Long-term activity trends, sleep pattern anomalies, and AI-generated clinical feedback.",
                  icon: <ChartLineUp className="w-8 h-8 text-blue-500" />,
                  delay: 0.1
                },
                {
                  role: "Administrator",
                  desc: "Complete system oversight, sensor health monitoring, and secure role-based access control.",
                  icon: <ShieldCheck className="w-8 h-8 text-purple-500" />,
                  delay: 0.2
                }
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-50px" }}
                  transition={{ delay: item.delay, type: 'spring', stiffness: 100 }}
                  className="liquid-glass rounded-[2rem] p-8 hover:bg-white/10 transition-colors cursor-default"
                >
                  <div className="w-14 h-14 rounded-2xl bg-zinc-900/80 flex items-center justify-center border border-white/5 mb-6">
                    {item.icon}
                  </div>
                  <h3 className="text-2xl font-semibold mb-3">{item.role}</h3>
                  <p className="text-zinc-400 leading-relaxed">{item.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 border-t border-white/5 text-center text-zinc-600 text-sm">
          <p>HAR Prototype System • Local AI Edge Deployment</p>
        </footer>
      </div>
    </div>
  );
}
