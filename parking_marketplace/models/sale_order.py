from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    parking_booking_id = fields.Many2one('parking.booking', string='Parking Booking', readonly=True, copy=False)
