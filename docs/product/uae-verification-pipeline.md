# UAE verification pipeline (product rules)

| | |
|---|---|
| **Audience** | Clients, partners, product, and compliance |
| **Distribution** | **Client-facing** - share under NDA; not legal advice. |
| **Disclaimer** | **Not legal advice.** Counsel should review flows for your licence and DLD / RERA obligations. |

This document describes **platform rules** aligned with common Dubai / UAE rental and brokerage practice.

## Identity: Emirates ID (UAE ID)

- **Authoritative identity verification** for natural persons is **Emirates ID** via the **UAE ID integration** (`UAEIDVerification`, moving toward the live government/API path described in the product gap analysis).
- **Passport** and **residence visa** uploads are **supporting KYC / compliance documents**. They do **not** replace UAE ID verification for gating sensitive actions.

## Tenants (renters)

- **Upload:** passport + residence visa (supporting documents).
- **Verified identity:** only when **UAE ID verification** is **approved** (API path).

## Realtors (brokers)

- **Upload (verification dossier):** passport, residence visa, **trade licence**, **RERA Broker Card (BRN)**, brokerage/realtor licence.
- **If `brokerage_type` = agency:** also **ORN** and **agency / supplementary licence** where applicable (optional in workflow if not relevant).
- **Platform approval:** `RealtorProfile.is_approved` (admin) after document review.
- **Owner selection:** `GET /api/auth/verified-realtors/` returns **approved** realtors only, sorted with **private brokers first**, then **agency** (less paperwork for owners), then name.

## Property owners (landlords)

- **Profile:** UAE ID (supporting scan), passport, and **residence visa** when **`LandlordProfile.is_emirati` is `false`** (unknown/null may omit visa until set).
- **Listings:** **One listing per title deed.** Each listing must reference:
  - `title_deed_document` - uploaded `Document` with type `title_deed`
  - `title_deed_reference` - text that must **match** the deed (plot / unit / property reference)
- **Uniqueness:** one active listing row per title-deed document (enforced in DB).

## Related code

| Area | Location |
|------|----------|
| Document types | `documents.models.Document` |
| Checklists & emails | `documents.checklist`, `documents.emails` |
| UAE helpers | `documents.uae_pipeline` |
| Listing + deed | `listings.models.Listing`, `listings.serializers.ListingSerializer` |
| Realtor sort | `accounts.verified_realtors_views`, `RealtorProfile.brokerage_type` |
