# Yallastay Frontend Documentation

React SPA for Yallastay  -  apartment finding for students and workers in Dubai.

---

## 1. Overview

| Item | Details |
|------|---------|
| **Framework** | React 18 |
| **Build** | Vite 5 |
| **Routing** | React Router v6 |
| **Styling** | Tailwind CSS |
| **Animations** | Framer Motion |
| **HTTP** | Axios |
| **Project root** | `yallastay/` (frontend folder, sibling to backend) |

---

## 2. Project Structure

```
yallastay/
├── src/
│   ├── main.jsx           # Entry point
│   ├── App.jsx             # Routes
│   ├── api/
│   │   └── client.js       # API client (axios)
│   ├── components/
│   │   ├── Layout.jsx
│   │   ├── Header.jsx
│   │   ├── Footer.jsx
│   │   └── PropertyCard.jsx
│   └── pages/
│       ├── Home.jsx
│       ├── Search.jsx
│       ├── Property.jsx
│       ├── Login.jsx
│       ├── Signup.jsx
│       ├── Verify.jsx
│       ├── Dashboard.jsx
│       ├── RealtorDashboard.jsx
│       ├── Messages.jsx
│       ├── Notifications.jsx
│       ├── Roommates.jsx
│       ├── Documents.jsx
│       ├── Services.jsx
│       ├── AddProperty.jsx
│       ├── ForPartners.jsx
│       └── BackendConfig.jsx
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

---

## 3. Routes

| Path | Page | Description |
|------|------|-------------|
| `/` | Home | Landing, search form |
| `/search` | Search | Filter listings (area, type) |
| `/property/:id` | Property | Listing detail, favorite, viewing, message, report |
| `/login` | Login | Email + password |
| `/signup` | Signup | Register (role: student/worker, landlord, realtor) |
| `/verify` | Verify | UAE ID & university verification |
| `/dashboard` | Dashboard | Account, favorites, viewings, reservations, links |
| `/realtor-dashboard` | RealtorDashboard | My listings, analytics |
| `/messages` | Messages | Conversations, send messages |
| `/notifications` | Notifications | List, mark read |
| `/roommates` | Roommates | Profile, search, express interest |
| `/documents` | Documents | List uploaded documents |
| `/services` | Services | Lifestyle plans |
| `/add-property` | AddProperty | Create listing (landlord/realtor) |
| `/for-partners` | ForPartners | Static partner info |
| `/backend` | BackendConfig | API status check |

---

## 4. API Client (`src/api/client.js`)

Axios instance with:

- **Base URL**: `VITE_API_URL` or `/api`
- **Auth**: `Authorization: Bearer <token>` from `localStorage.getItem('token')`
- **401**: Clears token and redirects to `/login`

### Client exports

| Export | Methods |
|--------|---------|
| `auth` | register, login, me, logout |
| `verification` | uaeId, university, status |
| `core` | areas, universities |
| `listings` | list, get, create, update, delete |
| `favorites` | list, add, remove |
| `bookings` | requestViewing, listViewings, updateViewing, createReservation, listReservations |
| `reviews` | create, list |
| `lifestyle` | plans, subscribe, subscriptions |
| `messaging` | listConversations, createConversation, listMessages, sendMessage, markMessageRead, markConversationRead |
| `notifications` | list, markRead, getPreferences, updatePreferences |
| `reports` | submit, list, get |
| `roommates` | getProfile, createProfile, updateProfile, search, expressInterest, listInterests, updateInterest |
| `documents` | list, upload, get |
| `analytics` | renterDemographics, popularAreas, myListingsInsights |

**Rule:** Use the API client (not raw `fetch`) for consistent auth and 401 handling.

---

## 5. Pages & Backend Usage

| Page | Backend Used |
|------|--------------|
| Home | listings, core (areas) |
| Search | listings, core |
| Property | listings, favorites, bookings, messaging, reports |
| Login/Signup | auth |
| Verify | verification |
| Dashboard | auth, favorites, bookings, messaging, notifications |
| RealtorDashboard | listings, analytics |
| Services | lifestyle |
| AddProperty | listings, core |
| Messages | messaging |
| Notifications | notifications |
| Roommates | roommates, core |
| Documents | documents |

---

## 6. Key Query Params

- **Listings**: `area_slug`, `type`, `min_price`, `max_price`
- **Areas**: Use `id` for create (AddProperty), `slug` for filters (Search, Home)

---

## 7. Auth Flow

1. Login/Signup stores JWT in `localStorage` under key `token`
2. `auth.me()` returns current user + profile
3. 401 responses trigger logout and redirect to `/login`
4. Protected pages check `token`; redirect to `/login` if missing

---

## 8. Environment

| Variable | Purpose |
|---------|---------|
| `VITE_API_URL` | Backend API base (e.g. `http://localhost:8000/api`) |

Dev: Often uses proxy in `vite.config.js` so `/api` hits the backend.

---

## 9. Scripts

```bash
npm run dev      # Start dev server (Vite)
npm run build    # Production build
npm run preview  # Preview production build
```

---

## 10. Styling

- **Tailwind**: Utility classes (`btn`, `card`, `text-accent`, etc.)
- **Design tokens**: `primary`, `accent`, `primary-dark` in Tailwind config
- **Framer Motion**: Page transitions, hover effects

---

## 11. Adding a New Page

1. Create `src/pages/<PageName>.jsx`
2. Import and add route in `App.jsx`
3. Add API client methods if new backend calls
4. Add navigation link in `Header.jsx` or `Dashboard.jsx`

---

## 12. Known Gaps / Partial

| Item | Status |
|------|--------|
| Verify (University) | Backend expects `university_id`, optional `student_id`; frontend sends `email` only |
| Verify (UAE ID file) | Optional file input does not persist via `documents.upload()` |
| Payments | No checkout flow; requires gateway integration |

---

## 13. Related Docs

- **FRONTEND_BACKEND_MAPPING.md** (in backend repo)  -  API ↔ client mapping
- **USAGE_GUIDE.md** (in backend repo)  -  Full-stack verification flows
- **ARCHITECTURE.md** (in backend repo)  -  Platform overview
