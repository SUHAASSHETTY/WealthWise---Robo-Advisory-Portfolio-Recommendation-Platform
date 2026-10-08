import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  createRecommendation,
  getLatestRecommendation,
  listRecommendations,
} from '../../api/recommendationsApi';
import type { RecommendationOut } from '../../types/recommendation';
import { AllocationBreakdown } from './AllocationBreakdown';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';
import { Badge } from '../../components/common/Badge';

export const RecommendationPage: React.FC = () => {
  const { token, persona } = useAuth();
  const [latestRec, setLatestRec] = useState<RecommendationOut | null>(null);
  const [recHistory, setRecHistory] = useState<RecommendationOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadRecommendations = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [latest, list] = await Promise.allSettled([
        getLatestRecommendation(token),
        listRecommendations(token),
      ]);

      if (latest.status === 'fulfilled') {
        setLatestRec(latest.value);
      } else {
        setLatestRec(null);
      }

      if (list.status === 'fulfilled') {
        setRecHistory(list.value);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load recommendations.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendations();
  }, [token, persona]);

  const handleGenerateRecommendation = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const res = await createRecommendation(token, {});
      setLatestRec(res);
      setSuccessMsg(
        `Generated recommendation (${res.risk_band}, Template v${res.template_version_no})!`,
      );
      const list = await listRecommendations(token);
      setRecHistory(list);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate recommendation.';
      setError(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Resolving your portfolio recommendation..." />;
  }

  return (
    <div className="feature-page recommendation-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Portfolio Allocation Recommendations</h2>
          <p className="page-subtitle">
            Deterministic, rule-based asset allocation tuned to your risk profile and goal horizon.
          </p>
        </div>
      </div>

      {error && <Alert type="error" title="Error" message={error} onClose={() => setError(null)} />}
      {successMsg && (
        <Alert type="success" title="Success" message={successMsg} onClose={() => setSuccessMsg(null)} />
      )}

      {latestRec ? (
        <div className="rec-content">
          <AllocationBreakdown
            recommendation={latestRec}
            onGenerateNew={handleGenerateRecommendation}
            isGenerating={isGenerating}
          />

          {recHistory.length > 1 && (
            <div className="card rec-history-card">
              <div className="card__header">
                <h3 className="card__title">Recommendation History</h3>
                <span className="card__subtitle">Append-only archive of target portfolio allocations</span>
              </div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Risk Band</th>
                      <th>Template</th>
                      <th>Source</th>
                      <th>Allocation (E/D/G/C)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recHistory.map((r) => {
                      const allocStr = r.allocation
                        .map((a) => `${a.target_pct}%`)
                        .join(' / ');
                      return (
                        <tr key={r.id}>
                          <td>{new Date(r.created_at).toLocaleString()}</td>
                          <td>
                            <Badge variant="neutral" size="sm">
                              {r.risk_band}
                            </Badge>
                          </td>
                          <td>v{r.template_version_no}</td>
                          <td>{r.source}</td>
                          <td>{allocStr}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="card empty-state">
          <div className="empty-state__icon">📊</div>
          <h3>No Recommendation Available</h3>
          <p>
            You must have an active risk profile assessment before a deterministic portfolio
            recommendation can be generated.
          </p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={handleGenerateRecommendation}
            disabled={isGenerating}
          >
            {isGenerating ? 'Generating...' : 'Generate Initial Recommendation'}
          </button>
        </div>
      )}
    </div>
  );
};
