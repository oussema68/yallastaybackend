# In-app notifications

This document describes **when users receive in-app notifications** (the bell / notification list in the product), **how that differs from email**, and **how the backend implements it**.

## Email vs in-app

| Channel | Purpose | Copy |
|--------|---------|------|
| **Email** | Full message in the inbox; can include legal/compliance (e.g. Trakheesi), links, HTML | Defined in **`emails`** app: `EmailTemplate` rows (seeded by migrations). Keys such as `listing_created`, `listing_created_first`. |
| **In-app** | Short line in the notification center; quick scan | Built in code as **title + body** strings  -  **not** copied from email templates. |

So users are **not** sent the same long body twice: email uses templates; notifications use short UI strings from `notifications.services.notify_user` and feature-specific helpers (e.g. `listings.notifications.notify_listing_published`).

## Data model

- **`notifications.Notification`**: one row per in-app notification (`user`, `notification_type`, `title`, `body`, `read`, `created_at`).
- **`notifications.NotificationPreference`**: optional row per `(user, channel, notification_type)` to turn channels on/off. For in-app, `channel="in_app"`.

If there is **no** preference row for a given type, **in-app notifications default to enabled**.

## API (for the frontend)

- `GET /api/notifications/`  -  list current user’s notifications (newest first).
- `PATCH /api/notifications/{id}/read/`  -  mark one as read.
- `GET/PATCH /api/notifications/preferences/`  -  list or update preferences (e.g. disable in-app for a type).

## When notifications are created (current behavior)

### Listing published (`notification_type="listing"`)

- **When:** After a landlord/realtor successfully **creates** a listing (`POST /api/listings/`), after the database transaction commits.
- **Who:** The **lister** (`listed_by`).
- **Rules (per user, not global):**
  - If this is their **only** listing → title **“Your first listing is live”**, body quotes the listing title and says it is visible to renters.
  - If they **already had** other listings → title **“New listing added”**, body quotes the title and says it was added to their listings.
- **Email:** A separate transactional email is sent via `listings.emails.send_listing_created_email` (templates `listing_created_first` / `listing_created`). Same commit hook; **different text** than the in-app notification.
- **Opt-out:** If the user sets **in-app** preference for type **`listing`** to disabled (`PATCH` preferences with `channel: "in_app"`, `notification_type: "listing"`, `enabled: false`), **no in-app row** is created; **email is unchanged** (email preferences are not wired the same way yet).

### Other types (`booking`, `viewing`, `message`, …)

The model defines types for future use. Creation is intended to go through `notifications.services.notify_user` so **in-app** preferences are respected. Not all flows may call it yet  -  add calls from the relevant app when you implement each feature.

## Implementation details

1. **`notifications.services.notify_user(user, notification_type, title, body)`**  
   Creates a `Notification` unless in-app is disabled for that `notification_type`.

2. **Feature-specific helpers** (keep copy out of the generic emails app):  
   - `listings.notifications.notify_listing_published`  -  short strings for listing publish.

3. **Listing create hook**  -  `listings.views._send_listing_after_commit` runs on `transaction.on_commit` and calls both `send_listing_created_email` and `notify_listing_published` with a shared `is_first` flag (one count query).

4. **Tests**  -  `listings.tests` assert notification titles for first vs subsequent listings and that in-app can be skipped while email still sends; `notifications.tests.test_services` cover `notify_user` and preferences.

## Adding a new notification type

1. Add a choice to `Notification.TYPE_CHOICES` if needed.
2. From the domain app (e.g. `bookings`), call `notify_user` with a **short** title/body, or add a small helper like `listings.notifications`.
3. Document the trigger here under “When notifications are created”.
4. If users should be able to disable it, ensure `notification_type` matches what clients send in preferences (`PATCH` with the same string).
