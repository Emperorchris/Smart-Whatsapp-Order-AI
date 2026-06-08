# WhatsApp Commerce Platform

> An AI-powered, multi-tenant e-commerce platform that enables Nigerian businesses to sell products directly through WhatsApp.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp_Business_API-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-AI_Agent-FF6F00?style=for-the-badge)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)

---

## Table of Contents

- [Overview](#overview)
- [Demo](#demo)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Database Setup](#database-setup)
  - [Running the Application](#running-the-application)
- [WhatsApp Webhook Setup](#whatsapp-webhook-setup)
- [AI Agent System](#ai-agent-system)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Real-Time WebSocket](#real-time-websocket)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**WhatsApp Commerce** is a production-ready platform built for Nigerian businesses (fashion, gadgets, hair, accessories, etc.) to manage their storefronts and sell directly through WhatsApp. Customers interact with an AI shopping assistant named **Alexa** who guides them through browsing, cart management, checkout, and order tracking — all within WhatsApp.

When the AI can't handle a request, it seamlessly hands off the conversation to a human staff member. The platform includes a full admin dashboard API with analytics, broadcasting, customer segmentation, and audit logging.

<!-- Replace with your actual demo screenshot -->
<!-- ![Dashboard Screenshot](docs/images/dashboard-screenshot.png) -->

---

## Demo

### Customer Shopping Experience

<!-- Replace with your actual demo video/gif -->
<!-- ![Customer Demo](docs/videos/customer-demo.gif) -->

> *Customer browsing products, adding to cart, and placing an order — all through WhatsApp.*

| Step | Screenshot |
|------|-----------|
| **Product Browsing** | <!-- ![Browse](docs/images/browse.png) --> *Add screenshot* |
| **Cart Management** | <!-- ![Cart](docs/images/cart.png) --> *Add screenshot* |
| **Checkout & Payment** | <!-- ![Checkout](docs/images/checkout.png) --> *Add screenshot* |
| **Order Tracking** | <!-- ![Tracking](docs/images/tracking.png) --> *Add screenshot* |

### Human Handoff

<!-- ![Handoff Demo](docs/videos/handoff-demo.gif) -->

> *AI detects customer frustration and seamlessly transfers to a human agent.*

### Admin Dashboard

<!-- ![Admin Dashboard](docs/images/admin-dashboard.png) -->

> *Analytics, order management, and real-time notifications.*

---

## Features

### AI-Powered Shopping Assistant
- Conversational product discovery and search
- Smart cart management with variant selection (size, color, etc.)
- Guided checkout with delivery address collection
- Order status tracking and cancellation
- Voice note support (speech-to-text & text-to-speech)
- Bilingual support (English & Nigerian Pidgin)
- Context-aware conversation memory with automatic summarization

### Human Handoff System
- AI-triggered escalation on customer frustration
- Customer-initiated handoff requests
- Staff queue management (`#next`, `#done`, `#queue`, `#skip`, `#info`)
- Dual chat modes: AI Mode & Customer Mode
- Real-time WebSocket notifications

### E-Commerce Engine
- Multi-product catalog with variants (size, color, material)
- Inventory tracking with low-stock alerts
- Order lifecycle management (pending → paid → shipped → delivered)
- Payment tracking with bank transfer instructions
- Order status history timeline
- CSV order export

### Admin Dashboard API
- Revenue analytics by day/week/month/year
- Top products and customers
- Cart-to-order conversion rate
- Customer segmentation (new, returning, VIP, churned)
- Broadcast messaging to segments
- Audit logging for compliance
- Staff role-based access control (Admin, Support, Sales)

### WhatsApp Integration
- Meta Cloud API (v21.0) — official Business API
- Interactive buttons and list messages
- Media support (images, videos, audio, documents)
- Webhook deduplication
- Phone number normalization (Nigerian formats)

### Real-Time Updates
- WebSocket broadcasts for admin dashboard
- Events: new messages, orders, handoffs, payments

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   WhatsApp      │◄───►│   Meta Cloud API     │◄───►│   FastAPI        │
│   (Customer)    │     │   (v21.0)            │     │   Application    │
└─────────────────┘     └──────────────────────┘     └────────┬────────┘
                                                              │
                        ┌─────────────────────────────────────┼──────────────────┐
                        │                                     │                  │
                   ┌────▼─────┐    ┌──────────────┐    ┌─────▼───────┐    ┌─────▼──────┐
                   │  AI Agent │    │  Services    │    │  API Layer  │    │  WebSocket │
                   │ (LangGraph)│    │  (Business   │    │  (22 REST   │    │  (Real-time│
                   │           │    │   Logic)     │    │   Routers)  │    │   Events)  │
                   └────┬──────┘    └──────┬───────┘    └─────┬───────┘    └────────────┘
                        │                  │                  │
                        │           ┌──────▼───────┐          │
                        └──────────►│  PostgreSQL  │◄─────────┘
                                    │  (Supabase)  │
                                    └──────────────┘
```

### Message Flow

```
Customer sends WhatsApp message
        │
        ▼
Meta Cloud API webhook (POST /api/v1/webhooks/whatsapp)
        │
        ▼
Webhook deduplication check
        │
        ▼
Identify sender (customer or staff)
        │
        ├── [CUSTOMER] ──────────────────────────────────┐
        │                                                 │
        │   Create/update customer profile                │
        │   Load conversation + memory (summary + recent) │
        │   Build AgentState                              │
        │   Run LangGraph agent                           │
        │       ├── Agent Node (LLM reasoning)            │
        │       ├── Tool Node (search, cart, order, etc.) │
        │       └── Loop until done                       │
        │   Save messages to DB                           │
        │   Send response via WhatsApp API                │
        │   Broadcast WebSocket event                     │
        │                                                 │
        ├── [STAFF] ─────────────────────────────────────┐
        │                                                 │
        │   Parse staff command (#next, #done, etc.)      │
        │   Route: AI mode or Customer forwarding mode    │
        │   Execute command or forward message            │
        │                                                 │
        ▼                                                 ▼
```

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend** | Python 3.12+, FastAPI, Uvicorn |
| **Database** | PostgreSQL (Supabase), SQLAlchemy (async), Alembic |
| **AI/LLM** | LangGraph, LangChain, OpenAI (GPT-5-nano, Whisper, TTS), Anthropic Claude |
| **WhatsApp** | Meta Cloud API v21.0 |
| **Auth** | JWT (PyJWT), Argon2 password hashing |
| **Media** | Cloudinary |
| **Real-Time** | WebSocket |
| **Rate Limiting** | SlowAPI |
| **HTTP Client** | HTTPX (async) |
| **Logging** | Loguru |
| **Scheduling** | APScheduler |

---

## Project Structure

```
whatsapp_commerce/
├── app/
│   ├── ai/                              # AI Agent System
│   │   ├── graph/
│   │   │   ├── agent_graph.py           # LangGraph state machine
│   │   │   └── agent_state.py           # Agent state definition
│   │   ├── tools/
│   │   │   ├── product_tools.py         # Product search & browsing
│   │   │   ├── cart_tools.py            # Cart management
│   │   │   ├── order_tools.py           # Order placement & tracking
│   │   │   ├── handoff_tools.py         # Human handoff operations
│   │   │   ├── address_tools.py         # Delivery address management
│   │   │   └── order_item_tools.py      # Order item details
│   │   ├── memory/
│   │   │   └── conversation_memory.py   # Memory with summarization
│   │   └── prompts/
│   │       ├── customers_prompt.py      # Customer-facing AI personality
│   │       └── staff_prompt.py          # Staff-facing AI personality
│   │
│   ├── api/
│   │   ├── router.py                    # Main API router
│   │   └── endpoints/                   # 22 API endpoint routers
│   │
│   ├── services/                        # 30+ business logic services
│   │
│   ├── db/
│   │   ├── db_engine.py                 # Async database engine
│   │   ├── base.py                      # SQLAlchemy declarative base
│   │   ├── model/                       # 20+ ORM models
│   │   └── schemas/                     # 45+ Pydantic schemas
│   │
│   ├── core/
│   │   ├── config.py                    # Environment configuration
│   │   ├── utils.py                     # Enums & utilities
│   │   ├── exceptions.py               # Custom exceptions
│   │   ├── dependencies.py             # FastAPI dependencies
│   │   └── rate_limiter.py             # Rate limiting setup
│   │
│   ├── middlewares/                     # Custom middleware
│   └── main.py                          # Application entry point
│
├── alembic/                             # Database migrations
│   ├── env.py
│   └── versions/
│
├── requirements.txt
├── alembic.ini
├── pyproject.toml
└── README.md
```

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **PostgreSQL** database (or [Supabase](https://supabase.com) account)
- **Meta WhatsApp Business API** access ([Meta for Developers](https://developers.facebook.com))
- **OpenAI API** key
- **Cloudinary** account (for media storage)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/whatsapp-commerce.git
cd whatsapp-commerce
```

2. **Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

Create a `.env` file in the project root with the following:

```env
# ─── Database ───────────────────────────────────────
CONNECTION_STRING=postgresql+asyncpg://user:password@host:5432/dbname
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# ─── Authentication ────────────────────────────────
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ─── AI / LLM ──────────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_LLM_MODEL=gpt-5-nano
OPENAI_WHISPER_MODEL=whisper-1
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=nova
ANTHROPIC_API_KEY=sk-ant-...          # Optional
ANTHROPIC_LLM_MODEL=claude-haiku-4-5  # Optional

# ─── WhatsApp (Meta Cloud API) ─────────────────────
META_WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
META_WHATSAPP_ACCESS_TOKEN=your-access-token
META_WHATSAPP_VERIFY_TOKEN=your-verify-token
META_WHATSAPP_API_VERSION=v21.0

# ─── Media Storage (Cloudinary) ────────────────────
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# ─── Business Settings ─────────────────────────────
DEFAULT_CURRENCY=NGN
```

### Database Setup

```bash
# Run database migrations
alembic upgrade head
```

### Running the Application

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive Swagger documentation.

---

## WhatsApp Webhook Setup

### 1. Expose Your Local Server

For development, use [ngrok](https://ngrok.com) to create a public URL:

```bash
ngrok http 8000
```

### 2. Configure Meta Webhook

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Navigate to your WhatsApp app → **Configuration** → **Webhooks**
3. Set the callback URL:
   ```
   https://your-ngrok-url.ngrok.io/api/v1/webhooks/whatsapp
   ```
4. Set the verify token to match your `META_WHATSAPP_VERIFY_TOKEN`
5. Subscribe to: `messages`, `message_deliveries`, `message_reads`

### 3. Verify the Webhook

Meta will send a GET request to verify your endpoint. The platform handles this automatically.

<!-- ![Webhook Setup](docs/images/webhook-setup.png) -->

> *Meta Developer Console webhook configuration.*

---

## AI Agent System

The AI agent is built with **LangGraph**, implementing a state machine that routes between LLM reasoning and tool execution.

### Agent Graph Flow

```
         ┌──────────┐
         │  START    │
         └────┬─────┘
              │
              ▼
      ┌───────────────┐
      │  Agent Node    │◄──────────────────┐
      │  (LLM + Tools) │                   │
      └───────┬───────┘                    │
              │                            │
              ▼                            │
     ┌─────────────────┐                   │
     │ should_continue  │                  │
     └────┬────────┬───┘                   │
          │        │                       │
     [end]│        │[tools called]         │
          │        │                       │
          ▼        ▼                       │
       ┌─────┐  ┌──────────┐              │
       │ END │  │ Tool Node │──────────────┘
       └─────┘  └──────────┘
```

### Available AI Tools

| Category | Tool | Description |
|----------|------|-------------|
| **Products** | `list_product_names` | Browse paginated catalog |
| | `search_products` | Search by name, description, price, tags |
| | `get_product_details` | Full product info with variants |
| | `get_product_media` | Product images and videos |
| **Cart** | `add_to_cart` | Add product with quantity & variant |
| | `remove_from_cart` | Remove product from cart |
| | `view_cart` | Display current cart |
| | `clear_cart` | Empty the cart |
| **Orders** | `place_order` | Create order from cart |
| | `check_order_status` | Get order status & tracking |
| | `cancel_order` | Cancel a pending order |
| | `make_payment` | Get payment instructions |
| **Address** | `get_my_addresses` | List saved addresses |
| | `save_delivery_address` | Save a new address |
| **Handoff** | `request_human_agent` | Escalate to human staff |
| | `cancel_handoff_request` | Cancel pending handoff |

### Conversation Memory

The system maintains conversation context through a hybrid memory approach:

- **Recent Messages**: Last 6 messages kept in full detail
- **Summarization**: Triggered at 10+ messages; older messages compressed into a summary
- **Persistence**: Memory stored in the database and reconstructed per conversation

---

## API Reference

The platform exposes **22 RESTful API routers** under `/api/v1/`. All endpoints (except webhooks) require JWT authentication.

### Authentication

```bash
# Login
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@store.com",
  "password": "your-password"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

Use the token in subsequent requests:
```
Authorization: Bearer <access_token>
```

### Core Endpoints

<details>
<summary><strong>Customers</strong> — <code>/api/v1/customers</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all customers (paginated) |
| `POST` | `/` | Create a new customer |
| `GET` | `/{id}` | Get customer by ID |
| `GET` | `/whatsapp/{number}` | Get customer by WhatsApp number |
| `PUT` | `/{id}` | Update customer |
| `DELETE` | `/{id}` | Delete customer |

</details>

<details>
<summary><strong>Products</strong> — <code>/api/v1/products</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all products (paginated) |
| `POST` | `/` | Create a new product |
| `GET` | `/search` | Search products |
| `GET` | `/{id}` | Get product by ID |
| `PUT` | `/{id}` | Update product |
| `DELETE` | `/{id}` | Delete product |
| `POST` | `/{id}/media` | Upload product media |

</details>

<details>
<summary><strong>Product Variants</strong> — <code>/api/v1/product-variants</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all variants |
| `POST` | `/` | Create a variant |
| `PUT` | `/{id}` | Update a variant |
| `DELETE` | `/{id}` | Delete a variant |

</details>

<details>
<summary><strong>Categories</strong> — <code>/api/v1/categories</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all categories |
| `POST` | `/` | Create a category |
| `PUT` | `/{id}` | Update a category |
| `DELETE` | `/{id}` | Delete a category |

</details>

<details>
<summary><strong>Inventory</strong> — <code>/api/v1/inventory</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/{product_id}` | Get inventory for a product |
| `POST` | `/adjust` | Adjust stock levels |
| `GET` | `/low-stock` | Get low stock items |

</details>

<details>
<summary><strong>Cart</strong> — <code>/api/v1/carts</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/customer/{id}` | Get customer's cart |
| `POST` | `/` | Create a cart |
| `PUT` | `/{id}` | Update cart |
| `DELETE` | `/{id}` | Delete cart |
| `PATCH` | `/{id}/checkout` | Checkout cart |

</details>

<details>
<summary><strong>Orders</strong> — <code>/api/v1/orders</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all orders |
| `POST` | `/` | Create an order |
| `GET` | `/{id}` | Get order by ID |
| `GET` | `/number/{number}` | Get order by order number |
| `GET` | `/customer/{id}` | Get orders by customer |
| `PUT` | `/{id}` | Update order |
| `PATCH` | `/{id}/status` | Update order status |
| `PATCH` | `/{id}/cancel` | Cancel an order |
| `GET` | `/{id}/timeline` | Get order tracking timeline |
| `DELETE` | `/{id}` | Delete order |

</details>

<details>
<summary><strong>Payments</strong> — <code>/api/v1/payments</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all payments |
| `POST` | `/` | Create a payment |
| `GET` | `/{id}` | Get payment by ID |
| `GET` | `/reference/{ref}` | Get payment by reference |
| `GET` | `/order/{id}` | Get payments for an order |
| `PUT` | `/{id}` | Update payment |
| `DELETE` | `/{id}` | Delete payment |

</details>

<details>
<summary><strong>Messages</strong> — <code>/api/v1/messages</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all messages |
| `POST` | `/` | Create a message |
| `GET` | `/{id}` | Get message by ID |
| `GET` | `/conversation/{id}` | Get messages by conversation |
| `PUT` | `/{id}` | Update message |
| `PATCH` | `/{id}/status` | Update message status |
| `POST` | `/voice` | Process voice note |
| `DELETE` | `/{id}` | Delete message |

</details>

<details>
<summary><strong>Conversations</strong> — <code>/api/v1/conversations</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all conversations |
| `POST` | `/` | Create a conversation |
| `GET` | `/{id}` | Get conversation by ID |
| `GET` | `/customer/{id}` | Get conversations by customer |
| `PUT` | `/{id}` | Update conversation |
| `DELETE` | `/{id}` | Delete conversation |
| `GET` | `/{id}/messages` | Get conversation messages |

</details>

<details>
<summary><strong>Handoffs</strong> — <code>/api/v1/handoffs</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all handoffs |
| `GET` | `/active` | Get active handoffs |
| `GET` | `/pending` | Get pending handoffs |
| `GET` | `/me` | Get my assigned handoffs |
| `POST` | `/claim` | Claim a handoff |
| `PATCH` | `/{id}/status` | Update handoff status |
| `PATCH` | `/{id}/cancel` | Cancel handoff |
| `GET` | `/conversation/{id}` | Get handoffs by conversation |
| `GET` | `/staff/{id}` | Get handoffs by staff |
| `DELETE` | `/{id}` | Delete handoff |

</details>

<details>
<summary><strong>Analytics</strong> — <code>/api/v1/analytics</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard` | Dashboard KPIs |
| `GET` | `/revenue` | Revenue by period (day/week/month/year) |
| `GET` | `/top-products` | Top products by revenue or quantity |
| `GET` | `/top-customers` | Top customers by spend |
| `GET` | `/conversion-rate` | Cart-to-order conversion rate |
| `GET` | `/orders/export` | Export orders as CSV |

</details>

<details>
<summary><strong>Broadcasting</strong> — <code>/api/v1/broadcast</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/segment` | Send message to a customer segment |
| `POST` | `/customers` | Send message to specific customers |

</details>

<details>
<summary><strong>Segmentation</strong> — <code>/api/v1/segmentation</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all segments |
| `POST` | `/` | Create a segment |
| `PUT` | `/{id}` | Update a segment |
| `GET` | `/{id}/members` | Get segment members |
| `DELETE` | `/{id}` | Delete segment |

</details>

<details>
<summary><strong>Staff</strong> — <code>/api/v1/staff</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all staff |
| `POST` | `/` | Create staff member |
| `GET` | `/{id}` | Get staff by ID |
| `GET` | `/email/{email}` | Get staff by email |
| `PUT` | `/{id}` | Update staff |
| `DELETE` | `/{id}` | Delete staff |

</details>

<details>
<summary><strong>Store Settings</strong> — <code>/api/v1/settings</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Get store settings |
| `PUT` | `/` | Update store settings |

</details>

<details>
<summary><strong>WhatsApp Webhook</strong> — <code>/api/v1/webhooks/whatsapp</code></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Webhook verification (Meta) |
| `POST` | `/` | Incoming message handler |

</details>

### Interactive API Documentation

Once the server is running, access the auto-generated docs:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

<!-- ![Swagger UI](docs/images/swagger-ui.png) -->

---

## Database Schema

### Entity Relationship Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Customer   │────►│ Conversation │────►│   Message    │
└──────┬───────┘     └──────┬───────┘     └──────────────┘
       │                    │
       │              ┌─────▼──────┐
       │              │  Handoff   │◄──── Staff
       │              └────────────┘
       │
       ├────►┌──────────────┐     ┌──────────────┐
       │     │    Cart      │────►│  Cart Item   │
       │     └──────────────┘     └──────┬───────┘
       │                                 │
       │                                 ▼
       │                          ┌──────────────┐     ┌──────────────┐
       │                          │   Product    │────►│   Variant    │
       │                          └──────┬───────┘     └──────────────┘
       │                                 │
       │                          ┌──────▼───────┐
       │                          │  Inventory   │
       │                          └──────────────┘
       │
       └────►┌──────────────┐     ┌──────────────┐
             │    Order     │────►│  Order Item  │
             └──────┬───────┘     └──────────────┘
                    │
              ┌─────▼──────┐     ┌──────────────────┐
              │  Payment   │     │ Order Status      │
              └────────────┘     │ History           │
                                 └──────────────────┘
```

### Key Models

| Model | Description |
|-------|-------------|
| **Customer** | WhatsApp users with segmentation (new, returning, VIP, churned) |
| **Product** | Catalog items with media, tags, SKU, and pricing |
| **Product Variant** | Size/color/material variations with individual pricing and stock |
| **Inventory** | Stock levels per product/variant with low-stock thresholds |
| **Category** | Product categorization |
| **Cart / Cart Item** | Active shopping carts with product selections |
| **Order / Order Item** | Completed orders with line items and delivery info |
| **Order Status History** | Audit trail of order status changes |
| **Payment** | Payment records with status tracking |
| **Conversation** | Customer conversation sessions with AI/handoff state |
| **Message** | Individual messages (text, media, tool calls) |
| **Human Hand Off** | Escalation records with staff assignment |
| **Staff** | Admin/support/sales team members |
| **Customer Address** | Saved delivery addresses |
| **Bank Account** | Business bank accounts for payment collection |
| **Store Settings** | Global store configuration |
| **Audit Log** | Admin action audit trail |
| **Processed Webhook** | Deduplication tracking for WhatsApp webhooks |

---

## Real-Time WebSocket

Connect to the WebSocket endpoint for live dashboard updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.payload);
};
```

### Event Types

| Event | Trigger |
|-------|---------|
| `NEW_MESSAGE` | Customer sends a message |
| `ORDER_PLACED` | New order created |
| `ORDER_STATUS_CHANGED` | Order status updated |
| `NEW_HANDOFF` | Customer escalation request |
| `HANDOFF_RESOLVED` | Handoff completed |
| `PAYMENT_RECEIVED` | Payment confirmed |

---

## Security

| Feature | Implementation |
|---------|---------------|
| **Authentication** | JWT tokens with configurable expiration |
| **Password Hashing** | Argon2 (via pwdlib) |
| **Role-Based Access** | Admin, Support, Sales roles with permission checks |
| **Rate Limiting** | 60 requests/minute on webhook endpoints (SlowAPI) |
| **SQL Injection Protection** | SQLAlchemy ORM parameterized queries |
| **Webhook Verification** | Token-based Meta webhook verification |
| **Secret Management** | Environment variables (never committed) |

> **Note**: CORS is currently set to allow all origins. Restrict `allow_origins` in production.

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is proprietary. All rights reserved.

---

<p align="center">
  Built with passion for Nigerian commerce
</p>
