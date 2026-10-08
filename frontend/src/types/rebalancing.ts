export interface RebalanceLineOut {
  asset_class: string;
  current_value: string;
  current_pct: string | null;
  target_pct: string | null;
  drift_pct: string | null;
  target_value: string | null;
  nav: string;
  action: 'BUY' | 'SELL' | 'HOLD' | string;
  quantity: string | null;
  trade_value: string | null;
}

export interface DecisionOut {
  decision: 'ACCEPTED' | 'DISMISSED' | string;
  actor_role: string;
  created_at: string;
  reason?: string | null;
}

export interface RebalanceProposalOut {
  id: string;
  customer_id: string;
  nav_date: string;
  status: 'PROPOSED' | 'ACCEPTED' | 'DISMISSED' | 'EXPIRED' | string;
  total_value: string;
  drift_threshold_pct: string;
  post_trade_cash: string;
  created_at: string;
  lines: RebalanceLineOut[];
  decision?: DecisionOut | null;
}

export interface RebalanceSummaryOut {
  id: string;
  status: string;
  nav_date: string;
  created_at: string;
}

export interface StubOrderOut {
  id: string;
  asset_class: string;
  side: 'BUY' | 'SELL' | string;
  quantity: string;
  trade_value: string;
  status: string;
}

export interface AcceptProposalOut {
  id: string;
  status: string;
  orders: StubOrderOut[];
}

export interface DismissProposalOut {
  id: string;
  status: string;
}
