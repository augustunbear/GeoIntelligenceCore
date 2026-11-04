# ADR-0001: independent reusable repository

- Date: 2026-11-04
- Status: Accepted by project owner (architecture direction)
- Decision: GeoIntelligenceCore lives in independent private GitHub repository `augustunbear/GeoIntelligenceCore`, not inside RestaurantTrafficDiagnosis.

## Context
Multiple products may require geocoding, POI, transportation catchments, census grids and provenance. One consumer currently uses Python/FastAPI and Neon PostgreSQL; coupling generic geography to restaurant business rules creates duplication.

## Decision
Build an independent versioned, installable Python package first. Public APIs/contracts are consumer-neutral and have adapters to configurable data providers. Consumer integrations import a pinned release (Git tag/private package or commit pin), not copy sources. An HTTP façade is optional once multiple consumers or non-Python clients justify operation.

## Consequences
Benefit: shared GIS conventions, provider selection, test suite and licensing rules. Cost: package versioning and compatibility testing. New remote infrastructure and automated GIS bulk ingestion require separate cost/security ADR. This ADR does not assert that any code has yet been implemented.

## Alternatives rejected at present
- Embedding source directly in RestaurantTrafficDiagnosis: less reusable.
- Starting a microservice: unnecessary operational cost and authorization surface before real cross-language use.
- Forking/vendor copying upstream projects: creates avoidable license and maintenance burden.
