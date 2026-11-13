# INCIDENT.md — T-200: Vendedores no pueden confirmar pedidos de venta

**Fecha:** viernes (hora pico de ventas)
**Severidad:** Crítica — bloquea el flujo principal de negocio
**Ticket:** T-200
**Módulo afectado:** `sale_commission` v17.0.1.1.0
**Rama de corrección:** `hotfix/T-200`

---

## Tramo A — Reproducción, causa raíz, corrección y prueba

### Cómo reproducir el bug

1. Instalar `sale_commission` (versión con el bug, rama `master-multi`).
2. Crear un usuario con grupo **Ventas / Usuario** (sin grupo `Gestor de Comisiones`).
3. Con ese usuario, crear un pedido de venta y hacer clic en **Confirmar**.
4. **Resultado:** `UserError: Solo el gestor de comisiones puede confirmar pedidos de venta. Contacte a su gerente.`
5. Con el usuario **administrador** o con un **Gestor de Comisiones**: el pedido se confirma sin error.

### Causa raíz

El commit `[FEAT] sale_commission: valida permiso de comisiones al confirmar pedido` introdujo un override de `SaleOrder.action_confirm` que exige `group_sale_commission_manager` antes de llamar a `super()`.

```python
# sale_commission/models/sale_order.py — versión con bug
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        if not self.env.user.has_group('sale_commission.group_sale_commission_manager'):
            raise UserError(_('Solo el gestor de comisiones puede confirmar pedidos...'))
        return super().action_confirm()
```

El error de diseño: el cálculo de comisiones es **automático y pasivo** (via `@api.depends` en `SaleOrderLine`). No requiere ninguna validación al confirmar. La intención del commit (garantizar que las comisiones estén configuradas) no necesitaba bloquear la confirmación; bastaba con que el campo `commission_rate` sea 0 si el usuario no tiene tasa.

### Corrección mínima

Eliminar el método `action_confirm` completo de `SaleOrder`. El módulo no necesita extender ese método.

```python
# sale_commission/models/sale_order.py — corregido
from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    # ... sin cambios
```

### Prueba que falla antes y pasa después

```python
# tests/test_sale_commission.py
def test_salesperson_can_confirm_order(self):
    """T-200: el vendedor (sin grupo gestor) debe poder confirmar pedidos."""
    order = self._create_order()
    order.with_user(self.salesperson).action_confirm()   # Falla en master, pasa en hotfix/T-200
    self.assertEqual(order.state, 'sale')
```

Ejecutar:
```bash
# Falla en master-multi:
git checkout master-multi
./odoo test -d prueba_limpia -m sale_commission
# FAIL: test_salesperson_can_confirm_order

# Pasa en hotfix/T-200:
git checkout hotfix/T-200
./odoo test -d prueba_limpia -m sale_commission
# OK: 5 tests passed
```

---

## Tramo B — Contención, comunicación y despliegue

### Contención inmediata (primeros 15 minutos)

**Opción elegida: el gerente confirma los pedidos urgentes manualmente** mientras llega el hotfix.

- Es reversible: el gerente solo ejecuta `action_confirm` sobre pedidos ya creados por los vendedores; no crea datos nuevos ni altera comisiones (el `user_id` del pedido sigue siendo el del vendedor que lo creó).
- Riesgo: el gerente podría confirmar pedidos que aún no están listos. Mitigación: pedirle que confirme solo los que el vendedor le indique explícitamente.
- **No se recomienda** otorgar temporalmente el grupo `Gestor de Comisiones` a todos los vendedores, porque ese grupo también da acceso al reporte de comisiones y a modificar tasas de otros usuarios.

### Commit que introdujo el error

```bash
git log --oneline | grep "valida permiso"
# c237eb9 [FEAT] sale_commission: valida permiso de comisiones al confirmar pedido
```

Identificado con `git log -S "action_confirm" src/custom/sale_commission/` o `git bisect` entre el último deploy correcto y el actual.

### Pasos de despliegue de la corrección

```bash
# 1. En el servidor, cambiar a la rama del hotfix
git fetch origin hotfix/T-200
git checkout hotfix/T-200

# 2. Actualizar el módulo (no hace falta migración: solo se elimina código Python)
./odoo update prueba-tecnica -d <base_produccion> -m sale_commission

# 3. Verificar en la interfaz: un vendedor confirma un pedido de prueba
# 4. Verificar en logs que no hay errores de importación del módulo
```

No hace falta reiniciar Odoo en modo mantenimiento: la actualización de un módulo que solo elimina un método Python es segura en caliente con `--dev=all` desactivado.

### Verificación post-despliegue

- Con un usuario vendedor (sin grupo gestor): crear pedido → confirmar → estado debe ser `sale`.
- Con el usuario gerente: confirmar también funciona (regresión).
- Revisar `mail.thread` del módulo: sin errores 500 en `/web#action=sale`.

### Mensaje al cliente (Comercial Los Andes C.A.)

> Buenas tardes. Identificamos la causa del error: una validación incorrecta que quedó activa por accidente en la actualización del mediodía impide que los vendedores confirmen pedidos. La corrección está lista y se puede desplegar en menos de 5 minutos sin bajar el sistema. Pueden proceder mañana con normalidad desde las 8:00 a.m. Lamentamos el inconveniente.

---

## Tramo C — Impacto en datos y prevención

### Datos potencialmente afectados

Desde el mediodía el gerente confirmó pedidos **en su nombre** (como usuario activo). Si alguno de esos pedidos quedó con `user_id = gerente` en lugar del vendedor real, la comisión calculada corresponde a la tasa del gerente, no a la del vendedor.

**Script de solo lectura para identificar casos:**

```sql
-- Pedidos confirmados hoy con user_id del gerente
-- donde el pedido fue creado originalmente por otro usuario.
-- Ajustar 'gerente@empresa.com' al login real del gerente.
SELECT
    so.name                         AS pedido,
    so.date_order                   AS fecha_confirmacion,
    rp.name                         AS cliente,
    ru.login                        AS confirmado_por,
    SUM(sol.commission_amount)      AS comision_calculada,
    so.id
FROM sale_order so
JOIN res_users ru ON ru.id = so.user_id
JOIN res_partner rp ON rp.id = so.partner_id
JOIN sale_order_line sol ON sol.order_id = so.id
WHERE so.state IN ('sale', 'done')
  AND so.date_order::date = CURRENT_DATE
  AND ru.login = 'gerente@empresa.com'   -- reemplazar por el login real
GROUP BY so.id, so.name, so.date_order, rp.name, ru.login
ORDER BY so.date_order DESC;
```

Si el resultado contiene pedidos, el plan de corrección es:
1. Consultar con el gerente qué vendedor debería ser `user_id` de cada pedido.
2. Actualizar `user_id` en `sale.order` → Odoo recalcula las comisiones automáticamente vía `@api.depends`.
3. Verificar que `commission_amount` en las líneas refleja la tasa correcta del vendedor.

### ¿El mismo patrón existe en otro lugar del módulo?

Revisado `sale_commission/models/sale_order.py`: el único override que existía era `action_confirm`. Eliminado. No hay otros puntos en el módulo que restrinjan métodos de ventas.

### Propuesta de prevención

1. **Regla de revisión de código:** cualquier override de métodos de workflow de Odoo (`action_confirm`, `action_done`, `action_cancel`) debe incluir una prueba que lo ejecute con un usuario de bajo privilegio. Esta prueba habría capturado el bug antes de llegar a producción.
2. **En el pipeline de CI:** agregar la suite de `sale_commission` al comando de prueba estándar del módulo antes de cada merge a `master`.
3. **En el proceso de deploy:** incluir en el checklist de actualización un paso de verificación manual: "confirmar un pedido con un usuario vendedor después de actualizar módulos de ventas".
