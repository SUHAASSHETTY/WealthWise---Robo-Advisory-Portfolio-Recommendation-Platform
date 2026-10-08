import React, { useEffect, useState } from 'react';
import {
  createDraftTemplateVersion,
  getActiveTemplateVersion,
  getDraftTemplateVersion,
  publishDraftTemplateVersion,
  updateDraftTemplateVersion,
} from '../../api/adminApi';
import type { VersionDetail } from '../../types/admin';
import { Badge } from '../../components/common/Badge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';

interface TemplateBandAllocation {
  EQUITY: string;
  DEBT: string;
  GOLD: string;
  CASH: string;
}

interface TemplateDefinition {
  drift_threshold_pct?: string;
  bands?: Record<string, TemplateBandAllocation>;
}

export const TemplateVersionManager: React.FC<{ token: string }> = ({ token }) => {
  const [activeVersion, setActiveVersion] = useState<VersionDetail | null>(null);
  const [draftVersion, setDraftVersion] = useState<VersionDetail | null>(null);
  const [draftDef, setDraftDef] = useState<TemplateDefinition>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadVersions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [active, draft] = await Promise.all([
        getActiveTemplateVersion(token),
        getDraftTemplateVersion(token),
      ]);
      setActiveVersion(active);
      setDraftVersion(draft);
      if (draft?.definition) {
        setDraftDef(draft.definition as unknown as TemplateDefinition);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load template versions.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadVersions();
  }, [token]);

  const handleCreateDraft = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const draft = await createDraftTemplateVersion(token);
      setDraftVersion(draft);
      setDraftDef(draft.definition as unknown as TemplateDefinition);
      setSuccessMsg(`Draft template version v${draft.version_no} created from current active template.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create draft template.';
      setError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateDraftAllocation = (
    band: string,
    asset: 'EQUITY' | 'DEBT' | 'GOLD' | 'CASH',
    value: string,
  ) => {
    setDraftDef((prev) => {
      const bands = prev.bands || {};
      const currentBand = bands[band] || { EQUITY: '0', DEBT: '0', GOLD: '0', CASH: '0' };
      return {
        ...prev,
        bands: {
          ...bands,
          [band]: {
            ...currentBand,
            [asset]: value,
          },
        },
      };
    });
  };

  const handleSaveDraft = async () => {
    if (!draftVersion) return;
    setIsSaving(true);
    setError(null);
    try {
      const updated = await updateDraftTemplateVersion(token, draftVersion.id, {
        definition: draftDef as unknown as Record<string, unknown>,
      });
      setDraftVersion(updated);
      setSuccessMsg('Draft template definition saved successfully.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update draft template.';
      setError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const handlePublishDraft = async () => {
    if (!draftVersion) return;
    setIsSaving(true);
    setError(null);
    try {
      const published = await publishDraftTemplateVersion(token, draftVersion.id);
      setSuccessMsg(`Template version v${published.version_no} successfully published and activated!`);
      await loadVersions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to publish draft template.';
      setError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading investment template versions..." />;
  }

  const activeDef = (activeVersion?.definition || {}) as unknown as TemplateDefinition;

  return (
    <div className="template-manager">
      {error && <Alert type="error" title="Error" message={error} onClose={() => setError(null)} />}
      {successMsg && (
        <Alert type="success" title="Success" message={successMsg} onClose={() => setSuccessMsg(null)} />
      )}

      {/* Active Version Card */}
      {activeVersion && (
        <div className="card active-version-card">
          <div className="card__header">
            <div>
              <div className="tag-row">
                <Badge variant="published" size="md">
                  PUBLISHED & ACTIVE
                </Badge>
                <span className="version-tag font-mono">Version {activeVersion.version_no}</span>
              </div>
              <h3 className="card__title">Current Active Template Policy</h3>
            </div>
            {!draftVersion && (
              <button
                type="button"
                className="btn btn--primary"
                onClick={handleCreateDraft}
                disabled={isSaving}
                id="create-template-draft-btn"
              >
                + Create Next Draft Version
              </button>
            )}
          </div>

          <div className="version-details">
            <div className="detail-pill">
              <span className="pill-label">Published At:</span>
              <span className="pill-val">
                {activeVersion.published_at ? new Date(activeVersion.published_at).toLocaleString() : 'N/A'}
              </span>
            </div>
            <div className="detail-pill">
              <span className="pill-label">Drift Threshold:</span>
              <span className="pill-val">{activeDef.drift_threshold_pct || '5.00'}%</span>
            </div>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Risk Band</th>
                  <th className="text-right">Equity %</th>
                  <th className="text-right">Debt %</th>
                  <th className="text-right">Gold %</th>
                  <th className="text-right">Cash %</th>
                  <th className="text-center">Total Sum</th>
                </tr>
              </thead>
              <tbody>
                {activeDef.bands &&
                  Object.entries(activeDef.bands).map(([band, alloc]) => (
                    <tr key={band}>
                      <td className="font-semibold">{band}</td>
                      <td className="text-right">{alloc.EQUITY}%</td>
                      <td className="text-right">{alloc.DEBT}%</td>
                      <td className="text-right">{alloc.GOLD}%</td>
                      <td className="text-right">{alloc.CASH}%</td>
                      <td className="text-center">
                        <span className="badge badge--success badge--sm">100.00%</span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Draft Version Card */}
      {draftVersion && (
        <div className="card draft-version-card">
          <div className="card__header">
            <div>
              <div className="tag-row">
                <Badge variant="draft" size="md">
                  DRAFT IN PROGRESS
                </Badge>
                <span className="version-tag font-mono">Version {draftVersion.version_no}</span>
              </div>
              <h3 className="card__title">Draft Template Version Editor</h3>
            </div>
            <div className="card-actions">
              <button
                type="button"
                className="btn btn--outline"
                onClick={handleSaveDraft}
                disabled={isSaving}
                id="save-template-draft-btn"
              >
                Save Draft
              </button>
              <button
                type="button"
                className="btn btn--success"
                onClick={handlePublishDraft}
                disabled={isSaving}
                id="publish-template-btn"
              >
                ✓ Publish Version {draftVersion.version_no}
              </button>
            </div>
          </div>

          <div className="form-group drift-threshold-group">
            <label htmlFor="draft-drift-threshold" className="form-label">
              Portfolio Drift Threshold (%)
            </label>
            <input
              id="draft-drift-threshold"
              type="text"
              className="form-input"
              value={draftDef.drift_threshold_pct || '5.00'}
              onChange={(e) => setDraftDef((prev) => ({ ...prev, drift_threshold_pct: e.target.value }))}
            />
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Risk Band</th>
                  <th>Equity (%)</th>
                  <th>Debt (%)</th>
                  <th>Gold (%)</th>
                  <th>Cash (%)</th>
                  <th>Sum Status</th>
                </tr>
              </thead>
              <tbody>
                {draftDef.bands &&
                  Object.entries(draftDef.bands).map(([band, alloc]) => {
                    const e = parseFloat(alloc.EQUITY) || 0;
                    const d = parseFloat(alloc.DEBT) || 0;
                    const g = parseFloat(alloc.GOLD) || 0;
                    const c = parseFloat(alloc.CASH) || 0;
                    const sum = (e + d + g + c).toFixed(2);
                    const is100 = sum === '100.00';
                    return (
                      <tr key={band}>
                        <td className="font-semibold">{band}</td>
                        <td>
                          <input
                            type="text"
                            className="form-input form-input--sm text-right"
                            value={alloc.EQUITY}
                            onChange={(ev) => handleUpdateDraftAllocation(band, 'EQUITY', ev.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            className="form-input form-input--sm text-right"
                            value={alloc.DEBT}
                            onChange={(ev) => handleUpdateDraftAllocation(band, 'DEBT', ev.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            className="form-input form-input--sm text-right"
                            value={alloc.GOLD}
                            onChange={(ev) => handleUpdateDraftAllocation(band, 'GOLD', ev.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            className="form-input form-input--sm text-right"
                            value={alloc.CASH}
                            onChange={(ev) => handleUpdateDraftAllocation(band, 'CASH', ev.target.value)}
                          />
                        </td>
                        <td>
                          <span className={`badge ${is100 ? 'badge--success' : 'badge--danger'} badge--sm`}>
                            {sum}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
