import React, { useEffect, useState } from 'react';
import { createAssetClass, listAssetClasses, patchAssetClass } from '../../api/adminApi';
import type { AssetClassOut } from '../../types/admin';
import { Badge } from '../../components/common/Badge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';

export const AssetClassManager: React.FC<{ token: string }> = ({ token }) => {
  const [assetClasses, setAssetClasses] = useState<AssetClassOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [newCode, setNewCode] = useState('');
  const [newName, setNewName] = useState('');
  const [newOrder, setNewOrder] = useState('5');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadAssetClasses = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await listAssetClasses(token);
      setAssetClasses(list);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load asset classes.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAssetClasses();
  }, [token]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!newCode.trim() || !newName.trim()) {
      setError('Code and Name are required.');
      return;
    }
    setIsCreating(true);
    try {
      await createAssetClass(token, {
        code: newCode.trim().toUpperCase(),
        name: newName.trim(),
        display_order: parseInt(newOrder, 10) || 5,
      });
      setSuccessMsg(`Asset class ${newCode.toUpperCase()} created successfully!`);
      setNewCode('');
      setNewName('');
      await loadAssetClasses();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create asset class.';
      setError(msg);
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggleActive = async (ac: AssetClassOut) => {
    setError(null);
    try {
      await patchAssetClass(token, ac.code, {
        is_active: !ac.is_active,
      });
      setSuccessMsg(`Asset class ${ac.code} ${ac.is_active ? 'deactivated' : 'activated'}.`);
      await loadAssetClasses();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update asset class.';
      setError(msg);
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading configured asset classes..." />;
  }

  return (
    <div className="asset-class-manager">
      {error && <Alert type="error" title="Error" message={error} onClose={() => setError(null)} />}
      {successMsg && (
        <Alert type="success" title="Success" message={successMsg} onClose={() => setSuccessMsg(null)} />
      )}

      <div className="card create-asset-card">
        <div className="card__header">
          <h3 className="card__title">+ Register New Asset Class</h3>
        </div>
        <form onSubmit={handleCreate} className="asset-create-form">
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="new-ac-code" className="form-label">
                Asset Code (UPPERCASE)
              </label>
              <input
                id="new-ac-code"
                type="text"
                className="form-input"
                placeholder="e.g. CRYPTO"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value.toUpperCase())}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="new-ac-name" className="form-label">
                Display Name
              </label>
              <input
                id="new-ac-name"
                type="text"
                className="form-input"
                placeholder="e.g. Digital Assets & Crypto"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="new-ac-order" className="form-label">
                Display Order
              </label>
              <input
                id="new-ac-order"
                type="number"
                className="form-input"
                value={newOrder}
                onChange={(e) => setNewOrder(e.target.value)}
                required
              />
            </div>
          </div>
          <button type="submit" className="btn btn--primary" disabled={isCreating} id="create-ac-btn">
            {isCreating ? 'Creating...' : 'Add Asset Class'}
          </button>
        </form>
      </div>

      <div className="card asset-list-card">
        <div className="card__header">
          <h3 className="card__title">Configured Asset Classes</h3>
        </div>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Display Name</th>
                <th>Display Order</th>
                <th>Status</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {assetClasses.map((ac) => (
                <tr key={ac.code}>
                  <td className="font-mono font-semibold">{ac.code}</td>
                  <td>{ac.name}</td>
                  <td>{ac.display_order}</td>
                  <td>
                    <Badge variant={ac.is_active ? 'success' : 'neutral'} size="sm">
                      {ac.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="text-right">
                    <button
                      type="button"
                      className="btn btn--sm btn--outline"
                      onClick={() => handleToggleActive(ac)}
                    >
                      {ac.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
