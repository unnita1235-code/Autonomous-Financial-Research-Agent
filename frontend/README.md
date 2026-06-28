# Autonomous Financial Research Agent - Frontend

This is the Next.js 14 frontend for the Autonomous Financial Research Agent. It provides a clean, professional dashboard to interact with the backend API, enabling you to run research tasks, monitor their progress, and view structured reports.

## Prerequisites

- Node.js 18+ and npm
- Running FastAPI backend (defaults to `http://localhost:8000`)

## Getting Started

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment variables**:
   Create a `.env.local` file in the root of the `frontend` directory (you can copy `.env.local.example`):
   ```bash
   cp .env.local.example .env.local
   ```
   
   Ensure `NEXT_PUBLIC_API_URL` points to your active backend server.

3. **Run the development server**:
   ```bash
   npm run dev
   ```

4. **Open the application**:
   Navigate to [http://localhost:3000](http://localhost:3000) with your browser.

## Building for Production

To create an optimized production build:

```bash
npm run build
```

Then start the production server:

```bash
npm run start
```

## Environment Variables

- `NEXT_PUBLIC_API_URL`: The base URL for the backend API (e.g., `http://localhost:8000`). If not provided, it defaults to `http://localhost:8000`.
