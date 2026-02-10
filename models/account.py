# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import base64
from lxml import etree
import requests

#from import XMLSigner

import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    pdf_fel = fields.Char('PDF FEL', copy=False)
    
    def _post(self, soft=True):
        self.certificar()
        return super()._post(soft)

    def certificar(self):
        if len(self) > 1 and not factura.journal_id.error_en_historial_fel:
            raise ValidationError('No se puede certificar más de una factura si no esta activa la opción de "Error FEL en historial" en el diario.')

        for factura in self:
            if factura.requiere_certificacion('infile'):
                factura.error_pre_validacion()

                if factura.company_id.buscar_nombre_para_dte_fel and not factura.partner_id.nombre_facturacion_fel:
                    factura.partner_id.nombre_facturacion_fel = factura.partner_id.obtener_datos_facturacion_fel(factura.company_id, factura.partner_id.vat)['nombre']
                
                dte = factura.dte_documento()
                xmls = etree.tostring(dte, encoding="UTF-8")
                _logger.info(xmls.decode("utf-8"))
                xmls_base64 = base64.b64encode(xmls)
                
                identificador = factura.journal_id.code+'-'+str(factura.id)
                if factura.uuid_pos_fel:
                    identificador = factura.uuid_pos_fel

                headers = { 
                    "UsuarioFirma": factura.company_id.usuario_fel,
                    "LlaveFirma": factura.company_id.token_firma_fel,
                    "UsuarioApi": factura.company_id.usuario_fel,
                    "LlaveApi": factura.company_id.clave_fel,
                    "identificador": identificador
                }
                data = xmls.decode("utf-8")
                _logger.info(data)
                r = requests.post('https://certificador.feel.com.gt/fel/procesounificado/transaccion/v2/xml', data=data, headers=headers)
                _logger.info(r.text)
                resultado_json = r.json()

                if resultado_json and "resultado" in resultado_json and resultado_json["resultado"]:
                    factura.firma_fel = resultado_json["uuid"]
                    factura.ref = str(resultado_json["serie"])+"-"+str(resultado_json["numero"])
                    factura.serie_fel = resultado_json["serie"]
                    factura.numero_fel = resultado_json["numero"]
                    factura.documento_xml_fel = xmls_base64
                    factura.resultado_xml_fel = resultado_json["xml_certificado"]
                    factura.pdf_fel = "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid="+resultado_json["uuid"]
                    factura.certificador_fel = "infile"
                else:
                    factura.error_certificador(str(resultado_json["descripcion_errores"])) 

        return True
        
    def button_cancel(self):
        result = super(AccountMove, self).button_cancel()

        for factura in self:
            if factura.requiere_certificacion() and factura.firma_fel:                    
                dte = factura.dte_anulacion()
                
                xmls = etree.tostring(dte, encoding="UTF-8")
                _logger.info(xmls.decode("utf-8"))

                identificador = factura.journal_id.code+'-'+str(factura.id)
                if factura.uuid_pos_fel:
                    identificador = factura.uuid_pos_fel

                headers = { 
                    "UsuarioFirma": factura.company_id.usuario_fel,
                    "LlaveFirma": factura.company_id.token_firma_fel,
                    "UsuarioApi": factura.company_id.usuario_fel,
                    "LlaveApi": factura.company_id.clave_fel,
                    "identificador": identificador
                }
                data = xmls.decode("utf-8")
                _logger.info(data)
                r = requests.post('https://certificador.feel.com.gt/fel/procesounificado/transaccion/v2/xml', data=data, headers=headers)
                _logger.info(r.text)
                resultado_json = r.json()

                if resultado_json and "resultado" in resultado_json and resultado_json["resultado"]:
                    factura.error_certificador(str(resultado_json["descripcion_errores"]))
                else:
                    factura.error_certificador(r.text)
        
        return result

class AccountJournal(models.Model):
    _inherit = "account.journal"

class ResCompany(models.Model):
    _inherit = "res.company"

    usuario_fel = fields.Char('Usuario FEL')
    clave_fel = fields.Char('Llave API FEL')
    token_firma_fel = fields.Char('Llave Firma FEL')
    certificador_fel = fields.Selection(selection_add=[('infile', 'Infile')])
    buscar_nombre_para_dte_fel = fields.Boolean('Buscar nombre en SAT para enviar al certificador')

class Partner(models.Model):
    _inherit = 'res.partner'
    
    def _datos_sat(self, company, vat):
        if vat:
            headers = { "Content-Type": "application/json" }
            data = {
                "emisor_codigo": company.usuario_fel,
                "emisor_clave": company.clave_fel,
                "nit_consulta": vat.replace('-',''),
            }
            r = requests.post('https://consultareceptores.feel.com.gt/rest/action', json=data, headers=headers)
            _logger.info(r.text)
            if r and r.json():
                return r.json()
                
        return {'nombre': '', 'nit': ''}
