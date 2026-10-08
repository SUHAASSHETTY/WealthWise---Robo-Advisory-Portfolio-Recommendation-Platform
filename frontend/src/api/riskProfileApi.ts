import { request } from './client';
import type {
  AssessmentIn,
  AssessmentOut,
  HistoryEntryOut,
  QuestionnaireOut,
  RiskProfileOut,
} from '../types/risk_profile';

export async function getQuestionnaire(token: string): Promise<QuestionnaireOut> {
  return request<QuestionnaireOut>('/api/v1/risk-profile/questionnaire', { token });
}

export async function submitAssessment(token: string, data: AssessmentIn): Promise<AssessmentOut> {
  return request<AssessmentOut>('/api/v1/risk-profile/assessments', {
    method: 'POST',
    token,
    body: data,
  });
}

export async function getRiskProfile(token: string): Promise<RiskProfileOut> {
  return request<RiskProfileOut>('/api/v1/risk-profile', { token });
}

export async function getRiskProfileHistory(token: string): Promise<HistoryEntryOut[]> {
  return request<HistoryEntryOut[]>('/api/v1/risk-profile/history', { token });
}
