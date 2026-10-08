import { request } from './client';
import type { GoalCreateIn, GoalOut, GoalProgressHistoryOut } from '../types/goals';

export async function listGoals(token: string): Promise<GoalOut[]> {
  return request<GoalOut[]>('/api/v1/goals', { token });
}

export async function createGoal(token: string, data: GoalCreateIn): Promise<GoalOut> {
  return request<GoalOut>('/api/v1/goals', {
    method: 'POST',
    token,
    body: data,
  });
}

export async function getGoal(token: string, goalId: string): Promise<GoalOut> {
  return request<GoalOut>(`/api/v1/goals/${goalId}`, { token });
}

export async function getGoalProgressHistory(token: string, goalId: string): Promise<GoalProgressHistoryOut> {
  return request<GoalProgressHistoryOut>(`/api/v1/goals/${goalId}/progress`, { token });
}
