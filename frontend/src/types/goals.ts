export interface GoalProgressOut {
  nav_date: string;
  current_goal_value: string;
  percent_complete: string;
  status: 'IN_PROGRESS' | 'ACHIEVED' | string;
  reason?: string | null;
  created_at?: string | null;
}

export interface GoalOut {
  id: string;
  customer_id: string;
  name: string;
  goal_type: string;
  target_amount: string;
  target_date: string;
  priority: number;
  funding_share_pct: string;
  created_at: string;
  updated_at: string;
  progress?: GoalProgressOut | null;
}

export interface GoalCreateIn {
  name: string;
  goal_type: string;
  target_amount: string;
  target_date: string;
  priority: number;
  funding_share_pct: string;
}

export interface GoalProgressHistoryOut {
  latest: GoalProgressOut | null;
  history: GoalProgressOut[];
}
