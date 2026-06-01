# WhatsApp Commerce - Frontend Developer Guide

## Project Overview

This is a **multi-business WhatsApp commerce platform** for Nigerian businesses. Customers chat with an AI assistant on WhatsApp to browse products, manage carts, place orders, and make payments. When needed, conversations are handed off to human staff.

The **admin dashboard** (what you're building) manages: products, orders, customers, staff, inventory, handoffs, conversations, and payments.

---

## Architecture

```
Customer (WhatsApp) → Meta Webhook → FastAPI Backend → AI Agent (Claude)
                                          ↕
Admin Dashboard (React/Next.js) → REST API → PostgreSQL (Supabase)
                                          ↕
Staff (WhatsApp) ← Mode Switching ← Handoff System
```

**Base URL:** `http://localhost:8000/api/v1`

---

## Authentication

### JWT Bearer Token (Two-token system)

| Token | Purpose | Lifetime |
|-------|---------|----------|
| `access_token` | API requests | Short-lived (minutes) |
| `refresh_token` | Get new access token | Long-lived (days) |

**Header format:** `Authorization: Bearer <access_token>`

### Login Flow

```
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin@store.com&password=password
```

**Response:**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "staff": {
    "id": "uuid",
    "name": "Admin",
    "email": "admin@store.com",
    "phone_number": null,
    "whatsapp_number": null,
    "role": "admin",
    "is_active": true,
    "created_at": "2026-05-28T06:22:58",
    "updated_at": "2026-05-28T06:22:58"
  }
}
```

### Refresh Flow

```
POST /api/v1/auth/refresh
Content-Type: application/json

{ "refresh_token": "eyJhbGciOi..." }
```

Returns same shape as login. Store both new tokens.

### Logout

```
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

Returns `204 No Content`.

---

## Role-Based Access

| Role | Value | Access |
|------|-------|--------|
| Admin | `"admin"` | Full access to everything |
| Support | `"support"` | Standard staff access |
| Sales | `"sales"` | Standard staff access |

**Dependency types on endpoints:**
- **No auth** — Public endpoints (products, categories)
- **CurrentStaff** — Any authenticated staff member
- **AdminOnly** — Must be `role: "admin"`

---

## Enum Values (Use These Exactly)

### Order Status
`"pending"` | `"paid"` | `"shipped"` | `"delivered"` | `"cancelled"`

### Payment Status
`"pending"` | `"completed"` | `"failed"`

### Payment Method
`"credit_card"` | `"debit_card"` | `"paypal"` | `"bank_transfer"` | `"cash_on_delivery"`

### Handoff Status
`"none"` | `"pending"` | `"requested"` | `"active"` | `"cancelled"` | `"resolved"`

### Handoff Triggered By
`"ai"` | `"customer"` | `"staff"` | `"rule"`

### Cart Status
`"active"` | `"checked_out"` | `"abandoned"`

### Staff Role
`"admin"` | `"support"` | `"sales"`

### Conversation Status
`"active"` | `"ended"`

### Message Sender Type
`"customer"` | `"ai"` | `"staff"` | `"tool"`

### Message Direction
`"inbound"` | `"outbound"`

### Message Type
`"text"` | `"image"` | `"video"` | `"audio"` | `"document"`

### Address Label
`"home"` | `"office"` | `"shop"` | `"other"`

### Delivery Status
`"pending"` | `"processing"` | `"shipped"` | `"delivered"` | `"returned"`

---

## API Endpoints

### Staff Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/staff/` | None | Create staff member |
| GET | `/staff/me` | CurrentStaff | Get current logged-in staff |
| GET | `/staff/` | AdminOnly | List all staff |
| GET | `/staff/{staff_id}` | CurrentStaff | Get staff by ID |
| PUT | `/staff/{staff_id}` | AdminOnly | Update staff |
| PATCH | `/staff/{staff_id}/password` | CurrentStaff | Change password |
| DELETE | `/staff/{staff_id}` | AdminOnly | Delete staff |

**StaffCreate (POST body):**
```json
{
  "name": "John Doe",
  "email": "john@store.com",
  "password": "securepass123",
  "phone_number": "+2347012345678",
  "whatsapp_number": "+2347012345678",
  "role": "support"
}
```

**StaffResponse:**
```json
{
  "id": "uuid",
  "name": "John Doe",
  "email": "john@store.com",
  "phone_number": "+2347012345678",
  "whatsapp_number": "+2347012345678",
  "role": "support",
  "is_active": true,
  "created_at": "2026-05-28T06:22:58",
  "updated_at": "2026-05-28T06:22:58"
}
```

---

### Products

**Note:** Create/Update use `multipart/form-data` (not JSON) because of file uploads.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/products/` | None | Create product (form-data + files) |
| GET | `/products/` | None | List all products (paginated) |
| GET | `/products/search` | None | Search products |
| GET | `/products/{product_id}` | None | Get product by ID |
| GET | `/products/sku/{sku}` | None | Get product by SKU |
| PUT | `/products/{product_id}` | None | Update product (form-data + files) |
| DELETE | `/products/{product_id}` | None | Soft-delete product |

**Create/Update form fields:**
```
name: "Ankara Midi Dress"          (required)
price: 15000.00                     (required, Decimal)
description: "Vibrant print..."     (optional)
sku: "FASH-001"                     (optional)
category_id: "uuid"                 (optional)
is_active: true                     (default: true)
is_live: false                      (default: false, marks media as live)
tags: '["ankara", "dress", "women"]' (optional, JSON string)
files: [File, File, ...]            (optional, multiple)
```

**Search query params:**
```
GET /products/search?name=ankara&min_price=5000&max_price=20000&tag=dress&skip=0&limit=10
```

**ProductResponse:**
```json
{
  "id": "uuid",
  "tracking_id": "ANKA-A1B2C3D4E5",
  "name": "Ankara Midi Dress",
  "description": "Vibrant Ankara print...",
  "price": "15000.00",
  "sku": "FASH-001",
  "category_id": "uuid",
  "tags": ["ankara", "dress", "midi", "fashion", "women"],
  "media": [
    {"url": "https://cloudinary.com/...", "type": "image"},
    {"url": "https://cloudinary.com/...", "type": "video"}
  ],
  "is_active": true,
  "created_at": "2026-05-28T06:22:58",
  "updated_at": "2026-05-28T06:22:58"
}
```

---

### Product Variants

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/product-variants/` | None | Create variant |
| GET | `/product-variants/` | None | List all variants |
| GET | `/product-variants/{variant_id}` | None | Get variant by ID |
| GET | `/product-variants/product/{product_id}` | None | Get variants for product |
| PUT | `/product-variants/{variant_id}` | None | Update variant |
| DELETE | `/product-variants/{variant_id}` | None | Delete variant |

**ProductVariantSchema:**
```json
{
  "product_id": "uuid",
  "attributes": {"size": "M", "color": "Red"},
  "product_variant_price": "15000.00",
  "inventory_quantity": 35,
  "low_stock_threshold": 5,
  "is_active": true
}
```

---

### Categories

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/categories/` | None | Create category |
| GET | `/categories/` | None | List all categories |
| GET | `/categories/root` | None | List root categories only |
| GET | `/categories/{category_id}` | None | Get category by ID |
| GET | `/categories/{category_id}/subcategories` | None | Get child categories |
| PUT | `/categories/{category_id}` | None | Update category |
| DELETE | `/categories/{category_id}` | None | Delete category |

**CategorySchema:**
```json
{
  "name": "Fashion",
  "description": "Clothing, shoes, and accessories",
  "parent_id": null,
  "is_active": true
}
```

---

### Orders

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/orders/` | None | Create order |
| GET | `/orders/` | None | List all orders |
| GET | `/orders/{order_id}` | None | Get order by ID |
| GET | `/orders/number/{order_number}` | None | Get by order number |
| GET | `/orders/customer/{customer_id}` | None | Get customer's orders |
| PUT | `/orders/{order_id}` | None | Update order |
| PATCH | `/orders/{order_id}/status` | None | Update order status |
| PATCH | `/orders/{order_id}/cancel` | None | Cancel order |
| DELETE | `/orders/{order_id}` | None | Delete order |

**Status update:**
```
PATCH /orders/{order_id}/status
Content-Type: application/json

{ "status": "shipped" }
```

**OrderResponse:**
```json
{
  "id": "uuid",
  "customer_id": "uuid",
  "order_number": "#ORD-202605281234",
  "customer_name": "Emperor",
  "customer_whatsapp_number": "2347039487884",
  "status": "pending",
  "total_amount": "43500.00",
  "payment_status": "pending",
  "address_label": "home",
  "address_line": "12 Allen Avenue",
  "address_city": "Ikeja",
  "address_state": "Lagos",
  "address_country": "Nigeria",
  "address_landmark": "Near GTBank",
  "created_at": "2026-05-28T06:22:58",
  "updated_at": "2026-05-28T06:22:58"
}
```

### Order Items

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/orders/{order_id}/items` | None | Add item to order |
| GET | `/orders/{order_id}/items` | None | List order items |
| GET | `/orders/{order_id}/items/{item_id}` | None | Get specific item |
| PUT | `/orders/{order_id}/items/{item_id}` | None | Update item |
| DELETE | `/orders/{order_id}/items/{item_id}` | None | Remove item |

---

### Payments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/payments/` | None | Create payment |
| GET | `/payments/` | None | List all payments |
| GET | `/payments/{payment_id}` | None | Get payment by ID |
| GET | `/payments/reference/{ref}` | None | Get by payment reference |
| GET | `/payments/order/{order_id}` | None | Get payments for order |
| PUT | `/payments/{payment_id}` | None | Update payment |
| DELETE | `/payments/{payment_id}` | None | Delete payment |

**PaymentResponse:**
```json
{
  "id": "uuid",
  "order_id": "uuid",
  "payment_reference": "PAY-ABC123",
  "amount": "43500.00",
  "currency": "NGN",
  "status": "pending",
  "payment_url": null,
  "paid_at": null,
  "created_at": "2026-05-28T06:22:58"
}
```

---

### Customers

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/customers/` | None | Create customer |
| GET | `/customers/` | None | List all customers (paginated) |
| GET | `/customers/{customer_id}` | None | Get customer |
| GET | `/customers/whatsapp/{number}` | None | Get by WhatsApp number |
| PUT | `/customers/{customer_id}` | None | Update customer |
| DELETE | `/customers/{customer_id}` | None | Delete customer |

**CustomerResponse:**
```json
{
  "id": "uuid",
  "name": "Emperor",
  "whatsapp_number": "2347039487884",
  "email": null,
  "display_name": "Emperor",
  "extra_metadata": {"wa_id": "2347039487884"},
  "created_at": "2026-05-28T06:22:58",
  "updated_at": "2026-05-28T06:22:58"
}
```

---

### Conversations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/conversations/` | None | Create conversation |
| GET | `/conversations/` | None | List all conversations |
| GET | `/conversations/{id}` | None | Get conversation |
| GET | `/conversations/customer/{customer_id}` | None | Get customer's conversations |
| PUT | `/conversations/{id}` | None | Update conversation |
| PUT | `/conversations/{id}/handoff/start` | CurrentStaff | Manually trigger handoff |
| PUT | `/conversations/{id}/handoff/assign` | CurrentStaff | Assign handoff to staff |
| PUT | `/conversations/{id}/handoff/resume` | CurrentStaff | Resume AI (end handoff) |
| DELETE | `/conversations/{id}` | None | Delete conversation |

**Handoff start body:** `{ "reason": "Customer needs help with refund" }` (reason is optional)

**Handoff assign body:** `{ "staff_id": "uuid" }` (required)

**ConversationResponse:**
```json
{
  "id": "uuid",
  "customer_id": "uuid",
  "ai_enabled": true,
  "handoff_to_human": false,
  "handoff_status": "none",
  "assigned_staff_id": null,
  "handoff_reason": null,
  "conversation_type": "AI_KNOWLEDGE_BASED",
  "status": "active",
  "started_at": "2026-05-28T06:22:58",
  "ended_at": null
}
```

---

### Messages

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/messages/` | None | Create message |
| GET | `/messages/` | None | List all messages |
| GET | `/messages/{message_id}` | None | Get message |
| GET | `/messages/conversation/{conversation_id}` | None | Get conversation messages |
| GET | `/messages/whatsapp/{whatsapp_message_id}` | None | Get by WhatsApp msg ID |
| PUT | `/messages/{message_id}` | None | Update message |
| PATCH | `/messages/{message_id}/status` | None | Update message status only |
| DELETE | `/messages/{message_id}` | None | Delete message |

**Status update body:** `{ "status": "read" }`

**MessageResponse:**
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "sender_type": "customer",
  "staff_id": null,
  "direction": "inbound",
  "message_type": "text",
  "content": "I want to buy earbuds",
  "media_urls": null,
  "status": "delivered",
  "whatsapp_message_id": "wamid.HBgNMjM...",
  "created_at": "2026-05-28T06:22:58",
  "updated_at": "2026-05-28T06:22:58"
}
```

---

### Handoffs (Human Escalation)

**All handoff endpoints require authentication.**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/handoffs/` | AdminOnly | List ALL handoffs |
| GET | `/handoffs/active` | CurrentStaff | List active handoffs |
| GET | `/handoffs/pending` | CurrentStaff | List pending queue |
| GET | `/handoffs/check/{conversation_id}` | CurrentStaff | Quick status check (returns string) |
| GET | `/handoffs/me` | CurrentStaff | Get my active handoff |
| GET | `/handoffs/{handoff_id}` | CurrentStaff | Get handoff by ID |
| GET | `/handoffs/conversation/{id}` | CurrentStaff | Get handoffs for conversation |
| GET | `/handoffs/staff/{staff_id}` | AdminOnly | Get handoffs for staff member |
| POST | `/handoffs/claim` | CurrentStaff | Claim next pending handoff |
| POST | `/handoffs/{id}/assign?staff_id=uuid` | AdminOnly | Assign to specific staff |
| PATCH | `/handoffs/{id}/cancel` | CurrentStaff | Cancel handoff |
| PATCH | `/handoffs/{id}/status` | CurrentStaff | Update handoff status |
| DELETE | `/handoffs/{id}` | AdminOnly | Delete handoff |

**HumanHandOffResponse:**
```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "triggered_by": "customer",
  "reason": "Customer requested to speak with a human agent",
  "assigned_staff_id": "uuid",
  "status": "active",
  "claimed_at": "2026-05-28T01:33:00",
  "requested_at": "2026-05-28T01:29:00",
  "resolved_at": null,
  "created_at": "2026-05-28T01:29:00",
  "updated_at": "2026-05-28T01:33:00",
  "staff": {
    "id": "uuid",
    "name": "Admin",
    "email": "admin@store.com",
    "role": "admin"
  },
  "conversation": {
    "id": "uuid",
    "status": "active",
    "ai_enabled": false,
    "handoff_status": "active"
  }
}
```

---

### Inventory

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/inventory/` | None | Create inventory record |
| GET | `/inventory/` | None | List all inventory |
| GET | `/inventory/{inventory_id}` | None | Get inventory by ID |
| GET | `/inventory/product/{product_id}` | None | Get inventory for product |
| PUT | `/inventory/{inventory_id}` | None | Update inventory |
| DELETE | `/inventory/{inventory_id}` | None | Delete inventory |

---

### Bank Accounts

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/bank-accounts/` | None | Create bank account |
| GET | `/bank-accounts/` | None | List all accounts |
| GET | `/bank-accounts/{id}` | None | Get account by ID |
| PUT | `/bank-accounts/{id}` | None | Update account |
| DELETE | `/bank-accounts/{id}` | None | Delete account |

---

### Customer Addresses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/addresses/` | None | Create address |
| GET | `/addresses/customer/{customer_id}` | None | Get customer addresses |
| GET | `/addresses/{address_id}` | None | Get address by ID |
| PUT | `/addresses/{address_id}` | None | Update address |
| DELETE | `/addresses/{address_id}` | None | Delete address |

---

## Admin Dashboard Pages (Suggested)

### 1. Dashboard (Home)
- Total orders today / this week / this month
- Revenue summary
- Pending handoffs count (badge)
- Recent orders list
- Low stock alerts

**APIs needed:** `GET /orders/`, `GET /handoffs/pending`, `GET /products/search?is_active=true`

### 2. Orders Management
- Table: all orders with status badges, customer name, amount, date
- Filter by: status, date range, customer
- Click to view order details + items
- Actions: update status, cancel order

**APIs needed:** `GET /orders/`, `GET /orders/{id}`, `GET /orders/{id}/items`, `PATCH /orders/{id}/status`

### 3. Products Management
- Grid/table view of all products with media thumbnails
- Create/edit product form with file upload
- Manage variants per product
- Tags editor
- Search and filter

**APIs needed:** `GET /products/`, `POST /products/` (form-data), `PUT /products/{id}`, `GET /product-variants/product/{id}`, `POST /product-variants/`

### 4. Customers
- Table of all customers
- Click to view: profile, orders, conversations, addresses
- Search by name or WhatsApp number

**APIs needed:** `GET /customers/{id}`, `GET /orders/customer/{id}`, `GET /conversations/customer/{id}`

### 5. Conversations & Messages
- List of conversations with status (active, handoff, ended)
- Click to view full message thread
- Filter by customer, handoff status

**APIs needed:** `GET /conversations/`, `GET /messages/conversation/{id}`

### 6. Handoff Queue (Real-time)
- Pending handoffs with customer info and wait time
- Active handoffs showing which staff is handling whom
- Claim/assign/cancel actions
- Consider WebSocket/polling for real-time updates

**APIs needed:** `GET /handoffs/pending`, `GET /handoffs/active`, `POST /handoffs/claim`, `POST /handoffs/{id}/assign`

### 7. Staff Management (Admin only)
- List staff with roles and status
- Create/edit/deactivate staff
- View staff handoff history

**APIs needed:** `GET /staff/`, `POST /staff/`, `PUT /staff/{id}`, `GET /handoffs/staff/{id}`

### 8. Categories
- Tree view of categories (parent/child)
- Create/edit/delete

**APIs needed:** `GET /categories/root`, `GET /categories/{id}/subcategories`, `POST /categories/`

### 9. Settings
- Bank accounts (for payment info displayed to customers)
- Store profile/config

**APIs needed:** `GET /bank-accounts/`, `POST /bank-accounts/`

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error message here"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (validation error) |
| 401 | Unauthorized (token expired/invalid) |
| 403 | Forbidden (insufficient role) |
| 404 | Not found |
| 409 | Conflict (duplicate SKU, email, etc.) |

---

## Important Notes

1. **All monetary values are in NGN** (Nigerian Naira) and returned as Decimal strings
2. **UUIDs everywhere** for IDs (use string type in TypeScript)
3. **Timestamps are UTC** in ISO 8601 format
4. **Product media** is an array of `{url, type}` objects. Types: `image`, `video`, `live_image`, `live_video`
5. **Product creation** uses `multipart/form-data`, not JSON. Tags must be a JSON string within the form
6. **Pagination**: use `skip` (offset) and `limit` on list endpoints. Default limit is 50, max 100
7. **WhatsApp numbers** are stored in various formats (`2347039487884`, `+2347039487884`, `07039487884`). The backend handles normalization
8. **Handoff endpoints** are the only ones requiring auth. Consider adding auth to other sensitive endpoints in production
9. **Auto-refresh tokens**: When you get a 401, try refreshing the token. If refresh fails, redirect to login
