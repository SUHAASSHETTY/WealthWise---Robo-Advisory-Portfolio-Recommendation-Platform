import React, { useEffect, useState } from 'react';
import {
  createDraftRiskPolicy,
  getActiveRiskPolicy,
  getDraftRiskPolicy,
  publishDraftRiskPolicy,
  updateDraftRiskPolicy,
} from '../../api/adminApi';
import type { VersionDetail } from '../../types/admin';
import { Badge } from '../../components/common/Badge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';

interface RiskPolicyDefinition {
  bands?: Record<string, { min_score: number; max_score: number }>;
  questions?: Array<{ code: string; prompt: string }>;
}

export const RiskPolicyManager: React.FC<{ token: string }> = ({ token }) => {
  const [activePolicy, setActivePolicy] = useState<VersionDetail | null>(null);
  const [draftPolicy, setDraftPolicy] = useState<VersionDetail | null>(null);
  const [draftDef, setDraftDef] = useState<RiskPolicyDefinition>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadPolicies = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [active, draft] = await Promise.all([
        getActiveRiskPolicy(token),
        getDraftRiskPolicy(token),
      ]);
      setActivePolicy(active);
      setDraftPolicy(draft);
      if (draft?.definition) {
        setDraftDef(draft.definition as unknown as RiskPolicyDefinition);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load risk policies.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, [token]);

  const handleCreateDraft = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const draft = await createDraftRiskPolicy(token);
      setDraftPolicy(draft);
      setDraftDef(draft.definition as unknown as RiskPolicyDefinition);
      setSuccessMsg(`Draft risk policy v${draft.version_no} created.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create draft policy.';
      setError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateBandRange = (band: string, field: 'min_score' | 'max_score', val: number) => {
    setDraftDef((prev) => {
      const bands = prev.bands || {};
      const current = bands[band] || { min_score: 0, max_score: 0 };
      return {
        ...prev,
        bands: {
          ...bands,
          [band]: {
            ...current,
            [field]: val,
          },
        },
      };
    });
  };

  const handleSaveDraft = async () => {
    if (!draftPolicy) return;
    setIsSaving(true);
    setError(null);
    try {
      const updated = await updateDraftRiskPolicy(token, draftPolicy.id, {
        definition: draftDef as unknown as Record<string, unknown>,
      });
      setDraftPolicy(updated);
      setSuccessMsg('Draft risk policy saved successfully.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update draft policy.';
      setError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const handlePublishDraft = async () => {
    if (!draftPolicy) return;
    setIsSaving(true);
    setError(null);
    try {
      const published = await publishDraftRiskPolicy(token, draftPolicy.id);
      setSuccessMsg(`Risk policy v${published.version_no} published and activated!`);
      await loadPolicies();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to publish draft policy.';
      setError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading risk policies..." />;
  }

  const activeDef = (activePolicy?.definition || {}) as unknown as RiskPolicyDefinition;

  return (
    <div className="policy-manager">
      {error && <Alert type="error" title="Error" message={error} onClose={() => setError(null)} />}
      {successMsg && (
        <Alert type="success" title="Success" message={successMsg} onClose={() => setSuccessMsg(null)} />
      )}

      {activePolicy && (
        <div className="card active-version-card">
          <div className="card__header">
            <div>
              <div className="tag-row">
                <Badge variant="published" size="md">
                  ACTIVE POLICY
                </Badge>
                <span className="version-tag font-mono">Version {activePolicy.version_no}</span>
              </div>
              <h3 className="card__title">Current Active Risk Questionnaire Policy</h3>
            </div>
            {!draftPolicy && (
              <button
                type="button"
                className="btn btn--primary"
                onClick={handleCreateDraft}
                disabled={isSaving}
              >
                + Create Next Draft Policy
              </button>
            )}
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Risk Band</th>
                  <th className="text-right">Min Score</th>
                  <th className="text-right">Max Score</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {activeDef.bands &&
                  Object.entries(activeDef.bands).map(([band, range]) => (
                    <tr key={band}>
                      <td className="font-semibold">{band}</td>
                      <td className="text-right font-mono">{range.min_score}</td>
                      <td className="text-right font-mono">{range.max_score}</td>
                      <td className="text-muted">Score Range {range.min_score}–{range.max_score} pts</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {draftPolicy && (
        <div className="card draft-version-card">
          <div className="card__header">
            <div>
              <div className="tag-row">
                <Badge variant="draft" size="md">
                  DRAFT POLICY
                </Badge>
                <span className="version-tag font-mono">Version {draftPolicy.version_no}</span>
              </div>
              <h3 className="card__title">Draft Risk Policy Editor</h3>
            </div>
            <div className="card-actions">
              <button
                type="button"
                className="btn btn--outline"
                onClick={handleSaveDraft}
                disabled={isSaving}
              >
                Save Draft
              </button>
              <button
                type="button"
                className="btn btn--success"
                onClick={handlePublishDraft}
                disabled={isSaving}
              >
                ✓ Publish Version {draftPolicy.version_no}
              </button>
            </div>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Risk Band</th>
                  <th>Min Score</th>
                  <th>Max Score</th>
                </tr>
              </thead>
              <tbody>
                {draftDef.bands &&
                  Object.entries(draftDef.bands).map(([band, range]) => (
                    <tr key={band}>
                      <td className="font-semibold">{band}</td>
                      <td>
                        <input
                          type="number"
                          className="form-input form-input--sm text-right"
                          value={range.min_score}
                          onChange={(e) =>
                            handleUpdateBandRange(band, 'min_score', parseInt(e.target.value, 10) || 0)
                          }
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          className="form-input form-input--sm text-right"
                          value={range.max_score}
                          onChange={(e) =>
                            handleUpdateBandRange(band, 'max_score', parseInt(e.target.value, 10) || 0)
                          }
                        />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
