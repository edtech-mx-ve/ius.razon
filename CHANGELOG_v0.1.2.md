# Changelog v0.1.2

## Corrección crítica de persistencia

- Se conserva la ubicación de la base activa en `.ius_razon_persistence.json`.
- Se detectan bases existentes dentro de `data*` y se prioriza la que contiene expedientes.
- Si se define `IUS_RAZON_DB_PATH`, el directorio de datos se deriva de su carpeta.
- La interfaz muestra la ruta absoluta de SQLite y el directorio de datos.
- Se crea un respaldo consistente de SQLite al iniciar y se conservan diez copias.
- Se añadieron pruebas para recuperación de ruta, descubrimiento de base previa y respaldo.
- No se modificó el esquema de datos.

## Causa corregida

Las variables de entorno de PowerShell son temporales. Al cerrar la terminal, la aplicación
volvía a `data/ius_razon.db`, por lo que una base usada previamente en `data_test` parecía
haber desaparecido. Los datos no se eliminaban; se estaba abriendo otra base.
