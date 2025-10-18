# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
import json
from datetime import datetime
import pytz
import requests

import logging
_logger = logging.getLogger(__name__)

class Partner(models.Model):
    _inherit = 'res.partner'

    def guardar_nombre_facturacion_fel(self):
        vat = self.vat
        if self.nit_facturacion_fel:
            vat = self.nit_facturacion_fel
            
        res = self.obtener_datos_facturacion_fel(self.env.company, vat)
        self.nombre_facturacion_fel = res['nombre']

    def obtener_datos_facturacion_fel(self, company, vat):
        res = self._datos_sat(self.env.company, vat)
        if not res['nombre']:
            res = self._datos_sat_cui(self.env.company, vat)
        return res
    
    def _datos_sat(self, company, nit):
        headers = { "Content-Type": "application/json" }
        data = {
            "emisor_codigo": company.usuario_fel,
            "emisor_clave": company.clave_fel,
            "nit_consulta": (nit or '').replace('-',''),
        }
        resultado_certificador_json = requests.post('https://consultareceptores.feel.com.gt/rest/action', json=data, headers=headers)
        _logger.info(resultado_certificador_json.text)

        datos_contribuyente = { 'nombre': '', 'nit': '', 'mensaje': '' }

        try:
            resultado_certificador = resultado_certificador_json.json()

            datos_contribuyente['nombre'] = resultado_certificador.get('nombre')
            datos_contribuyente['nit'] = resultado_certificador.get('nit')
            datos_contribuyente['mensaje'] = resultado_certificador.get('mensaje')
        except Exception as e:
            _logger.info(e)
            datos_contribuyente['mensaje'] = e

        return datos_contribuyente

    def _datos_sat_cui(self, company, cui):
        token = self._obtener_token(company)
        headers = { "Authorization": f"Bearer {token['token']}" }
        data = {
            "cui": cui or '',
        }

        resultado_certificador_json = requests.post('https://certificador.feel.com.gt/api/v2/servicios/externos/cui', data=data, headers=headers)
        _logger.info(resultado_certificador_json.text)

        datos_contribuyente = { 'nombre': '', 'nit': '', 'mensaje': '' }

        try:
            resultado_certificador = resultado_certificador_json.json()
            resultado_certificador_cui = resultado_certificador.get('cui', {})

            if resultado_certificador_cui:
                datos_contribuyente['nombre'] = resultado_certificador_cui.get('nombre')
                datos_contribuyente['nit'] = resultado_certificador_cui.get('cui')
            else:
                datos_contribuyente['mensaje'] = resultado_certificador.get('descripcion')
        except Exception as e:
            _logger.info(e)
            datos_contribuyente['mensaje'] = e

        return datos_contribuyente
    
    def _obtener_token(self, company):
        datos_token = { 'token': '', 'mensaje': '' }
        
        if company.token_cui:
            token_cui = json.loads(company.token_cui)
            vencimiento_token = token_cui.get('fecha_de_vencimiento')
            ahora = datetime.now(pytz.timezone('America/Guatemala'))

            if ahora < datetime.fromisoformat(vencimiento_token):
                datos_token['token'] = token_cui.get('token')
            else:
                company.token_cui = ''

        # Si el token está vencido
        if not datos_token['token']:
            data_post = {
                "prefijo": company.usuario_fel,
                "llave": company.clave_fel,
            }
            resultado_certificador_json = requests.post('https://certificador.feel.com.gt/api/v2/servicios/externos/login', data=data_post)
            _logger.info(resultado_certificador_json.text)

            try:
                resultado_certificador = resultado_certificador_json.json()
                if resultado_certificador.get('resultado'):
                    datos_token['token'] = resultado_certificador.get('token', '')
                    datos_token['mensaje'] = resultado_certificador.get('descripcion', '')

                    company.token_cui = json.dumps(resultado_certificador)                    
            except Exception as e:
                datos_token['mensaje'] = e

        return datos_token
