# Daton ESG

Daton ESG is the Worton ESG Report Generator monorepo. The product is an internal SaaS platform for generating sustainability reports in Portuguese, based on client documents and aligned primarily to the GRI standard.

The goal of the MVP is to reduce the time required to produce ESG reports by automating document intake, data extraction, report drafting with AI, chart and table generation, GRI index mapping, consultant review, and export to Word and PDF.

## Planned Scope

- Project and report management for Worton consultants
- Upload and parsing of PDF, Excel/CSV, and Word documents
- ESG data classification and indicator extraction
- AI-assisted generation of report sections
- Automatic charts, tables, and GRI index generation
- Review and editing workflow before final export

## Repository Structure

```text
.
├── backend/             # FastAPI backend
├── frontend/            # React + Vite frontend
├── infra/               # Infrastructure, deployment, and local environment files
├── docs/                # Product, architecture, and reference materials
└── .github/workflows/   # CI/CD workflows
```

## Documentation

Core product and domain references currently live in [`docs/`](/Users/webstar/Daton/daton-esg/docs):

- [`docs/PRD_Worton_ESG_Report_Generator_v1.docx`](/Users/webstar/Daton/daton-esg/docs/PRD_Worton_ESG_Report_Generator_v1.docx)
- [`docs/Documentos de Instrução/01) Diretrizes de IA para Relatórios de Sustentabilidade - Versão 2.docx`](/Users/webstar/Daton/daton-esg/docs/Documentos%20de%20Instruc%CC%A7a%CC%83o/01%29%20Diretrizes%20de%20IA%20para%20Relato%CC%81rios%20de%20Sustentabilidade%20-%20Versa%CC%83o%202.docx)
- [`docs/arch-diagrams/Arquitetura_Tecnica_Worton_ESG_v1.docx`](/Users/webstar/Daton/daton-esg/docs/arch-diagrams/Arquitetura_Tecnica_Worton_ESG_v1.docx)
- [`docs/mvp-backlog.md`](/Users/webstar/Daton/daton-esg/docs/mvp-backlog.md)
- [`docs/onboarding-guide.md`](/Users/webstar/Daton/daton-esg/docs/onboarding-guide.md)

## Status

This repository is in the foundation phase of the MVP. The monorepo structure and source documentation are present, while the application skeleton, local environment, database setup, and CI workflows are being added incrementally.
