export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}

export interface ReadinessResponse {
  status: "ok" | "degraded";
  checks: {
    database: boolean;
    redis: boolean;
  };
}