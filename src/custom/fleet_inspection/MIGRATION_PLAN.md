# MIGRATION_PLAN — fleet_inspection 17.0.1.0.0 → 17.0.2.0.0

**Escenario:** actualización en producción de un cliente con datos existentes.  
**Cambio:** `vehicle_type` (Selection) → `vehicle_type_id` (Many2one a catálogo).

---

## 0. Pre-requisitos

- Acceso al servidor Odoo de producción (SSH o panel de administración).
- Acceso directo a la base de datos PostgreSQL (para verificaciones).
- Respaldo disponible y verificado (ver paso 1).
- Ventana de mantenimiento acordada con el cliente (recomendado: sábado a las 8:00 a.m. antes de apertura).

---

## 1. Respaldo

```bash
# En el servidor de producción:
pg_dump -U odoo -Fc <nombre_base> > backup_fleetinspection_$(date +%Y%m%d_%H%M%S).dump

# Verificar que el dump no está vacío:
ls -lh backup_fleetinspection_*.dump

# Copiar a almacenamiento externo:
scp backup_fleetinspection_*.dump usuario@backup-server:/backups/
```

---

## 2. Verificación previa (antes de actualizar)

```sql
-- Cuántas inspecciones hay y cómo están distribuidas por tipo:
SELECT vehicle_type, COUNT(*) AS total
  FROM fleet_inspection
 GROUP BY vehicle_type
 ORDER BY total DESC;

-- Hay alguna inspección sin tipo? (no debería si el campo es required)
SELECT COUNT(*) FROM fleet_inspection WHERE vehicle_type IS NULL OR vehicle_type = '';

-- Guardar el resultado para comparación posterior:
-- Anotar los conteos por tipo para validar la migración.
```

**Criterio de paso:** ninguna inspección sin tipo, conteos registrados.

---

## 3. Ejecución de la actualización

```bash
# 1. Poner Odoo en modo mantenimiento (desde la UI: Ajustes → Modo mantenimiento)
#    o detener el servicio:
sudo systemctl stop odoo

# 2. Actualizar el código en el servidor:
cd /opt/odoo/custom-addons
git pull origin master   # o copiar los archivos manualmente

# 3. Actualizar el módulo (esto ejecuta el script post_migrate.py):
./odoo -u fleet_inspection -d <nombre_base> --stop-after-init

# 4. Revisar los logs para confirmar que el script de migración corrió sin errores:
grep "fleet_inspection migrate" /var/log/odoo/odoo.log | tail -20
```

**Qué buscar en el log:**
```
fleet_inspection migrate: creado tipo "Carro" (code=car)   ← solo en primera ejecución
fleet_inspection migrate: 45 inspección(es) actualizadas para tipo "Carro"
fleet_inspection migrate: todas las inspecciones tienen vehicle_type_id.
```

---

## 4. Verificación posterior

```sql
-- Comprobar que el catálogo se creó:
SELECT code, name FROM fleet_inspection_vehicle_type ORDER BY sequence;
-- Debe devolver: moto, car, truck, other (y sus nombres en español)

-- Comprobar que TODAS las inspecciones tienen tipo asignado:
SELECT COUNT(*) FROM fleet_inspection WHERE vehicle_type_id IS NULL;
-- Debe devolver: 0

-- Comparar conteos con la verificación previa:
SELECT vt.code, vt.name, COUNT(fi.id) AS total
  FROM fleet_inspection_vehicle_type vt
  LEFT JOIN fleet_inspection fi ON fi.vehicle_type_id = vt.id
 GROUP BY vt.code, vt.name
 ORDER BY total DESC;
-- Los totales deben coincidir con los del paso 2.
```

**Criterio de paso:** 0 inspecciones sin tipo, conteos idénticos a los del paso 2.

---

## 5. Reversión (si algo falla)

**Escenario A — el script de migración falló a mitad:**
```bash
# Restaurar el backup:
sudo systemctl stop odoo
dropdb <nombre_base>
pg_restore -U odoo -d <nombre_base> backup_fleetinspection_*.dump
# Revertir el código a la versión anterior:
git checkout 906a62d  # commit de la versión 17.0.1.0.0
sudo systemctl start odoo
```

**Escenario B — la migración terminó pero los datos no son correctos:**
```bash
# El script es idempotente: se puede correr de nuevo.
# Si los tipos son incorrectos, corregirlos en el catálogo UI
# y volver a ejecutar el UPDATE del script manualmente.
```

**Tiempo estimado de reversión:** 10-15 minutos (depende del tamaño de la base).

---

## Notas adicionales

- El campo `vehicle_type` (columna) queda en la BD como huérfana. No interfiere con Odoo y no se recomienda borrarlo para mantener la opción de reversión.
- El script de migración es idempotente: se puede correr dos veces sin riesgo.
- Para bases con más de 10.000 inspecciones, el `UPDATE` SQL del script corre por tipo (4 queries) y no tiene bucle Python, por lo que el consumo de memoria es constante.
