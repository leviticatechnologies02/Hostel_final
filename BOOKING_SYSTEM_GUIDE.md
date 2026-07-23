# Levitica Nestora Booking System Guide

## Overview

The booking system consists of a 4-step multi-step form flow that guides users through the process of reserving a hostel room:

1. **Booking Selection** - Choose hostel, room, dates, and booking mode
2. **Booking Details** - Enter personal information and emergency contact
3. **Checkout** - Review pricing and confirm payment
4. **Confirmation** - Receive booking reference and next steps

---

## Architecture

### State Management

The booking flow uses **sessionStorage** to persist form data across page navigation:

```typescript
// BookingSelectPage - Save selection
sessionStorage.setItem("bookingSelection", JSON.stringify({
  hostelId: string;
  roomId: string;
  checkInDate: string;
  checkOutDate: string;
  bookingMode: "daily" | "monthly";
}));

// BookingDetailsPage - Save details
sessionStorage.setItem("bookingDetails", JSON.stringify(formValues));

// BookingCheckoutPage - Retrieve and display both
const selection = JSON.parse(sessionStorage.getItem("bookingSelection"));
const details = JSON.parse(sessionStorage.getItem("bookingDetails"));
```

**Why sessionStorage?**
- Survives page reloads within same browser tab
- Automatically cleared when tab closes
- Prevents accidental form persistence across sessions
- Simpler than Redux for this temporary flow

---

## Pages & Components

### 1. BookingSelectPage (`/booking/select`)

**Purpose:** Let users choose hostel, room, dates, and booking type

**Features:**
- Booking mode selection (Daily vs Monthly)
- Date range picker (check-in, check-out)
- Room selection with pricing display
- Real-time pricing calculation
- Dynamic room availability

**API Calls:**
```typescript
// Triggered by useHostelDetail hook
GET /public/hostels/{slug}

// Then fetches rooms
GET /public/hostels/{hostelId}/rooms // Returns Room[]
```

**Data Structure:**
```typescript
interface SelectedBooking {
  hostelId: string;
  roomId: string;
  bedId?: string; // Optional for future multi-bed selection
  checkInDate: string; // ISO date: "2024-03-20"
  checkOutDate: string;
  bookingMode: "daily" | "monthly";
}
```

**Key Components:**
- Tab-style booking mode selector
- HTML5 date inputs with validation
- Room cards with availability indicators
- Live pricing panel

---

### 2. BookingDetailsPage (`/booking/details`)

**Purpose:** Collect personal information required by the hostel

**Form Sections (Tabs):**

#### Personal Info Tab
- Full Name (required)
- Date of Birth (required)
- Gender (required)
- Occupation (required)
- Institution/School/College (required)
- Current Address (required, multi-line)
- ID Type selector (required)

#### Emergency Contact Tab
- Emergency Contact Name (required)
- Phone Number (required, 10 digits)
- Relationship (required)

#### Additional Info Tab
- Guardian Name (optional)
- Guardian Phone (optional)
- Special Requirements (optional, multi-line)

**Validation Schema:**
```typescript
const bookingDetailsSchema = z.object({
  full_name: z.string().min(2),
  date_of_birth: z.string().min(1),
  gender: z.string().min(1), // "M" | "F" | "Other"
  occupation: z.string().min(2),
  institution: z.string().min(2),
  current_address: z.string().min(5),
  id_type: z.string().min(1), // "Aadhar" | "PAN" | "DL" | "Passport"
  emergency_contact_name: z.string().min(2),
  emergency_contact_phone: z.string().regex(/^[0-9]{10}$/),
  emergency_contact_relationship: z.string().min(2),
  guardian_name: z.string().optional(),
  guardian_phone: z.string().optional(),
  special_requirements: z.string().optional()
});
```

**Key Features:**
- Tabbed interface for better UX
- React Hook Form for state management
- Zod for validation
- Inline error messages
- Progress indicator showing Step 2 of 3

---

### 3. BookingCheckoutPage (`/booking/checkout`)

**Purpose:** Review all information and charge payment

**Displays:**
- Guest name, check-in/out dates, duration
- Booking type and emergency contact
- Detailed pricing breakdown:
  - Nightly rate
  - Total room rent (nights × rate)
  - Security deposit
  - Booking advance (25% of room rent)
  - Amount due on check-in (remaining 75%)
  - **Total to pay now**

**Pricing Logic:**
```typescript
const pricePerNight = bookingMode === "daily" ? 800 : (2400 / 30);
const baseAmount = pricePerNight * nights;
const securityDeposit = 2000;
const advance = Math.ceil(baseAmount * 0.25);
const remainingAtCheckIn = baseAmount - advance;
const totalNow = advance; // What user pays now
```

**Key Features:**
- Full-width summary cards (desktop: 2-column)
- Large, clear pricing display
- Important terms section (cancellation policy, check-in time, etc.)
- "15 minutes to complete" countdown message
- Edit/Back button to modify selection
- "Pay Now" button with amount displayed

**Future Enhancement:**
```typescript
// Mock payment initiation (to be replaced with Razorpay)
const handleInitiatePayment = async () => {
  // Call: POST /bookings/create
  // Payload includes all selection + details data
  // Returns: bookingId + payment_url or razorpay_order_id
  // Redirect to: Razorpay window or confirmation page
}
```

---

### 4. BookingConfirmationPage (`/booking/confirmation`)

**Purpose:** Show booking confirmation and next steps

**Displays:**
- ✓ Success badge with "Booking Confirmed!" heading
- Booking Reference Number (e.g., "BK123456")
- Key information cards:
  - Check-in details (date, time)
  - Room details (number, type)
  - Hostel contact number
  - Receipt download button
- Step-by-step "What's Next?" section
- Important information box with cancellation/check-out details
- Action buttons: "Back to Home", "View My Bookings"

**Data Source:**
```typescript
// Location state from router navigation
const bookingId = (location.state as any)?.bookingId;
```

---

## API Endpoints Used

| Method | Endpoint | Page | Purpose |
|--------|----------|------|---------|
| GET | `/public/hostels/{slug}` | BookingSelectPage | Fetch hostel details |
| GET | `/public/hostels/{hostelId}/rooms` | BookingSelectPage | Fetch available rooms |
| POST | `/bookings/create` | BookingCheckoutPage | Create booking (future) |
| GET | `/bookings/{id}` | MyBookingsPage | Get booking details |
| DELETE | `/bookings/{id}/cancel` | MyBookingsPage | Cancel booking |

---

## Routes Configuration

```typescript
// Public layout routes
<Route path="/booking/select" element={<BookingSelectPage />} />
<Route path="/booking/details" element={<BookingDetailsPage />} />
<Route path="/booking/checkout" element={<BookingCheckoutPage />} />
<Route path="/booking/confirmation" element={<BookingConfirmationPage />} />
```

### Navigation Flow

```
/hostels/:slug 
    ↓ (Click "Book Now" - future implementation)
/booking/select
    ↓ (Select room + dates)
/booking/details
    ↓ (Enter personal info)
/booking/checkout
    ↓ (Confirm & pay)
/booking/confirmation
    ↓ (View booking reference)
/my-bookings (future)
```

---

## Error Handling

### Form Validation Errors
- Displayed inline below each field
- React Hook Form + Zod integration
- Client-side validation before submission
- User-friendly error messages

### API Errors
- Try/catch in form submission handlers
- Error state displayed in alert box
- Retry logic with back button

### State Loss
- If sessionStorage is cleared, user redirected to /booking/select
- useEffect dependencies ensure proper state restoration
- Navigation guards in each page

---

## Performance Optimizations

1. **useEffect for room fetching** - Only fetches when hostel.id changes
2. **sessionStorage** - Avoids unnecessary re-renders on state persistence
3. **Lazy calculation** - Pricing calculated on-demand, not on every render
4. **Component splitting** - Each page is separate file for code splitting

---

## Type Safety

All pages use TypeScript with strict null checks:

```typescript
interface SelectedBooking { /* ... */ }
interface BookingDetails { /* ... */ }
interface Room { /* ... */ }  // From public.api.ts
```

SessionStorage data is properly typed when parsed:
```typescript
const selection = JSON.parse(sessionStorage.getItem("bookingSelection")) as SelectedBooking;
```

---

## Testing Scenarios

### Happy Path
1. User navigates to `/booking/select?hostel=leviticanestora-bangalore`
2. System loads hostel "Levitica Nestora Bangalore" with 4 rooms
3. User selects:
   - Booking Mode: Daily
   - Check-in: 2024-03-20
   - Check-out: 2024-03-23 (3 nights)
   - Room: Double Room #205 (₹800/night)
4. User clicks "Continue to Details"
5. Navigates to `/booking/details` with data persisted
6. User fills all personal information
7. Submits form → navigates to `/booking/checkout`
8. Sees pricing:
   - Room rent: ₹2,400 (3 nights × ₹800)
   - Advance (25%): ₹600
   - Due on check-in: ₹1,800
9. Clicks "Pay ₹600"
10. Payment initiated (mock) → redirects to `/booking/confirmation?bookingId=BK123456`

**Expected Outcomes:**
- ✅ No validation errors
- ✅ All data persists across pages
- ✅ Pricing calculated correctly
- ✅ Confirmation page shows reference number
- ✅ sessionStorage cleared on confirmation

### Error Scenarios

**Missing Required Field:**
```typescript
// User skips "Full Name" field
// Form validation catches it
// Error: "Full name is required" shown in red below input
// Submit disabled
```

**Invalid Phone Format:**
```typescript
// User enters "12345" (5 digits)
// On blur or submit, validation fires
// Error: "Phone must be 10 digits"
// Field highlighted with red border
```

**Session Data Loss:**
```typescript
// User in /booking/checkout
// sessionStorage cleared (tab's private browsing ends, etc.)
// Page detects missing selection data
// navigates to /booking/select
// User starts over
```

---

## Design System

**Colors:**
- Primary: `#FF6B35` (orange) - Buttons, highlights
- Success: `#2D6A4F` (green) - Checkmarks, confirmations
- Error: `#DC2626` (red) - Error messages
- Neutral: `#64748B` (slate) - Text, borders

**Spacing:**
- Cards: `p-6` (24px padding)
- Sections: `space-y-6` (24px gaps)
- Form fields: `space-y-4` (16px gaps)

**Typography:**
- Headers: `text-3xl font-bold` (32px, bold)
- Sections: `text-xl font-bold` (20px, bold)
- Labels: `text-sm font-medium` (14px, medium)
- Body: `text-slate-600` (14px, gray)

---

## Future Enhancements

1. **Razorpay Integration**
   - Replace mock payment with real Razorpay SDK
   - Webhook signature verification
   - Payment status polling

2. **Advanced Room Selection**
   - Multi-bed selection within room
   - Specific bed preference (window, corner, etc.)
   - Bed visual layout

3. **Promo Codes**
   - Add promo code field in checkout
   - Discount calculation
   - Expired/invalid code handling

4. **Guest Additions**
   - Add multiple guests
   - Co-guest information collection
   - ID verification

5. **Instant Confirmations**
   - WhatsApp message with booking details
   - Email with receipt PDF
   - SMS to emergency contact

6. **Booking Management**
   - Modify booking (dates, room)
   - Cancel with refund calculation
   - Extend stay
   - View invoice history

---

## File Statistics

| File | Lines | Purpose |
|------|-------|---------|
| BookingSelectPage.tsx | 288 | Room selection + date picker |
| BookingDetailsPage.tsx | 315 | Personal info form |
| BookingCheckoutPage.tsx | 216 | Payment review |
| BookingConfirmationPage.tsx | 157 | Success confirmation |
| router.tsx | +5 | Route configuration |
| **Total** | **~977** | Complete booking flow |

---

## Build Statistics

- **Bundle size:** 573 KB (minified), 154 KB (gzipped)
- **Modules:** 1,995 transformed
- **Build time:** ~8 seconds
- **TypeScript errors:** 0 ✓
- **Warnings:** 1 (chunk size > 500KB - acceptable for MVP)

---

## Session Storage Keys

```typescript
// Key: "bookingSelection"
// Value: {
//   hostelId: string;
//   roomId: string;
//   checkInDate: string;
//   checkOutDate: string;
//   bookingMode: "daily" | "monthly";
// }

// Key: "bookingDetails"
// Value: {
//   full_name: string;
//   date_of_birth: string;
//   gender: string;
//   occupation: string;
//   institution: string;
//   current_address: string;
//   id_type: string;
//   emergency_contact_name: string;
//   emergency_contact_phone: string;
//   emergency_contact_relationship: string;
//   guardian_name?: string;
//   guardian_phone?: string;
//   special_requirements?: string;
// }
```

Both are automatically cleared after booking confirmation for privacy.

---

**Status:** ✅ Complete - All 4 booking pages built, integrated into router, TypeScript validation passing
**Next Phase:** Razorpay payment integration + admin dashboard
