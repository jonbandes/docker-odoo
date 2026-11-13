# payment_request — Solicitudes de Pago con Aprobación

## Versión de Odoo
**Odoo 17**

## Tramos completados
- **Tramo A ✓** — Modelo, grupos, vistas, reglas de registro, flujo completo
- **Tramo B ✓** — Niveles de aprobación configurables, actividad en envío, wizard de rechazo con motivo, wizard de pago, reporte PDF QWeb

## Supuestos y preguntas al cliente

### Preguntas que le haría a Carolina Méndez (Distribuidora Andina C.A.)

1. **¿Cuáles son los montos exactos que definen "pago normal" vs. "pago grande"?**
   Sin estos umbrales no puedo configurar los niveles de aprobación correctamente.
   *Supuesto asumido:* cualquier monto puede ser configurado en la pantalla "Niveles de Aprobación" sin necesidad de cambiar código.

2. **¿El jefe de área aprueba para cualquier monto o solo hasta cierto tope?**
   El correo dice "pagos normales los aprueba el jefe del área, pero los grandes los aprueba gerencia". ¿Coexisten? ¿El jefe aprueba hasta X y gerencia aprueba lo que supera X?
   *Supuesto asumido:* la regla es: el nivel con `amount_min` más alto que sea ≤ al monto de la solicitud es quien aprueba.

3. **¿Puede el empleado ver todas las solicitudes de su departamento o solo las suyas?**
   El correo no lo menciona.
   *Supuesto asumido:* el empleado solo ve las suyas.

4. **¿La moneda de registro siempre es bolívares (VES) o se manejan varias monedas?**
   El correo menciona que "muchos proveedores facturan en dólares pero les pagamos en bolívares". Esto implica conversión de tasa en el momento del pago.
   *Supuesto asumido (Tramo A/B):* la solicitud puede tener cualquier moneda; el diario de pago en el wizard puede ser en otra moneda (Odoo maneja la conversión via `account.payment`). La lógica multi-moneda avanzada (tasa fija por día) está en el Tramo C del enunciado.

5. **¿Las aprobaciones son por compañía o globales?**
   Si hay varias compañías (casas matrices o filiales), los niveles y solicitudes deberían estar separadas.
   *Supuesto asumido:* una sola compañía para Tramo A/B. Multi-compañía se menciona en Tramo C.

6. **¿Qué usuario es "jefe del área"?** ¿Es un usuario específico o un rol genérico?
   *Supuesto asumido:* Tesorería configura los niveles y asigna manualmente qué usuario es el aprobador de cada rango.

### Supuestos técnicos

- El modelo es `payment.request`, separado de `account.payment` para no interferir con el flujo contable nativo hasta que se confirme el pago.
- El wizard de pago crea y confirma un `account.payment` de tipo `outbound` (pago a proveedor) vinculado a la solicitud.
- Una solicitud pagada no tiene botón de retroceso (es estado terminal).
- El PDF incluye espacio para tres firmas físicas (solicitante, aprobador, tesorería) pensado para la carpeta del proveedor.

## Cómo probarlo

```bash
./odoo test -d prueba_limpia -m payment_request
```

Prueba manual del flujo completo:
1. Crear usuario Solicitante y asignarle grupo "Solicitante"
2. Crear usuario Aprobador con grupo "Aprobador"
3. Configurar un nivel de aprobación (Configuración → Niveles de Aprobación)
4. Con el Solicitante: crear solicitud → Enviar para aprobación
5. Con el Aprobador: revisar solicitud → Aprobar (o Rechazar con motivo)
6. Con Tesorería: Registrar Pago → verificar que crea account.payment
7. Imprimir solicitud (botón Imprimir) → PDF con datos de aprobación
