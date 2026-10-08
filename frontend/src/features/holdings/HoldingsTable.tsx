import React from 'react';
import type { HoldingsResponse } from '../../types/holdings';
import { FormattedMoney } from '../../components/common/FormattedMoney';
import { FormattedPercent } from '../../components/common/FormattedPercent';
import { Badge } from '../../components/common/Badge';

interface HoldingsTableProps {
  holdings: HoldingsResponse;
}

const ASSET_ICONS: Record<string, string> = {
  EQUITY: '📈',
  DEBT: '🏛️',
  GOLD: '🪙',
  CASH: '💵',
};

export const HoldingsTable: React.FC<HoldingsTableProps> = ({ holdings }) => {
  return (
    <div className="holdings-table-container">
      {/* Desktop Table View */}
      <div className="table-responsive holdings-desktop-view">
        <table className="data-table holdings-table" aria-label="Holdings and Allocation Drift Table">
          <thead>
            <tr>
              <th>Asset Class</th>
              <th className="text-right">Units Held</th>
              <th className="text-right">NAV Price</th>
              <th className="text-right">Valuation</th>
              <th className="text-right">Current %</th>
              <th className="text-right">Target %</th>
              <th className="text-right">Drift %</th>
              <th className="text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {holdings.lines.map((line) => {
              const icon = ASSET_ICONS[line.asset_class] || '📦';
              const isBreached = line.breached === true;
              return (
                <tr
                  key={line.asset_class}
                  className={`holdings-row ${isBreached ? 'holdings-row--breached' : ''}`}
                  id={`holding-row-${line.asset_class}`}
                >
                  <td className="asset-cell">
                    <span className="asset-cell-icon">{icon}</span>
                    <span className="asset-cell-name">{line.asset_class}</span>
                  </td>
                  <td className="text-right font-mono">{line.units}</td>
                  <td className="text-right font-mono">
                    <FormattedMoney value={line.nav} />
                  </td>
                  <td className="text-right font-semibold">
                    <FormattedMoney value={line.current_value} />
                  </td>
                  <td className="text-right">
                    <FormattedPercent value={line.current_pct} />
                  </td>
                  <td className="text-right">
                    <FormattedPercent value={line.target_pct} />
                  </td>
                  <td className="text-right font-mono">
                    {line.drift_pct ? (
                      <span className={isBreached ? 'drift-val--breached' : 'drift-val--ok'}>
                        <FormattedPercent value={line.drift_pct} />
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="text-center">
                    {line.breached === null ? (
                      <span className="text-muted">—</span>
                    ) : isBreached ? (
                      <Badge variant="breached" size="sm">
                        BREACHED
                      </Badge>
                    ) : (
                      <Badge variant="balanced" size="sm">
                        NORMAL
                      </Badge>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Responsive Cards View (<= 640px) */}
      <div className="holdings-mobile-view">
        {holdings.lines.map((line) => {
          const icon = ASSET_ICONS[line.asset_class] || '📦';
          const isBreached = line.breached === true;
          return (
            <div
              key={line.asset_class}
              className={`card holding-mobile-card ${isBreached ? 'holding-mobile-card--breached' : ''}`}
            >
              <div className="holding-mobile-card__header">
                <div className="holding-mobile-card__title">
                  <span className="asset-cell-icon">{icon}</span>
                  <span className="asset-cell-name">{line.asset_class}</span>
                </div>
                {line.breached !== null && (
                  <Badge variant={isBreached ? 'breached' : 'balanced'} size="sm">
                    {isBreached ? 'BREACHED' : 'NORMAL'}
                  </Badge>
                )}
              </div>

              <div className="holding-mobile-card__grid">
                <div>
                  <span className="m-label">Valuation</span>
                  <span className="m-val font-semibold">
                    <FormattedMoney value={line.current_value} />
                  </span>
                </div>
                <div>
                  <span className="m-label">Units Held</span>
                  <span className="m-val font-mono">{line.units}</span>
                </div>
                <div>
                  <span className="m-label">Current %</span>
                  <span className="m-val">
                    <FormattedPercent value={line.current_pct} />
                  </span>
                </div>
                <div>
                  <span className="m-label">Target %</span>
                  <span className="m-val">
                    <FormattedPercent value={line.target_pct} />
                  </span>
                </div>
                <div>
                  <span className="m-label">Drift %</span>
                  <span className={`m-val ${isBreached ? 'drift-val--breached' : ''}`}>
                    <FormattedPercent value={line.drift_pct} />
                  </span>
                </div>
                <div>
                  <span className="m-label">NAV</span>
                  <span className="m-val">
                    <FormattedMoney value={line.nav} />
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
