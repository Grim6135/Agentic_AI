import React, { useEffect, useState } from 'react';
import { planTrip } from '../api';
import type { TripPreferences, TripResult } from '../api';

interface PlannerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function PlannerModal({ isOpen, onClose }: PlannerModalProps) {
  const [origin, setOrigin] = useState('New Delhi, India');
  const [destination, setDestination] = useState('');
  const [startDate, setStartDate] = useState('2026-11-15');
  const [endDate, setEndDate] = useState('2026-11-20');
  const [budgetMax, setBudgetMax] = useState<number | ''>(2500);
  const [currency, setCurrency] = useState('USD');
  const [travelers, setTravelers] = useState(2);
  const [travelStyle, setTravelStyle] = useState('cultural');
  const [preferredTransport, setPreferredTransport] = useState('mixed');
  const [interests, setInterests] = useState('history, food, temples');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TripResult | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getCurrencySymbol = (curr?: string) => {
    switch (curr?.toUpperCase()) {
      case 'INR':
        return '₹';
      case 'EUR':
        return '€';
      case 'GBP':
        return '£';
      case 'JPY':
        return '¥';
      default:
        return '$';
    }
  };

  const currSymbol = getCurrencySymbol(result?.currency || result?.budget?.currency || currency);

  const handleCopyId = () => {
    if (result) {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(result.trip_id);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleApplyPreset = (
    orig: string,
    dest: string,
    curr: string,
    budget: number,
    style: string,
    transport: string,
    keywords: string,
  ) => {
    setOrigin(orig);
    setDestination(dest);
    setCurrency(curr);
    setBudgetMax(budget);
    setTravelStyle(style);
    setPreferredTransport(transport);
    setInterests(keywords);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const payload: TripPreferences = {
      origin: origin.trim(),
      destinations: destination.trim() ? [destination.trim()] : null,
      start_date: startDate,
      end_date: endDate,
      budget_max: budgetMax !== '' ? Number(budgetMax) : null,
      currency: currency,
      travelers: Number(travelers),
      travel_style: travelStyle,
      preferred_transport: preferredTransport,
      interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
    };

    const res = await planTrip(payload);
    setLoading(false);

    if (res.error) {
      setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
    } else if (res.data) {
      setResult(res.data);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="planner-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto"
    >
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto glass bg-surface-900 border border-white/10 rounded-3xl p-6 sm:p-8 text-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">✈️</span>
            <h2 id="planner-modal-title" className="text-xl sm:text-2xl font-bold gradient-text">
              {result ? 'Your AI Travel Plan' : 'Plan Your Autonomous Trip'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-surface-100/60 hover:text-white rounded-xl hover:bg-white/10 transition-colors"
            aria-label="Close planner modal"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        {!result ? (
          <form onSubmit={handleSubmit} className="mt-6 space-y-6">
            {/* Quick Presets */}
            <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10">
              <span className="text-[11px] font-semibold text-surface-100/60 uppercase tracking-wider block mb-2">
                ⚡ Quick Trip Presets:
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'Tokyo, Japan',
                      'Kyoto, Japan',
                      'USD',
                      2800,
                      'cultural',
                      'train',
                      'temples, matcha, history, zen gardens',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-all cursor-pointer"
                >
                  🇯🇵 Kyoto Cultural ($)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'New Delhi, India',
                      'Kasol, India',
                      'INR',
                      22000,
                      'adventure',
                      'bus',
                      'trekking, parvati river, cafes, pine trails',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-primary-600/30 hover:bg-primary-600/50 border border-primary-500/40 text-primary-200 transition-all cursor-pointer"
                >
                  🇮🇳 Kasol Parvati Trail (₹)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'Milan, Italy',
                      'Rome, Italy',
                      'EUR',
                      2200,
                      'cultural',
                      'train',
                      'colosseum, vatican, pasta, architecture',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-all cursor-pointer"
                >
                  🇮🇹 Rome Highlights (€)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'London, UK',
                      'Paris, France',
                      'EUR',
                      1800,
                      'romantic',
                      'train',
                      'louvre, eiffel tower, cafes, pastry',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-all cursor-pointer"
                >
                  🇫🇷 Paris Romance (€)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'Jakarta, Indonesia',
                      'Bali, Indonesia',
                      'USD',
                      1900,
                      'relaxation',
                      'flight',
                      'beaches, ubud rice terraces, snorkeling, temples',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-all cursor-pointer"
                >
                  🇮🇩 Bali Wellness ($)
                </button>
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="p-4 rounded-xl bg-red-500/20 border border-red-500/40 text-red-200 text-sm flex items-start justify-between gap-2"
              >
                <div>
                  <span className="font-semibold block">⚠️ Planning Request Error:</span>
                  <p className="mt-1 leading-relaxed">{error}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setError(null)}
                  className="px-2 py-1 text-xs rounded bg-red-500/30 hover:bg-red-500/50 text-white transition-colors"
                >
                  Dismiss
                </button>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Origin City *
                </label>
                <input
                  type="text"
                  required
                  value={origin}
                  onChange={(e) => setOrigin(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                  placeholder="e.g. New Delhi, India"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Preferred Destination (Optional)
                </label>
                <input
                  type="text"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                  placeholder="e.g. Kasol, India (or leave empty for AI selection)"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Start Date *
                </label>
                <input
                  type="date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  End Date *
                </label>
                <input
                  type="date"
                  required
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Maximum Budget ({currSymbol})
                </label>
                <input
                  type="number"
                  min="50"
                  value={budgetMax}
                  onChange={(e) => setBudgetMax(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                  placeholder={currency === 'INR' ? 'e.g. 25000' : 'e.g. 2500'}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Currency
                </label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-800 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="USD">USD ($ - US Dollar)</option>
                  <option value="INR">INR (₹ - Indian Rupee)</option>
                  <option value="EUR">EUR (€ - Euro)</option>
                  <option value="GBP">GBP (£ - British Pound)</option>
                  <option value="JPY">JPY (¥ - Japanese Yen)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Travelers
                </label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={travelers}
                  onChange={(e) => setTravelers(Number(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Travel Style
                </label>
                <select
                  value={travelStyle}
                  onChange={(e) => setTravelStyle(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-800 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="cultural">Cultural & Historic</option>
                  <option value="relaxation">Relaxation & Wellness</option>
                  <option value="adventure">Outdoor & Adventure</option>
                  <option value="budget">Budget Backpacker</option>
                  <option value="luxury">Luxury & Fine Living</option>
                  <option value="romantic">Romantic Getaway</option>
                  <option value="family">Family Friendly</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Preferred Transport
                </label>
                <select
                  value={preferredTransport}
                  onChange={(e) => setPreferredTransport(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-800 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="mixed">Mixed (Flight / Train / Bus)</option>
                  <option value="flight">Flight</option>
                  <option value="train">Train</option>
                  <option value="bus">Bus / Coach</option>
                  <option value="car">Car / Drive</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                Interests & Keywords (comma-separated)
              </label>
              <input
                type="text"
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                placeholder="e.g. trekking, rivers, cafes, local culture"
              />
            </div>

            <div className="pt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl border border-white/10 text-sm text-surface-100/70 hover:text-white hover:border-white/20 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 font-semibold text-white shadow-glow transition-all active:scale-95 disabled:opacity-50 flex items-center gap-2 cursor-pointer"
              >
                {loading && (
                  <span
                    className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
                    aria-hidden="true"
                  />
                )}
                <span>{loading ? 'AI Agents Collaborating…' : 'Generate AI Itinerary'}</span>
              </button>
            </div>
          </form>
        ) : (
          /* ===== Plan Results ===== */
          <div className="mt-6 space-y-6">
            {/* Header info */}
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <span className="text-xs uppercase tracking-wider text-primary-400 font-semibold">
                  Destination: {result.destinations.join(', ')}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-surface-100/70">
                    💾 Persisted to Store
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyId}
                    title="Click to copy Trip ID"
                    className="text-xs text-surface-100/70 hover:text-white px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 transition-colors flex items-center gap-1 cursor-pointer"
                  >
                    <span>ID: {result.trip_id}</span>
                    <span className="text-[10px] text-primary-400">
                      {copied ? '✓ Copied' : '📋'}
                    </span>
                  </button>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-surface-100/80">{result.summary}</p>
            </div>

            {/* Warnings banner */}
            {result.warnings.length > 0 && (
              <div className="p-4 rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-200 text-xs space-y-1">
                <span className="font-semibold block text-amber-300">⚠️ Advisory Notices:</span>
                {result.warnings.map((w, idx) => (
                  <p key={idx}>• {w}</p>
                ))}
              </div>
            )}

            {/* External Integrations: Weather & Route */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Weather Forecast */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-surface-100/80 flex items-center gap-1.5">
                    <span>🌦️</span> Weather Forecast
                  </span>
                  {result.weather && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                        result.weather.is_live
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}
                    >
                      {result.weather.is_live ? '🟢 Verified Live' : 'Estimated Seasonal'}
                    </span>
                  )}
                </div>

                {result.weather ? (
                  <div className="space-y-1 text-xs text-surface-100/70">
                    <p className="text-white font-medium text-sm">
                      {result.weather.temperature_c}°C — {result.weather.condition}
                    </p>
                    <p className="text-[11px] text-surface-100/60">
                      Precipitation chance: {result.weather.precipitation_chance}%
                    </p>
                    <p className="text-surface-100/60 leading-relaxed pt-1">
                      {result.weather.summary}
                    </p>
                    <p className="text-[10px] text-surface-100/40 pt-1">
                      Source: {result.weather.provider_name}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-surface-100/50 italic">
                    Live weather forecast currently unavailable for this destination.
                  </p>
                )}
              </div>

              {/* Transit & Routing */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-surface-100/80 flex items-center gap-1.5">
                    <span>🗺️</span> Transit & Route Estimate
                  </span>
                  {result.route_estimate && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                        result.route_estimate.is_live
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}
                    >
                      {result.route_estimate.is_live ? '🟢 Verified Route' : 'Estimated Baseline'}
                    </span>
                  )}
                </div>

                {result.route_estimate ? (
                  <div className="space-y-1.5 text-xs text-surface-100/70">
                    <p className="text-white font-medium text-sm">
                      {result.route_estimate.distance_km.toLocaleString()} km (~{result.route_estimate.duration_hours}h {result.route_estimate.mode})
                    </p>
                    <p className="text-surface-100/60 leading-relaxed">
                      {result.route_estimate.route_summary}
                    </p>
                    <p className="text-[10px] text-surface-100/40 pt-1">
                      Source: {result.route_estimate.provider_name}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-surface-100/50 italic">
                    Direct route estimation unavailable.
                  </p>
                )}
              </div>
            </div>

            {/* RAG Guidebook Knowledge & Sources */}
            {((result.destination_guidance && result.destination_guidance.length > 0) ||
              (result.rag_sources && result.rag_sources.length > 0)) && (
              <div className="p-4 rounded-2xl bg-primary-950/40 border border-primary-500/20 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-primary-300 flex items-center gap-1.5">
                    <span>📚</span> Curated Destination Guidance (RAG Verified)
                  </span>
                  {result.rag_sources && result.rag_sources.length > 0 && (
                    <span className="text-[10px] text-surface-100/50">
                      {result.rag_sources.length} guidebook source(s)
                    </span>
                  )}
                </div>

                {result.destination_guidance && result.destination_guidance.length > 0 && (
                  <ul className="space-y-2 text-xs text-surface-100/70">
                    {result.destination_guidance.map((guide, idx) => (
                      <li key={idx} className="bg-white/5 p-2.5 rounded-xl border border-white/5">
                        {guide}
                      </li>
                    ))}
                  </ul>
                )}

                {result.rag_sources && result.rag_sources.length > 0 && (
                  <div className="pt-2 border-t border-white/10 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] text-surface-100/50">Sources:</span>
                    {result.rag_sources.map((src, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] bg-primary-600/20 text-primary-300 px-2 py-0.5 rounded-md border border-primary-500/30"
                      >
                        {src}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Itemized Budget */}
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-surface-100/80">
                  Itemized Deterministic Budget ({currSymbol})
                </span>
                <span className="text-xs text-amber-300/80 italic">
                  *Curated prices remain estimates unless verified live
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Transport</span>
                  <span className="font-semibold text-white">{currSymbol}{result.budget.transport.toFixed(2)}</span>
                </div>
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Lodging</span>
                  <span className="font-semibold text-white">{currSymbol}{result.budget.accommodation.toFixed(2)}</span>
                </div>
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Activities</span>
                  <span className="font-semibold text-white">{currSymbol}{result.budget.activities.toFixed(2)}</span>
                </div>
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Dining (Est.)</span>
                  <span className="font-semibold text-white">{currSymbol}{result.budget.food_estimate.toFixed(2)}</span>
                </div>
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Misc (8%)</span>
                  <span className="font-semibold text-white">{currSymbol}{result.budget.miscellaneous.toFixed(2)}</span>
                </div>
                <div className="bg-primary-600/20 border border-primary-500/30 p-2.5 rounded-xl">
                  <span className="text-primary-300 block text-[10px] font-semibold">Total</span>
                  <span className="font-bold text-white text-sm">{currSymbol}{result.budget.total.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Day-by-day Itinerary */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-white">Daily Itinerary</h3>
              <div className="space-y-3">
                {result.itinerary.map((day) => (
                  <div
                    key={day.day}
                    className="p-3.5 rounded-2xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors"
                  >
                    <div className="flex items-center justify-between text-xs font-semibold text-primary-400 mb-2">
                      <span>Day {day.day} — {day.date}</span>
                      {day.daily_budget && (
                        <span className="text-surface-100/50 font-normal">
                          Daily Target: {currSymbol}{day.daily_budget.toFixed(2)}
                        </span>
                      )}
                    </div>

                    {/* Accommodation */}
                    {day.accommodation && (
                      <p className="text-xs text-surface-100/70 mb-1.5">
                        🏨 <strong>Stay:</strong> {day.accommodation.name} ({currSymbol}{day.accommodation.cost_per_night}/night)
                      </p>
                    )}

                    {/* Transport legs */}
                    {day.transport && day.transport.length > 0 && (
                      <div className="text-xs text-surface-100/70 mb-1.5 space-y-1">
                        {day.transport.map((t, idx) => (
                          <p key={idx}>
                            🚆 <strong>Transit:</strong> {t.origin} → {t.destination} ({t.departure} - {t.arrival})
                          </p>
                        ))}
                      </div>
                    )}

                    {/* Activities */}
                    {day.activities && day.activities.length > 0 && (
                      <div className="text-xs text-surface-100/80 space-y-1 pt-1 border-t border-white/5">
                        {day.activities.map((act, idx) => (
                          <div key={idx} className="flex justify-between gap-2">
                            <span>• {act.name} ({act.duration_hours}h)</span>
                            <span className="text-surface-100/50">{currSymbol}{act.cost_estimate ?? 0}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Footer action */}
            <div className="pt-4 flex justify-between items-center border-t border-white/10">
              <button
                type="button"
                onClick={() => setResult(null)}
                className="text-xs text-surface-100/60 hover:text-white transition-colors cursor-pointer"
              >
                ← Plan Another Trip
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold text-white transition-colors cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
