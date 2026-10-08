import { request } from './client';
import type { RecommendationIn, RecommendationOut } from '../types/recommendation';

export async function createRecommendation(
  token: string,
  data: RecommendationIn = {},
): Promise<RecommendationOut> {
  return request<RecommendationOut>('/api/v1/recommendations', {
    method: 'POST',
    token,
    body: data,
  });
}

export async function getLatestRecommendation(token: string): Promise<RecommendationOut> {
  return request<RecommendationOut>('/api/v1/recommendations/latest', { token });
}

export async function listRecommendations(token: string): Promise<RecommendationOut[]> {
  return request<RecommendationOut[]>('/api/v1/recommendations', { token });
}
