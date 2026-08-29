# NHAI DAS Dashboard Frontend

This directory contains the user interface for the NHAI Dashcam Analytics Service (DAS). It is a high-performance web dashboard built with React 18 and Vite, customized with a premium dark Glassmorphism design system.

---

## 🎨 Technology Stack & Design System

1.  **Core Framework**: React 18 (Hooks, state context polling) + Vite (ultra-fast Hot Module Replacement dev server).
2.  **Interactive GIS Mapping**: Leaflet JS + OpenStreetMap API, pre-styled with **CartoDB Dark Matter** dark-mode vector tiles. Pulsing neon markers indicate GPS coordinate anomalies.
3.  **Data Visualization**: **Recharts** Area charts showing defect category frequency trends over the week.
4.  **Icons**: **Lucide React** for premium vector telemetry HUD icons.
5.  **Styling**: Vanilla CSS variable design system ([index.css](file:///c:/Users/MSI-1/Desktop/Dashcam/services/dashboard-frontend/src/index.css)) featuring blur backdrops, radial neon glow borders, and vibrant contrast indicators.

---

## ⚙️ Configuration & Environment

The frontend is fully portable and loads backend microservice URLs dynamically from environment variables. Set them in a local `.env` file or export them on your CI container:

*   `VITE_API_BASE` — Base URL of the `dashboard-api` Cloud Run service (defaults to the deployed GCP instance).
*   `VITE_REPORT_BASE` — Base URL of the `report-generator` Cloud Run service (defaults to the deployed GCP instance).

### Example `.env`:
```env
VITE_API_BASE=http://localhost:8000
VITE_REPORT_BASE=http://localhost:8001
```

---

## 🚀 Commands & Workflows

### 1. Install Dependencies
```bash
npm install
```

### 2. Launch Local Dev Server
Runs the HMR dev server at `http://localhost:5173/`:
```bash
npm run dev
```

### 3. Build for Production
Compiles optimized, static assets into `dist/` ready to be served by NGINX or static site hosts:
```bash
npm run build
```

### 4. Run Linter
Checks code style and verifies there are no unused imports or syntax issues:
```bash
npm run lint
```

---

## 📂 Directory Layout

*   `src/App.jsx` — Core application, state orchestration, Leaflet hooks, and overlay HUD drawing.
*   `src/index.css` — High-tech Glassmorphism variables and neon CSS pulse keyframe declarations.
*   `src/components/` — Reusable dashboard panels:
    *   `Sidebar.jsx` — Navigation panel with safe `onViewChange` fallback guards.
    *   `StatCard.jsx` — Premium metric panels with trend colors.
*   `public/` — Static branding assets.
