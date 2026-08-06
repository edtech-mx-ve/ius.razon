# Reporte técnico — Sprint 2 de IUS-Razón

## Versión

`0.2.0`

## Objetivo

Extender el núcleo fáctico y probatorio de Sprint 1 con la capa de investigación jurídica:
problemas jurídicos, normas, jurisprudencia, doctrina y relaciones explicadas entre preguntas
y fuentes.

## Incremento funcional

### Problemas jurídicos

Cada problema registra:

- código automático `PJ-###`;
- título;
- pregunta;
- delimitación;
- estado;
- marcas temporales.

### Normas

Cada norma registra:

- código `N-###`;
- jurisdicción y materia;
- instrumento y artículo;
- texto;
- jerarquía;
- publicación;
- vigencia inicial y final;
- versión o reforma;
- referencia y notas;
- documento y SHA-256 opcionales.

### Jurisprudencia

Cada precedente registra:

- código `J-###`;
- órgano e identificador;
- jurisdicción, materia y fecha;
- hechos relevantes;
- problema jurídico;
- criterio;
- decisión;
- normas interpretadas;
- carácter declarado;
- similitudes y diferencias;
- documento y SHA-256 opcionales.

### Doctrina

Cada fuente doctrinal registra:

- código `D-###`;
- autor, obra, edición y año;
- concepto;
- síntesis;
- fragmento o paráfrasis;
- referencia bibliográfica;
- función argumentativa;
- ubicación;
- documento y SHA-256 opcionales.

### Matriz problema–fuente

La matriz registra:

- problema;
- tipo y fuente;
- orientación;
- razón de aplicabilidad;
- notas.

El vínculo es único por problema, tipo y fuente. Un registro repetido actualiza la evaluación
sin duplicar la relación.

## Persistencia y migración

El cambio es aditivo mediante `CREATE TABLE IF NOT EXISTS`. Las tablas nuevas son:

```text
legal_issues
norms
jurisprudence
doctrine
issue_source_links
```

No se modifica el formato de las tablas de Sprint 1. Se verificó una migración real desde una
base v0.1.2: el expediente previo continuó disponible.

## Seguridad

- límites de tamaño;
- lista de extensiones permitidas;
- saneamiento de nombres;
- almacenamiento con UUID;
- SHA-256;
- verificación de pertenencia al expediente;
- variables de entorno para configuración;
- auditoría sin contenido jurídico sensible.

## Pruebas ejecutadas

- flujo completo de Sprint 1;
- validación de modelos;
- integridad referencial;
- persistencia de ruta;
- respaldo;
- creación de tres tipos de fuente;
- documentos asociados;
- matriz problema–fuente;
- rechazo de vínculos entre expedientes;
- rechazo de vigencia invertida.

Resultado:

```text
12 passed
```

## Criterios de aceptación

- [x] conservar datos de Sprint 1;
- [x] registrar problemas jurídicos;
- [x] registrar normas;
- [x] registrar jurisprudencia;
- [x] registrar doctrina;
- [x] asociar documentos;
- [x] controlar versión y vigencia normativa;
- [x] vincular fuentes a problemas;
- [x] explicar aplicabilidad;
- [x] evitar vínculos entre expedientes;
- [x] auditar operaciones;
- [x] ejecutar pruebas automatizadas.

## Limitaciones

La aplicación organiza fuentes declaradas por el usuario. No confirma que un texto sea oficial,
vigente, obligatorio o aplicable. Tampoco genera aún una conclusión jurídica.
