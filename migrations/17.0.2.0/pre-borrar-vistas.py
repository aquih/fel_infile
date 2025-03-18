import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("delete from ir_ui_view where id in (select res_id from ir_model_data where module = 'fel_infile' and model = 'ir.ui.view') and type in ('form', 'tree');")
    _logger.info("Vistas viejas borradas")