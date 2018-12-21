# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError        
    
class TablasAntiguedadesLine(models.Model):
    _name = 'tablas.antiguedades.line'

    form_id = fields.Many2one('tablas.cfdi', string='Vacaciones y aguinaldos', required=True) 
    antiguedad = fields.Float('Antigüedad/Años') 
    vacaciones = fields.Float('Vacaciones/Días') 
    prima_vac = fields.Float('Prima vacacional (%)')
    aguinaldo = fields.Float('Aguinaldo/Días')

class TablasGeneralLine(models.Model):
    _name = 'tablas.general.line'

    form_id = fields.Many2one('tablas.cfdi', string='ISR Mensual Art. 113 LISR', required=True) 
    lim_inf = fields.Float('Límite inferior') 
    c_fija = fields.Float('Cuota fija') 
    s_excedente = fields.Float('Sobre excedente (%)')

class TablasSubsidiolLine(models.Model):
    _name = 'tablas.subsidio.line'

    form_id = fields.Many2one('tablas.cfdi', string='Subem mensual/CAS Mensual', required=True) 
    lim_inf = fields.Float('Límite inferior') 
    s_mensual = fields.Float('Subsidio mensual')

class TablasSubsidio2lLine(models.Model):
    _name = 'tablas.subsidio2.line'

    form_id = fields.Many2one('tablas.cfdi', string='Subsidio Mensual Art. 114 LISR', required=True) 
    lim_inf = fields.Float('Límite inferior') 
    c_fija = fields.Float('Cuota fija') 
    s_imp_marginal = fields.Float('Sobre imp. marginal (%)')

class TablasSubsidioAcreditablelLine(models.Model):
    _name = 'tablas.subsidioacreditable.line'

    form_id = fields.Many2one('tablas.cfdi', string='Subsidio acreditable', required=True) 
    ano = fields.Float('Año') 
    s_mensual = fields.Float('Subsidio (%)')

class TablasCFDI(models.Model):
    _name = 'tablas.cfdi'
    
    name = fields.Char("Nombre")
    tabla_antiguedades = fields.One2many('tablas.antiguedades.line', 'form_id') 
    tabla_LISR = fields.One2many('tablas.general.line', 'form_id')
    tabla_subem = fields.One2many('tablas.subsidio.line', 'form_id')
    tabla_subsidio = fields.One2many('tablas.subsidio2.line', 'form_id')
    tabla_subsidio_acreditable = fields.One2many('tablas.subsidioacreditable.line', 'form_id')
    uma = fields.Float(string=_('UMA'), default='80.60')
    salario_minimo = fields.Float(string=_('Salario mínimo'))
    importe_utilidades = fields.Float(string=_('Importe a repartir a todos los empleados'), default=0)
    dias_min_trabajados = fields.Float(string=_('Dias mínimos trabajados en empleados eventuales'), default=60)
    funcion_ingresos = fields.Float(string=_('% a repartir en función de los ingresos'), default=50)
    funcion_dias = fields.Float(string=_('% a repartir en función de los días trabajados'), compute='_compute_funcion_dias', readonly=True)
    total_dias_trabajados = fields.Float(string=_('Total de días trabajados'), default=0)
    total_sueldo_percibido = fields.Float(string=_('Total de sueldo percibido'), default=0)
    factor_dias = fields.Float(string=_('Factor por dias trabajados'), compute='_factor_dias', readonly=True)
    factor_sueldo = fields.Float(string=_('Factor por sueldo percibido'), compute='_factor_sueldo', readonly=True)
    fecha_inicio = fields.Date('Fecha inicio')
    fecha_fin = fields.Date('Fecha fin')

    @api.one
    @api.constrains('name')
    def _check_name(self):
        if self.name:
            if self.search([('id', '!=', self.id),('name','=',self.name)]):
                raise ValidationError(_('Reference with same name already exist.'))
            
    @api.model
    def default_get(self,fields):
        res = super(TablasCFDI,self).default_get(fields)
        if 'name' in fields:
            res['name'] = self.env['ir.sequence'].next_by_code('tablas.cfdi.reference')
        return res

    @api.one
    @api.depends('funcion_ingresos')
    def _compute_funcion_dias(self):
        self.funcion_dias = 100 - self.funcion_ingresos

    @api.one
    @api.depends('total_dias_trabajados', 'total_sueldo_percibido')
    def _factor_dias(self):
        if self.total_dias_trabajados > 0:
            self.factor_dias = (self.importe_utilidades*(self.funcion_dias/100)) / self.total_dias_trabajados

    @api.one
    @api.depends('total_dias_trabajados', 'total_sueldo_percibido')
    def _factor_sueldo(self):
        if self.total_sueldo_percibido > 0:
            self.factor_sueldo = (self.importe_utilidades*(self.funcion_ingresos/100)) / self.total_sueldo_percibido

    def calcular_reparto_utilidades(self):
        payslips = self.env['hr.payslip'].search([('date_from', '>=', self.fecha_inicio), ('date_to', '<=', self.fecha_fin),('tipo_nomina','=', 'O')])
        work100_lines = payslips.mapped('worked_days_line_ids').filtered(lambda x:x.code=='WORK100')
        net_lines = payslips.mapped('line_ids').filtered(lambda x:x.code=='NET')
        
        total_dias_trabajados, total_sueldo_percibido = 0.0, 0.0
        
        total_dias_by_employee = {}
        total_sueldo_employee = {}
        for line in work100_lines:
            total_dias_trabajados += line.number_of_days
            if line.payslip_id.employee_id not in total_dias_by_employee:
                total_dias_by_employee.update({line.payslip_id.employee_id: 0.0})
            total_dias_by_employee[line.payslip_id.employee_id] += line.number_of_days
            
        for line in net_lines:
            total_sueldo_percibido += line.total
            if line.slip_id.employee_id not in total_sueldo_employee:
                total_sueldo_employee.update({line.slip_id.employee_id: 0.0})
            total_sueldo_employee[line.slip_id.employee_id] += line.total
        
        employees = list(set(list(total_dias_by_employee.keys())  + list(total_sueldo_employee.keys())))
        for employee in employees:
            employee.write({'dias_utilidad' : total_dias_by_employee.get(employee, 0.0), 'sueldo_utilidad' : total_sueldo_employee.get(employee,0.0)})
            
        self.write({'total_dias_trabajados': total_dias_trabajados, 'total_sueldo_percibido':total_sueldo_percibido})
        
        return True

    @api.multi
    def button_dummy(self):
        self.calcular_reparto_utilidades()
        return True