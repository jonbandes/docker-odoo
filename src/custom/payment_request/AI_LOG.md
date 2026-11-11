# AI_LOG — payment_request

## Herramientas
- Claude Sonnet 4.6 (Claude Code CLI)

## Prompts clave

1. **"Lee el correo de Carolina Méndez como un consultor. ¿Qué falta en el requerimiento?"**
   - Identificó: umbrales de monto no definidos, rol de 'jefe del área' ambiguo, pregunta de multi-moneda implícita. Usé esto para redactar la sección de supuestos en el README.

2. **"Diseña el modelo de aprobación por niveles más simple posible"**
   - Propuso un modelo con `threshold_amount` y `approver_group_id`. Lo simplifiqué: uso directamente `approver_id` (un usuario concreto) en lugar de un grupo, porque la pregunta al cliente #6 no tiene respuesta y es más simple de configurar.

3. **"¿Cómo garantizo que el solicitante no apruebe aunque no haya nivel configurado?"**
   - Generó correctamente la verificación de `has_group` como fallback cuando `approver_id` no está asignado.

## Lo que la IA hizo mal

- En el primer borrador del reporte QWeb, generó código con `t-esc` donde debería ser `t-field` y viceversa. Los corregí consultando la documentación de Odoo QWeb.
- Propuso usar `account.move` directamente en lugar de `account.payment`. Para un pago de proveedor en Odoo 17, `account.payment` es el modelo correcto y genera la `account.move` internamente.

## Lo que escribí yo sin IA

- La sección "Preguntas al cliente" — es criterio de negocio, no técnico. La IA genera preguntas genéricas; yo identifiqué las dos más críticas para el cliente: los umbrales de monto y la definición de "jefe del área".
- La decisión de hacer el pago en el wizard (en vez de directamente en el modelo) para poder manejar la selección del diario en la UI.
