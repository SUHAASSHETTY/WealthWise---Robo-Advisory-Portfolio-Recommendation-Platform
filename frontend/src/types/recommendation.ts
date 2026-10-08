import type { RiskBand } from './risk_profile';

export interface AllocationRowOut {
  asset_class: string;
  target_pct: string;
}

export interface RecommendationOut {
  id: string;
  source: string;
  risk_band: RiskBand;
  template_version_no: number;
  goal_id: string | null;
  horizon_months: number | null;
  horizon_rule: string;
  as_of_date: string;
  allocation: AllocationRowOut[];
  total_pct: string;
  created_at: string;
}

export interface RecommendationIn {
  goal_id?: string | null;
}
