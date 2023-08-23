from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ProjectTime(models.Model):
    _name ="project.time"
    _description = 'Time taken to transfer between projects'
    
    from_project = fields.Many2one('project.project' , string="From Project")
    
    to_project = fields.Many2one('project.project' , string="To Project") 
    
    time = fields.Integer(string="Time Required (Minutes)" ,
                          help="Required Time to move from project to another") 
    
    @api.constrains('from_project', 'to_project')
    def _check_recurrence(self):
        records = self.env['project.time'].search(["|",
                                                        "&",
                                                            ["from_project","=",self.from_project.id],
                                                            ["to_project","=",self.to_project.id],
                                                        "&",
                                                            ["from_project","=",self.to_project.id],
                                                            ["to_project","=",self.from_project.id]
                                                        ])
        if len(records) >= 2:
                raise ValidationError("The time required to move between the two projects has already been entered")
        
            