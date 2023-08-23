# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'RMS Custom',
    'version': '1.0',
    'summary': 'RMS Custom Module',
    'depends': ['web','base','hr','project', 'hr_attendance', 'hr_holidays'],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Views
        'views/project.xml',
        'views/attendance.xml',
        'views/employee.xml',
        'views/time_project_view.xml',
        'views/leave.xml',      






        'views/attendance_config.xml',
        'views/attendance_stats.xml',
        'views/attendance_daily_stats.xml',
        # Data
        'data/work_entry_types.xml',
        'data/cron_job.xml',
        'data/server_action.xml',
    ],
    'demo': [
    ],
    'css': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
