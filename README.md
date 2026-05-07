# Facility Management System — Odoo 19

## Modular Stack (First Release)

Install only these modules, in this order:

1. `rua_facility_base` — Security groups, SLA engine, shared settings
2. `rua_facility_campus` — Campus → Building → Floor → Space → Asset hierarchy
3. `rua_facility_operations` — Requests, work orders, ratings, SLA enforcement
4. `rua_facility_portal_api` — JWT REST API for the Next.js portal

## Legacy Module

> ⚠️ **`facility_management`** is a legacy/reference module and **must NOT be installed** in the first release.
> It is kept in the repository for reference only. Do not add it as a dependency.

## Demo Data

Demo data is included in the `demo/` directories of each module and loads automatically when installing with demo data enabled.

| Module | Demo Files |
|--------|-----------|
| `rua_facility_base` | `demo_users.xml` (22 users + partners) |
| `rua_facility_campus` | `demo_campus.xml` (72 records), `demo_assets.xml` (31 records) |
| `rua_facility_operations` | `demo_requests.xml` (27 requests), `demo_work_orders.xml` (33 WOs), `demo_ratings.xml` (20 ratings) |

## Localization

- **Source language**: English
- **Arabic translations**: via `i18n/ar.po` files in each module
- Switch user language to Arabic in Odoo preferences for RTL interface

## Portal

- Next.js portal runs on port 3003
- Portal configuration: `rua-facility-portal/.env.local`
- API proxy: `/api/*` → Odoo at port 8089
