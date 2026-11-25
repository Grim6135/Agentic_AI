import { useState } from 'react';

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <a href="/" className="flex items-center gap-2 group" id="nav-logo">
            <span className="text-2xl" role="img" aria-label="airplane">✈️</span>
            <span className="text-xl font-bold gradient-text tracking-tight">
              TRIPPY
            </span>
          </a>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-8">
            <a
              href="#features"
              className="text-sm text-surface-100/70 hover:text-white transition-colors duration-200"
              id="nav-features"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="text-sm text-surface-100/70 hover:text-white transition-colors duration-200"
              id="nav-how-it-works"
            >
              How It Works
            </a>
            <button
              onClick={() => {
                const btn = document.getElementById('hero-cta');
                if (btn) btn.click();
              }}
              className="rounded-xl bg-primary-600 px-5 py-2 text-sm font-semibold text-white
                         hover:bg-primary-500 transition-all duration-200 hover:shadow-glow
                         active:scale-95 cursor-pointer"
              id="nav-cta"
            >
              Plan a Trip
            </button>

          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2 text-surface-100/70 hover:text-white transition-colors cursor-pointer"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
            id="nav-menu-toggle"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {menuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden pb-4 animate-slide-up">
            <div className="flex flex-col gap-3 pt-2">
              <a
                href="#features"
                className="text-surface-100/70 hover:text-white transition-colors px-2 py-1"
                onClick={() => setMenuOpen(false)}
              >
                Features
              </a>
              <a
                href="#how-it-works"
                className="text-surface-100/70 hover:text-white transition-colors px-2 py-1"
                onClick={() => setMenuOpen(false)}
              >
                How It Works
              </a>
              <button
                className="rounded-xl bg-primary-600 px-5 py-2 text-sm font-semibold text-white
                           hover:bg-primary-500 transition-all duration-200 mt-1 cursor-pointer"
              >
                Plan a Trip
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
