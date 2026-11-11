# AI_LOG — fleet_inspection

## Herramientas
- Claude Sonnet 4.6 (Claude Code CLI)

## Prompts clave

1. **"¿Qué cambios concretos hay entre Odoo 16 y 17 en las vistas XML?"**
   - Me listó: `attrs` → `invisible=/readonly=`, `states` en botones, `<tree>` se mantiene en 17 (pasa a `<list>` en 18+). Verifiqué en la documentación oficial antes de aplicar.

2. **"Escribe un script de migración idempotente para convertir un campo Selection a Many2one"**
   - Generó una versión que usaba `env.cr.execute` directamente sin el contexto `api.Environment`. La corregí para usar `api.Environment(cr, SUPERUSER_ID, {})` y poder acceder al ORM.

3. **"¿El script necesita pre-migrate o post-migrate?"**
   - Razonó correctamente: `post-migrate` porque necesita que el nuevo campo `vehicle_type_id` ya exista en la BD (lo crea el ORM al actualizar el módulo).

## Lo que la IA hizo mal

- Propuso borrar la columna `vehicle_type` vieja al final del script. Incorrecto: Odoo no gestiona drops de columnas en migraciones y hacerlo manualmente rompe la reversibilidad. Lo omití.
- En la primera versión de la vista, dejó `attrs` mezclado con `invisible=`. Lo unifiqué todo a la sintaxis de Odoo 17.

## Lo que escribí yo sin IA

- La decisión de usar `code` como campo separado en `fleet.inspection.vehicle.type` (en lugar de solo `name`) para garantizar la idempotencia del script de migración. Con solo `name` el script sería frágil a cambios de traducción.
- La verificación final que cuenta registros huérfanos y lanza un `_logger.warning`.
