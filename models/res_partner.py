# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round

import requests

import logging

class Partner(models.Model):
    _inherit = 'res.partner'

    def obtener_nombre_facturacion_fel(self):
        vat = self.vat
        if self.nit_facturacion_fel:
            vat = self.nit_facturacion_fel
            
        res = self._datos_sat(self.env.company, vat)
        self.nombre_facturacion_fel = res['nombre']
    
    def _datos_sat(self, company, vat):
        if vat:
            headers = { "Content-Type": "application/json" }
            data = {
                "emisor_codigo": company.usuario_fel,
                "emisor_clave": company.clave_fel,
                "nit_consulta": vat.replace('-',''),
            }
            r = requests.post('https://consultareceptores.feel.com.gt/rest/action', json=data, headers=headers)
            logging.warning(r.text)
            if r and r.json():
                return r.json()
                
        return {'nombre': '', 'nit': ''}

    def _datos_sat_cui(self, company, cui):
        if cui:
            data_token = {
                "prefijo": company.usuario_fel,
                "llave": company.clave_fel,
            }
            r_token = requests.post('https://certificador.feel.com.gt/api/v2/servicios/externos/login', data=data_token)
            logging.warning(r_token.text)
            if r_token and r_token.json():
                if r_token.json()['resultado'] == False:
                    return r_token.json()
                else:
                    token = r_token.json()['token']
                    headers = { "Authorization": f"Bearer {token}" }
                    data = {
                        "cui": cui,
                    }
                    r = requests.post('https://certificador.feel.com.gt/api/v2/servicios/externos/cui', data=data, headers=headers)
                    logging.warning(r.text)
                    if r and r.json():
                        return r.json()
        return {'nombre': '', 'cui': ''}
