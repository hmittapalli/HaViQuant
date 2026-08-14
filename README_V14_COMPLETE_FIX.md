# HaViQuant Complete Migration — V14

This package is a complete source-based migration of the supplied V13 package, with the React runtime crash fixed and the existing Python intelligence engines kept as the source of truth.

## Important fixes

- Fixed the React `ListPanel` crash:
  `TypeError: (items || []).slice is not a function`
- Added a global API response normalizer so list/object/wrapper responses render safely.
- Made DataTable handle object/wrapper responses safely.
- Stock Analysis now includes:
  - Production Decision
  - Live quote
  - Technical Intelligence
  - Fundamental Intelligence
  - Company Intelligence
  - Evidence Research Phase 3.8 / 3.9 / 3.9.1
  - Portfolio context
- Company Intelligence renders risks, demand, governance/research and competition without assuming arrays.
- News handles wrapped and direct list responses.
- Research remains isolated from the production decision.
- Existing Python engines and data files are preserved; no sample intelligence was substituted for the supplied engine.
- Web and mobile clients remain API consumers of the same backend.
- Added `.env.example` files for web/mobile.

## Start everything

```bash
cd ~/Downloads/HaViQuant_COMPLETE_MIGRATED_WEB_IOS_ANDROID_V14
chmod +x start_all.sh
./start_all.sh
```

Open:

http://127.0.0.1:5173

Backend health:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

NVDA workspace:

```bash
curl http://127.0.0.1:8000/api/v1/stock/NVDA
```

## If an old server is running

The launcher clears ports 8000 and 5173 before starting V14. Do not start V11/V12/V13 at the same time.

## Mobile

```bash
cd mobile/app
npm install
npx expo start
```

For a physical device, set `EXPO_PUBLIC_API_URL` to the Mac's LAN address, for example:

```text
http://192.168.1.151:8000/api/v1
```

The backend must listen on an address reachable by the device. For local development, change the uvicorn host in the launcher from `127.0.0.1` to `0.0.0.0` if the phone cannot reach the Mac.

## Architecture

Existing Python intelligence engines remain authoritative:

Python engines -> FastAPI -> React Web / React Native

Research validation never silently changes the production BUY/SELL decision.
