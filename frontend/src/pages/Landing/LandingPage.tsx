import { Link } from 'react-router-dom';
import { Brain, Users, Shield, Zap, Settings, ArrowRight, SearchCode } from 'lucide-react';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#201E25] font-['Montserrat',sans-serif] text-white overflow-x-hidden relative">
      {/* Background Graphic/Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-[#6C48C3]/20 to-transparent blur-3xl rounded-full pointer-events-none -z-10"></div>

      {/* Navigation (Simple) */}
      <nav className="container mx-auto px-6 py-8 flex items-center justify-between relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[#6C48C3] rounded-xl flex items-center justify-center shadow-lg shadow-[#6C48C3]/30">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-[#C530EA] to-[#11D5F7] text-transparent bg-clip-text">
            AgenticAI
          </span>
        </div>
        <div>
          <Link
            to="/login"
            className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
          >
            Sign In
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="container mx-auto px-6 pt-24 pb-20 relative z-10">
        <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-8 max-w-7xl mx-auto">
          {/* Left: Text Content */}
          <div className="flex-1 text-center lg:text-left">
            <h1 className="text-5xl md:text-6xl font-bold leading-tight mb-8">
              Transforming businesses with <br className="hidden lg:block" />
              <span className="bg-gradient-to-r from-[#C530EA] to-[#11D5F7] text-transparent bg-clip-text">personalized experiences</span> <br className="hidden lg:block" />
              & predictive analytics.
            </h1>

            <p className="text-lg md:text-xl text-gray-400 mb-12 max-w-2xl mx-auto lg:mx-0">
              From Days to Minutes: How AgenticAI is Automating the Art of Deep Research.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4">
              <Link
                to="/login"
                className="bg-[#6C48C3] hover:bg-[#5b3da6] text-white px-8 py-4 rounded font-semibold text-lg transition-all transform hover:-translate-y-1 shadow-[0_4px_15px_rgba(108,72,195,0.4)] hover:shadow-[0_8px_25px_rgba(108,72,195,0.6)] flex items-center gap-2"
              >
                Try AgenticAI <span className="text-xl leading-none">&rarr;</span>
              </Link>
            </div>
          </div>

          {/* Right: Video Section */}
          <div className="flex-1 w-full relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-[#C530EA] to-[#11D5F7] rounded-2xl blur opacity-30 group-hover:opacity-50 transition duration-1000"></div>
            <div className="relative aspect-video bg-[#071217] rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
              <iframe 
                width="100%" 
                height="100%" 
                src="https://www.youtube.com/embed/dQw4w9WgXcQ" 
                title="AgenticAI Overview Video" 
                frameBorder="0" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowFullScreen
                className="w-full h-full object-cover"
              ></iframe>
            </div>
          </div>
        </div>
      </main>

      {/* Subtle overlay elements */}
      <div className="absolute top-[20%] left-0 w-64 h-64 bg-[#11D5F7]/10 blur-[100px] rounded-full pointer-events-none -z-10"></div>
      <div className="absolute top-[40%] right-0 w-96 h-96 bg-[#C530EA]/10 blur-[120px] rounded-full pointer-events-none -z-10"></div>

      {/* Introduction Section */}
      <section className="container mx-auto px-6 py-20 relative z-10 border-t border-white/5 mt-10">
        <div className="max-w-4xl mx-auto flex flex-col items-center text-center">
          <div className="w-16 h-16 bg-[#071217] border border-white/10 rounded-2xl flex items-center justify-center mb-6 text-[#11D5F7] shadow-lg">
            <SearchCode className="w-8 h-8" />
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-6 text-white">The Research Bottleneck</h2>
          <div className="space-y-6 text-gray-400 text-lg leading-relaxed text-left">
            <p>
              For the modern analyst, the "grind" is rarely about high-level thinking; it is a battle against tab-hell and PDF-fatigue. The traditional research model—defined by the billable hour and a burnout-heavy cycle of manual data scavenging—is failing to keep pace with the speed of global markets. We have reached a point where information is infinite, but human cognitive bandwidth remains a static, expensive resource.
            </p>
            <p>
              AgenticAI enters this landscape not as another search tool, but as an autonomous <span className="text-[#C530EA] font-semibold">"research factory."</span> By orchestrating a swarm of intelligent agents, it transforms a multi-day slog into a streamlined process that takes only minutes. It promises an asymmetric advantage for the tech-forward enterprise: the ability to move from a complex query to a boardroom-ready report with almost zero manual intervention.
            </p>
          </div>
        </div>
      </section>

      {/* Takeaways Grid */}
      <section className="container mx-auto px-6 py-20 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">

          {/* Takeaway 1 */}
          <div className="bg-[#071217] border border-white/10 rounded-[10px] p-8 md:p-10 transition-transform duration-300 hover:-translate-y-2 hover:shadow-[0_10px_30px_rgba(108,72,195,0.15)] relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-[#11D5F7]/20 to-transparent blur-2xl group-hover:from-[#11D5F7]/30 transition-colors"></div>
            <div className="w-12 h-12 bg-[#201E25] rounded-xl flex items-center justify-center mb-6 border border-white/5 text-[#11D5F7]">
              <Users className="w-6 h-6" />
            </div>
            <h3 className="text-2xl font-bold mb-4">The Power of Simulated Perspectives</h3>
            <p className="text-gray-400 mb-4 leading-relaxed">
              The sophistication begins with its "Analyst Creation" phase. Rather than executing a linear keyword search, the system generates a team of analytical personas specifically tailored to the nuances of the user’s topic. They engage in multi-turn, simulated interviews, autonomously querying the web in real-time to challenge and refine their findings.
            </p>
            <p className="text-gray-400 leading-relaxed mb-6">
              This mimics the operational velocity of a high-level focus group, transforming research from a passive retrieval task into an active, dialectic inquiry.
            </p>
            <div className="border-l-2 border-[#11D5F7] pl-4 italic text-sm text-gray-300">
              "Conduct multi-turn, simulated interviews to gather diverse perspectives on a given topic."
            </div>
          </div>

          {/* Takeaway 2 */}
          <div className="bg-[#071217] border border-white/10 rounded-[10px] p-8 md:p-10 transition-transform duration-300 hover:-translate-y-2 hover:shadow-[0_10px_30px_rgba(197,48,234,0.15)] relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-[#C530EA]/20 to-transparent blur-2xl group-hover:from-[#C530EA]/30 transition-colors"></div>
            <div className="w-12 h-12 bg-[#201E25] rounded-xl flex items-center justify-center mb-6 border border-white/5 text-[#C530EA]">
              <Shield className="w-6 h-6" />
            </div>
            <h3 className="text-2xl font-bold mb-4">Erasing the "Human Bias" from Analysis</h3>
            <p className="text-gray-400 mb-4 leading-relaxed">
              In the traditional research cycle, the "echo chamber" is an ever-present risk. AgenticAI architecturalizes a solution to this problem through its multi-agent swarm, which effectively acts as an automated peer-review system.
            </p>
            <p className="text-gray-400 leading-relaxed">
              By gathering diverse perspectives autonomously, the system acts as a hedge against narrow-mindedness. Embedded in its technical foundation is a "bias detector" within the database schema to track and mitigate skewed outputs. AI doesn't just mimic human intelligence—it cleanses the research process of human subjectivity.
            </p>
          </div>

          {/* Takeaway 3 */}
          <div className="bg-[#071217] border border-white/10 rounded-[10px] p-8 md:p-10 transition-transform duration-300 hover:-translate-y-2 hover:shadow-[0_10px_30px_rgba(108,72,195,0.15)] relative overflow-hidden group">
            <div className="absolute bottom-0 left-0 w-32 h-32 bg-gradient-to-tr from-[#6C48C3]/20 to-transparent blur-2xl group-hover:from-[#6C48C3]/30 transition-colors"></div>
            <div className="w-12 h-12 bg-[#201E25] rounded-xl flex items-center justify-center mb-6 border border-white/5 text-[#6C48C3]">
              <Zap className="w-6 h-6" />
            </div>
            <h3 className="text-2xl font-bold mb-4">The 90% Efficiency Leap</h3>
            <p className="text-gray-400 mb-4 leading-relaxed">
              The "so what" for any business leader is found in a single, staggering metric: AgenticAI reduces research and report generation time by up to 90%. Waiting three days for a comprehensive market analysis is a luxury few can afford.
            </p>
            <p className="text-gray-400 leading-relaxed">
              This efficiency leap represents a fundamental shift in professional work. By automating the heavy lifting of data synthesis, organizations can pivot their talent away from the "gatherer" role and toward "strategy and action"—the high-value tasks that actually drive growth and innovation.
            </p>
          </div>

          {/* Takeaway 4 */}
          <div className="bg-[#071217] border border-white/10 rounded-[10px] p-8 md:p-10 transition-transform duration-300 hover:-translate-y-2 hover:shadow-[0_10px_30px_rgba(17,213,247,0.15)] relative overflow-hidden group">
            <div className="absolute bottom-0 right-0 w-32 h-32 bg-gradient-to-tl from-[#11D5F7]/20 to-transparent blur-2xl group-hover:from-[#11D5F7]/30 transition-colors"></div>
            <div className="w-12 h-12 bg-[#201E25] rounded-xl flex items-center justify-center mb-6 border border-white/5 text-[#11D5F7]">
              <Settings className="w-6 h-6" />
            </div>
            <h3 className="text-2xl font-bold mb-4">A Seamless End-to-End "Research Factory"</h3>
            <p className="text-gray-400 mb-4 leading-relaxed">
              The technical elegance of the system lies in its orchestration. Built on a stack featuring LangGraph and LangChain, AgenticAI manages a complex pipeline that begins at a React-based UI and terminates in a professionally formatted PDF via FPDF2.
            </p>
            <p className="text-gray-400 leading-relaxed mb-6">
              The agents utilize tools like Tavily for precision web searching, yfinance for real-time market data, and YouTube Search for multimedia context. This ensures that the final output is a rigorous, multi-source document.
            </p>
            <div className="border-l-2 border-[#11D5F7] pl-4 italic text-sm text-gray-300">
              "Synthesize findings into structured, professional, and comprehensive PDF reports."
            </div>
          </div>

        </div>
      </section>

      {/* Conclusion Section */}
      <section className="container mx-auto px-6 py-24 relative z-10 border-t border-white/5 mb-20">
        <div className="max-w-4xl mx-auto bg-gradient-to-br from-[#201E25] to-[#071217] border border-white/10 p-10 md:p-14 rounded-2xl text-center relative overflow-hidden shadow-2xl">
          <div className="absolute inset-0 bg-gradient-to-r from-[#C530EA]/10 to-[#11D5F7]/10 opacity-50 mix-blend-overlay"></div>

          <h2 className="text-3xl md:text-4xl font-bold mb-8 relative z-10">The Future of Agentic Work</h2>

          <div className="text-gray-300 text-lg leading-relaxed space-y-6 max-w-3xl mx-auto relative z-10">
            <p>
              AgenticAI is a harbinger of the "Agentic Economy," where the role of the human professional shifts from being a producer of information to an editor and strategist of autonomous outputs. As the burden of data collection vanishes, the value of a professional will increasingly be measured by the quality of the questions they ask and the speed at which they can turn insights into execution.
            </p>
            <p>
              For the executive, the value proposition is clear: you are no longer limited by the number of hours your analysts can spend in front of a screen. If an autonomous agent can handle 90% of your research load, the only remaining question is a strategic one:
            </p>
            <p className="text-xl font-semibold text-white pt-4 pb-8">
              "How will you spend the 90% of the time you just won back?"
            </p>

            <Link
              to="/login"
              className="inline-flex items-center gap-2 bg-white text-[#071217] px-8 py-4 rounded font-semibold text-lg hover:bg-gray-200 transition-colors shadow-lg"
            >
              Start using AgenticAI <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
