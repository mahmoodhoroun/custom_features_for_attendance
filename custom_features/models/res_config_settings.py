from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    
    time_between_unknown = fields.Float(string="Travel time between two unknown points (Minutes)" ,  config_parameter="custom_features.time_between_points_unknown" , default=100)
    auto_check_out_close = fields.Integer(string="Hour Close Check out" , default=22 , config_parameter="custom_features.time_check_out_auto")
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.sale_double_validation = 'two_step' if self.sale_order_approval else 'one_step'
