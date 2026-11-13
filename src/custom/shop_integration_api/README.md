# shop_integration_api — Integración API Tienda en Línea

## Versión de Odoo
**Odoo 17**

## Tramos completados
- **Tramo A ✓** — GET /api/v1/products con filtros y auth de sesión
- **Tramo B ✓** — Bearer token (API keys nativas), POST /api/v1/orders, log de llamadas
- **Tramo C ✓** — Paginación con metadatos, Idempotency-Key, webhook asíncrono en entrega

## Endpoints

### GET /api/v1/products

**Autenticación:** sesión de Odoo (Tramo A) o `Authorization: Bearer <api_key>` (Tramo B+)

**Parámetros opcionales:**
| Parámetro | Tipo | Descripción |
|---|---|---|
| `category_id` | int | ID de categoría (incluye subcategorías) |
| `in_stock` | bool (`1`/`true`) | Solo productos con stock disponible > 0 |
| `modified_since` | string ISO 8601 | Solo productos modificados desde esa fecha |
| `page` | int | Número de página (default: 1) |
| `page_size` | int | Tamaño de página (default: 20, max: 100) |

**Respuesta 200:**
```json
{
  "products": [
    {"id": 5, "default_code": "PROD-001", "name": "Producto X", "lst_price": 100.0, "qty_available": 50.0}
  ],
  "meta": {"total": 150, "page": 1, "page_size": 20, "next": "/api/v1/products?page=2&page_size=20"}
}
```

**Respuesta 400 (fecha inválida):**
```json
{"error": {"code": "INVALID_DATE", "field": "modified_since", "message": "Formato de fecha inválido..."}}
```

### POST /api/v1/orders

**Autenticación:** `Authorization: Bearer <api_key>` (obligatorio)  
**Cabecera opcional:** `Idempotency-Key: <string>` para prevenir duplicados

**Cuerpo:**
```json
{
  "vat": "J-12345678-9",
  "external_ref": "SHOP-ORDER-456",
  "lines": [
    {"default_code": "PROD-001", "qty": 3}
  ]
}
```

**Respuesta 201:**
```json
{"order_id": 42, "order_name": "S00042", "state": "draft", "partner": "Cliente SA", "lines_count": 1}
```

**Códigos de error:**
| Código | HTTP | Descripción |
|---|---|---|
| `UNAUTHORIZED` | 401 | Sin Bearer token o token inválido |
| `MISSING_FIELD` | 422 | Campo requerido faltante |
| `PARTNER_NOT_FOUND` | 422 | No existe cliente con ese RIF |
| `PRODUCT_NOT_FOUND` | 422 | No existe producto con ese código |
| `INVALID_VALUE` | 422 | Cantidad ≤ 0 |
| `IDEMPOTENCY_CONFLICT` | 409 | Misma clave, contenido diferente |

## Supuestos y limitaciones

1. **El pedido se crea como cotización (draft):** la confirmación la hace el equipo de ventas internamente. Esto evita comprometer stock automáticamente desde integraciones externas.
2. **RIF = campo `vat` de `res.partner`:** se asume que el RIF venezolano se almacena en ese campo estándar.
3. **Stock calculado en batch:** `product.product.qty_available` en Odoo se computa mediante una única consulta para todos los productos del recordset (ver `product.product._compute_quantities()`). No hay N+1.
4. **Webhook asíncrono:** se encola y un `ir.cron` lo envía cada 5 minutos. El usuario que valida la entrega no queda bloqueado si la tienda no responde.
5. **pgcrypto requerido:** la validación de API keys usa `crypt()` de PostgreSQL. Esta extensión viene incluida en la imagen Docker oficial de Odoo.

## Cómo probarlo

```bash
# Pruebas unitarias (lógica de negocio)
./odoo test -d prueba_limpia -m shop_integration_api

# Prueba manual del GET (con sesión):
curl -b cookies.txt "http://localhost:8069/api/v1/products?in_stock=1"

# Prueba manual del POST (con API key):
curl -X POST http://localhost:8069/api/v1/orders \
  -H "Authorization: Bearer <tu_api_key>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-001" \
  -d '{"vat":"J-12345678-9","external_ref":"EXT-001","lines":[{"default_code":"PROD-001","qty":2}]}'
```
