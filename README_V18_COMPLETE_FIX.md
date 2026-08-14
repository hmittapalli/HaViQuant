# HaViQuant V18 — 360 UI Data/Overlap Fix

This release fixes the React presentation layer without replacing the existing intelligence engines.

## Fixed
- Technical indicators now map canonical engine keys (`sma_20`, `sma_50`, `sma_200`) correctly.
- Technical score now reads the production decision engine's `technical_score`/`score`.
- Fundamental score, P/E, EPS, profitability and growth map to the actual company-intelligence schema.
- Company scorecards use the actual engine fields: `overall_company_score`, `business_quality`, `growth_score`, `financial_strength`.
- Products/Demand is rendered as structured driver cards instead of one giant JSON table cell.
- Tables are horizontally scrollable and long JSON cannot force page width.
- Responsive layout prevents card/panel/header overlap.
- 1-second quote refresh remains enabled; historical series is not redundantly re-downloaded every second.
- Existing Phase 3.8/3.9/3.9.1 research remains isolated from production decisions.
- Existing portfolio/risk/company/fundamental engines are preserved.
- Missing provider data is explicitly labeled rather than fabricated.

## Important
Backlog, competition, governance/ethics and some company-specific fields may legitimately be unavailable from Yahoo Finance. The UI now explains this instead of presenting an unattractive giant raw JSON block.

## Run
```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_V18_FIXED
chmod +x start_all.sh
./start_all.sh
```

Web: http://localhost:5173/
API: http://127.0.0.1:8000/
