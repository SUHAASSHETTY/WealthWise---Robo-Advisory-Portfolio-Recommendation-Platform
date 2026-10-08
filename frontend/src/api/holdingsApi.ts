import { request } from './client';
import type { HoldingsResponse } from '../types/holdings';

export async function getHoldings(token: string): Promise<HoldingsResponse> {
  return request<HoldingsResponse>('/api/v1/holdings', { token });
}
