# Yallastay  -  Location & distance (product notes)

Guidance for **listing ↔ university/work distance**, **exact location**, and **when to build what**. This complements `ARCHITECTURE.md` and domain models (`Area`, `University`, user `work_area`, listings).

---

## What distance needs

Distance is computed from **two coordinate pairs** (latitude / longitude): one for the **listing side** and one for the **user side** (university and/or work).

- **Straight-line distance** (km): Haversine formula or PostGIS  -  **no ongoing map “distance API”** if coordinates are already stored.
- **Drive time / road distance**: separate layer  -  **Distance Matrix** or routing APIs (Google, Mapbox, etc.), billing, and stricter rate limits.

---

## “Exact location”  -  do you need an API?

You do **not** need a dedicated backend endpoint whose only job is “point to exact location.” You need a **reliable source of coordinates**.

| Approach | How coordinates are obtained | Third-party geocoding API? |
|----------|------------------------------|----------------------------|
| **Area only** | One lat/lng per `Area` (centroid); listing inherits from its area | **No**, if centroids are seeded/admin-maintained |
| **Exact listing** | Address → geocoding **or** user picks a **map pin** in the app | Geocoding/Places **if** you convert text address to coords; map pin → your API **stores** `lat`/`lng` |
| **Exact work** | Same: profile pin or “search address” + geocode | Same split |

**Backend responsibility:** normal CRUD APIs that read/write **latitude** and **longitude** on listings and/or profiles (or derive from `Area` / `University` when “exact” is not required).

**Optional integrations:** **Geocoding** (address → coordinates) or **Places** (search + pick a point). The client may call those providers directly or your server proxies them  -  product/security choice.

---

## Now vs later

### Do something lightweight **now** (recommended for early MVP)

- **Area-level distance** using **centroids** on `Area` (and/or fixed coords on `University`) is enough to **sort or filter “roughly near X”** without geocoding keys, billing, or per-listing pins.
- Fewer moving parts while you ship search and listing flows.

### Add **exact location + richer distance** **later** (or when it becomes differentiating)

- **Per-listing** lat/lng (and optionally a precise work pin) when:
  - You want commute-style UX (“~15 min from campus”),
  - Users say **area is too vague**,
  - You are ready for **geocoding/Places** (keys, billing, address validation, privacy policy).

### Practical rule of thumb

- **Now:** implement **distance from whatever coordinates you already store** (even area centroids) so **API shape** stays stable (e.g. optional `distance_km`, sort/filter by distance).
- **Later:** **geocoding and/or map pin** for “exact” unless pin-level accuracy is a **launch** requirement.

---

## Summary

| Question | Answer |
|----------|--------|
| Need a special “distance API” from Google/Mapbox for the math? | **No**  -  store coords and compute (or use Distance Matrix only for **drive** metrics). |
| Need something for “exact” address/pin? | **Coordinates**  -  from manual seed, **geocoding**, or **map picker**; your API **persists** them. |
| Build everything now? | **Rough distance from areas** can ship early; **exact pin + geocoding** often **later** unless commute accuracy is core to v1. |

---

*Last updated: product/design note for implementation planning.*
