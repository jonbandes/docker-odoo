# AI_LOG — shop_integration_api

## Herramientas
- Claude Sonnet 4.6 (Claude Code CLI)

## Prompts clave

1. **"¿Cómo valido una API key de Odoo 17 (res.users.apikeys) desde un controlador con auth='none'?"**
   - Me explicó el mecanismo de `crypt()` de pgcrypto. Generó el SQL directo. Lo usé con verificación previa en la documentación de Odoo 17.

2. **"Diseña un mecanismo de Idempotency-Key para POST /api/v1/orders"**
   - Propuso un modelo ORM completo. Lo simplifiqué para usar una tabla directa con constraint UNIQUE porque el modelo ORM añadiría overhead innecesario para un índice de caché.

3. **"¿Cómo se calcula qty_available en batch sin N+1 queries en Odoo?"**
   - Explicó correctamente que `product.product._compute_quantities()` hace batch. Añadí la prueba `test_stock_computed_in_batch` para demostrarlo documentalmente.

## Lo que la IA hizo mal

- En la primera versión del controlador, usó `type='json'` en el decorador `@http.route`. Eso hace que Odoo espere un cuerpo JSON de RPC, no REST puro. Lo cambié a `type='http'` con parsing manual.
- Propuso manejar los reintentos del webhook dentro del mismo request de validación de entrega. Incorrecto: bloquearía al usuario. Lo cambié a encolar y procesar con cron.

## Lo que escribí yo sin IA

- La decisión de crear cotización (draft) en vez de pedido confirmado — una decisión de negocio que no tiene respuesta obvia y que documenté como supuesto.
- El cálculo de `body_hash` para la idempotencia usando `sort_keys=True` para garantizar que `{"a":1,"b":2}` y `{"b":2,"a":1}` sean iguales.
