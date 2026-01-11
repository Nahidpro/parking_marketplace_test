# Parking Marketplace - User Guide

This guide provides instructions for the two main user types of the Parking Marketplace module: Space Owners and Drivers.

---

## 1. For Space Owners

As a Space Owner, you can manage your parking spaces and see their activity.

### How to Manage Your Parking Spaces

1.  **Navigate to Parking Management:** From the main Odoo dashboard, go to `Sales > Parking Management > Parking Spaces`.
2.  **View Your Spaces:** You will see a list of all parking spaces. You can click on any space to see its details.
3.  **Deactivate/Reactivate a Space:**
    *   Open the parking space you wish to manage.
    *   Click the "Edit" button.
    *   Find the "**Active**" checkbox.
    *   **To deactivate (delist)** the space, uncheck the box.
    *   **To reactivate** it, check the box.
    *   Click "Save". Inactive spaces are hidden from drivers.

### How to View Your Bookings

You can see all the bookings for a specific space directly from its form view.

1.  Navigate to the Parking Space you want to inspect.
2.  At the top of the form, you will see two "Smart Buttons":
    *   **Bookings:** This button shows the total number of bookings for this space. Click it to see a list of all past, present, and future bookings for this specific location.
    *   **Total Revenue:** This shows the total revenue generated from this space from all confirmed bookings.

---

## 2. For Drivers

As a Driver, you can manage your bookings through the customer portal.

### How to Track Your Booking Status

1.  **Log in to the Portal:** Access the Odoo portal by clicking "My Account" from the main website.
2.  **View Your Sales Orders:** Your parking bookings are managed as Sales Orders in the portal. Click on "Sales Orders" to see a list of all your bookings.
3.  **Check the Status:** The status of your Sales Order corresponds to the status of your booking. You can see if it is confirmed and paid. The details of the order will contain the name of the parking space and the start/end times.

---

## 3. State Glossary

This explains what each booking status means. You can see this status on the `parking.booking` records in the backend.

*   **Draft:** The booking has been created but not yet confirmed. It does not block availability.
*   **Pending Approval:** (If enabled for the space) The booking is awaiting approval from the space owner. It does not yet block availability.
*   **Confirmed:** The booking has been confirmed (and payment has been authorized). It now blocks the time slot, and no one else can book it.
*   **In Use:** The booking's start time has passed, and the parking space is currently occupied by the driver.
*   **Completed:** The booking's end time has passed. The driver's payment has been captured, and the payout process for the owner has been initiated.
*   **Cancelled:** The booking was cancelled by the driver before the start time.
*   **Expired:** The booking was pending approval but was not approved by the owner within the configured time limit (e.g., 60 minutes). It was automatically cancelled.
