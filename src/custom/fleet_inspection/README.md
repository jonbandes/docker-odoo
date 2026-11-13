# fleet_inspection — Inspecciones de Vehículos

## Versión de Odoo
**Odoo 17**

## Tramos completados
- **Tramo A ✓** — Migración completa de Odoo 16 a 17
- **Tramo B ✓** — `vehicle_type` convertido a catálogo `many2one` con script de migración

## Tabla de cambios de migración (Odoo 16 → 17)

| Qué cambió | Por qué | Cómo se resolvió |
|---|---|---|
| `attrs="{'invisible': [...]}"` en vistas | Deprecated en Odoo 17; lanza `DeprecationWarning` y se eliminará en 18 | Reemplazado por `invisible="expresión"` en cada campo y botón |
| `states="draft"` en botones | Mismo motivo que `attrs` | Reemplazado por `invisible="state != 'draft'"` |
| Manifiesto `version: 16.0.1.0.0` | La versión debe reflejar la versión de Odoo compatible | Actualizado a `17.0.1.0.0` |
| `vehicle_type` Selection → `vehicle_type_id` Many2one | Tramo B: catálogo extensible sin cambiar código | Nuevo modelo `fleet.inspection.vehicle.type`, datos semilla en XML, script en `migrations/17.0.2.0.0/post_migrate.py` |
| Nueva entrada en `ir.model.access.csv` | El nuevo modelo necesita permisos | Agregadas dos líneas: lectura para todos y escritura/borrado para gestores |
| `category_id` en grupos: `base.module_category_field_service` → `base.module_category_fleet` | `field_service` no existe en Odoo 17 (es un módulo separado); `fleet` sí | Reemplazado en `security/security.xml` |

## Cómo probarlo

```bash
# Tramo A
./odoo test -d prueba_limpia -m fleet_inspection

# Tramo B: simula la migración
# 1. Instala 17.0.1.0.0
# 2. Crea inspecciones con tipos variados
# 3. Actualiza el módulo (versión 17.0.2.0.0):
./odoo -u fleet_inspection -d prueba_limpia
# Verifica que todas las inspecciones tienen vehicle_type_id asignado
```

## Supuestos y limitaciones

- Se asume que el módulo `fleet` de Odoo 17 está instalado.
- El campo `vehicle_type` (selección) se mantiene en la base de datos como columna huérfana después de la migración; Odoo no lo borra. No se propone borrarlo para no comprometer reversibilidad.
- El tipo "Otro" se conserva con `code='other'` para no perder información en inspecciones existentes.
