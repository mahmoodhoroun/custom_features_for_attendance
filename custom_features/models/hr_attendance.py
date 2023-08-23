import pytz
from odoo import models, fields, api, _
from odoo.tools import format_datetime
from odoo.exceptions import UserError , ValidationError
from datetime import datetime, timedelta, time, date
import calendar
import base64
import requests 
import json


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    # worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours_new', store=True, readonly=True)
    employee_number = fields.Char(string='Employee Number' , related="employee_id.barcode")
    project_id = fields.Many2one(
        'project.project',
        string = "Project"
    )
    transfer_time = fields.Float(
        string="Estimated T.T",
    )
    transfer_time_actual = fields.Float(
        string="Actual T.T",
        compute="_calc_time_between_project",
        store=True
    )
    close_auto = fields.Boolean(
        string="Automatic closing",
        default = False,
        store=True,
        readonly=True
    )   
    project_check_in = fields.Many2one(
        'project.project',
        string="Project Check in"
    )
    project_check_out = fields.Many2one(
        'project.project',
        string="Project Check out"
    )
    location_check_in = fields.Char(
        string="Location Check in Hide",
    )
    location_check_in_show = fields.Char(
        string="Location Check in",
        compute="_decode_location_checkIn"
    )
    location_check_out = fields.Char(
        string="Location Check out Hide",
    )
    location_check_out_show = fields.Char(
        string="Location Check out",
        compute="_decode_location_checkOut",
    )
    net_hours = fields.Float(
        string="Net Hours",
        compute="_compute_net_hours",
        store=True
    )
    overtime_day =fields.Float(
        string = "OT",
        compute="_compute_overtime",
        default= 0.0,
        store=True
    )
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
        
    def get_required_working_hours(self, day ,calender_emp):
        attendance = calender_emp.attendance_ids
        week_day = day.strftime('%w')
        H_MO , H_TH = 0 , 0 
                
        for rec in attendance:
            if rec.dayofweek == '0':
                H_MO = rec
            elif rec.dayofweek == '3':
                H_TH = rec
                        
        working_time = {
                    'MO': float(H_MO.hour_to - H_MO.hour_from),
                    'TH': float(H_TH.hour_to - H_TH.hour_from),
        } 
        if week_day == '4':
            return working_time['TH']
        elif week_day == '5':
            return 0
        else:
            return working_time['MO']
    
    @api.model
    def compare_daily_working_hours(self):
        employees = self.env['hr.employee'].search([])
        for employee in employees:
             resourse_calendar = employee.resource_calendar_id
             dt = datetime.now().date()
             required_daily_hours = self.get_required_working_hours(dt , resourse_calendar)
             num_hours = 0
             
            # Calculate start and end datetimes for the day
             start_datetime = datetime.combine(dt, time.min)
             end_datetime = datetime.combine(dt, time.max)
            
            # Search for attendance records
             attendance_records = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_datetime),
                ('check_in', '<=', end_datetime),
            ])
             
             for rec in attendance_records:
                num_hours += rec.net_hours
             under_OT = required_daily_hours - num_hours
             overtime = num_hours - required_daily_hours
             
             record = self.env['attendance.daily.stat'].create({
                    'employee_id': employee.id,
                    'date': dt,
                    'required_hours' : required_daily_hours,
                    'under_overtime' : 0 if under_OT < 0 else under_OT,
                    'overtime' : 0 if overtime < 0 else overtime,
                    'net_hours' : num_hours})
             
    @api.model
    def compare_daily_hours_pervious_month(self):
        employees = self.env['hr.employee'].search([])
        date_from = datetime(2023,8,1)
        date_end  = datetime(2023,8,8)
        current_date = date_from 
        while(current_date <= date_end):
            for employee in employees:
                resourse_calendar = employee.resource_calendar_id
                dt = current_date
                required_daily_hours = self.get_required_working_hours(dt , resourse_calendar)
                num_hours = 0
                
                # Calculate start and end datetimes for the day
                start_datetime = datetime.combine(dt, time.min)
                end_datetime = datetime.combine(dt, time.max)
                
                # Search for attendance records
                attendance_records = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', start_datetime),
                    ('check_in', '<=', end_datetime),
                ])
                
                for rec in attendance_records:
                    num_hours += rec.net_hours
                under_OT = required_daily_hours - num_hours
                overtime = num_hours - required_daily_hours
                
                record = self.env['attendance.daily.stat'].create({
                        'employee_id': employee.id,
                        'date': dt,
                        'required_hours' : required_daily_hours,
                        'under_overtime' : 0 if under_OT < 0 else under_OT,
                        'overtime' : 0 if overtime < 0 else overtime,
                        'net_hours' : num_hours})
                    
                #  if num_hours < required_daily_hours:
                #      diff = required_daily_hours - num_hours
                #      id_emp = employee.id
                #      title ="Notify Working Hours"
                #      message = f"You did not work the required hours today.You have {diff} working hours left"
                #      self.send_notification(id_emp , title , message)
            
            current_date = current_date + timedelta(days=1)      
    @api.depends('location_check_in')
    def _decode_location_checkIn(self):
        for rec in self:
            text = rec.location_check_in
            try:
                rec.location_check_in_show = base64.b64decode(text).decode('utf-8')
            except:
                rec.location_check_in_show = text

    @api.depends('location_check_out')
    def _decode_location_checkOut(self):
        for rec in self:
            text = rec.location_check_out
            try:
                rec.location_check_out_show = base64.b64decode(text).decode('utf-8')
            except:
                rec.location_check_out_show = text
    
    @api.depends('check_in', 'check_out')
    def _compute_net_hours(self):
        for attendance in self:
            transfer = 0 
            if attendance.worked_hours:
                # to calucate Transfer Time between projects
                if attendance.transfer_time_actual < attendance.transfer_time:
                    transfer =  attendance.transfer_time_actual / 60.0
                else:
                    transfer =  attendance.transfer_time / 60.0
                
                attendance.net_hours = attendance.worked_hours + transfer
                
            else:
                attendance.net_hours = False   
               
    @api.depends('check_in', 'check_out' , 'project_check_in')
    def _calc_time_between_project(self):
        for rec in self:
            if rec.check_in:
                ICPSudo = rec.env['ir.config_parameter'].sudo()
                time_unknown = ICPSudo.get_param('custom_features.time_between_points_unknown')
                year = int(rec.check_in.strftime('%Y'))
                month = int(rec.check_in.strftime('%m'))
                day = int(rec.check_in.strftime('%d'))
                
                start_date = datetime(year, month, day, 0, 0, 0)

                last_attendance = rec.env['hr.attendance'].search([
                                                                ('employee_id','=',rec.employee_id.id),
                                                                ('check_in' , '>=' , start_date),
                                                                ('check_in' , '<' , rec.check_in),
                ],limit=1)
                
                if last_attendance and last_attendance.check_out:
                    delta = rec.check_in - last_attendance.check_out
                    rec.transfer_time_actual = delta.total_seconds() / 60.0
                    project_from = last_attendance.project_check_in.id
                    project_to = rec.project_check_in.id
                    
                    if project_from and project_to:
                        time_project = rec.env['project.time'].search(["|",
                                                                            "&",
                                                                                ["from_project","=",project_from],
                                                                                ["to_project","=",project_to],
                                                                            "&",
                                                                                ["from_project","=",project_to],
                                                                                ["to_project","=",project_from]
                                                                            ],limit=1)
                
                        if len(time_project) == 1:
                            rec.transfer_time = time_project.time 

                        else:
                            rec.transfer_time =  time_unknown
                    else:
                        rec.transfer_time =  time_unknown  
                else:
                    rec.transfer_time = 0
                    rec.transfer_time_actual = 0
    
    @api.depends('check_out')
    def _compute_overtime(self):
        """
            Return Overtime in the same employee and same day.
            
            :return: Float value in Overtime 
        """
        for record in self:
            day_check_in = record.check_in.date()
            day_of_week = int(day_check_in.weekday()) 
            num_hours = 0
            resource_calendar = record.employee_id.resource_calendar_id
            # Convert day string to datetime object
            day = record.check_in.date()
            day_dt = datetime.strptime(str(day), '%Y-%m-%d').date()
            
            # Calculate start and end datetimes for the day
            start_datetime = datetime.combine(day_dt, time.min)
            end_datetime = datetime.combine(day_dt, time.max)
            
            # Search for attendance records
            attendance_records = self.search([
                ('employee_id', '=', record.employee_id.id),
                ('check_in', '>=', start_datetime),
                ('check_in', '<=', end_datetime),
            ])
            for rec in attendance_records:
                num_hours += rec.worked_hours
                
            attendance_ids = resource_calendar.attendance_ids
        
            req_hour = 0     
            for rec in attendance_ids:
                if rec.dayofweek == '3' and day_of_week == 3:
                    req_hour = float(rec.hour_to - rec.hour_from)
                elif rec.dayofweek == str(day_of_week):
                    req_hour = float(rec.hour_to - rec.hour_from)
            
            OT = num_hours - req_hour
            record.overtime_day = 0 if OT < 0.0 else OT   
                       
    @api.model
    def closing_records_attendance_night(self):
        
        rows_no_check_out = self.env['hr.attendance'].search([
                                    ('check_out', '=' , False),
                                    ('employee_id.worktime_type' , '=' , 'night_shift')
                                    ])
        for rec in rows_no_check_out:
            ICPSudo = rec.env['ir.config_parameter'].sudo()
            hour = int(ICPSudo.get_param('custom_features.time_check_out_auto'))
            hour = hour - 3
            try:
                auto_check_out = datetime(rec.check_in.year, rec.check_in.month, rec.check_in.day , hour , 00, 00)
                rec.write({'check_out':auto_check_out , 'close_auto':True})
            except:
                auto_check_out = rec.check_in + timedelta(hours=4)
                rec.write({'check_out':auto_check_out , 'close_auto':True})
    
    @api.model
    def closing_records_attendance_morning(self):
        
        rows_no_check_out = self.env['hr.attendance'].search([
                                    ('check_out', '=' , False),
                                    # ('employee_id.worktime_type' , '=' , 'morning_shift')
                                    ])
        for rec in rows_no_check_out:
            ICPSudo = rec.env['ir.config_parameter'].sudo()
            hour = int(ICPSudo.get_param('custom_features.time_check_out_auto'))
            hour = hour - 3
            try:
                auto_check_out = datetime(rec.check_in.year, rec.check_in.month, rec.check_in.day , hour , 00, 00)
                rec.write({'check_out':auto_check_out , 'close_auto':True})
            except:
                auto_check_out = datetime.now()
                rec.write({'check_out':auto_check_out , 'close_auto':True})
                
    @api.model
    def calucate_time_between_projects(self):
        records_attendance = self.env['hr.attendance'].search([])
        for record in records_attendance:
            for rec in record:
                if rec.check_in:
                    ICPSudo = rec.env['ir.config_parameter'].sudo()
                    time_unknown = ICPSudo.get_param('custom_features.time_between_points_unknown')
                    year = int(rec.check_in.strftime('%Y'))
                    month = int(rec.check_in.strftime('%m'))
                    day = int(rec.check_in.strftime('%d'))
                    
                    start_date = datetime(year, month, day, 0, 0, 0)

                    last_attendance = rec.env['hr.attendance'].search([
                                                                    ('employee_id','=',rec.employee_id.id),
                                                                    ('check_in' , '>=' , start_date),
                                                                    ('check_in' , '<' , rec.check_in),
                    ],limit=1)
                    
                    if last_attendance and last_attendance.check_out:
                        delta = rec.check_in - last_attendance.check_out
                        rec.transfer_time_actual = delta.total_seconds() / 60.0
                        project_from = last_attendance.project_check_in.id
                        project_to = rec.project_check_in.id
                        
                        if project_from and project_to:
                            time_project = rec.env['project.time'].search(["|",
                                                                                "&",
                                                                                    ["from_project","=",project_from],
                                                                                    ["to_project","=",project_to],
                                                                                "&",
                                                                                    ["from_project","=",project_to],
                                                                                    ["to_project","=",project_from]
                                                                                ],limit=1)
                    
                            if len(time_project) == 1:
                                rec.transfer_time = time_project.time 

                            else:
                                rec.transfer_time =  time_unknown
                        else:
                            rec.transfer_time =  time_unknown  
                    else:
                        rec.transfer_time = 0
                        rec.transfer_time_actual = 0
    
class hr_attendance_stat(models.Model):
    _name = "employee.attendance.stat"
    _description = 'Statistical data about employee attendance'
    _rec_name = 'employee_id'
    _order = "create_date desc"
    
    employee_id = fields.Many2one('hr.employee' , string="Employee")
    employee_number = fields.Char(string='Employee Number' , related="employee_id.barcode")
    month = fields.Char(string='Month')
    num_hours_month = fields.Float(string="Monthly Hours" , default=0)
    total_hours_worked = fields.Float(string="Attendance Hours")
    overtime_hours = fields.Float(string="OT Hours" ,compute="_compute_overtime")
    total_days_absent = fields.Integer(string="Absent Days")
    under_overtime = fields.Float(string = "UOT" , compute="_compute_under_overtime")
    paid_leave_days = fields.Float(string="Paid Leave")
    paid_payroll_hours = fields.Float(string="Payroll Hours")
    unpaid_leave = fields.Float(string="Un-paid Leave")
    common_leave = fields.Integer(string="Common Leave")
    friday_per_month = fields.Integer(string="Friday Per Month")
    friday_worker_month = fields.Integer(string="Friday Working in Month")
    friday_working_hours = fields.Float(string="Friday Working Hours")
    attendnace_days = fields.Integer(string="Attendance Days")
    total_month_days = fields.Integer(string="Total Month Days", compute="_compute_month_days")
    
    @api.depends('attendnace_days','common_leave','paid_leave_days')
    def _compute_month_days(self):
        for rec in self:
            friday_days = rec.friday_worker_month + rec.friday_per_month 
            leaves_days = rec.paid_leave_days + rec.common_leave + rec.unpaid_leave
            rec.total_month_days = rec.attendnace_days + friday_days + leaves_days + rec.total_days_absent
            return

    def count_days_of_day_in_month(self , year, month, day):
        """
            Returns the number of days of a specific day in a specific month.
            Args:
            - year (int): Year as a four-digit integer.
            - month (int): Month as an integer (1-12).
            - day (int): Day of the week as an integer (0-6, where 0 is Monday and 6 is Sunday).

            Returns:
            - The number of days of the given day in the given month as an integer.
        """
        num_days = 0
        cal = calendar.monthcalendar(year, month)
        for week in cal:
            if week[day] != 0:
                num_days += 1
        return num_days
           
    def get_required_working_hours(self, day ,calender_emp):
        attendance = calender_emp.attendance_ids
        week_day = day.strftime('%w')
        H_MO , H_TH = 0 , 0 
                
        for rec in attendance:
            if rec.dayofweek == '0':
                H_MO = rec
            elif rec.dayofweek == '3':
                H_TH = rec
                        
        working_time = {
            'MO': float(H_MO.hour_to - H_MO.hour_from),
            'TH': float(H_TH.hour_to - H_TH.hour_from),
        } 
        if week_day == '4':
            return working_time['TH']
        elif week_day == '5':
            return 0
        else:
            return working_time['MO']
    
    @api.depends('total_hours_worked')
    def _compute_under_overtime(self):
        for rec in self:
            UOT = rec.num_hours_month - rec.total_hours_worked
            rec.under_overtime = 0 if UOT < 0 else UOT
    
    @api.depends('total_hours_worked')
    def _compute_overtime(self):
        for rec in self:
            OT = rec.total_hours_worked - rec.num_hours_month
            rec.overtime_hours = 0 if OT < 0 else OT
    
    def get_dates_between(self,start_date , end_date):
        date_list = []
        current_date = start_date
        
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
            
        return date_list

    def count_fridays(self, year, month):
        friday_count = 0
        day = date(year, month, 1)

        while day.month == month:
            if day.weekday() == 4:
                friday_count += 1
            day += timedelta(days=1)

        return friday_count
    
    @api.model
    def update_employee_attendance_stats(self):
        employees = self.env['hr.employee'].search([])
        
        # Get current month
        today_date = datetime.now()
        current_month = today_date.strftime('%B %Y')
        
        for employee in employees:
            
            # Check if a record already exists for the current month
            existing_record = self.search([('employee_id', '=', employee.id), ('month', '=', current_month)])
            calender_emp = employee.resource_calendar_id

            if not existing_record:
                # Create a new record for the employee for the current month
                record = self.create({
                    'employee_id': employee.id,
                    'month': current_month,
                    'total_hours_worked': 0,
                    'num_hours_month' : 0, 
                    'overtime_hours': 0,
                    'total_days_absent': 0,
                    'friday_per_month' :self.count_fridays(today_date.year, today_date.month) , 
                    'friday_worker_month' : 0 ,
                })
            
            current_date = date(today_date.year,today_date.month, today_date.day)
            
            required_hours_today = self.get_required_working_hours(current_date , calender_emp)

            record['num_hours_month'] += required_hours_today
            attendance = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', current_date),
                ('check_in', '<', current_date + timedelta(days=1)),
            ])
            
            # Calucate State to Employees
            if len(attendance) > 0:
                if current_date.strftime('%w') == '5':
                    record['friday_worker_month'] += 1
                    record['friday_per_month'] -= 1
                else:
                    record['attendnace_days'] += 1
                    
                for entry in attendance:
                    if entry.check_in.strftime('%w') == '5':
                        record['friday_working_hours'] += entry.net_hours
                    else:
                        record['total_hours_worked'] += entry.net_hours
                        record['paid_payroll_hours'] += entry.net_hours 
                
            if current_date.strftime('%w') != '5':
                self.compute_paid_leave_days( record , current_date , employee , required_hours_today ,len(attendance))    
    
                
            current_date = current_date + timedelta(days=1) 
    
    @api.model
    def create_employee_attendance_pervious_month(self):
        date_from = datetime(2023,7,1)
        date_end  = datetime(2023,7,31)
        employees = self.env['hr.employee'].search([])
        
        # Get current month
        current_month = date_from.strftime('%B %Y')
        
        for employee in employees:
            # Check if a record already exists for the current month
            existing_record = self.search([('employee_id', '=', employee.id), ('month', '=', current_month)])
            calender_emp = employee.resource_calendar_id

            if not existing_record:
                # Create a new record for the employee for the current month
                record = self.create({
                    'employee_id': employee.id,
                    'month': current_month,
                    'total_hours_worked': 0,
                    'num_hours_month' : 0, 
                    'overtime_hours': 0,
                    'total_days_absent': 0,
                    'friday_per_month' :self.count_fridays(date_from.year, date_from.month) , 
                    'friday_worker_month' : 0 ,
                    'attendnace_days' : 0 ,
                })
            
            current_date = date_from
            while(current_date <= date_end):                    
                required_hours_today = self.get_required_working_hours(current_date , calender_emp)

                record['num_hours_month'] += required_hours_today
                attendance = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', current_date),
                    ('check_in', '<', current_date + timedelta(days=1)),
                ])
                
                if len(attendance) > 0:
                    if current_date.strftime('%w') == '5':
                        record['friday_worker_month'] += 1
                        record['friday_per_month'] -= 1
                    else:
                        record['attendnace_days'] += 1
                    
                    for entry in attendance:
                        if entry.check_in.strftime('%w') == '5':
                            record['friday_working_hours'] += entry.net_hours
                        else:
                            record['total_hours_worked'] += entry.net_hours
                            record['paid_payroll_hours'] += entry.net_hours

                    
                if current_date.strftime('%w') != '5':
                    self.compute_paid_leave_days( record , current_date , employee , required_hours_today ,len(attendance))    
                    
                current_date = current_date + timedelta(days=1) 
                
    def compute_paid_leave_days(self, record, date, employee, required_hours_today , len_attendance):
        """
            Update record with paid leave days, payroll hours, Common Leave, and total days absent 
            
            Args:
                record (obj): Target record to update.
                date (datetime): Date to consider for leave.
                employee (obj): Employee object.
                required_hours_today (float): Required hours for a single day.
        """    
        leave = self.env['hr.leave']
        
        leave_criteria = [
            ('employee_id', '=' , employee.id),
            ('request_date_to' , '>=' , date),
            ('holiday_status_id.name', '!=', 'unpaid_leave'),
            ('state' , '=', 'validate'),
        ]
        
        unpaid_leave_criteria = [
            ('employee_id', '=' , employee.id),
            ('request_date_to' , '>=' , date),
            ('holiday_status_id.name', '=', 'unpaid_leave'),
            ('state' , '=', 'validate'),
        ]
        
        paid_records = leave.search(leave_criteria)
        unpaid_records = leave.search(unpaid_leave_criteria)
        
        if isinstance(date, datetime):
            date = date.date()
        # check Number of days Paid Leave Only 
        for leave_record in paid_records:
            date_range = self.get_dates_between(leave_record.request_date_from, leave_record.request_date_to)
            
            # اذا الموظف حضر في يوم إجازته يتم خصم اليوم من ايام الحضور لانه اجازة 
            if date in date_range and len_attendance > 0:
                record['attendnace_days'] -= 1
            
            if date in date_range:
                # Check if the day is Therday to calucate Friday 
                if date.strftime('%w') == '4':
                    friday_date = date + timedelta(days=1)
                    if friday_date in date_range:
                        if leave_record.holiday_status_id.name in ['annual_leave', 'sick_leave', 'compensatory_days']:
                            record['paid_leave_days'] += 1
                            record['friday_per_month'] -= 1
                        
                # Check if the day off is common to all employees or No 
                if leave_record.holiday_status_id.is_common:
                    record['common_leave'] += 1
                    record['paid_payroll_hours'] += required_hours_today
                    record['num_hours_month'] -= required_hours_today
                    return
                else:
                    record['paid_leave_days'] += 1
                    record['paid_payroll_hours'] += required_hours_today
                    record['num_hours_month'] -= required_hours_today
                    return
            
            
        # Check Number of days to Unpaid Leave Only 
        for leave_record in unpaid_records:
    
            date_range = self.get_dates_between(leave_record.request_date_from, leave_record.request_date_to)
            
            if date in date_range and len_attendance > 0:
                record['attendnace_days'] -= 1
                
            if date.strftime('%w') == '4':
                friday_date = date + timedelta(days=1)
                if friday_date in date_range:
                    record['unpaid_leave'] += 1
                    record['friday_per_month'] -= 1
                    
            if date in date_range:
                record['unpaid_leave'] += 1
                record['num_hours_month'] -= required_hours_today
                return
            
        if len_attendance == 0:    
            record['total_days_absent'] +=1

    @api.model
    def validate_data_attendance(self):
        for record in self:
            record['total_hours_worked'] = 0
            record['paid_payroll_hours'] = 0
            record['total_days_absent'] = 0
            record['paid_leave_days'] = 0
            record['num_hours_month'] = 0
            month = record.month
            input_date = datetime.strptime(month , '%B %Y')
            
            date_from = input_date.replace(day=1)
            date_to = (date_from  + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            
            date_today = datetime.now()
            
            if date_today >  date_to:
                date_to = date_to
            else:
                date_to = date_today
            
            
            current_date = date_from
            while(current_date <= date_to):
                calender_emp = record.employee_id.resource_calendar_id
                required_hours_today = self.get_required_working_hours(current_date, calender_emp)
                record['num_hours_month'] += required_hours_today
                attendance = self.env['hr.attendance'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('check_in', '>=', current_date),
                    ('check_in', '<', current_date + timedelta(days=1)),
                ])
                # Get Leave to Employee
                # self.compute_paid_leave_days( rec , current_date , rec.employee_id)
            
                if len(attendance) > 0:
                    for entry in attendance:
                        record['total_hours_worked'] += entry.net_hours
                        record['paid_payroll_hours'] += entry.net_hours

                    
                if current_date.strftime('%w') != '5':
                    self.compute_paid_leave_days(record , current_date , record.employee_id , required_hours_today ,len(attendance))
                current_date = current_date + timedelta(days=1) 
        
class attendance_daily_stat(models.Model):
    _name = 'attendance.daily.stat'
    _description = "Daily Attendance Stats"
    
    employee_id = fields.Many2one('hr.employee' , string="Employee")
    date = fields.Date(string="Date")
    required_hours = fields.Float(string="Daily Required Hours")
    under_overtime = fields.Float(string="UOT")
    overtime = fields.Float(string="OT")
    net_hours = fields.Float(string="Net Hours")
    net_hours_str = fields.Char(string="Net Hours Start", compute="_float_to_hours_minutes", store=True)
    
    def get_required_working_hours(self, day ,calender_emp):
        attendance = calender_emp.attendance_ids
        week_day = day.strftime('%w')
        H_MO , H_TH = 0 , 0 
                
        for rec in attendance:
            if rec.dayofweek == '0':
                H_MO = rec
            elif rec.dayofweek == '3':
                H_TH = rec
                        
        working_time = {
            'MO': float(H_MO.hour_to - H_MO.hour_from),
            'TH': float(H_TH.hour_to - H_TH.hour_from),
        } 
        if week_day == '4':
            return working_time['TH']
        elif week_day == '5':
            return 0
        else:
            return working_time['MO']
    
    @api.model
    def _update_attendance_daily_stat(self):
        employees = self.env['hr.employee'].search([])
        
        for rec in employees:
            calender_emp = rec.resource_calendar_id
            datetime_today = datetime.now()
            date_today = date(datetime_today.year, datetime_today.month, datetime_today.day )
            req_daily_hours = self.get_required_working_hours(calender_emp, date_today)
            
            record = self.create({
                'employee_id': rec.id,
                'date': datetime.now(),
                'required_hours': 0,
                'under_overtime' : 0, 
                'overtime': 0,
                'net_hours': 0
            })
    
    @api.depends('net_hours')
    def _float_to_hours_minutes(self):
        for rec in self:
            hours = int(rec.net_hours)
            minutes = int((rec.net_hours - hours) * 60)
            time_str = f"{hours}:{minutes}" 
            rec.net_hours_str = time_str