from odoo import fields , models , api , _
from odoo.exceptions import UserError , ValidationError
from datetime import datetime, date, timedelta, time
import json
import requests 
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY

class LeaveType(models.Model):
    _inherit = 'hr.leave.type'
    
    leave_category = [
        ('casual_leave','Casual Leave'),
        ('annual_leave','Annual Leave'),
        ('sick_leave','Sick Time Off'),
        ('maternity_leave' , 'maternity Leave'),
        ('paid_leave' , 'Paid Time Off'),
        ('unpaid_leave' , 'Unpaid Leave'),
        ('eid_alfitr' , 'Eid Al-Fitr'),
        ('eid_aladha' , 'Eid Al-Adha'),
        ('national_day' , 'National Day'),
        ('sports_day' , 'Sports Day'),
        ('compensatory_days','Compensatory Days'),
        ('gratuity_leave' , 'Gratuity (End of Services)'),    
        ]
    
    name = fields.Selection(string="Name Leave" , selection=leave_category , required=True)
    is_common = fields.Boolean(string="Is Common")
    is_paid = fields.Boolean(string="Is Paid " )
    duration_leave = fields.Float(string ="Duration",
                                #   compute = "_compute_duration_leave",
                                  store = True)
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'A Leave already exists with this name . Leave name must be unique!'),
    ]
    
    # @api.depends('validity_start','validity_stop' , 'is_common')
    # def _compute_duration_leave(self):
    #     for record in self:
    #         if record.is_common:
    #             if record.validity_start and record.validity_stop:
    #                 delta = record.validity_stop - record.validity_start
    #                 record.duration_leave = delta.days / 1.0
    #             else:
    #                 record.duration_leave = False
    #         else:
    #             record.duration_leave = False

class Leave(models.Model):
    _inherit = 'hr.leave'
    
    balance = fields.Float(string="Balance",
                           compute = "_get_balance_leave" ,
                           store = True)
    
    def send_notification(self,id_odoo , title , message):
        serverToken = 'AAAA3vCpz1U:APA91bEhLpl47MlwpUv57qZJiLCvgh5qURZhG-57GiwZ0bUPdkKIJNLZa2FcjMzmi4IkCJGb9dTYLcSjK_VvGQrcxoI6gGsjOT2dJaHGvKc6_AUe8SSZfMThjXp1jV-vohjAOOJFHG2p'
        deviceToken = '/topics/' + str(id_odoo)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'key=' + serverToken,
        }
        body = {
            'notification': {'title': str(title),
                            'body':str(message) 
                                },
            'to': deviceToken,
            }
        response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body))
        if response.status_code == 200:
            return True
        else:
            return False

    def count_fridays(self ,start_date, end_date):

        start = start_date
        end = end_date
        while start.weekday() != 4:
            start += timedelta(days=1)

        num_fridays = 0
        while start <= end:
            num_fridays += 1
            start += timedelta(days=7)
        
        return num_fridays
    
    
    def _get_number_of_days(self, date_from, date_to, employee_id):
        """ Returns a float equals to the timedelta between two dates given as string."""
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            # We force the company in the domain as we are more than likely in a compute_sudo
            domain = [('company_id', 'in', self.env.company.ids + self.env.context.get('allowed_company_ids', []))]
            result = employee._get_work_days_data_batch(date_from, date_to, domain=domain)[employee.id]
            if self.request_unit_half and result['hours'] > 0:
                result['days'] = 0.5
            if self.holiday_status_id.is_common == False:
                result['days'] += self.count_fridays(date_from , date_to)
            return result
        today_hours = self.env.company.resource_calendar_id.get_work_hours_count(
            datetime.combine(date_from.date(), time.min),
            datetime.combine(date_from.date(), time.max),
            False)

        hours = self.env.company.resource_calendar_id.get_work_hours_count(date_from, date_to)
        days = hours / (today_hours or HOURS_PER_DAY) if not self.request_unit_half else 0.5
        return {'days': days, 'hours': hours}
        
    @api.depends('employee_id')
    def _get_balance_leave(self):
            for rec in self:    
                leave_type = rec.holiday_status_id.name
                if leave_type == 'casual_leave':
                    rec.balance =  rec.employee_id.casual_leave
                    
                elif leave_type == 'annual_leave':
                    rec.balance = rec.employee_id.annual_leave
                    
                elif leave_type == 'sick_leave':
                    rec.balance = rec.employee_id.sick_leave
                    
                elif leave_type == 'maternity_leave':
                    rec.balance = rec.employee_id.maternity_leave
                    
                elif leave_type == 'unpaid_leave':
                    rec.balance = rec.employee_id.unpaid_leave
                    
                elif leave_type == 'eid_alfitr':
                    rec.balance = rec.employee_id.eid_alfitr_leave
                    
                elif leave_type == 'eid_aladha':
                    rec.balance = rec.employee_id.eid_aladha_leave
                    
                elif leave_type == 'national_day':
                    rec.balance = rec.employee_id.national_day_leave
                    
                elif leave_type == 'sports_day':
                    rec.balance = rec.employee_id.sports_day_leave
                    
                elif leave_type == 'gratuity_leave':
                    rec.balance = rec.employee_id.gratuity_leave

                else:
                    rec.balance = 10
                
    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['draft', 'confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Time off request must be confirmed or validated in order to refuse it.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').write({'active': False})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()

        # Post a second message, more verbose than the tracking message
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_('Your %(leave_type)s planned on %(date)s has been refused', leave_type=holiday.holiday_status_id.display_name, date=holiday.date_from),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self._remove_resource_leave()
        self.activity_update()
        id_empolyee = self.employee_id.id
        title = "Leave is Refused"
        body = f"Request Leave in {self.request_date_from} is Refused"
        self.send_notification(id_empolyee , title , body)
        return True

    def action_validate(self):
        current_employee = self.env.user.employee_id
        leaves = self.filtered(lambda l: l.employee_id and not l.number_of_days)
        if leaves:
            raise ValidationError(_('The following employees are not supposed to work during that period:\n %s') % ','.join(leaves.mapped('employee_id.name')))

        if any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})
        self.filtered(lambda holiday: holiday.validation_type == 'both').write({'second_approver_id': current_employee.id})
        self.filtered(lambda holiday: holiday.validation_type != 'both').write({'first_approver_id': current_employee.id})

        for holiday in self.filtered(lambda holiday: holiday.holiday_type != 'employee'):
            if holiday.holiday_type == 'category':
                employees = holiday.category_id.employee_ids
            elif holiday.holiday_type == 'company':
                employees = self.env['hr.employee'].search([('company_id', '=', holiday.mode_company_id.id)])
            else:
                employees = holiday.department_id.member_ids

            conflicting_leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True
            ).search([
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('state', 'not in', ['cancel', 'refuse']),
                ('holiday_type', '=', 'employee'),
                ('employee_id', 'in', employees.ids)])

            if conflicting_leaves:
                # YTI: More complex use cases could be managed in master
                if holiday.leave_type_request_unit != 'day' or any(l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                    raise ValidationError(_('You can not have 2 time off that overlaps on the same day.'))

                # keep track of conflicting leaves states before refusal
                target_states = {l.id: l.state for l in conflicting_leaves}
                conflicting_leaves.action_refuse()
                split_leaves_vals = []
                for conflicting_leave in conflicting_leaves:
                    if conflicting_leave.leave_type_request_unit == 'half_day' and conflicting_leave.request_unit_half:
                        continue

                    # Leaves in days
                    if conflicting_leave.date_from < holiday.date_from:
                        before_leave_vals = conflicting_leave.copy_data({
                            'date_from': conflicting_leave.date_from.date(),
                            'date_to': holiday.date_from.date() + timedelta(days=-1),
                            'state': target_states[conflicting_leave.id],
                        })[0]
                        before_leave = self.env['hr.leave'].new(before_leave_vals)
                        before_leave._compute_date_from_to()

                        # Could happen for part-time contract, that time off is not necessary
                        # anymore.
                        # Imagine you work on monday-wednesday-friday only.
                        # You take a time off on friday.
                        # We create a company time off on friday.
                        # By looking at the last attendance before the company time off
                        # start date to compute the date_to, you would have a date_from > date_to.
                        # Just don't create the leave at that time. That's the reason why we use
                        # new instead of create. As the leave is not actually created yet, the sql
                        # constraint didn't check date_from < date_to yet.
                        if before_leave.date_from < before_leave.date_to:
                            split_leaves_vals.append(before_leave._convert_to_write(before_leave._cache))
                    if conflicting_leave.date_to > holiday.date_to:
                        after_leave_vals = conflicting_leave.copy_data({
                            'date_from': holiday.date_to.date() + timedelta(days=1),
                            'date_to': conflicting_leave.date_to.date(),
                            'state': target_states[conflicting_leave.id],
                        })[0]
                        after_leave = self.env['hr.leave'].new(after_leave_vals)
                        after_leave._compute_date_from_to()
                        # Could happen for part-time contract, that time off is not necessary
                        # anymore.
                        if after_leave.date_from < after_leave.date_to:
                            split_leaves_vals.append(after_leave._convert_to_write(after_leave._cache))

                split_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    leave_skip_state_check=True
                ).create(split_leaves_vals)

                split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

            values = holiday._prepare_employees_holiday_values(employees)
            leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
                leave_skip_state_check=True,
            ).create(values)

            leaves._validate_leave_request()

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
            
        id_empolyee = self.employee_id.id
        title = "Leave is Accepted"
        body = f"Request Leave in {self.request_date_from} is Accepted "
        if self.state == 'validate':
            self.send_notification(id_empolyee , title , body)
        return True
