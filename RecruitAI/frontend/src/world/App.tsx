import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  BarChart3,
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  ChevronRight,
  CircleUserRound,
  Clock3,
  Heart,
  LineChart,
  Mail,
  Menu,
  MessageSquareText,
  Search,
  ShieldCheck,
  Sparkles,
  UsersRound,
  X,
} from 'lucide-react'

type ProductId = 'hire' | 'invite' | 'quant'

type Product = {
  id: ProductId
  name: string
  eyebrow: string
  headline: string
  description: string
  features: string[]
  accent: string
}

const products: Product[] = [
  {
    id: 'hire',
    name: 'HaViHire',
    eyebrow: 'People. Potential. Progress.',
    headline: 'AI Recruiting Platform for Modern Hiring Teams',
    description:
      'Recruiter-first ATS + CRM with explainable candidate matching, interviews, pipeline automation, and actionable analytics.',
    features: ['AI Candidate Matching', 'ATS + CRM', 'Interviews & Analytics', 'Built for Speed & Quality'],
    accent: 'hire',
  },
  {
    id: 'invite',
    name: 'HaViInvite',
    eyebrow: 'Moments. People. Together.',
    headline: 'Beautiful Invitations, RSVP & Reminders',
    description:
      'Create premium invitation experiences, manage guest responses, and automate email and SMS reminders beautifully.',
    features: ['Stunning Invitation Designs', 'Email & SMS Reminders', 'RSVP Tracking', 'Perfect for Every Occasion'],
    accent: 'invite',
  },
  {
    id: 'quant',
    name: 'HaViQuant',
    eyebrow: 'Insights. Intelligence. Impact.',
    headline: 'AI-Powered Market Intelligence & Investing',
    description:
      'Research markets, understand portfolios, track evidence, and turn complex information into clearer investment decisions.',
    features: ['Real-Time Market Insights', 'AI Analysis & Forecasting', 'Portfolio Tracking', 'Smarter Investment Decisions'],
    accent: 'quant',
  },
]

const HAVIQUANT_URL = 'https://haviquant-web.onrender.com/';
function productHref(id: ProductId) {
  return `#product-${id}`;
}

function useHashRoute() {
  const read = () => window.location.hash.replace(/^#\/?/, '') || 'home'
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const handler = () => setRoute(read())
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])
  return route
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <a className="brand" href="#home" aria-label="HaVi World home">
      <div className="brand-mark" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
      </div>
      <div className="brand-copy">
        <div className="brand-name">HaVi<span>World</span></div>
        {!compact && <div className="brand-tagline">Apps for a smarter tomorrow</div>}
      </div>
    </a>
  )
}

function Nav({ onSearch }: { onSearch: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <header className="nav-wrap">
      <nav className="top-nav glass-nav">
        <Brand />
        <div className={`nav-links ${menuOpen ? 'show' : ''}`}>
          <a href="#home" onClick={() => setMenuOpen(false)}>Home</a>
          <a href="#home-apps" onClick={() => setMenuOpen(false)}>Our Apps</a>
          <a href="#home-platform" onClick={() => setMenuOpen(false)}>Platform</a>
          <a href="#home-about" onClick={() => setMenuOpen(false)}>About</a>
          <a href="#home-support" onClick={() => setMenuOpen(false)}>Support</a>
        </div>
        <div className="nav-actions">
          <button className="icon-button" onClick={onSearch} aria-label="Search apps"><Search size={18} /></button>
          <a className="nav-secondary" href="./index.html#Overview">Open HaViHire</a>
          <button className="nav-primary" onClick={() => (window.location.hash = 'home-apps')}>Get Started</button>
          <button className="menu-button" onClick={() => setMenuOpen((v) => !v)} aria-label="Menu">
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </nav>
    </header>
  )
}

function Hero() {
  return (
    <section className="hero-section section-shell" id="home">
      <div className="hero-backdrop">
        <div className="hero-aurora hero-a" />
        <div className="hero-aurora hero-b" />
        <div className="hero-city city-left" />
        <div className="hero-city city-right" />
        <div className="hero-sun" />
      </div>
      <div className="hero-content">
        <div className="hero-copy">
          <p className="eyebrow light">ONE ECOSYSTEM. ENDLESS POSSIBILITIES.</p>
          <h1>HaVi World</h1>
          <h2>Intelligent Apps for<br />Work, Life & Business</h2>
          <p className="hero-description">
            A growing family of powerful, beautifully designed apps to help you hire, celebrate, invest,
            organize and achieve more — all in one place.
          </p>
          <div className="hero-actions">
            <a className="button button-light" href="#home-apps">Explore Our Apps <ArrowRight size={18} /></a>
            <span className="watch-button">Product concepts · In development</span>
          </div>
        </div>

        <div className="hero-art" aria-label="A brighter tomorrow together">
          <div className="orb-shadow" />
          <div className="orb-ring ring-a" />
          <div className="orb-ring ring-b" />
          <div className="hero-orb">
            <div className="orb-gloss" />
            <div className="orb-landscape">
              <span className="orb-tree tree-a" />
              <span className="orb-tree tree-b" />
              <span className="orb-tree tree-c" />
            </div>
            <div className="orb-words">
              <span>A</span><span>Brighter</span><span>Tomorrow</span><strong>Together</strong>
              <i />
            </div>
          </div>
          <div className="hero-handwriting">People<br />Ideas<br />Celebrations<br />Opportunities<br /><strong>A Better You</strong></div>
        </div>
      </div>
    </section>
  )
}

function HirePreview() {
  return (
    <div className="product-preview hire-preview">
      <div className="candidate-profile">
        <div className="candidate-photo"><span>SR</span></div>
        <div><small>Top Talent Profile</small><b>Alex Morgan</b></div>
      </div>
      <div className="match-box">
        <div className="match-ring"><span>92%</span><small>Match</small></div>
        <div className="match-list"><span>✓ Experience</span><span>✓ Leadership</span><span>✓ Role Fit</span></div>
      </div>
      <div className="mini-list">
        <div><span className="mini-avatar">MK</span><p><b>Candidate One</b><small>92% match</small></p></div>
        <div><span className="mini-avatar">PS</span><p><b>Candidate Two</b><small>88% match</small></p></div>
      </div>
    </div>
  )
}

function InvitePreview() {
  return (
    <div className="product-preview invite-preview">
      <div className="invite-flower flower-one">✿</div>
      <div className="invite-flower flower-two">✦</div>
      <div className="paper-stack">
        <div className="invite-paper paper-back" />
        <div className="invite-paper paper-main">
          <small>YOU'RE INVITED</small>
          <strong>Celebrate<br />With Us</strong>
          <span>RSVP • EMAIL • SMS</span>
          <div className="paper-icons"><Mail size={14}/><MessageSquareText size={14}/><CalendarDays size={14}/></div>
        </div>
      </div>
    </div>
  )
}

function QuantPreview() {
  return (
    <div className="product-preview quant-preview">
      <div className="portfolio-card">
        <small>PORTFOLIO VALUE</small>
        <b>$125,430</b>
        <span>↑ 12.4%</span>
        <svg className="portfolio-line" viewBox="0 0 230 90" role="img" aria-label="Portfolio rising chart">
          <polyline points="2,72 24,58 44,66 64,42 86,50 108,32 132,38 152,18 176,28 205,8 228,16" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <div className="ticker-stack">
        <span>Momentum <b>+2.4%</b></span>
        <span>Growth <b>+1.6%</b></span>
        <span>Balance <b>+1.2%</b></span>
      </div>
    </div>
  )
}

function ProductCard({ product }: { product: Product }) {
  return <article className={`product-card ${product.accent}`}>
    <div className="product-glow" />
    <div className="compact-brand"><span className={`app-emblem ${product.id}`} aria-hidden="true">{product.id === 'hire' ? <UsersRound/> : product.id === 'invite' ? <Heart/> : <BarChart3/>}</span><div><h3>HaVi<span>{product.id === 'hire' ? 'Hire' : product.id === 'invite' ? 'Invite' : 'Quant'}</span></h3><p>{product.eyebrow}</p></div></div>
    <h4 className="compact-headline">{product.headline}</h4>
    <ul className="product-features">{product.features.map(feature=><li key={feature}><Check size={14}/>{feature}</li>)}</ul>
    {product.id === 'hire' && <div className="floating-matches"><b>Top Match</b>{['92%','88%','78%'].map((score,i)=><div key={score}><span className="sample-avatar">{['AM','JL','PS'][i]}</span><span>Profile {i+1}</span><strong>{score}</strong></div>)}<small>Sample data</small></div>}
    {product.id === 'invite' && <div className="invitation-script">You’re<br/>Invited</div>}
    {product.id === 'quant' && <QuantPreview/>}
    <a className="product-button" href={productHref(product.id)}>Explore {product.name}<ArrowRight size={16}/></a>
    <div className="product-motto">{product.id === 'hire' ? 'HIRE A BRIGHTER TOMORROW' : product.id === 'invite' ? 'CELEBRATE BEAUTIFULLY' : 'INVEST IN A BRIGHTER TOMORROW'}</div>
  </article>
}

function AppsSection() {
  return (
    <section className="apps-section section-shell" id="home-apps">
      <div className="section-heading" id="home-about">
        <h2>Our Apps</h2>
        <p>Different needs. One world. Explore our growing family of intelligent apps.</p>
      </div>
      <div className="product-grid">
        {products.map((product) => <ProductCard key={product.id} product={product} />)}
      </div>
      <div className="benefit-strip" id="home-platform">
        <div><CircleUserRound size={28}/><b>One Account</b><span>Access all HaVi apps with a single login</span></div>
        <div><BarChart3 size={28}/><b>Simple Billing</b><span>Manage subscriptions in one place</span></div>
        <div><ShieldCheck size={28}/><b>Secure & Reliable</b><span>Enterprise-grade security and protection</span></div>
        <div><UsersRound size={28}/><b>Growing Ecosystem</b><span>More innovative apps coming soon</span></div>
        <div><Heart size={28}/><b>Built for People</b><span>Designed to make work and life better</span></div>
      </div>
    </section>
  )
}

function PlatformSection() {
  return (
    <section className="platform-section section-shell" id="home-platform">
      <div className="platform-copy">
        <p className="eyebrow ink">THE HAVI WORLD PLATFORM</p>
        <h2>One account.<br />A growing ecosystem.</h2>
        <p>Start with the app you need today. Add more as HaVi World grows. Identity, billing, security and shared experiences stay consistent.</p>
        <button className="button button-dark">Create Your HaVi Account <ChevronRight size={18}/></button>
      </div>
      <div className="platform-grid glass-light">
        <div className="platform-item"><CircleUserRound/><div><b>One Identity</b><span>Secure account access across every HaVi app.</span></div></div>
        <div className="platform-item"><ShieldCheck/><div><b>Security First</b><span>Built with privacy, permissions and trust in mind.</span></div></div>
        <div className="platform-item"><Sparkles/><div><b>Purposeful AI</b><span>Intelligence that explains, assists and stays human-centered.</span></div></div>
        <div className="platform-item"><UsersRound/><div><b>Shared Ecosystem</b><span>A consistent design and account experience as products grow.</span></div></div>
      </div>
    </section>
  )
}

function AboutSection() {
  return (
    <section className="about-section section-shell" id="home-about">
      <div className="about-panel">
        <div className="about-icon"><Sparkles/></div>
        <p className="eyebrow ink">OUR PHILOSOPHY</p>
        <h2>Technology should feel intelligent — not complicated.</h2>
        <p>HaVi World combines useful AI, thoughtful workflows and a premium visual experience so people can move faster without feeling overwhelmed.</p>
      </div>
    </section>
  )
}

function FinalCta() {
  return (
    <section className="final-cta section-shell" id="home-support">
      <div>
        <p className="eyebrow light">BE PART OF THE JOURNEY</p>
        <h2>Be Part of HaVi World</h2>
        <p>Smarter tools. Better experiences. One growing ecosystem.</p>
      </div>
      <a className="button button-light" href="#home-apps">Explore Our Apps <ArrowRight size={18}/></a>
    </section>
  )
}

function Footer() {
  return (
    <footer className="footer section-shell">
      <Brand compact />
      <p>© 2026 HaVi World. Designed for a smarter tomorrow.</p>
      <div className="footer-links"><a href="#home-apps">Our Apps</a><a href="#home-support">Get Started</a></div>
    </footer>
  )
}

function SearchPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(
    () => products.filter((p) => `${p.name} ${p.headline} ${p.description}`.toLowerCase().includes(query.toLowerCase())),
    [query],
  )
  useEffect(() => { if (!open) return; const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose() }; document.addEventListener("keydown", close); return () => document.removeEventListener("keydown", close) }, [open, onClose])
  if (!open) return null
  return (
    <div className="search-overlay" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Search HaVi apps" className="search-dialog" onMouseDown={(e) => e.stopPropagation()}>
        <div className="search-input-wrap"><Search size={20}/><input autoFocus value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="Search HaVi apps..."/><button aria-label="Close search" onClick={onClose}><X size={18}/></button></div>
        <div className="search-results">{!filtered.length && <p>No apps found. Try hiring, invitations, or markets.</p>}
          {filtered.map((product) => (
            <a key={product.id} href={productHref(product.id)} onClick={onClose}>
              <div className={`search-icon ${product.id}`}><Sparkles size={17}/></div>
              <div><b>{product.name}</b><span>{product.headline}</span></div>
              <ArrowRight size={16}/>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}

function ProductPage({ product }: { product: Product }) {
  const icon = product.id === 'hire' ? <BriefcaseBusiness/> : product.id === 'invite' ? <Heart/> : <LineChart/>
  const metrics = product.id === 'hire'
    ? [['92%', 'Top Match'], ['18', 'Active Interviews'], ['12', 'Open Jobs']]
    : product.id === 'invite'
    ? [['248', 'Guests'], ['86%', 'RSVP Rate'], ['3', 'Reminders']]
    : [['+12.4%', 'Portfolio'], ['24', 'Watchlist'], ['8', 'Signals']]
  return (
    <main className={`product-page product-page-${product.id}`}>
      <section className="product-page-hero section-shell">
        <a className="back-link" href="#home">← Back to HaVi World</a>
        <div className="product-page-grid">
          <div>
            <div className={`page-icon ${product.id}`}>{icon}</div>
            <p className="eyebrow light">{product.eyebrow}</p>
            <h1>{product.name}</h1>
            <h2>{product.headline}</h2>
            <p>{product.description}</p>
            <div className="hero-actions">{product.id === "hire" ? <a className="button button-light" href="./index.html#Overview">Open Local Workspace <ArrowRight size={18}/></a> : product.id === "quant" ? <a className="button button-light" href={HAVIQUANT_URL}>Open HaViQuant <ArrowRight size={18}/></a> : <a className="button button-light" href="./invite.html">Open HaViInvite <ArrowRight size={18}/></a>}<a className="watch-button" href="#product-features">View Features</a></div>
          </div>
          <div className="product-page-card">
            <div className="product-page-card-top"><span>Illustrative concept · sample data</span><Bell size={17}/></div>
            <div className="page-metrics">{metrics.map(([value,label]) => <div key={label}><b>{value}</b><span>{label}</span></div>)}</div>
            <div className="page-dashboard">
              <div className="dash-nav"><span className="active">Overview</span><span>Activity</span><span>Analytics</span></div>
              <div className="dash-body">
                <div className="dash-chart"><div className="chart-bars">{[28,46,40,60,54,76,68,88].map((h,i)=><i key={i} style={{height:`${h}%`}}/>)}</div></div>
                <div className="dash-list"><span><b>Today</b><small>High-priority activity</small></span><span><b>3 updates</b><small>Needs your attention</small></span><span><b>Ready</b><small>AI insights available</small></span></div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="product-page-features section-shell" id="product-features">
        <div className="section-heading"><p className="eyebrow ink">BUILT TO FEEL BETTER</p><h2>Focused, polished and practical.</h2></div>
        <div className="feature-cards">
          {product.features.concat(['Fast workflows', 'Secure by design']).map((feature, index) => (
            <div key={feature}><div className="feature-card-icon">{index % 2 === 0 ? <Sparkles/> : <ShieldCheck/>}</div><b>{feature}</b><p>Designed as a first-class workflow with clear actions, strong visual hierarchy and minimal friction.</p></div>
          ))}
        </div>
      </section>
    </main>
  )
}

function HomePage() {
  return <main><Hero/><AppsSection/><FinalCta/></main>
}

export default function App() {
  const route = useHashRoute()
  const [searchOpen, setSearchOpen] = useState(false)
  const [lastProduct, setLastProduct] = useState<ProductId>("hire")
  useEffect(() => { if (route.startsWith("product-") && route !== "product-features") setLastProduct(route.replace("product-", "") as ProductId) }, [route])
  const productId = route === "product-features" ? lastProduct : route.startsWith('product-') ? (route.replace('product-', '') as ProductId) : null
  const product = productId ? products.find((p) => p.id === productId) : undefined

  useEffect(() => {
    if (!route.startsWith('home-') && route !== 'product-features') { window.scrollTo(0,0); return }
    const id = route
    requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }))
  }, [route])

  return (
    <div className="app-shell">
      <Nav onSearch={() => setSearchOpen(true)} />
      {product ? <ProductPage product={product} /> : <HomePage />}
      <Footer />
      <SearchPanel open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  )
}
