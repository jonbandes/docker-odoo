# sale_commission — Comisiones de Ventas

## Versión de Odoo
**Odoo 17**

## Tramos completados (Ejercicio 3)
- **Tramo A ✓** — Bug reproducido, causa raíz identificada, corrección mínima, prueba que falla/pasa
- **Tramo B ✓** — Contención, commit identificado, pasos de despliegue, mensaje al cliente
- **Tramo C ✓** — Script SQL de solo lectura, plan de corrección de datos, propuesta de prevención

## Estado actual en esta rama (master)
⚠️ Esta rama contiene el bug activo (commit d410c68). La corrección está en `hotfix/T-200`.

## Cómo probarlo

```bash
# Prueba que FALLA en esta rama (master, con bug):
./odoo test -d prueba_limpia -m sale_commission
# test_salesperson_can_confirm_order falla con UserError

# Prueba que PASA en hotfix/T-200:
git checkout hotfix/T-200
./odoo test -d prueba_limpia -m sale_commission
# Todos los tests pasan
```

## Funcionalidad del módulo

- Campo `commission_rate` (%) en cada usuario vendedor
- En cada línea de pedido se calcula `commission_rate` y `commission_amount` automáticamente
- Reporte de comisiones (menú Ventas → Comisiones), solo visible para gestores
- Grupo `group_sale_commission_manager`: gestiona tasas y ve reportes (no confirma pedidos)

## Supuestos y limitaciones

- La comisión se calcula sobre el subtotal antes de impuestos.
- El reporte usa una vista de las líneas de pedido agrupada; en producción con volumen alto se recomendaría un modelo analítico dedicado.
- Ver `INCIDENT.md` en la rama `hotfix/T-200` para el análisis completo del incidente.
