# Hostel Registration & Approval Workflow

This document outlines the end-to-end architecture and workflow for onboarding new hostels into the Levitica Nestora/HostelHub platform. 

It covers both the public-facing registration process and the internal Super Admin approval process.

---

## 1. Public Hostel Registration Flow
*This flow is used when a new hostel owner visits the website and wants to list their property.*

### A. Document Upload (Optional but Recommended)
Before submitting the form, the frontend can upload the owner's business registration document (e.g., Trade License, GST Certificate).
- **Endpoint:** `POST /api/v1/uploads/hostel-registration-document`
- **Auth Required:** No (Public)
- **Action:** Uploads the file securely to Cloudinary.
- **Returns:** A public `url` to be used in the final submission.

### B. Form Submission
The hostel owner fills out the "Register Your Hostel" form and submits it.
- **Endpoint:** `POST /api/v1/public/hostels/register`
- **Auth Required:** No (Public)
- **Payload:** Includes `name`, `hostel_type` (case-insensitive), address details, contact details, and the `document_url`.
- **Backend Actions:**
  1. The hostel is created in the database.
  2. **Security Check:** The backend *forces* `status = "pending_approval"`.
  3. **Visibility Lock:** The backend *forces* `is_public = False`, `is_active = False`, and `is_featured = False`, meaning the hostel will completely bypass public search results.
  4. **Notification:** An automated email is sent to the hostel owner confirming receipt of their application.

---

## 2. Super Admin Approval Workflow
*This flow is used by the internal team (Super Admins) to review pending applications from the Admin Dashboard.*

When an admin clicks on a pending hostel in the dashboard, they have three primary actions:

### Action 1: Approve Hostel
- **Endpoint:** `POST /api/v1/super_admin/hostels/{hostel_id}/approve`
- **Action:** 
  - Sets `status = "active"`.
  - Enables visibility (`is_public = True`, `is_active = True`, `is_verified = True`).
- **Notification:** Sends a "Congratulations, your hostel is live!" email to the owner, optionally including a custom note from the admin.

### Action 2: Request Changes
- **Endpoint:** `POST /api/v1/super_admin/hostels/{hostel_id}/request-changes`
- **Payload:** Requires a `reason` (e.g., "Please upload a clearer GST certificate").
- **Action:** 
  - Sets `status = "changes_requested"`.
  - Keeps the hostel hidden from the public.
- **Notification:** Sends an "Action Required" email to the owner detailing exactly what needs to be fixed.

### Action 3: Reject Hostel
- **Endpoint:** `POST /api/v1/super_admin/hostels/{hostel_id}/reject`
- **Payload:** Requires a `reason` (e.g., "Property does not meet our minimum standards").
- **Action:**
  - Sets `status = "rejected"`.
  - Keeps the hostel permanently hidden.
- **Notification:** Sends a rejection email to the owner including the specific reason.

---

## 3. Super Admin Manual Creation
*If the internal team is onboarding a hostel manually without the public form.*

- **Endpoint:** `POST /api/v1/super_admin/hostels`
- **Process:** Super admins can create a hostel directly. As a safety measure, these hostels also start in the `pending_approval` (Draft) state. This allows the team to take their time adding rooms, uploading gallery images, and setting up the mess menu. Once the setup is perfect, the admin simply clicks **Approve** to push it live.

---

## Technical Edge-Cases Handled
1. **Case-Insensitive Enums:** The `hostel_type` field expects specific lowercase enums (`boys`, `girls`, `co-living`). A custom Pydantic validator intercepts frontend values (like `"Boys"` or `"CO-LIVING"`) and safely converts them to avoid 500 Server Errors.
2. **Security Bypasses:** Malicious API requests cannot force a hostel to go live during registration. The backend entirely ignores `is_public` or `is_featured` flags during the `POST /register` call.
