export interface AssetClassOut {
  code: string;
  name: string;
  is_active: boolean;
  display_order: number;
  created_at: string;
}

export interface AssetClassCreateIn {
  code: string;
  name: string;
  display_order: number;
}

export interface AssetClassPatchIn {
  name?: string | null;
  is_active?: boolean | null;
  display_order?: number | null;
}

export type PolicyStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';

export interface VersionSummary {
  id: string;
  version_no: number;
  status: PolicyStatus;
  published_at: string | null;
}

export interface VersionDetail extends VersionSummary {
  created_at: string;
  definition: Record<string, unknown>;
}

export interface DefinitionUpdate {
  definition: Record<string, unknown>;
}

export interface NavRefreshResponse {
  nav_date?: string;
  prices_loaded?: number;
  status?: string;
}
