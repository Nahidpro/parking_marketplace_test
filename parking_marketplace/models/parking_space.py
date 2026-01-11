from odoo import models, fields

class ParkingSpace(models.Model):
    _name = 'parking.space'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Parking Space Listing'

    name = fields.Char(string='Name', required=True)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True)
    address = fields.Text(string='Address')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    hourly_rate = fields.Monetary(string='Hourly Rate', currency_field='currency_id', required=True)

    active = fields.Boolean(default=True)

    total_revenue = fields.Monetary(string="Total Revenue", compute='_compute_total_revenue')
    booking_count = fields.Integer(string="Booking Count", compute='_compute_booking_count')

    _sql_constraints = [
        ('check_hourly_rate_positive', 'CHECK(hourly_rate >= 0)', 'The hourly rate cannot be negative.'),
    ]

    def _compute_total_revenue(self):
        for space in self:
            bookings = self.env['parking.booking'].search([('space_id', '=', space.id), ('sale_order_id', '!=', False)])
            space.total_revenue = sum(bookings.mapped('sale_order_id.amount_total'))

    def _compute_booking_count(self):
        for space in self:
            space.booking_count = self.env['parking.booking'].search_count([('space_id', '=', space.id)])

    def action_view_bookings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bookings',
            'view_mode': 'tree,form',
            'res_model': 'parking.booking',
            'domain': [('space_id', '=', self.id)],
            'context': {'default_space_id': self.id}
        }

    def action_view_revenue(self):
        self.ensure_one()
        bookings = self.env['parking.booking'].search([('space_id', '=', self.id), ('sale_order_id', '!=', False)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Orders',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'domain': [('id', 'in', bookings.mapped('sale_order_id').ids)],
        }
