from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ParkingBooking(models.Model):
    _name = 'parking.booking'
    _description = 'Parking Booking'

    space_id = fields.Many2one('parking.space', string='Parking Space', required=True, ondelete='cascade')
    driver_id = fields.Many2one('res.partner', string='Driver', required=True)
    start_date = fields.Datetime(string='Start Time', required=True)
    end_date = fields.Datetime(string='End Time', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('in_use', 'In Use'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)

    @api.constrains('start_date', 'end_date', 'space_id', 'state')
    def _check_availability(self):
        for booking in self:
            if booking.state in ('draft', 'cancelled'):
                continue

            # Check for overlapping bookings
            overlapping_bookings = self.env['parking.booking'].search([
                ('id', '!=', booking.id),
                ('space_id', '=', booking.space_id.id),
                ('state', 'not in', ['draft', 'cancelled']),
                ('start_date', '<', booking.end_date),
                ('end_date', '>', booking.start_date),
            ])
            if overlapping_bookings:
                raise ValidationError("Error: This time slot overlaps with an existing booking.")
