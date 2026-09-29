# GEO Visibility Agent Dashboard

This React + TypeScript dashboard can show the staged 1/5/10 demo and run scans through the linked local Python pipeline.

## Start the linked app

Start the API from the project root in one terminal:

```powershell
python -m integration.api
```

Then, in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The brand and category fields are editable. **Run visibility scan** sends them through Vite's `/api` proxy to the local Python API. Mock mode is enabled by default, so this works without provider keys; its evidence is simulated. Live scans require the credentials in the root `.env.example`.

After a live scan, record an action and its observed outcome in the Hindsight timeline. Saved actions appear there and inform the next recommendation. `src/data/demoData.ts` supplies the 1/5/10 staged demo selector. `src/services/api.ts` calls the Python API for scans and action records.
