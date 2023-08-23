from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from json import dumps
from datetime import datetime , date
from dateutil.relativedelta import relativedelta

class PayrollContract(models.Model):
    _inherit = ['hr.contract']
    
    marital_list = [('single','Single'),('family','Family')]


    marital_status = fields.Selection(selection = marital_list, string="Marital Status")
    num_wife = fields.Integer(string="Number of Wife")
    num_children = fields.Integer(string="Number of Children")
    @api.model
    def update_state(self):
        contracts = self.search([
            ('state', '=', 'open'), ('kanban_state', '!=', 'blocked'),
            '|',
            '&',
            ('date_end', '<=', fields.Date.to_string(date.today() + relativedelta(days=7))),
            ('date_end', '>=', fields.Date.to_string(date.today() + relativedelta(days=1))),
            '&',
            ('visa_expire', '<=', fields.Date.to_string(date.today() + relativedelta(days=60))),
            ('visa_expire', '>=', fields.Date.to_string(date.today() + relativedelta(days=1))),
        ])

        for contract in contracts:
            contract.activity_schedule(
                'mail.mail_activity_data_todo', contract.date_end,
                _("The contract of %s is about to expire.", contract.employee_id.name),
                user_id=contract.hr_responsible_id.id or self.env.uid)

        contracts.write({'kanban_state': 'blocked'})

        self.search([
            ('state', '=', 'open'),
            ('date_end', '<=', fields.Date.to_string(date.today() + relativedelta(days=1))),
        ]).write({
            'state': 'close'
        })

        self.search([('state', '=', 'draft'), ('kanban_state', '=', 'done'), ('date_start', '<=', fields.Date.to_string(date.today())),]).write({
            'state': 'open'
        })

        contract_ids = self.search([('date_end', '=', False), ('state', '=', 'close'), ('employee_id', '!=', False)])
        # Ensure all closed contract followed by a new contract have a end date.
        # If closed contract has no closed date, the work entries will be generated for an unlimited period.
        for contract in contract_ids:
           contract.write({'state': 'open'})
        return True