import { request } from './client';
import type {
  AssetClassCreateIn,
  AssetClassOut,
  AssetClassPatchIn,
  DefinitionUpdate,
  NavRefreshResponse,
  VersionDetail,
  VersionSummary,
} from '../types/admin';

// Asset Classes
export async function listAssetClasses(token: string): Promise<AssetClassOut[]> {
  return request<AssetClassOut[]>('/api/v1/admin/asset-classes', { token });
}

export async function createAssetClass(token: string, data: AssetClassCreateIn): Promise<AssetClassOut> {
  return request<AssetClassOut>('/api/v1/admin/asset-classes', {
    method: 'POST',
    token,
    body: data,
  });
}

export async function patchAssetClass(
  token: string,
  code: string,
  data: AssetClassPatchIn,
): Promise<AssetClassOut> {
  return request<AssetClassOut>(`/api/v1/admin/asset-classes/${code}`, {
    method: 'PATCH',
    token,
    body: data,
  });
}

// Template Versions
export async function listTemplateVersions(token: string): Promise<VersionSummary[]> {
  return request<VersionSummary[]>('/api/v1/admin/template-versions', { token });
}

export async function getTemplateVersion(token: string, versionId: string): Promise<VersionDetail> {
  return request<VersionDetail>(`/api/v1/admin/template-versions/${versionId}`, { token });
}

export async function getActiveTemplateVersion(token: string): Promise<VersionDetail | null> {
  const versions = await listTemplateVersions(token);
  const published = versions
    .filter((v) => v.status === 'PUBLISHED')
    .sort((a, b) => b.version_no - a.version_no);
  if (published.length === 0 || !published[0]) return null;
  return getTemplateVersion(token, published[0].id);
}

export async function getDraftTemplateVersion(token: string): Promise<VersionDetail | null> {
  const versions = await listTemplateVersions(token);
  const draft = versions.find((v) => v.status === 'DRAFT');
  if (!draft) return null;
  return getTemplateVersion(token, draft.id);
}

export async function createDraftTemplateVersion(token: string): Promise<VersionDetail> {
  return request<VersionDetail>('/api/v1/admin/template-versions/drafts', {
    method: 'POST',
    token,
  });
}

export async function updateDraftTemplateVersion(
  token: string,
  versionId: string,
  data: DefinitionUpdate,
): Promise<VersionDetail> {
  return request<VersionDetail>(`/api/v1/admin/template-versions/${versionId}`, {
    method: 'PUT',
    token,
    body: data,
  });
}

export async function publishDraftTemplateVersion(token: string, versionId: string): Promise<VersionSummary> {
  return request<VersionSummary>(`/api/v1/admin/template-versions/${versionId}/publish`, {
    method: 'POST',
    token,
  });
}

// Risk Policies
export async function listRiskPolicies(token: string): Promise<VersionSummary[]> {
  return request<VersionSummary[]>('/api/v1/admin/risk-policies', { token });
}

export async function getRiskPolicy(token: string, versionId: string): Promise<VersionDetail> {
  return request<VersionDetail>(`/api/v1/admin/risk-policies/${versionId}`, { token });
}

export async function getActiveRiskPolicy(token: string): Promise<VersionDetail | null> {
  const versions = await listRiskPolicies(token);
  const published = versions
    .filter((v) => v.status === 'PUBLISHED')
    .sort((a, b) => b.version_no - a.version_no);
  if (published.length === 0 || !published[0]) return null;
  return getRiskPolicy(token, published[0].id);
}

export async function getDraftRiskPolicy(token: string): Promise<VersionDetail | null> {
  const versions = await listRiskPolicies(token);
  const draft = versions.find((v) => v.status === 'DRAFT');
  if (!draft) return null;
  return getRiskPolicy(token, draft.id);
}

export async function createDraftRiskPolicy(token: string): Promise<VersionDetail> {
  return request<VersionDetail>('/api/v1/admin/risk-policies/drafts', {
    method: 'POST',
    token,
  });
}

export async function updateDraftRiskPolicy(
  token: string,
  versionId: string,
  data: DefinitionUpdate,
): Promise<VersionDetail> {
  return request<VersionDetail>(`/api/v1/admin/risk-policies/${versionId}`, {
    method: 'PUT',
    token,
    body: data,
  });
}

export async function publishDraftRiskPolicy(token: string, versionId: string): Promise<VersionSummary> {
  return request<VersionSummary>(`/api/v1/admin/risk-policies/${versionId}/publish`, {
    method: 'POST',
    token,
  });
}

// NAV Refresh
export async function refreshNav(token: string, targetDate?: string): Promise<NavRefreshResponse> {
  const query = targetDate ? `?target_date=${encodeURIComponent(targetDate)}` : '';
  return request<NavRefreshResponse>(`/api/v1/admin/nav-refresh${query}`, {
    method: 'POST',
    token,
  });
}
