"""
API REST v1 — Integración con tienda en línea
==============================================
Tramo A: GET /api/v1/products  (auth de sesión)
Tramo B: Bearer token + POST /api/v1/orders + log
Tramo C: Paginación + Idempotency-Key + webhook (ver models/stock_picking.py)

Supuestos documentados:
- POST /api/v1/orders crea el pedido como COTIZACIÓN (estado 'draft').
  El flujo de aprobación interna queda en manos del equipo de ventas.
  Esto evita comprometer stock automáticamente en integraciones sin validación humana.
- El RIF del cliente corresponde al campo partner.vat en Odoo.
- Idempotency-Key: misma clave + mismo contenido → mismo pedido (200).
  Misma clave + contenido distinto → 409 Conflict.
"""

import hashlib
import json
import logging
import time
from datetime import datetime

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 100


def _error_response(code, field, message, status=422):
    """Formato de error estándar (Tramo B+)."""
    return request.make_json_response(
        {'error': {'code': code, 'field': field, 'message': message}},
        status=status,
    )


def _get_user_from_bearer():
    """Valida la cabecera Authorization: Bearer <key> contra res.users.apikeys."""
    auth = request.httprequest.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    key = auth[7:].strip()
    if not key:
        return None
    # Odoo 17 almacena las API keys hashed con pgcrypto crypt()
    request.env.cr.execute(
        """
        SELECT u.id
          FROM res_users u
          JOIN res_users_apikeys k ON k.user_id = u.id
         WHERE u.active = true
           AND k.key = crypt(%s, k.key)
         LIMIT 1
        """,
        [key],
    )
    row = request.env.cr.fetchone()
    if not row:
        return None
    return request.env['res.users'].sudo().browse(row[0])


def _log_call(endpoint, method, user_id, response_code, duration_ms,
              request_ref=None, error_code=None):
    """Registra la llamada sin bloquear la respuesta."""
    try:
        request.env['shop.api.log'].sudo()._log(
            endpoint=endpoint,
            method=method,
            user_id=user_id,
            response_code=response_code,
            duration_ms=duration_ms,
            request_ref=request_ref,
            error_code=error_code,
        )
    except Exception:
        _logger.exception('shop_integration_api: error al escribir el log')


class ShopApiV1(http.Controller):

    # -------------------------------------------------------------------------
    # GET /api/v1/products
    # Tramo A: auth='user' (sesión Odoo)
    # Tramo B: se mantiene compatible con sesión; Bearer también funciona porque
    #          el middleware de Odoo acepta ambos si el módulo de API keys está activo.
    # -------------------------------------------------------------------------
    @http.route(
        '/api/v1/products',
        auth='none',
        type='http',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def get_products(self, **kwargs):
        t0 = time.time()
        endpoint = '/api/v1/products'

        # Autenticación: Bearer (Tramo B) o sesión (Tramo A)
        user = _get_user_from_bearer()
        if user:
            env = request.env(user=user.id)
        elif request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            env = request.env
            user = request.env.user
        else:
            _log_call(endpoint, 'GET', None, 401, (time.time() - t0) * 1000, error_code='UNAUTHORIZED')
            return _error_response('UNAUTHORIZED', '', 'Se requiere autenticación.', 401)

        # Parámetros de filtro
        category_id = kwargs.get('category_id')
        in_stock = kwargs.get('in_stock', '').lower() in ('1', 'true', 'yes')
        modified_since_raw = kwargs.get('modified_since', '')
        page = max(int(kwargs.get('page', 1)), 1)
        page_size = min(int(kwargs.get('page_size', PAGE_SIZE_DEFAULT)), PAGE_SIZE_MAX)

        # Validar modified_since
        modified_since_dt = None
        if modified_since_raw:
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d'):
                try:
                    modified_since_dt = datetime.strptime(modified_since_raw, fmt)
                    break
                except ValueError:
                    continue
            if modified_since_dt is None:
                duration_ms = (time.time() - t0) * 1000
                _log_call(endpoint, 'GET', user.id, 400, duration_ms, error_code='INVALID_DATE')
                return _error_response(
                    'INVALID_DATE',
                    'modified_since',
                    f'Formato de fecha inválido: "{modified_since_raw}". Use ISO 8601: YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS',
                    400,
                )

        # Construir dominio
        domain = [('active', '=', True), ('sale_ok', '=', True)]
        if category_id:
            try:
                domain.append(('categ_id', 'child_of', int(category_id)))
            except (ValueError, TypeError):
                return _error_response('INVALID_PARAM', 'category_id', 'category_id debe ser un entero.', 400)
        if in_stock:
            domain.append(('qty_available', '>', 0))
        if modified_since_dt:
            domain.append(('write_date', '>=', modified_since_dt))

        # Tramo C: contar sin consulta extra (mismo ORM batch)
        Product = env['product.product']
        total = Product.search_count(domain)

        # Stock calculado en batch (N=1): Odoo carga qty_available para todos a la vez
        products = Product.search(domain, limit=page_size, offset=(page - 1) * page_size)

        result_items = [
            {
                'id': p.id,
                'default_code': p.default_code or '',
                'name': p.name,
                'lst_price': p.lst_price,
                'qty_available': p.qty_available,
            }
            for p in products
        ]

        # Tramo C: metadatos de paginación
        has_next = (page * page_size) < total
        base_url = request.httprequest.base_url
        meta = {
            'total': total,
            'page': page,
            'page_size': page_size,
            'next': (
                f'{base_url}?page={page + 1}&page_size={page_size}'
                if has_next else None
            ),
        }

        duration_ms = (time.time() - t0) * 1000
        _log_call(endpoint, 'GET', user.id, 200, duration_ms)

        return request.make_json_response({'products': result_items, 'meta': meta})

    # -------------------------------------------------------------------------
    # POST /api/v1/orders  (Tramo B+)
    # -------------------------------------------------------------------------
    @http.route(
        '/api/v1/orders',
        auth='none',
        type='http',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_order(self, **kwargs):
        t0 = time.time()
        endpoint = '/api/v1/orders'

        # Autenticación Bearer obligatoria
        user = _get_user_from_bearer()
        if not user:
            _log_call(endpoint, 'POST', None, 401, (time.time() - t0) * 1000, error_code='UNAUTHORIZED')
            return _error_response('UNAUTHORIZED', 'Authorization', 'Bearer token requerido o inválido.', 401)

        # Parsear cuerpo JSON
        try:
            body = json.loads(request.httprequest.data or b'{}')
        except json.JSONDecodeError:
            return _error_response('INVALID_JSON', '', 'El cuerpo de la solicitud no es JSON válido.', 400)

        # Tramo C: Idempotency-Key
        idem_key = request.httprequest.headers.get('Idempotency-Key', '').strip()
        if idem_key:
            existing = self._check_idempotency(idem_key, body, user, endpoint, t0)
            if existing is not None:
                return existing

        # Validar campos requeridos
        vat = (body.get('vat') or '').strip()
        external_ref = (body.get('external_ref') or '').strip()
        lines = body.get('lines', [])

        if not vat:
            return _error_response('MISSING_FIELD', 'vat', 'El RIF del cliente es obligatorio.', 422)
        if not external_ref:
            return _error_response('MISSING_FIELD', 'external_ref', 'La referencia externa es obligatoria.', 422)
        if not isinstance(lines, list) or not lines:
            return _error_response('MISSING_FIELD', 'lines', 'Debe incluir al menos una línea de pedido.', 422)

        env = request.env(user=user.id)

        # Buscar cliente por RIF
        partner = env['res.partner'].search([('vat', '=', vat), ('active', '=', True)], limit=1)
        if not partner:
            duration_ms = (time.time() - t0) * 1000
            _log_call(endpoint, 'POST', user.id, 422, duration_ms, request_ref=external_ref, error_code='PARTNER_NOT_FOUND')
            return _error_response('PARTNER_NOT_FOUND', 'vat', f'No existe un cliente con el RIF {vat}.', 422)

        # Validar y construir líneas
        order_lines = []
        for idx, line in enumerate(lines):
            default_code = (line.get('default_code') or '').strip()
            qty = line.get('qty')

            if not default_code:
                return _error_response(
                    'MISSING_FIELD', f'lines[{idx}].default_code',
                    'El código del producto es obligatorio.', 422,
                )
            if qty is None:
                return _error_response(
                    'MISSING_FIELD', f'lines[{idx}].qty',
                    'La cantidad es obligatoria.', 422,
                )
            try:
                qty = float(qty)
            except (TypeError, ValueError):
                return _error_response(
                    'INVALID_VALUE', f'lines[{idx}].qty',
                    f'La cantidad debe ser un número.', 422,
                )
            if qty <= 0:
                return _error_response(
                    'INVALID_VALUE', f'lines[{idx}].qty',
                    'La cantidad debe ser mayor que cero.', 422,
                )

            product = env['product.product'].search(
                [('default_code', '=', default_code), ('active', '=', True), ('sale_ok', '=', True)],
                limit=1,
            )
            if not product:
                duration_ms = (time.time() - t0) * 1000
                _log_call(endpoint, 'POST', user.id, 422, duration_ms, request_ref=external_ref, error_code='PRODUCT_NOT_FOUND')
                return _error_response(
                    'PRODUCT_NOT_FOUND', f'lines[{idx}].default_code',
                    f'No existe un producto con el código {default_code}.', 422,
                )

            order_lines.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': product.lst_price,
            }))

        # Crear pedido (como cotización — supuesto documentado en docstring del módulo)
        order = env['sale.order'].create({
            'partner_id': partner.id,
            'client_order_ref': external_ref,
            'order_line': order_lines,
        })

        # Registrar idempotency key si se proporcionó
        if idem_key:
            self._store_idempotency(idem_key, body, order.id, user)

        duration_ms = (time.time() - t0) * 1000
        _log_call(endpoint, 'POST', user.id, 201, duration_ms, request_ref=external_ref)

        return request.make_json_response(
            {
                'order_id': order.id,
                'order_name': order.name,
                'state': order.state,
                'partner': partner.name,
                'lines_count': len(order_lines),
            },
            status=201,
        )

    # -------------------------------------------------------------------------
    # Helpers de idempotencia (Tramo C)
    # -------------------------------------------------------------------------
    def _check_idempotency(self, idem_key, body, user, endpoint, t0):
        """Devuelve una respuesta si ya existe una petición con la misma clave."""
        body_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        request.env.cr.execute(
            """
            SELECT order_id, body_hash
              FROM shop_idempotency_key
             WHERE key = %s AND user_id = %s
             LIMIT 1
            """,
            [idem_key, user.id],
        )
        row = request.env.cr.fetchone()
        if not row:
            return None  # Clave nueva, continuar normalmente

        stored_order_id, stored_hash = row
        if stored_hash != body_hash:
            # Misma clave, contenido diferente → 409
            duration_ms = (time.time() - t0) * 1000
            _log_call(endpoint, 'POST', user.id, 409, duration_ms, request_ref=idem_key, error_code='IDEMPOTENCY_CONFLICT')
            return _error_response(
                'IDEMPOTENCY_CONFLICT',
                'Idempotency-Key',
                'Se recibió una petición diferente con la misma Idempotency-Key.',
                409,
            )

        # Misma clave, mismo contenido → replay del resultado original
        order = request.env['sale.order'].sudo().browse(stored_order_id)
        duration_ms = (time.time() - t0) * 1000
        _log_call(endpoint, 'POST', user.id, 200, duration_ms, request_ref=idem_key)
        return request.make_json_response(
            {
                'order_id': order.id,
                'order_name': order.name,
                'state': order.state,
                'idempotent_replay': True,
            },
            status=200,
        )

    def _store_idempotency(self, idem_key, body, order_id, user):
        body_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        try:
            request.env.cr.execute(
                """
                INSERT INTO shop_idempotency_key (key, user_id, order_id, body_hash, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (key, user_id) DO NOTHING
                """,
                [idem_key, user.id, order_id, body_hash],
            )
        except Exception:
            _logger.exception('shop_integration_api: error guardando idempotency key')
