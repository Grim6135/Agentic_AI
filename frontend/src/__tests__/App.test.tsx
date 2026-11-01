import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from '../App';

// Mock the fetch API for health check
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok', version: '0.1.0' }),
    }),
  );
});

describe('App & LandingPage', () => {
  it('renders TRIPPY branding in navigation and footer', () => {
    render(<App />);
    const brandLinks = screen.getAllByText(/TRIPPY/i);
    expect(brandLinks.length).toBeGreaterThan(0);
  });

  it('renders the main hero headline', () => {
    render(<App />);
    expect(
      screen.getByRole('heading', { name: /Your Next Adventure/i, level: 1 }),
    ).toBeInTheDocument();
  });

  it('displays the five specialist AI agent feature cards', () => {
    render(<App />);
    expect(screen.getByText('AI Destination Picker')).toBeInTheDocument();
    expect(screen.getByText('Smart Transport')).toBeInTheDocument();
    expect(screen.getByText('Stay & Activities')).toBeInTheDocument();
    expect(screen.getByText('Budget Optimizer')).toBeInTheDocument();
    expect(screen.getByText('Auto Itinerary')).toBeInTheDocument();
  });

  it('renders the trip planning call to action buttons', () => {
    render(<App />);
    expect(screen.getByText(/Start Planning — It's Free/i)).toBeInTheDocument();
    expect(screen.getByText(/Plan My Trip Now/i)).toBeInTheDocument();
  });

  it('detects backend status as online when health check succeeds', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/Backend Online/i)).toBeInTheDocument();
    });
  });
});
