import React, { useState } from 'react';
import { refreshNav } from '../../api/adminApi';
import type { NavRefreshResponse } from '../../types/admin';
import { Alert } from '../../components/common/Alert';
import { StatCard } from '../../components/common/StatCard';

export const NavFeedManager: React.FC<{ token: string }> = ({ token }) => {
  const [targetDate, setTargetDate] = useState('2026-01-16');
  const [lastResult, setLastResult] = useState<NavRefreshResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleRefresh = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsRefreshing(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await refreshNav(token, targetDate || undefined);
      setLastResult(res);
      if (res.status === 'ALREADY_LOADED') {
        setSuccessMsg(`NAV feed for ${targetDate} was already loaded previously (idempotent).`);
      } else {
        setSuccessMsg(
          `NAV feed updated for ${res.nav_date}! Loaded ${res.prices_loaded} asset prices and evaluated goal snapshots.`,
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to refresh NAV feed.';
      setError(msg);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="nav-feed-manager">
      {error && <Alert type="error" title="Error" message={error} onClose={() => setError(null)} />}
      {successMsg && (
        <Alert type="success" title="Success" message={successMsg} onClose={() => setSuccessMsg(null)} />
      )}

      <div className="card nav-ops-card">
        <div className="card__header">
          <div>
            <h3 className="card__title">Daily NAV Feed Operations</h3>
            <span className="card__subtitle">
              Advance market NAV prices from series data, revalue holdings, and snapshot goal progress
            </span>
          </div>
        </div>

        <form onSubmit={handleRefresh} className="nav-refresh-form">
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="nav-target-date" className="form-label">
                Target Business Date (YYYY-MM-DD)
              </label>
              <input
                id="nav-target-date"
                type="date"
                className="form-input"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
              />
            </div>
          </div>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={isRefreshing}
            id="trigger-nav-refresh-btn"
          >
            {isRefreshing ? 'Processing Feed...' : '⚡ Trigger Daily NAV Refresh'}
          </button>
        </form>
      </div>

      {lastResult && (
        <div className="kpi-grid">
          <StatCard
            title="NAV Valuation Date"
            value={lastResult.nav_date || targetDate}
            subtitle={lastResult.status === 'ALREADY_LOADED' ? 'Already Cached' : 'Newly Loaded'}
            variant="indigo"
            icon="📅"
          />
          <StatCard
            title="Asset Prices Loaded"
            value={lastResult.prices_loaded || 4}
            subtitle="Equity, Debt, Gold, Cash"
            variant="emerald"
            icon="📈"
          />
          <StatCard
            title="Batch Status"
            value={lastResult.status || 'PROCESSED'}
            subtitle="Goal snapshots updated"
            variant="emerald"
            icon="✅"
          />
        </div>
      )}
    </div>
  );
};
