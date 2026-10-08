import { request } from './client';
import type {
  AdvisorCustomerOut,
  AdvisorCustomerPortfolioOut,
  AuditEventOut,
  ManualRecommendationIn,
  RiskOverrideIn,
  RiskOverrideOut,
} from '../types/advisor';
import type { RecommendationOut } from '../types/recommendation';

export async function listAdvisorCustomers(token: string): Promise<AdvisorCustomerOut[]> {
  return request<AdvisorCustomerOut[]>('/api/v1/advisor/customers', { token });
}

export async function getAdvisorCustomerPortfolio(
  token: string,
  customerId: string,
): Promise<AdvisorCustomerPortfolioOut> {
  return request<AdvisorCustomerPortfolioOut>(`/api/v1/advisor/customers/${customerId}/portfolio`, { token });
}

export async function submitRiskOverride(
  token: string,
  customerId: string,
  data: RiskOverrideIn,
): Promise<RiskOverrideOut> {
  return request<RiskOverrideOut>(`/api/v1/advisor/customers/${customerId}/risk-overrides`, {
    method: 'POST',
    token,
    body: data,
  });
}

export async function submitManualRecommendation(
  token: string,
  customerId: string,
  data: ManualRecommendationIn,
): Promise<RecommendationOut> {
  return request<RecommendationOut>(`/api/v1/advisor/customers/${customerId}/manual-recommendations`, {
    method: 'POST',
    token,
    body: data,
  });
}

export async function getCustomerAuditTrail(token: string, customerId: string): Promise<AuditEventOut[]> {
  return request<AuditEventOut[]>(`/api/v1/advisor/customers/${customerId}/audit`, { token });
}
