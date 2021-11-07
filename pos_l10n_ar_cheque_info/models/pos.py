# -*- coding: utf-8 -*-

from itertools import groupby
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext
import odoo.addons.decimal_precision as dp


class PosOrder(models.Model):

	_inherit = "pos.order"

	def _process_payment_lines(self, pos_order, order, pos_session, draft):
		prec_acc = order.pricelist_id.currency_id.decimal_places
		order_bank_statement_lines= self.env['pos.payment'].search([('pos_order_id', '=', order.id)])
		order_bank_statement_lines.unlink()
		for payments in pos_order['statement_ids']:
			if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc):
				order.add_payment(self._payment_fields(order, payments[2], pos_order))

		order.amount_paid = sum(order.payment_ids.mapped('amount'))
		bank = self.env['res.bank'].browse(pos_order.get('bank_id'))

		if not draft and not float_is_zero(pos_order['amount_return'], prec_acc):
			cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
			if not cash_payment_method:
				raise UserError(_("No cash found for this session. Unable to record returned cash."))
			return_payment_vals = {
				'name': _('return'),
				'pos_order_id': order.id,
				'amount': -pos_order['amount_return'],
				'payment_date': fields.Date.context_today(self),
				'payment_method_id': cash_payment_method.id,
				'cheque_owner_name' : pos_order.get('owner_name'),
				'cheque_bank' : bank.id,
				'bank_account' : pos_order.get('bank_account'),
				'cheque_number' : pos_order.get('cheque_number'),
				'check_issue_date' : pos_order.get('check_issue_date'),
			}
			order.add_payment(return_payment_vals)
		
	def _payment_fields(self, order, ui_paymentline, pos_order):
		payment_date = ui_paymentline['name']
		bank = self.env['res.bank'].browse(pos_order.get('bank_id'))
		payment_date = fields.Date.context_today(self, fields.Datetime.from_string(payment_date))
		payment_method = self.env['pos.payment.method'].browse(ui_paymentline['payment_method_id'])
		if payment_method.pos_l10n_ar_cheque_info == True:
			return {
				'amount': ui_paymentline['amount'] or 0.0,
				'payment_date': payment_date,
				'payment_method_id': ui_paymentline['payment_method_id'],
				'card_type': ui_paymentline.get('card_type'),
				'transaction_id': ui_paymentline.get('transaction_id'),
				'pos_order_id': order.id,
				'cheque_owner_name' : pos_order.get('owner_name'),
				'cheque_bank' : bank.id,
				'bank_account' : pos_order.get('bank_account'),
				'cheque_number' : pos_order.get('cheque_number'),
				'check_issue_date' : pos_order.get('check_issue_date'),
				
			}
		else:
			return {
				'amount': ui_paymentline['amount'] or 0.0,
				'payment_date': payment_date,
				'payment_method_id': ui_paymentline['payment_method_id'],
				'card_type': ui_paymentline.get('card_type'),
				'transaction_id': ui_paymentline.get('transaction_id'),
				'pos_order_id': order.id,
			}

class PosConfigInherit(models.Model):

	_inherit = "pos.config"

	pos_l10n_ar_cheque_info = fields.Boolean(string="Add Check Details")
	bank = fields.Many2one('res.bank')

class PosOrderInherit(models.Model):

	_inherit = "pos.payment"

	cheque_owner_name = fields.Char(string="Owner name")
	cheque_bank = fields.Many2one('res.bank',string="Bank")
	bank_account = fields.Char(string="Bank Account")
	cheque_number = fields.Char(string="Cheque Number")
	check_issue_date = fields.Date(string="Cheque Date")

class AccountJournal(models.Model):

	_inherit = "pos.payment.method"

	pos_l10n_ar_cheque_info = fields.Boolean(string="Add Check Details")