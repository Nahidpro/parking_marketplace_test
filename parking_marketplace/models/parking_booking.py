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
    ], string='Status', default='draft', required=True, tracking=True)

    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True, copy=False)
    date_pending_approval = fields.Datetime(string='Pending Approval Time', readonly=True)

    duration = fields.Float(string="Duration (hours)", compute='_compute_duration_and_price', store=True)
    total_price = fields.Monetary(string="Total Price", compute='_compute_duration_and_price', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='space_id.currency_id')

    @api.depends('start_date', 'end_date', 'space_id.hourly_rate')
    def _compute_duration_and_price(self):
        for booking in self:
            if booking.start_date and booking.end_date:
                duration_seconds = (booking.end_date - booking.start_date).total_seconds()
                booking.duration = duration_seconds / 3600
                booking.total_price = booking.duration * booking.space_id.hourly_rate
            else:
                booking.duration = 0
                booking.total_price = 0

    @api.constrains('start_date', 'end_date', 'space_id', 'state')
    def _check_availability(self):
        for booking in self:
            if booking.state in ('draft', 'cancelled'):
                continue

            # Check for overlapping bookings
            overlapping_bookings = self.env['parking.booking'].search([
                ('id', '!=', booking.id),
                ('space_id', '=', booking.space_id.id),
                ('state', 'not in', ['draft', 'cancelled'], 'expired']),
                ('start_date', '<', booking.end_date),
                ('end_date', '>', booking.start_date),
            ])
            if overlapping_bookings:
                raise ValidationError("Error: This time slot overlaps with an existing booking.")

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'pending_approval':
            vals['date_pending_approval'] = fields.Datetime.now()
        return super(ParkingBooking, self).write(vals)

    # ACTION METHODS
    def action_confirm(self):
        for booking in self:
            if booking.state != 'draft':
                continue
            booking._create_sale_order()
            booking.write({'state': 'confirmed'})

    def action_start(self):
        self.write({'state': 'in_use'})

    def action_complete(self):
        for booking in self:
            if booking.state != 'in_use':
                continue
            booking._trigger_payout_and_revenue_recognition()
            booking.write({'state': 'completed'})

    def action_cancel(self):
        # In a real module, this would handle refunds. For now, it's a simple state change.
        self.write({'state': 'cancelled'})

    def action_expire(self):
        self.write({'state': 'expired'})


    def _trigger_payout_and_revenue_recognition(self):
        self.ensure_one()

        # 1. Capture the payment
        tx = self.sale_order_id.transaction_ids.filtered(lambda t: t.state == 'authorized')
        if tx:
            tx._do_capture()

        # 2. Create and post Vendor Bill for the owner. The account is set on the product.
        owner = self.space_id.owner_id
        payout_product = self.env.ref('parking_marketplace.product_owner_payout')
        fee_percent_str = self.env['ir.config_parameter'].sudo().get_param('parking.platform_fee_percent', '15.0')
        fee_percent = float(fee_percent_str)
        platform_fee = self.total_price * (fee_percent / 100)
        owner_share = self.total_price - platform_fee

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': owner.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_line_ids': [
                (0, 0, {
                    'name': f"Payout for booking {self.id} - {self.space_id.name}",
                    'product_id': payout_product.id,
                    'quantity': 1,
                    'price_unit': owner_share,
                })
            ],
        })
        bill.action_post()

        # 3. Journal Entry to move funds from Escrow to Revenue and balance the Vendor Bill's expense account
        escrow_account = self.env.ref('parking_marketplace.parking_account_escrow')
        revenue_account = self.env.ref('parking_marketplace.parking_account_revenue')
        clearing_account = self.env.ref('parking_marketplace.parking_account_clearing')
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)

        self.env['account.move'].create({
            'move_type': 'entry',
            'ref': f"Booking {self.id} Revenue Recognition",
            'journal_id': journal.id,
            'line_ids': [
                (0, 0, {'account_id': escrow_account.id, 'debit': self.total_price, 'credit': 0}),
                (0, 0, {'account_id': clearing_account.id, 'debit': 0, 'credit': owner_share}),
                (0, 0, {'account_id': revenue_account.id, 'debit': 0, 'credit': platform_fee}),
            ],
        }).action_post()


    def _create_sale_order(self):
        self.ensure_one()
        if self.sale_order_id:
            return

        service_product = self.env.ref('parking_marketplace.product_parking_service')
        fee_product = self.env.ref('parking_marketplace.product_platform_fee')

        fee_percent_str = self.env['ir.config_parameter'].sudo().get_param('parking.platform_fee_percent', '15.0')
        fee_percent = float(fee_percent_str)

        platform_fee = self.total_price * (fee_percent / 100)
        owner_share = self.total_price - platform_fee

        so = self.env['sale.order'].create({
            'partner_id': self.driver_id.id,
            'parking_booking_id': self.id,
            'order_line': [
                (0, 0, {
                    'product_id': service_product.id,
                    'name': f"Parking at {self.space_id.name} from {self.start_date} to {self.end_date}",
                    'price_unit': owner_share,
                    'product_uom_qty': 1,
                }),
                (0, 0, {
                    'product_id': fee_product.id,
                    'price_unit': platform_fee,
                    'product_uom_qty': 1,
                })
            ]
        })

        self.sale_order_id = so.id
        so.action_confirm()

    # CRON JOB METHODS
    @api.model
    def _cron_start_bookings(self):
        now = fields.Datetime.now()
        bookings_to_start = self.search([
            ('state', '=', 'confirmed'),
            ('start_date', '<=', now)
        ])
        bookings_to_start.action_start()

    @api.model
    def _cron_complete_bookings(self):
        now = fields.Datetime.now()
        bookings_to_complete = self.search([
            ('state', '=', 'in_use'),
            ('end_date', '<=', now)
        ])
        bookings_to_complete.action_complete()

    @api.model
    def _cron_expire_pending_bookings(self):
        expiration_minutes = int(self.env['ir.config_parameter'].sudo().get_param('parking.expiration_minutes', '60'))
        expiration_time = fields.Datetime.subtract(fields.Datetime.now(), minutes=expiration_minutes)

        bookings_to_expire = self.search([
            ('state', '=', 'pending_approval'),
            ('date_pending_approval', '<=', expiration_time)
        ])
        bookings_to_expire.action_expire()
