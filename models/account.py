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
        facturas_a_certificar = self.filtered(lambda f: f.requiere_certificacion('infile'))
        diarios_sin_error_en_historial = self.filtered(lambda f: not f.journal_id.error_en_historial_fel)
        
        if len(facturas_a_certificar) > 1 and len(diarios_sin_error_en_historial) > 0:
            raise ValidationError('No se puede certificar más de una factura si no esta activa la opción de "Error FEL en historial" todos los diarios.')

        for factura in facturas_a_certificar:
            factura.error_pre_validacion()

            if factura.company_id.buscar_nombre_para_dte_fel and not factura.partner_id.nombre_facturacion_fel:
                factura.partner_id.nombre_facturacion_fel = factura.partner_id.obtener_datos_facturacion_fel(factura.partner_id.vat)['nombre']
            
            dte = factura.dte_documento()
            xmls = etree.tostring(dte, encoding="utf-8", xml_declaration=True)
            _logger.info(xmls)
            xmls_base64 = base64.b64encode(xmls)
            
            identificador = factura.journal_id.code+'-'+str(factura.id)
            if factura.uuid_pos_fel:
                identificador = factura.uuid_pos_fel

            headers = { 
                "UsuarioFirma": factura.company_id.usuario_fel,
                "LlaveFirma": factura.company_id.token_firma_fel,
                "UsuarioApi": factura.company_id.usuario_fel,
                "LlaveApi": factura.company_id.clave_fel,
                "identificador": identificador,
                "Content-Type": "application/xml",
            }
            _logger.info(headers)

            r = requests.post('https://certificador.feel.com.gt/fel/procesounificado/transaccion/v2/xml', data=xmls, headers=headers)
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
                
                xmls = etree.tostring(dte, encoding="utf-8", xml_declaration=True)
                _logger.info(xmls)

                identificador = factura.journal_id.code+'-'+str(factura.id)
                if factura.uuid_pos_fel:
                    identificador = factura.uuid_pos_fel

                headers = { 
                    "UsuarioFirma": factura.company_id.usuario_fel,
                    "LlaveFirma": factura.company_id.token_firma_fel,
                    "UsuarioApi": factura.company_id.usuario_fel,
                    "LlaveApi": factura.company_id.clave_fel,
                    "identificador": identificador,
                    "Content-Type": "application/xml",
                }
                _logger.info(headers)
                
                r = requests.post('https://certificador.feel.com.gt/fel/procesounificado/transaccion/v2/xml', data=xmls, headers=headers)
                _logger.info(r.text)
                resultado_json = r.json()

                if not resultado_json["resultado"]:
                    raise UserError(str(resultado_json["descripcion_errores"]))
        
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
