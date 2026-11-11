# Prueba Técnica — Desarrollador Odoo · Binaural · 2026-Q4

## Versión de Odoo declarada
**Odoo 17**

## Módulos entregados

| Ejercicio | Módulo | Tramos | Estado |
|---|---|---|---|
| 1 — Integración API tienda en línea | `shop_integration_api` | A, B, C | ✅ |
| 2 — Migración módulo inspecciones | `fleet_inspection` | A, B | ✅ |
| 3 — Ticket urgente T-200 | `sale_commission` | A, B, C | ✅ (ver rama `hotfix/T-200`) |
| 4 — Solicitudes de pago | `payment_request` | A, B | ✅ |

## Ramas

- **`master`**: código de los 4 módulos. Para `sale_commission`, contiene el bug activo (simula el estado de producción al momento del incidente).
- **`hotfix/T-200`**: corrección del bug T-200 en `sale_commission`. Esta rama es el PR de corrección urgente.

## Cómo instalar

```bash
# Clonar y configurar entorno Docker (basado en binaural-dev/docker-odoo)
git clone <este-repo>
cp .env.example .env
# Editar .env → ODOO_VERSION=17.0
docker compose up -d

# Instalar los módulos
./odoo -i shop_integration_api,fleet_inspection,sale_commission,payment_request -d prueba_limpia
```

## Cómo ejecutar todas las pruebas

```bash
./odoo test -d prueba_limpia \
  -m shop_integration_api,fleet_inspection,sale_commission,payment_request
```

> **Nota T-200:** ejecutar las pruebas en `master` mostrará un fallo esperado en `sale_commission::test_salesperson_can_confirm_order` (que demuestra el bug). Para ver el verde completo, cambia a la rama `hotfix/T-200`.

## Resumen de decisiones clave

### Ejercicio 1 — shop_integration_api
- El pedido se crea como **cotización** (no confirmado). La confirmación queda a cargo del equipo de ventas. Ver README del módulo para justificación.
- El stock se calcula en **batch** (N=1 queries para N productos) usando el mecanismo nativo de Odoo.
- El webhook de entrega es **asíncrono** (cola + cron), para no bloquear al usuario que valida la entrega.

### Ejercicio 2 — fleet_inspection
- El campo `vehicle_type` viejo (Selection) **no se borra** de la BD para preservar reversibilidad. Queda como columna huérfana.
- El script de migración es **idempotente**: se puede correr dos veces sin dañar nada.
- Se usó un campo `code` en `fleet.inspection.vehicle.type` para garantizar que la migración sea robusta ante cambios de traducción del `name`.

### Ejercicio 3 — sale_commission
- **Cambio mínimo**: se eliminó solo el override de `action_confirm`. Sin reescribir el módulo.
- **Contención**: otorgar temporalmente el grupo al usuario, no tocar código.
- Ver `INCIDENT.md` en `hotfix/T-200` para el análisis completo.

### Ejercicio 4 — payment_request
- Los niveles de aprobación son **configurables por UI** (sin cambiar código), lo que responde a la pregunta implícita de Carolina sobre los umbrales.
- El pago crea un `account.payment` vinculado; no se duplica si se llama dos veces.
- Ver README del módulo para las 6 preguntas que haría al cliente antes de continuar.

## Lista de verificación (sección 8 del enunciado)

- [x] Los módulos instalan juntos en una base nueva
- [x] El comando de pruebas termina sin errores (excepto el fallo intencional de T-200 en `master`)
- [x] Versión de Odoo declarada en este README (Odoo 17)
- [x] Cada módulo tiene `README.md` y `AI_LOG.md`
- [x] Ejercicio 1: formato de error y códigos HTTP documentados
- [x] Ejercicio 2: tabla de cambios de versión en `fleet_inspection/README.md`
- [x] Ejercicio 3: `INCIDENT.md` y PR de la rama `hotfix/T-200`
- [x] Ejercicio 4: sección "Supuestos y preguntas al cliente" en `payment_request/README.md`
- [x] Historial de commits con prefijos (`[FEAT]`, `[FIX]`, `[MIG]`, `[TEST]`, `[DOC]`)
- [x] Sin datos reales, contraseñas ni claves en el repositorio
