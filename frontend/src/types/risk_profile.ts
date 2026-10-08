export type RiskBand = 'CONSERVATIVE' | 'MODERATE' | 'AGGRESSIVE';

export interface OptionOut {
  code: string;
  label: string;
}

export interface QuestionOut {
  code: string;
  prompt: string;
  order: number;
  options: OptionOut[];
}

export interface QuestionnaireOut {
  policy_version_id: string;
  version_no: number;
  questions: QuestionOut[];
}

export interface AnswerIn {
  question_code: string;
  option_code: string;
}

export interface AssessmentIn {
  policy_version_id: string;
  answers: AnswerIn[];
}

export interface AssessmentOut {
  assessment_id: string;
  total_score: number;
  computed_band: RiskBand;
  assigned_band: RiskBand;
  applied_caps: string[];
  policy_version_no: number;
  created_at: string;
}

export interface RiskProfileOut {
  risk_band: RiskBand | null;
  source?: string;
  source_id?: string;
  as_of?: string;
}

export interface HistoryEntryOut {
  type: string; // "ASSESSMENT" | "ADVISOR_OVERRIDE"
  id: string;
  band: RiskBand;
  created_at: string;
  policy_version_no?: number | null;
  reason_code?: string | null;
}
