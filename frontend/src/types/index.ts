export interface HealthResponse {
  status: string;
  service: string;
  services?: Record<string, string>;
}
