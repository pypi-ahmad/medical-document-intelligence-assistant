# Folder Structure

```
medical-document-intelligence-assistant/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── routers/
│   │   │   ├── services/
│   │   │   │   ├── infrastructure/
│   │   │   │   └── medical/
│   │   │   ├── models/
│   │   │   ├── security/
│   │   │   └── utils/
│   │   ├── alembic/
│   │   ├── tests/
│   │   └── data/
│   └── frontend/
│       └── src/
│           ├── app/
│           ├── components/
│           └── lib/
├── docs/
│   ├── diagrams/
│   └── screenshots/
├── infra/
│   ├── nginx/
│   ├── prometheus/
│   ├── loki/
│   └── otel/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

## Why this layout
- Clear app boundaries (`backend`, `frontend`)
- Domain-first backend separation
- Infrastructure as code co-located with app
- Documentation and diagrams first-class in repo
