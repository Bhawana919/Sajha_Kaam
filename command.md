# Sajha Kaam: run commands

All commands are for PowerShell on Windows, run from the `Sajha_Kaam_Hackathon_Kit` folder.

## 1. The app: `sajha-kaam/` (backend + mobile)

Full details are in [sajha-kaam/README.md](sajha-kaam/README.md).

Copy only the lines inside each box, never the ``` lines.

### Install everything (first time only)

```powershell
pip install -r requirements.txt
cd sajha-kaam\mobile
npm install
```

`requirements.txt` holds all the Python packages, at exact versions that pass the tests. `npm install` sets up the mobile app.

If you see `Could not install packages due to an OSError ... Long Path`, Windows is refusing a very long file name inside the `anthropic` package. Install from a short folder path, or turn on Windows long paths.

### Run the backend (terminal 1)

The backend seeds the demo data on start. API docs: http://localhost:8000/docs

```powershell
.\sajha-kaam\backend\start.ps1
```

If a package is missing, the script tells you the install command. Leave this terminal open.

### Run the app (terminal 2)

`sajha-kaam\mobile\.env` already points the app at this laptop (`http://192.168.1.3:8000`). If your Wi-Fi address changes, update it there. Find it with `ipconfig`, under Wi-Fi → IPv4 Address.

```powershell
cd sajha-kaam\mobile
npx expo start --clear
```

Scan the QR code with Expo Go, or press `w` for the browser. If Windows Firewall asks about Python, allow **Private networks**, so your phone can reach the backend.

To browse with mock data only (no backend), run `npm run start:mock` instead.

### Proof pages (any browser, no sign-in)

| Page | Address |
|---|---|
| Fair Pick Receipt | http://localhost:8000/receipt/card-dashain-posts (after the pick) |
| Work Passport (public) | from the QR code on the worker's Passport tab |
| Verify one record | the "Open the Verify page" button on a public record |
| Signing key | http://localhost:8000/.well-known/sajha-kaam-keys.json |

### Demo controls

```powershell
curl.exe -X POST http://localhost:8000/demo/reset    # fresh sample data
```

In the app, **Help** has a reset button too.

### Checks

```powershell
cd sajha-kaam\backend; python -m pytest -q; python -m ruff check .
cd sajha-kaam\mobile; npm run check
cd sajha-kaam\mobile; npm run i18n:review    # refresh docs\NEPALI_REVIEW.md for the Nepali reviewer
```

### Deploy (Render)

Push `sajha-kaam/` to GitHub, then on Render choose **New → Blueprint**, which uses `render.yaml`. Set `PUBLIC_BASE_URL` to the service URL.

### Optional: real AI drafting

Without a key, Kaam Cards come from the offline template, labelled "From template". To use Claude, start the backend like this instead:

```powershell
$env:LLM_PROVIDER = "anthropic"
$env:LLM_API_KEY = "sk-ant-..."
.\sajha-kaam\backend\start.ps1
```

## 2. Slides and video (Remotion)

The rendered video is already at `sajha-kaam-slides\out\sajha-kaam.mp4`.

```powershell
cd sajha-kaam-slides
npm run dev          # opens Remotion Studio in the browser
```

## 3. Static prototype and concept video

These need no setup. Open them in a browser:

```powershell
start Sajha_Kaam\prototype\index.html
start Sajha_Kaam\video\video.html
```

## Mauri design update (run once after unzipping)

```powershell
cd sajha-kaam\mobile
npm install            # drops @expo/vector-icons (replaced by our own SVG icons)
npm run check          # i18n + formats + verify + typecheck + lint
npx expo start -c      # -c clears the old cached icon and splash
```

Icons, splash and favicon are generated from the Mauri geometry. After changing the bee:

```powershell
npx tsx scripts/make-icons.ts
node scripts/render-icons.mjs      # uses Edge; or: pip install cairosvg; python scripts/render-icons.py
```

The animated splash only shows fully in a real build (APK), not in Expo Go.
