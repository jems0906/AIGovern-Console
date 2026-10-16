import { defineRailway, github, postgres, preserve, project, service, volume } from "railway/iac";

export default defineRailway(() => {
  const AIGovernConsole = github("jems0906/AIGovern-Console", { rootDirectory: "/" });

  const Postgres = postgres("Postgres", { region: "us-west2" });
  Postgres.networking = { privateNetworkEndpoint: "postgres" };
  const postgresVolume = volume("postgres-volume", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "us-west2", sizeMB: 50000 });
  const backend = service("backend", {
    source: AIGovernConsole,
    build: { buildEnvironment: "V3", builder: "DOCKERFILE", dockerfilePath: "backend/Dockerfile" },
    healthcheck: "/api/health",
    healthcheckTimeout: 120,
    replicas: { "us-west2": 1 },
    deploy: { restartPolicyMaxRetries: 3 },
    env: { ADMIN_API_KEY: preserve(), DATABASE_URL: preserve(), ENVIRONMENT: preserve(), PORT: preserve() },
  });
  const frontend = service("frontend", {
    source: AIGovernConsole,
    build: { buildEnvironment: "V3", builder: "DOCKERFILE", dockerfilePath: "frontend/Dockerfile" },
    healthcheck: "/",
    healthcheckTimeout: 120,
    replicas: { "us-west2": 1 },
    deploy: { restartPolicyMaxRetries: 3 },
    env: { BACKEND_UPSTREAM: preserve(), PORT: preserve() },
  });

  return project("AIGovern-Console", {
    resources: [backend, frontend, Postgres, postgresVolume],
  });
});
