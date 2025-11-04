# Agentic BI Frontend

Modern, AI-powered data analysis and visualization platform frontend built with Next.js 16, React 19, and TypeScript.

## 🚀 Tech Stack

- **Framework**: Next.js 16.0.1 (with Turbopack)
- **UI Library**: React 19.2.0
- **Styling**: Tailwind CSS 4.1.16
- **Language**: TypeScript 5.9.3
- **State Management**: Zustand 5.0.8
- **HTTP Client**: Axios 1.7.0
- **Components**: Shadcn/ui (Radix UI primitives)
- **Icons**: Lucide React
- **Charts**: Recharts (for visualization - PR#14)

## 📦 Installation

```bash
# Install dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# Update .env.local with your backend URL
# Default: http://localhost:8000
```

## 🏃 Development

### Start Development Server (with Turbopack!)

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### Type Check

```bash
npm run type-check
```

### Build for Production

```bash
npm run build
```

### Start Production Server

```bash
npm start
```

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── app/              # Next.js App Router pages
│   │   ├── login/        # Login page
│   │   ├── register/     # Register page
│   │   ├── dashboard/    # Protected dashboard
│   │   ├── layout.tsx    # Root layout
│   │   └── page.tsx      # Homepage (auto-redirect)
│   │
│   ├── components/
│   │   ├── ui/           # Shadcn/ui components
│   │   └── layout/       # Layout components (Header, Sidebar)
│   │
│   ├── hooks/            # Custom React hooks
│   │   └── useAuth.ts    # Auth hooks
│   │
│   ├── lib/              # Utilities
│   │   ├── api-client.ts # Axios instance
│   │   ├── storage.ts    # LocalStorage utils
│   │   └── utils.ts      # Helper functions
│   │
│   ├── services/         # API services
│   │   ├── auth.service.ts
│   │   └── workflow.service.ts
│   │
│   ├── stores/           # Zustand stores
│   │   ├── auth.store.ts
│   │   └── workflow.store.ts
│   │
│   └── types/            # TypeScript types
│       ├── user.types.ts
│       ├── workflow.types.ts
│       └── api.types.ts
│
├── .env.local            # Environment variables (git-ignored)
├── .env.local.example    # Environment template
├── components.json       # Shadcn/ui config
├── next.config.js        # Next.js config
├── tailwind.config.ts    # Tailwind config
└── tsconfig.json         # TypeScript config
```

## 🔐 Authentication

The app uses JWT-based authentication with automatic token refresh:

1. **Login**: POST `/api/v1/auth/login`
2. **Register**: POST `/api/v1/auth/register`
3. **Token Refresh**: Automatic on 401 errors
4. **Logout**: POST `/api/v1/auth/logout`

### Protected Routes

- All routes under `/dashboard` require authentication
- Unauthenticated users are redirected to `/login`
- Token refresh happens automatically via Axios interceptor

## 🎨 UI Components

We use [Shadcn/ui](https://ui.shadcn.com/) components built on top of Radix UI:

- Button
- Input
- Card
- Dropdown Menu
- (More to be added in PR#10)

## 📡 API Integration

### API Client

The app uses a configured Axios instance with:
- Automatic token injection
- Token refresh on 401 errors
- Error handling
- 30-second timeout

### Services

- **authService**: Login, register, refresh, logout
- **workflowService**: Execute workflows (basic - extended in PR#10)

### State Management

- **authStore**: User authentication state
- **workflowStore**: Workflow execution state (basic - extended in PR#10)

## 🌐 Environment Variables

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Feature Flags
NEXT_PUBLIC_ENABLE_WEBSOCKET=true
NEXT_PUBLIC_ENABLE_HITL=true
```

## 🚦 Current Status

**PR#9: Frontend Project Setup** ✅ **COMPLETE**

### What Works
- ✅ Modern tech stack (Next.js 16, React 19, Tailwind v4)
- ✅ Authentication (login, register, logout)
- ✅ Protected routes
- ✅ JWT token auto-refresh
- ✅ Basic dashboard layout
- ✅ Type-safe API client

### What's Next (PR#10)
- Query input interface
- Workflow execution UI
- Results display
- WebSocket integration (PR#11)
- Visualization rendering (PR#14)

## 📝 Development Notes

### Next.js 16 Changes
- Turbopack is now enabled by default
- Much faster dev server (~5-10x)
- React automatic runtime (jsx: "react-jsx")

### Tailwind CSS 4
- 100x faster builds
- Compatibility mode enabled (JS config)
- Can migrate to CSS-first config later

### React 19
- New features available (Actions, Compiler)
- Zustand 5 required for compatibility

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### Type Errors
```bash
# Regenerate Next.js types
rm -rf .next
npm run dev
```

### Build Errors
```bash
# Clean install
rm -rf node_modules package-lock.json .next
npm install
```

## 📚 Documentation

- **Implementation Summary**: `../docs/PR9_IMPLEMENTATION_SUMMARY.md`
- **Implementation Plan**: `../docs/PR9_IMPLEMENTATION_PLAN.md`
- **Quick Start**: `../docs/PR9_QUICK_START.md`
- **Modernization Details**: `../docs/FRONTEND_MODERNIZATION.md`

## 🤝 Contributing

1. Ensure backend is running (`make dev` in root)
2. Start frontend dev server (`npm run dev`)
3. Test authentication flows
4. Run type check before committing
5. Follow Next.js 16 App Router patterns

## 📄 License

See root LICENSE file.

---

**Built with ❤️ using Next.js 16 + React 19 + Turbopack**
