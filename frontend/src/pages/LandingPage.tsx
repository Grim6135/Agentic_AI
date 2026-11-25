import { useEffect, useState } from 'react';
import { FeatureCard, PlannerModal } from '../components';
import { checkHealth } from '../api';

const FEATURES = [

  {
    icon: '🌍',
    title: 'AI Destination Picker',
    description:
      'Our Destination Agent analyzes your preferences, travel style, and budget to recommend the perfect destinations worldwide.',
  },
  {
    icon: '🚆',
    title: 'Smart Transport',
    description:
      'The Transport Agent finds optimal routes — flights, trains, buses, and drives — with real-time pricing and eco-friendly options.',
  },
  {
    icon: '🏨',
    title: 'Stay & Activities',
    description:
      'From luxury resorts to hidden gems, the Stay & Activity Agent curates accommodations and experiences tailored to you.',
  },
  {
    icon: '💰',
    title: 'Budget Optimizer',
    description:
      'The Budget Agent keeps every trip financially smart, tracking costs and surfacing deals without sacrificing quality.',
  },
  {
    icon: '📋',
    title: 'Auto Itinerary',
    description:
      'The Itinerary Agent weaves everything into a polished, day-by-day plan you can share, edit, and take on the go.',
  },
];

const STEPS = [
  { num: '01', title: 'Tell Us Your Dream', desc: 'Share your travel preferences, dates, and budget.' },
  { num: '02', title: 'AI Agents Collaborate', desc: 'Five specialist agents research and plan in parallel.' },
  { num: '03', title: 'Get Your Itinerary', desc: 'Receive a detailed, day-by-day travel plan ready to go.' },
];

export default function LandingPage() {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [isPlannerOpen, setIsPlannerOpen] = useState(false);

  useEffect(() => {
    checkHealth().then((res) => setBackendOnline(res.error === null));
  }, []);

  return (
    <div className="min-h-screen bg-surface-950 text-white">
      {/* Planner Modal */}
      <PlannerModal isOpen={isPlannerOpen} onClose={() => setIsPlannerOpen(false)} />

      {/* ===== HERO ===== */}
      <section className="gradient-hero relative overflow-hidden pt-32 pb-24 sm:pt-40 sm:pb-32" id="hero">
        {/* Decorative orbs */}
        <div className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full bg-primary-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-accent-500/15 blur-3xl" />

        <div className="relative mx-auto max-w-4xl px-4 text-center animate-fade-in">
          {/* Status badge */}
          <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-white/10
                          bg-white/5 px-4 py-1.5 text-xs text-surface-100/70">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                backendOnline === null
                  ? 'bg-yellow-400 animate-pulse'
                  : backendOnline
                    ? 'bg-emerald-400'
                    : 'bg-red-400'
              }`}
            />
            {backendOnline === null
              ? 'Connecting…'
              : backendOnline
                ? 'Backend Online'
                : 'Backend Offline — UI only'}
          </div>

          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1]">
            Your Next Adventure,{' '}
            <span className="gradient-text">Planned by AI</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg text-surface-100/60 leading-relaxed">
            TRIPPY uses five autonomous AI agents to research destinations, compare transport,
            find stays, optimize your budget, and craft the perfect itinerary — all in seconds.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => setIsPlannerOpen(true)}
              className="rounded-2xl bg-primary-600 px-8 py-3.5 text-base font-semibold text-white
                         shadow-lg shadow-primary-600/25 hover:bg-primary-500 hover:shadow-primary-500/30
                         transition-all duration-200 active:scale-95 cursor-pointer"
              id="hero-cta"
            >
              Start Planning — It&apos;s Free
            </button>

            <a
              href="#how-it-works"
              className="group flex items-center gap-2 rounded-2xl border border-white/10 px-6 py-3.5
                         text-sm text-surface-100/70 hover:border-white/20 hover:text-white transition-all duration-200"
              id="hero-secondary"
            >
              See How It Works
              <span className="inline-block transition-transform group-hover:translate-x-1">→</span>
            </a>
          </div>
        </div>
      </section>

      {/* ===== FEATURES ===== */}
      <section className="py-20 sm:py-28" id="features">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Five AI Agents, <span className="gradient-text">One Perfect Trip</span>
            </h2>
            <p className="mt-4 text-surface-100/50 max-w-xl mx-auto">
              Each agent is a specialist that collaborates with the others to build your ideal travel plan.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <FeatureCard key={f.title} icon={f.icon} title={f.title} description={f.description} delay={i * 100} />
            ))}
          </div>
        </div>
      </section>

      {/* ===== HOW IT WORKS ===== */}
      <section className="py-20 sm:py-28 border-t border-white/5" id="how-it-works">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              How <span className="gradient-text">TRIPPY</span> Works
            </h2>
          </div>

          <div className="grid gap-8 sm:grid-cols-3">
            {STEPS.map((step, i) => (
              <div
                key={step.num}
                className="relative rounded-2xl border border-white/5 bg-surface-900/50 p-8
                           hover:border-primary-500/30 transition-all duration-300 animate-slide-up"
                style={{ animationDelay: `${i * 150}ms` }}
              >
                <span className="text-5xl font-black text-primary-600/20">{step.num}</span>
                <h3 className="mt-3 text-lg font-semibold text-white">{step.title}</h3>
                <p className="mt-2 text-sm text-surface-100/50 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== BOTTOM CTA ===== */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-3xl px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Ready to <span className="gradient-text">Explore?</span>
          </h2>
          <p className="mt-4 text-surface-100/50 max-w-lg mx-auto">
            Let AI handle the research. You handle the adventure.
          </p>
          <button
            onClick={() => setIsPlannerOpen(true)}
            className="mt-8 rounded-2xl bg-primary-600 px-10 py-4 text-base font-semibold text-white
                       shadow-lg shadow-primary-600/25 hover:bg-primary-500 hover:shadow-primary-500/30
                       transition-all duration-200 active:scale-95 cursor-pointer"
            id="bottom-cta"
          >
            Plan My Trip Now
          </button>

        </div>
      </section>
    </div>
  );
}
