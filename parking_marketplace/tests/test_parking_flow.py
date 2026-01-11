from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class TestParkingFlow(TransactionCase):

    def setUp(self):
        super(TestParkingFlow, self).setUp()
        self.ParkingSpace = self.env['parking.space']
        self.ParkingBooking = self.env['parking.booking']
        self.Partner = self.env['res.partner']

        self.owner = self.Partner.create({'name': 'Test Owner'})
        self.driver1 = self.Partner.create({'name': 'Test Driver 1'})
        self.driver2 = self.Partner.create({'name': 'Test Driver 2'})

        self.space = self.ParkingSpace.create({
            'name': 'Test Space 1',
            'owner_id': self.owner.id,
            'hourly_rate': 10.0,
        })

    def test_01_booking_collision(self):
        """Test that the system prevents creating overlapping bookings."""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)

        # Create the first, valid booking
        booking1 = self.ParkingBooking.create({
            'space_id': self.space.id,
            'driver_id': self.driver1.id,
            'start_date': start_time,
            'end_date': end_time,
        })
        booking1.action_confirm()
        self.assertEqual(booking1.state, 'confirmed', "Booking 1 should be confirmed.")

        # Attempt to create a second, overlapping booking
        overlapping_start_time = start_time + timedelta(minutes=30)
        overlapping_end_time = end_time - timedelta(minutes=30)

        with self.assertRaises(ValidationError, msg="Should not be able to create an overlapping booking."):
            self.ParkingBooking.create({
                'space_id': self.space.id,
                'driver_id': self.driver2.id,
                'start_date': overlapping_start_time,
                'end_date': overlapping_end_time,
                'state': 'confirmed', # Set state to trigger the constrains
            })

    def test_02_money_flow_on_confirmation(self):
        """Test that a Sales Order with correct lines and total is created on confirmation."""
        start_time = datetime.now() + timedelta(hours=3)
        end_time = start_time + timedelta(hours=2) # 2 hours @ $10/hr = $20

        booking = self.ParkingBooking.create({
            'space_id': self.space.id,
            'driver_id': self.driver1.id,
            'start_date': start_time,
            'end_date': end_time,
        })

        # Trigger the SO creation
        booking.action_confirm()

        self.assertTrue(booking.sale_order_id, "Sales Order should be created.")
        self.assertEqual(booking.state, 'confirmed', "Booking should be in 'confirmed' state.")
        self.assertEqual(booking.total_price, 20.0, "Booking total price should be calculated correctly.")

        so = booking.sale_order_id
        self.assertEqual(len(so.order_line), 2, "Sales Order should have exactly two lines.")

        total_so_amount = sum(line.price_subtotal for line in so.order_line)
        self.assertAlmostEqual(total_so_amount, booking.total_price, places=2, msg="Sales Order total should match the booking total price.")

    def test_03_lifecycle_and_payout(self):
        """Test the full booking lifecycle from confirmed to completed and verify vendor bill creation."""
        start_time = datetime.now() - timedelta(hours=2) # Booking started in the past
        end_time = start_time + timedelta(hours=1) # Booking ended in the past

        booking = self.ParkingBooking.create({
            'space_id': self.space.id,
            'driver_id': self.driver1.id,
            'start_date': start_time,
            'end_date': end_time,
        })
        booking.action_confirm()
        self.assertEqual(booking.state, 'confirmed', "Booking should be confirmed.")

        # Manually trigger the 'start' cron's logic
        self.ParkingBooking._cron_start_bookings()
        self.assertEqual(booking.state, 'in_use', "Booking should move to 'in_use'.")

        # Manually trigger the 'complete' cron's logic
        self.ParkingBooking._cron_complete_bookings()
        self.assertEqual(booking.state, 'completed', "Booking should move to 'completed'.")

        # Verify that a Vendor Bill was created for the owner
        vendor_bill = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('partner_id', '=', self.owner.id),
        ])
        self.assertEqual(len(vendor_bill), 1, "Exactly one vendor bill should be created for the owner.")

        # Verify the amount of the vendor bill (Owner's share)
        fee_percent_str = self.env['ir.config_parameter'].sudo().get_param('parking.platform_fee_percent', '15.0')
        fee_percent = float(fee_percent_str)
        expected_owner_share = booking.total_price * (1 - (fee_percent / 100))

        self.assertAlmostEqual(vendor_bill.amount_total, expected_owner_share, places=2, msg="Vendor bill amount should be the owner's share.")
