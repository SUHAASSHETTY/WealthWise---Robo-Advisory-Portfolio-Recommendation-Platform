import type { GoalOut } from './goals';
import type { HoldingsResponse } from './holdings';
import type { RebalanceProposalOut } from './rebalancing';
import type { RecommendationOut } from './recommendation';

export interface AdvisorCustomerOut {
  customer_id: string;
  display_name: string;
  effective_band: string | null;
  band_source: string | null;
  portfolio_breached: boolean;
  open_rebalance_id: string | null;
}

export interface CustomerInfoOut {
  id: string;
  display_name: string;
  kyc_verified: boolean;
}

export interface RiskProfileSummaryOut {
  band: string | null;
  source: string | null;
  as_of: string | null;
}

export interface AdvisorCustomerPortfolioOut {
  customer: CustomerInfoOut;
  risk_profile: RiskProfileSummaryOut;
  goals: GoalOut[];
  holdings: HoldingsResponse;
  latest_recommendation: RecommendationOut | null;
  open_rebalance: RebalanceProposalOut | null;
}

export interface RiskOverrideIn {
  new_band: string;
  reason_code: string;
  note: string;
}

export interface RiskOverrideOut {
  override_id: string;
  previous_band: string;
  new_band: string;
  reason_code: string;
  actor_user_id: string;
  created_at: string;
}

export interface ManualAllocationItemIn {
  asset_class: string;
  target_pct: string;
}

export interface ManualRecommendationIn {
  allocation: ManualAllocationItemIn[];
  note: string;
}

export interface AuditEventOut {
  occurred_at: string;
  action: string;
  actor_role: string;
  actor_user_id?: string | null;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
}
