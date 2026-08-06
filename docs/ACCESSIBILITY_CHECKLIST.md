# Checklist de accesibilidad y respuesta — IUS-Razón

## Navegación y estructura

- [ ] Existe un único encabezado principal visible.
- [ ] El enlace para saltar al contenido recibe foco.
- [ ] Área y sección tienen etiquetas visibles.
- [ ] El orden de tabulación coincide con el orden visual.
- [ ] Ningún control requiere exclusivamente ratón.

## Foco y controles

- [ ] El foco es visible en botones, enlaces, campos y selectores.
- [ ] Los controles principales alcanzan 44 px de altura.
- [ ] Los botones comunican una acción concreta.
- [ ] Los errores aparecen junto al flujo que los produjo.
- [ ] Las operaciones largas muestran estado de carga.

## Contenido

- [ ] Los encabezados siguen una jerarquía comprensible.
- [ ] Las instrucciones no dependen solo del color.
- [ ] Las tablas permiten desplazamiento interno.
- [ ] Los valores sensibles no aparecen en mensajes ni logs.
- [ ] El modo público oculta rutas y bloquea cargas.

## Diseño responsivo

- [ ] 360 px: una columna y sin desbordamiento global.
- [ ] 768 px: formularios legibles y controles táctiles.
- [ ] 1024 px: navegación y contenido equilibrados.
- [ ] 1440 px: contenido limitado a un ancho legible.
- [ ] La orientación y el zoom no bloquean acciones.

## Movimiento y rendimiento

- [ ] `prefers-reduced-motion` reduce transiciones.
- [ ] Solo se renderiza la vista activa.
- [ ] Los logs de tiempo no contienen datos jurídicos.
- [ ] Una vista lenta genera advertencia técnica.
- [ ] No se introducen llamadas externas al cambiar de sección.
