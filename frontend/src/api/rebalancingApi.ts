import { request } from './client';
import type {
  AcceptProposalOut,
  DismissProposalOut,
  RebalanceProposalOut,
  RebalanceSummaryOut,
} from '../types/rebalancing';

export async function evaluateRebalancing(token: string): Promise<RebalanceProposalOut> {
  return request<RebalanceProposalOut>('/api/v1/rebalancing/evaluate', {
    method: 'POST',
    token,
  });
}

export async function listRebalanceRecommendations(token: string): Promise<RebalanceSummaryOut[]> {
  return request<RebalanceSummaryOut[]>('/api/v1/rebalancing/recommendations', { token });
}

export async function getRebalanceRecommendation(token: string, id: string): Promise<RebalanceProposalOut> {
  return request<RebalanceProposalOut>(`/api/v1/rebalancing/recommendations/${id}`, { token });
}

export async function acceptRebalancingProposal(token: string, id: string): Promise<AcceptProposalOut> {
  return request<AcceptProposalOut>(`/api/v1/rebalancing/recommendations/${id}/accept`, {
    method: 'POST',
    token,
  });
}

export async function dismissRebalancingProposal(
  token: string,
  id: string,
  reason?: string,
): Promise<DismissProposalOut> {
  return request<DismissProposalOut>(`/api/v1/rebalancing/recommendations/${id}/dismiss`, {
    method: 'POST',
    token,
    body: { reason },
  });
}
