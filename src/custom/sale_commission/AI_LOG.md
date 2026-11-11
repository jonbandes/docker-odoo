# AI_LOG — sale_commission

## Herramientas
- Claude Sonnet 4.6 (Claude Code CLI)

## Prompts clave

1. **"Diseña el bug más realista que rompa la confirmación de pedidos solo para vendedores (no managers)"**
   - Propuso varias opciones: access rule, constraint en campo, override de método. Elegí el override con `has_group` por ser el más claro para demostrar en una prueba y el más reconocible en revisión de código.

2. **"Escribe el INCIDENT.md con secciones A, B y C del ejercicio"**
   - Generó una estructura sólida. Ajusté el tono del mensaje al cliente (lo simplifiqué) y añadí la referencia al script SQL.

3. **"¿El script SQL de impacto modifica datos?"**
   - Confirmó que solo tiene `SELECT`. Verifiqué manualmente.

## Lo que la IA hizo mal

- En el primer borrador del mensaje al cliente usó jerga técnica ("override", "commit"). Reescrito en lenguaje administrativo.
- Propuso `git bisect --first-parent`, flag no universal. Reemplazado con bisect básico.

## Lo que escribí yo sin IA

- La decisión final de qué bug elegir (ver arriba) basada en experiencia real con Odoo.
- La verificación de que el SQL es de solo lectura.
