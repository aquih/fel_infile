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
            logging.info(r.text)

            if r:
                try:
                    response = r.json()
                    return {
                        'nombre': response.get('nombre'), 
                        'nit': response.get('nit'), 
                        'mensaje': response.get('mensaje')
                    }
                except Exception as e:
                    logging.warning(f"Error al procesar json: {e}")
                    return {
                        'nombre': '', 
                        'nit': '', 
                        'mensaje': 'No se pudo procesar la respuesta json.'
                    }
        return {'nombre': '', 'nit': '', 'mensaje': ''}

    def _datos_sat_cui(self, company, cui):
        if cui:
            token = ''
            if company.token_cui:
                token_cui = json.loads(company.token_cui)
                vencimiento_token = token_cui.get('fecha_de_vencimiento')
                ahora = datetime.now(pytz.timezone('America/Guatemala'))
                if ahora < datetime.fromisoformat(vencimiento_token):
                    token = token_cui.get('token')
    
            if not token:
                result_token_generado = self._generar_token(company)             
                if result_token_generado.get('mensaje', {}):
                    return {
                        'nombre': '', 
                        'nit': '', 
                        'mensaje': result_token_generado.get('mensaje', {})
                    } 
                else: 
                    token = result_token_generado['token']
            
            headers = { "Authorization": f"Bearer {token}" }
            data = {
                "cui": cui,
            }
            r = requests.post('https://certificador.feel.com.gt/api/v2/servicios/externos/cui', data=data, headers=headers)
            logging.info(r.text)

            if r is not None:
                try:
                    response = r.json()
                    if response.get('cui', {}) and response.get('cui', {}).get('nombre') != 'NA':
                        return {
                            'nombre': response['cui']['nombre'],
                            'nit': response['cui']['cui'],
                            'mensaje': ''
                        }
                    else:
                        return {
                            'nombre': '',
                            'nit': '',
                            'mensaje': response.get('descripcion', 'No se encontró descripción')
                        }
                except Exception as e:
                    logging.warning(f"Error al procesar json: {e}")
                    return {
                        'nombre': '', 
                        'nit': '', 
                        'mensaje': 'No se pudo procesar la respuesta json.'
                        } 
        return {'nombre': '', 'nit': '', 'mensaje': "No se pudo obtener el CUI."}
    
    def _generar_token(self, company):
        data_token = {
            "prefijo": company.usuario_fel,
            "llave": company.clave_fel,
        }
        r_token = requests.post('https://certificador.feel.com.gt/api/v2/servicios/externos/login', data=data_token)
        logging.info(r_token.text)

        if r_token is not None:
            try:
                token_response = r_token.json()
                if token_response.get('resultado') is False:
                    return {
                        'token': '',
                        'mensaje': token_response.get('descripcion', 'Sin descripción')
                    }
                else:
                    company.token_cui = json.dumps(token_response)
                    return {
                        'token': token_response.get('token', ''),
                        'mensaje': token_response.get('descripcion', '')
                    }
            except Exception as e:
                logging.warning(f"Error al procesar json: {e}")
                return {
                    'token': '',
                    'mensaje': 'No se pudo procesar la respuesta json.'
                }
        return {'token': '', 'mensaje': "No se pudo obtener el token de autenticación para CUI."}
            
