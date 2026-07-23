# 🏨 Frontend Spec — Hostel Admin Payment Settings

## Overview

Each Hostel Admin needs a **Payment Settings** page in their dashboard where they can configure their own Razorpay account credentials. Once configured, students can pay hostel rent directly into the Hostel Admin's Razorpay account.

---

## 📍 Page Details

| Property | Value |
|---|---|
| **Route** | `/admin/payment-settings` |
| **Access** | Hostel Admin only (role: `hostel_admin`) |
| **Sidebar Label** | Payment Settings |
| **Sidebar Icon** | 💳 or wallet icon |

---

## 🖥️ Page Layout

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│  💳 Payment Settings                                         │
│  Configure your Razorpay account to accept student payments  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─── Current Status ────────────────────────────────────┐  │
│  │  ✅ Online payments are ACTIVE                         │  │
│  │  Key ID: rzp_live_xxxx••••••••          [Edit Keys]   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── Razorpay Configuration ────────────────────────────┐  │
│  │                                                        │  │
│  │  Razorpay Key ID *                                     │  │
│  │  [ rzp_live_xxxxxxxxxxxxxxxxxx        ]                │  │
│  │                                                        │  │
│  │  Razorpay Key Secret *                                 │  │
│  │  [ ••••••••••••••••••••••••••   👁 ]                  │  │
│  │                                                        │  │
│  │  Webhook Secret  (optional)                            │  │
│  │  [ ••••••••••••••••••••••••••   👁 ]                  │  │
│  │                                                        │  │
│  │  Enable Online Payments                                │  │
│  │  [ ●───  ON ]                                          │  │
│  │                                                        │  │
│  │  [ Save Configuration ]   [ Cancel ]                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── ℹ️ How to get your Razorpay Keys ──────────────────┐  │
│  │  1. Log in to Razorpay Dashboard                       │  │
│  │  2. Go to Settings → API Keys                          │  │
│  │  3. Generate/copy your Key ID and Key Secret           │  │
│  │  4. Use Test keys for testing, Live keys for production │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
\`\`\`

---

## 📋 Form Fields

### 1. Razorpay Key ID
| Property | Value |
|---|---|
| **Label** | Razorpay Key ID |
| **Type** | \`text\` input |
| **Required** | ✅ Yes |
| **Placeholder** | \`rzp_test_xxxxxxxxxx\` or \`rzp_live_xxxxxxxxxx\` |
| **Validation** | Must start with \`rzp_test_\` or \`rzp_live_\` |
| **Visible** | Always visible (not masked) |

### 2. Razorpay Key Secret
| Property | Value |
|---|---|
| **Label** | Razorpay Key Secret |
| **Type** | \`password\` input (masked by default) |
| **Required** | ✅ Yes |
| **Placeholder** | \`Enter your Key Secret\` |
| **Toggle** | 👁 Eye icon to show/hide |
| **Note** | On edit, show empty field — do NOT prefill with existing secret |

### 3. Webhook Secret *(Optional)*
| Property | Value |
|---|---|
| **Label** | Webhook Secret |
| **Type** | \`password\` input (masked by default) |
| **Required** | ❌ No |
| **Placeholder** | \`Enter your Webhook Secret (optional)\` |
| **Toggle** | 👁 Eye icon to show/hide |

### 4. Enable Online Payments
| Property | Value |
|---|---|
| **Label** | Enable Online Payments |
| **Type** | Toggle switch |
| **Default** | \`ON\` when keys are configured |
| **Description** | "Turn off to temporarily disable online payments for your hostel" |

---

## 🔄 Status Display (Read-only section above the form)

### When CONFIGURED and ACTIVE:
\`\`\`
✅ Online payments are ACTIVE
   Razorpay Key ID: rzp_live_xxxx••••••••
   Last updated: 15 Jul 2026
\`\`\`

### When CONFIGURED but INACTIVE (toggle is OFF):
\`\`\`
⚠️ Online payments are PAUSED
   Razorpay Key ID: rzp_live_xxxx••••••••
   Students cannot pay online until you re-enable payments.
\`\`\`

### When NOT CONFIGURED:
\`\`\`
❌ Online payments are not configured
   Students cannot pay online until you add your Razorpay keys.
   👉 Fill in the form below to get started.
\`\`\`

---

## 🌐 API Endpoints

### GET — Fetch current config
\`\`\`
GET /api/v1/admin/payment-config
Authorization: Bearer <token>
\`\`\`

**Success Response (200):**
\`\`\`json
{
  "hostel_id": "uuid-here",
  "razorpay_key_id": "rzp_live_xxxx",
  "is_active": true,
  "is_configured": true,
  "updated_at": "2026-07-15T10:30:00Z"
}
\`\`\`

**When not configured:**
\`\`\`json
{
  "is_configured": false,
  "is_active": false
}
\`\`\`

> [!IMPORTANT]
> The API **never returns** \`razorpay_key_secret\` or \`webhook_secret\`. The frontend should show empty password fields when editing.

---

### PUT — Save / Update config
\`\`\`
PUT /api/v1/admin/payment-config
Authorization: Bearer <token>
Content-Type: application/json
\`\`\`

**Request Body:**
\`\`\`json
{
  "razorpay_key_id": "rzp_live_xxxxxxxxxx",
  "razorpay_key_secret": "your_secret_here",
  "razorpay_webhook_secret": "your_webhook_secret",
  "is_active": true
}
\`\`\`

**Success Response (200):**
\`\`\`json
{
  "message": "Payment configuration saved successfully.",
  "hostel_id": "uuid-here",
  "razorpay_key_id": "rzp_live_xxxx",
  "is_active": true,
  "is_configured": true
}
\`\`\`

**Error Responses:**

| Status | Scenario | Message |
|---|---|---|
| \`400\` | Invalid Key ID format | \`"Key ID must start with rzp_test_ or rzp_live_"\` |
| \`401\` | Not authenticated | \`"Unauthorized"\` |
| \`403\` | Not a Hostel Admin | \`"Forbidden"\` |
| \`422\` | Validation error | Field-level errors |

---

## ✅ Frontend Validation Rules

| Field | Rule |
|---|---|
| Key ID | Required; must match \`rzp_(test|live)_[a-zA-Z0-9]+\` |
| Key Secret | Required on first save; optional on update (if blank → keep existing) |
| Webhook Secret | Optional; no format restriction |

> [!TIP]
> **On Edit:** Pre-fill the Key ID but leave Key Secret and Webhook Secret **empty**. Only send secret fields in the PUT request if they are non-empty.

---

## ⚠️ Error & Loading States

| State | UI Behavior |
|---|---|
| Loading GET | Show skeleton loader in status section |
| Saving PUT | Disable submit button, show spinner |
| Save success | Toast: ✅ *"Payment configuration saved successfully."* |
| Save error | Inline error message below form |
| Network error | Toast: ❌ *"Something went wrong. Please try again."* |

---

## 🎓 Student-Facing Behavior

When a student tries to pay for a hostel whose admin has **not configured Razorpay**:

\`\`\`
❌ Online payment unavailable

This hostel has not set up online payments yet.
Please contact the hostel directly for payment arrangements.

[Go Back]
\`\`\`

> The backend returns **HTTP 402** for this case. Frontend should catch this status code and show the above message instead of the payment UI.

---

## 🔐 Security Notes for Frontend

1. **Never log** the Key Secret or Webhook Secret to console
2. **Mask secret fields** by default — show only on explicit 👁 toggle
3. **Clear secret fields** from memory after form submission
4. **Do not cache** the PUT request body in localStorage or history
5. Show Key ID partially masked in status: `rzp_live_xxxx••••••••` (first 12 chars only)

---

## 📦 Component Summary

| Component | Purpose |
|---|---|
| \`PaymentStatusCard\` | Shows current config status (configured / active / inactive) |
| \`PaymentConfigForm\` | Form with Key ID, Key Secret, Webhook Secret, toggle |
| \`PasswordToggleInput\` | Reusable masked input with 👁 toggle |
| \`HowToGetKeysInfo\` | Collapsible info box with Razorpay setup instructions |

---

## 🔗 Related Pages / Navigation

- Hostel Admin Sidebar → **Payment Settings**
- After saving → stay on same page, refresh status card
- Super Admin can view payment config status of all hostels (read-only via Super Admin panel)
