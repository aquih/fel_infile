# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
import json
from datetime import datetime
import pytz
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
            if company.token_cui and datetime.now(pytz.timezone('America/Guatemala')) < datetime.fromisoformat(json.loads(company.token_cui).get('fecha_de_vencimiento')):
                token = json.loads(company.token_cui).get('token')
            else:
                result_token_generado = self._generar_token(company)                
                if result_token_generado.get('mensaje', {}): #NO se obtuvo token nuevo, retorna solo el mensaje
                    return result_token_generado
                else: 
                    token = result_token_generado['token']
            
            headers = { "Authorization": f"Bearer {token}" }
            data = {
                "cui": cui,
            }
            r = requests.post('https://certificador.feel.com.gt/api/v2/servicios/externos/cui', data=data, headers=headers)
            logging.warning(r.text)
            if r is not None and r.json():
                new_r = r.json()
                new_r['mensaje'] = new_r.get('descripcion')
                return new_r
        return {'nombre': '', 'cui': '', 'mensaje': "No se pudo obtener el CUI."}
    
    def _generar_token(self, company):
        data_token = {
            "prefijo": company.usuario_fel,
            "llave": company.clave_fel,
        }
        r_token = requests.post('https://certificador.feel.com.gt/api/v2/servicios/externos/login', data=data_token)
        logging.warning(r_token.text)
        if r_token is not None and r_token.json():
            if r_token.json()['resultado'] == False:
                return {'mensaje':r_token.json()['descripcion']} 
            else:
                company.token_cui = json.dumps(r_token.json())
                return r_token.json()
        else:
            return {'mensaje': "No se pudo obtener el token de autenticación para CUI."}
            
