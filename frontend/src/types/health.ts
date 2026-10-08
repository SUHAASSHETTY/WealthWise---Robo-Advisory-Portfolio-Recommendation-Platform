/** Mirrors GET /health (app_spec §5.8). */
export interface HealthStatus {
  status: 'ok' | 'unavailable';
  db: 'connected' | 'unreachable';
}
