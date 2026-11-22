# SwarmOS Dashboard

React dashboard for visualizing SwarmOS test results and agent workflows.

## Features

- 📊 **Test Results Dashboard** - View all test runs and their status
- 🔀 **Workflow Visualization** - Interactive graph showing agent interactions
- ✅ **Validation Results** - See which checks passed or failed
- 📝 **Event Timeline** - Detailed log of all agent events
- 🎨 **Modern UI** - Dark theme with neon accents

## Setup

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local

# Run development server
npm run dev
```

The dashboard will be available at http://localhost:3000

## Environment Variables

Create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

```bash
# Development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Type check
npm run type-check

# Lint
npm run lint
```

## Deployment

### Deploy to Vercel (Recommended)

1. Push code to GitHub
2. Import repository in Vercel
3. Set environment variable:
   - `NEXT_PUBLIC_API_URL`: Your backend API URL (e.g., https://swarmos-api.render.com)
4. Deploy!

Vercel free tier includes:
- Unlimited bandwidth
- Automatic HTTPS
- Global CDN
- Preview deployments

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Visualization**: React Flow (workflow graphs)
- **Icons**: Lucide React
- **Type Safety**: TypeScript

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx              # Dashboard (trace list)
│   ├── traces/[id]/page.tsx  # Trace detail view
│   └── layout.tsx            # Root layout
├── lib/
│   └── api.ts                # Backend API client
└── public/                   # Static assets
```

## Features

### Dashboard Page

- Lists all test runs
- Shows status (completed, failed, running)
- Quick navigation to detailed views
- Real-time updates

### Trace Detail Page

- **Workflow Graph**: Visual representation of agent flow with React Flow
- **Metrics Bar**: Events captured, agent count, transitions, validations
- **Validation Results**: Pass/fail status for each check
- **Event Timeline**: Chronological list of all events

## UI/UX

- **Dark Theme**: Slate background with neon blue/purple/pink accents
- **Responsive**: Works on desktop and mobile
- **Accessible**: WCAG compliant color contrasts
- **Fast**: Optimized with Next.js 14

## Connecting to Backend

Make sure the SwarmOS backend is running:

```bash
cd ../backend
python -m uvicorn api.main:app --reload
```

Or use the CLI:

```bash
swarmos dashboard
```

## Troubleshooting

**Q: Dashboard shows "Failed to load traces"**
- Make sure backend is running on `http://localhost:8000`
- Check console for CORS errors
- Verify `NEXT_PUBLIC_API_URL` in `.env.local`

**Q: Workflow graph is empty**
- Check that traces have events
- Verify agents are being instrumented correctly
- Look for errors in browser console

**Q: Build fails on Vercel**
- Make sure all dependencies are in `package.json`
- Check that TypeScript has no errors: `npm run build`
- Verify Node.js version (18.17 or higher)

## Future Enhancements

- Real-time updates with WebSockets
- Test run comparisons
- Performance metrics
- Export/import traces
- Dark/light theme toggle
- Advanced filtering and search
