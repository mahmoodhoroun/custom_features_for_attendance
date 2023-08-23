from odoo import api, fields, models, _
import requests
import json
from datetime import datetime, timedelta, date

class Employee(models.Model):
    _inherit = 'hr.employee'
    
    marital_list = [
        ('single','Single'),
        ('family','Family')
    ]
    received_type_list = [
        ('tickets','Tickets'),
        ('allowance','Allowance')
    ] 
    contract_selection = [
        ("head_office","Head Office"),
        ("site","Site")
    ]
    
    working_time_type = [
        ("morning_shift" , "Morning Shift"),
        ("night_shift"  , "Night Shift")
    ]

    contract_type = fields.Selection(string="Contract Type" , selection=contract_selection)
    
    leave_ids = fields.One2many('hr.leave.report' , 'employee_id' ,string="Leaves")
    
    structure_type_id = fields.Many2one(
        string = 'Salary Structure Type ',
        related = 'contract_id.structure_type_id',
        store = True
    )
    casual_leave = fields.Float(
        string='Casual Leave',
        # compute="_compute_balence_casual",
        # store = True
    )
    annual_leave = fields.Float(
        string='Annual Leave',
        # compute="_compute_balance_annual",
        # store = True
    )
    sick_leave = fields.Float(
        string="Sick Leave",
        # compute="_compute_balance_sick",
        # store = True
    )
    maternity_leave = fields.Float(
        string="Maternity Leave",
        # compute="_compute_balance_maternity",
        # store = True
    )
    unpaid_leave = fields.Float(
        string="Unpaid Leave",
        # compute="_compute_balance_unpaid",
        # store = True
    )
    eid_alfitr_leave = fields.Float(
        string='Eid Al-Fitr',
    )
    eid_aladha_leave = fields.Float(
        string='Eid Al-Adha',
    )
    national_day_leave = fields.Float(
        string='National Day',
    )
    sports_day_leave = fields.Float(
        string='Sports Day',
    )
    gratuity_leave = fields.Float(
        string='Gratuity (End of Services)',
        # compute="_compute_balance_gratuity",
        # store = True
    )
    compensatory_leave = fields.Float(
        string='Compensatory Days',
    )
    worktime_type = fields.Selection(
        string="Work Time Type" ,
        selection = working_time_type
    )

    due_date = fields.Date(
        string="Due Date",
        compute="_compute_due_date"
    )
    marital_status = fields.Selection(
        selection= marital_list,
        string="Marital_status",
    )
    balance_tickets = fields.Integer(
        default = 0 ,
        string="Balance Tickets",
    )
    is_received = fields.Boolean(
        string="Is Received"
    )
    received_date = fields.Date(string="Receipt Date")
    
    received_type = fields.Selection(
        selection=received_type_list,
        string="Received Type"
    )
    tickets_cost = fields.Float(string="Allowance Tickets Amount",default=0.0)

    @api.depends('contract_id.date_start')
    def _compute_due_date(self):
        for rec in self:
            current_start_date = False
            if rec.contract_id.date_start:
                current_start_date = rec.contract_id.date_start.replace(year=datetime.now().year)
                
            inital_due_date = '' 
            if current_start_date:
                inital_due_date = current_start_date + timedelta(days=365)
                
            if rec.is_received and rec.due_date:
                inital_due_date = rec.due_date + timedelta(days=365)
                    
            rec.due_date = inital_due_date

    # def _compute_balance_ticket(self):
        # for rec in self:
            

    def check_user_in_group(self):
        group_id = self.env['res.groups'].search([('id', '=', 33)], limit=1)
        if group_id:
            user_ids = group_id.users
            user_3 = self.env['res.users'].browse(3)
            if user_3 in user_ids:
                return True
        return False
    
    @api.depends('leave_ids.number_of_days')
    def _compute_balence_casual(self):
        balance_leave = 0
        id_user = int(self.id)
        for rec in self:
            for leave in rec.leave_ids:
                if leave.holiday_status_id.name == 'casual_leave' and leave.state == "validate":
                    balance_leave = balance_leave + leave.number_of_days
        self.casual_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET casual_leave= {balance_leave} WHERE id={id_user}""")

                
    @api.depends('leave_ids.number_of_days')
    def _compute_balance_annual(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'annual_leave' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.annual_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET annual_leave = {balance_leave} WHERE id={id_user}""")
        
    @api.depends('leave_ids.number_of_days')
    def _compute_balance_sick(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'sick_leave' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.sick_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET sick_leave= {balance_leave} WHERE id={id_user}""")

    @api.depends('leave_ids.number_of_days')
    def _compute_balance_maternity(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'maternity_leave' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.maternity_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET maternity_leave= {balance_leave} WHERE id={id_user}""")

    @api.depends('leave_ids.number_of_days')
    def _compute_balance_unpaid(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'unpaid_leave' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.unpaid_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET unpaid_leave= {balance_leave} WHERE id={id_user}""")

    @api.depends('leave_ids.number_of_days')
    def _compute_balance_eid_alfiter(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'eid_alfitr' and  leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.eid_alfitr_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET eid_alfitr_leave= {balance_leave} WHERE id={id_user}""")
            
    @api.depends('leave_ids.number_of_days')
    def _compute_balance_eid_aladha(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'eid_aladha' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.eid_aladha_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET eid_aladha_leave= {balance_leave} WHERE id={id_user}""")
    
    def compute_balance_national(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'national_day' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.national_day_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET national_day_leave= {balance_leave} WHERE id={id_user}""")
        
    @api.depends('leave_ids.number_of_days')
    def _compute_balance_sport(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'sports_day' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.sports_day_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET sports_day_leave= {balance_leave} WHERE id={id_user}""")
        
        
    @api.depends('leave_ids.number_of_days')
    def _compute_balance_gratuity(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'gratuity_leave' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.gratuity_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET gratuity_leave= {balance_leave} WHERE id={id_user}""")
        
    @api.depends('leave_ids.number_of_days')
    def _compute_balance_compensatory(self):
        balance_leave = 0
        id_user = int(self.id)
        for leave in self.leave_ids:
           if leave.holiday_status_id.name == 'compensatory_days' and leave.state == "validate":
                balance_leave = balance_leave + leave.number_of_days
        self.compensatory_leave = balance_leave
        self.env.cr.execute(f"""UPDATE hr_employee SET compensatory_leave= {balance_leave} WHERE id={id_user}""")
    
    @api.model
    def cron_balnace(self):
        employees = self.env['hr.employee'].search([])
        for rec in employees:
            rec._compute_balence_casual()
            rec._compute_balance_annual()
            rec._compute_balance_sick()
            rec._compute_balance_maternity()
            rec._compute_balance_unpaid()
            rec._compute_balance_eid_alfiter()
            rec._compute_balance_eid_aladha()
            rec._compute_balance_sport()
            rec._compute_balance_gratuity()
            rec.compute_balance_national()
            rec._compute_balance_compensatory()
        
class ElecEmployee(models.Model):
    _inherit = 'hr.employee.public'
    
    contract_selection = [
        ("head_office","Head Office"),
        ("site","Site")
    ]

    contract_type = fields.Selection(string="Contract Type" , selection=contract_selection)
    
    structure_type_id = fields.Many2one(
        'hr.payroll.structure.type',
         string = 'Salary Structure Type ',
         store = True,
    )
    casual_leave = fields.Float(
        string='Casual Leave',
    )
    annual_leave = fields.Float(
        string='Annual Leave',
    )
    sick_leave = fields.Float(
        string="Sick Leave",
    )
    maternity_leave = fields.Float(
        string="Maternity Leave",
    )
    unpaid_leave = fields.Float(
        string="Unpaid Leave",
    )
    eid_alfitr_leave = fields.Float(
        string='Eid Al-Fitr',
    )
    eid_aladha_leave = fields.Float(
        string='Eid Al-Adha',
    )
    national_day_leave = fields.Float(
        string='National Day',
    )
    sports_day_leave = fields.Float(
        string='Sports Day',
    )
    gratuity_leave = fields.Float(
        string='Gratuity (End of Services)',
    )
    compensatory_leave = fields.Float(
        string='Compensatory Leave',
    )

