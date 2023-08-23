from odoo import api, fields, models, _

class Project(models.Model):
    _inherit = 'project.project'

    radius = fields.Float(string="Radius")
    longitude = fields.Float(string="Longitude")
    latitude = fields.Float(string="Latitude")
    