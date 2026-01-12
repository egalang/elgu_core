# from odoo import http


# class ElguCore(http.Controller):
#     @http.route('/elgu_core/elgu_core', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/elgu_core/elgu_core/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('elgu_core.listing', {
#             'root': '/elgu_core/elgu_core',
#             'objects': http.request.env['elgu_core.elgu_core'].search([]),
#         })

#     @http.route('/elgu_core/elgu_core/objects/<model("elgu_core.elgu_core"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('elgu_core.object', {
#             'object': obj
#         })

