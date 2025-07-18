import logging
from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    util.records.remove_view(cr, xml_id="fel_infile.fel_infile_view_move_form")
    util.records.remove_view(cr, xml_id="fel_infile.journal_form_fel_infile")
    util.records.remove_view(cr, xml_id="fel_infile.view_company_form_fel_infile")
    util.records.remove_view(cr, xml_id="fel_infile.view_partner_form_fel_infile")
    _logger.info("Vistas viejas borradas")
