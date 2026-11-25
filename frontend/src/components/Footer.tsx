export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-white/5 bg-surface-950/80">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Brand */}
          <div className="flex items-center gap-2">
            <span className="text-xl">✈️</span>
            <span className="font-bold gradient-text">TRIPPY</span>
          </div>

          {/* Links */}
          <div className="flex gap-6 text-sm text-surface-100/50">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white transition-colors"
            >
              GitHub
            </a>
          </div>

          {/* Copyright */}
          <p className="text-xs text-surface-100/30">
            © {year} TRIPPY. Crafted with AI.
          </p>
        </div>
      </div>
    </footer>
  );
}
