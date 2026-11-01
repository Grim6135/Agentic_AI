interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  delay?: number;
}

export default function FeatureCard({ icon, title, description, delay = 0 }: FeatureCardProps) {
  return (
    <div
      className="group glass rounded-2xl p-6 hover:bg-white/12 transition-all duration-300
                 hover:-translate-y-1 hover:shadow-glow animate-slide-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl
                      bg-primary-600/20 text-2xl group-hover:scale-110 transition-transform duration-300">
        {icon}
      </div>
      <h3 className="mb-2 text-lg font-semibold text-white">{title}</h3>
      <p className="text-sm leading-relaxed text-surface-100/60">{description}</p>
    </div>
  );
}
