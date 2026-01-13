# Parking Marketplace - Architect Map & Technical Handover

This document provides a technical overview of the `parking_marketplace` module for developers and system administrators.

---

## 1. Model Map

The module introduces two primary models and extends one core Odoo model.

*   `parking.space`
    *   **Purpose:** Represents a physical parking space listing. This is the root resource.
    *   **Key Relations:**
        *   `owner_id`: Many2one relationship to `res.partner` (the space owner).
        *   Has a one-to-many relationship with `parking.booking`.

*   `parking.booking`
    *   **Purpose:** The central model representing a time-based reservation for a `parking.space`. This model is the **source of truth** for availability.
    *   **Key Relations:**
        *   `space_id`: Many2one relationship to `parking.space`.
        *   `driver_id`: Many2one relationship to `res.partner` (the driver).
        *   `sale_order_id`: One-to-one relationship (via Many2one) to `sale.order`.

*   `sale.order` (Extended)
    *   **Purpose:** Acts as the **financial shadow** of a `parking.booking`. It is created *only* to handle the payment and invoicing flow. It **never** controls availability.
    *   **Key Relations:**
        *   `parking_booking_id`: A Many2one field providing a link back to the source booking for traceability.

---

## 2. Core Logic Summary

### "Time-Lock" Availability Logic

The core constraint of the system is to prevent double bookings.

*   **Implementation:** An `@api.constrains` method in the `parking.booking` model.
*   **Formula:** The constraint triggers if a new or modified booking overlaps with any existing booking for the same `space_id`. The overlap formula is:
    `start_date < existing.end_date AND end_date > existing.start_date`
*   **Exclusions:** Bookings in the `draft`, `cancelled`, or `expired` states are excluded from this check, as they do not reserve a time slot.

### "Escrow" Accounting Flow

The system ensures that the platform holds the driver's payment until the booking is completed, and only then are funds distributed.

1.  **Booking Confirmed:**
    *   A `sale.order` is created with two lines (owner's share, platform fee).
    *   The products on these lines are configured to post their revenue to a **Liability** account named "**Parking Escrow**".
    *   The driver's payment is **Authorized** (but not captured).

2.  **Booking Completed:**
    *   The driver's payment is **Captured**.
    *   A **Vendor Bill** is created for the `owner_id`. The product on this bill is configured to use a liability account named "**Owner Payout Clearing Account**" as its expense account.
    *   A final `account.move` (Journal Entry) is created to balance the accounts:
        *   **DEBIT** `Parking Escrow` (for the full amount, clearing it).
        *   **CREDIT** `Platform Service Fee Revenue` (recognizing the platform's income).
        *   **CREDIT** `Owner Payout Clearing Account` (balancing the debit from the Vendor Bill).

---

## 3. Cron Registry (Scheduled Jobs)

The module relies on three automated jobs to manage the booking lifecycle. These can be found and managed in Odoo under `Settings > Technical > Automation > Scheduled Actions`.

1.  **Parking: Start Confirmed Bookings**
    *   **Method:** `_cron_start_bookings()` on `parking.booking`.
    *   **Purpose:** Finds all `confirmed` bookings whose `start_date` is in the past and moves them to the `in_use` state.
    *   **Frequency:** Runs every 5 minutes.

2.  **Parking: Complete In-Use Bookings**
    *   **Method:** `_cron_complete_bookings()` on `parking.booking`.
    *   **Purpose:** Finds all `in_use` bookings whose `end_date` is in the past, moves them to `completed`, and triggers the payout logic.
    *   **Frequency:** Runs every 5 minutes.

3.  **Parking: Expire Pending Bookings**
    *   **Method:** `_cron_expire_pending_bookings()` on `parking.booking`.
    *   **Purpose:** Finds all `pending_approval` bookings that are older than the system's configured expiration time and moves them to `expired`.
    *   **Frequency:** Runs every 15 minutes.
