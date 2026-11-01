import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PlannerModal from '../components/PlannerModal';
import * as api from '../api';

const mockLiveTripResult: api.TripResult = {
  trip_id: 'trip_test123',
  preferences: {
    origin: 'New Delhi, India',
    destinations: ['Kyoto, Japan'],
    start_date: '2026-11-15',
    end_date: '2026-11-20',
    budget_max: 2500,
    travelers: 2,
    travel_style: 'cultural',
    preferred_transport: 'flight',
    interests: ['history', 'food'],
  },
  destinations: ['Kyoto, Japan'],
  itinerary: [
    {
      day: 1,
      date: '2026-11-15',
      activities: [
        {
          name: 'Fushimi Inari Torii Gates Walk',
          location: 'Kyoto, Japan',
          duration_hours: 3.0,
          cost_estimate: 0.0,
          description: 'Hike through thousands of vermilion torii gates at sunrise.',
        },
      ],
      accommodation: {
        name: 'Kyoto Machiya Heritage Inn',
        location: 'Kyoto, Japan',
        cost_per_night: 135.0,
      },
      transport: [
        {
          mode: 'flight',
          origin: 'New Delhi, India',
          destination: 'Kyoto, Japan',
          departure: 'Morning (08:30)',
          arrival: 'Day 1 (~9.0h transit)',
        },
      ],
      daily_budget: 380.0,
    },
  ],
  budget: {
    transport: 825.0,
    accommodation: 540.0,
    activities: 180.0,
    food_estimate: 200.0,
    miscellaneous: 139.6,
    total: 1884.6,
  },
  summary: 'A curated 5-day cultural journey to Kyoto, Japan.',
  warnings: [],
  weather: {
    destination: 'Kyoto, Japan',
    temperature_c: 18.5,
    condition: 'Partly Cloudy ⛅',
    precipitation_chance: 12.0,
    summary: 'Verified live forecast for Kyoto: Daily highs averaging 18.5°C with Partly Cloudy.',
    is_live: true,
    provider_name: 'Open-Meteo Live API',
    recorded_at: '2026-11-02 01:00 UTC',
  },
  route_estimate: {
    origin: 'New Delhi, India',
    destination: 'Kyoto, Japan',
    distance_km: 5850.0,
    duration_hours: 8.8,
    mode: 'flight',
    is_live: true,
    provider_name: 'Geodesic Coordinate Engine',
    route_summary: 'Verified geodesic trajectory: 5850 km flight path.',
  },
  rag_sources: ['Kyoto Heritage & Cultural Travel Guide (2026)'],
  destination_guidance: [
    '[Temples, Shrines, and Sacred Spaces] When visiting Fushimi Inari Shrine, an early morning ascent around 06:30 is strongly advised (Source: Kyoto Heritage & Cultural Travel Guide (2026))',
  ],
};

const mockUnavailableTripResult: api.TripResult = {
  ...mockLiveTripResult,
  trip_id: 'trip_unavail',
  weather: null,
  route_estimate: null,
  rag_sources: [],
  destination_guidance: [],
};

describe('PlannerModal Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders form inputs when opened', () => {
    render(<PlannerModal isOpen={true} onClose={() => {}} />);
    expect(screen.getByPlaceholderText(/e\.g\. New Delhi, India/i)).toBeInTheDocument();
    expect(screen.getByText(/Maximum Budget/i)).toBeInTheDocument();
    expect(screen.getByText(/Generate AI Itinerary/i)).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    const { container } = render(<PlannerModal isOpen={false} onClose={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('displays destination guidance, source labels, live weather, and live route when available', async () => {
    vi.spyOn(api, 'planTrip').mockResolvedValue({
      data: mockLiveTripResult,
      error: null,
      status: 200,
    });

    render(<PlannerModal isOpen={true} onClose={() => {}} />);

    // Click submit
    fireEvent.click(screen.getByText(/Generate AI Itinerary/i));

    await waitFor(() => {
      expect(screen.getByText(/Your AI Travel Plan/i)).toBeInTheDocument();
    });

    // Destination guidance & source label
    expect(screen.getByText(/Curated Destination Guidance \(RAG Verified\)/i)).toBeInTheDocument();
    expect(screen.getByText('Kyoto Heritage & Cultural Travel Guide (2026)')).toBeInTheDocument();
    expect(screen.getByText(/Fushimi Inari Shrine/i)).toBeInTheDocument();

    // Weather forecast & live badge
    expect(screen.getByText(/18.5°C — Partly Cloudy ⛅/i)).toBeInTheDocument();
    expect(screen.getByText('🟢 Verified Live')).toBeInTheDocument();

    // Route estimate & live badge
    expect(screen.getByText(/5,850 km \(~8.8h flight\)/i)).toBeInTheDocument();
    expect(screen.getByText('🟢 Verified Route')).toBeInTheDocument();

    // Estimated prices disclaimer
    expect(
      screen.getByText(/\*Curated prices remain estimates unless verified live/i),
    ).toBeInTheDocument();
  });

  it('displays honest unavailable states when weather or route data fails', async () => {
    vi.spyOn(api, 'planTrip').mockResolvedValue({
      data: mockUnavailableTripResult,
      error: null,
      status: 200,
    });

    render(<PlannerModal isOpen={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText(/Generate AI Itinerary/i));

    await waitFor(() => {
      expect(screen.getByText(/Your AI Travel Plan/i)).toBeInTheDocument();
    });

    // Honest unavailable states
    expect(
      screen.getByText(/Live weather forecast currently unavailable for this destination/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Direct route estimation unavailable/i),
    ).toBeInTheDocument();
  });

  it('calls onClose when Escape key is pressed', () => {
    const handleClose = vi.fn();
    render(<PlannerModal isOpen={true} onClose={handleClose} />);
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('displays error banner and allows dismissing it', async () => {
    vi.spyOn(api, 'planTrip').mockResolvedValue({
      data: null,
      error: 'Trip end date must be after start date.',
      status: 422,
    });

    render(<PlannerModal isOpen={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText(/Generate AI Itinerary/i));

    await waitFor(() => {
      expect(screen.getByText(/Planning Request Error/i)).toBeInTheDocument();
      expect(screen.getByText(/Trip end date must be after start date/i)).toBeInTheDocument();
    });

    // Dismiss error
    fireEvent.click(screen.getByText(/Dismiss/i));
    expect(screen.queryByText(/Trip end date must be after start date/i)).not.toBeInTheDocument();
  });

  it('displays persistent trip ID and store badge in results', async () => {
    vi.spyOn(api, 'planTrip').mockResolvedValue({
      data: mockLiveTripResult,
      error: null,
      status: 200,
    });

    render(<PlannerModal isOpen={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText(/Generate AI Itinerary/i));

    await waitFor(() => {
      expect(screen.getByText(/Persisted to Store/i)).toBeInTheDocument();
      expect(screen.getByText(/ID: trip_test123/i)).toBeInTheDocument();
    });
  });
});

