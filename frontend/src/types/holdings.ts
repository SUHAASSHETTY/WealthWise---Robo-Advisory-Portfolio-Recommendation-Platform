export interface HoldingLineResponse {
  asset_class: string;
  units: string;
  nav: string;
  current_value: string;
  current_pct: string | null;
  target_pct: string | null;
  drift_pct: string | null;
  breached: boolean | null;
}

export interface HoldingsResponse {
  nav_date: string;
  total_value: string;
  has_target: boolean;
  recommendation_id: string | null;
  template_version_no: number | null;
  drift_threshold_pct: string | null;
  portfolio_breached: boolean;
  lines: HoldingLineResponse[];
}
