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

    _sql_constraints = [
        ('check_hourly_rate_positive', 'CHECK(hourly_rate >= 0)', 'The hourly rate cannot be negative.'),
    ]

    def action_view_revenue(self):
        pass

    def _compute_total_revenue(self):
        for space in self:
            completed_bookings = self.env['parking.booking'].search([
                ('space_id', '=', space.id),
                ('state', '=', 'completed')
            ])
            space.total_revenue = sum(completed_bookings.mapped('total_price'))
