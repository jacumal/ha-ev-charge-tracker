# Beta 9 — checklist de cierre

## Implementado en el repositorio
- [x] Selector limitado a modelos con imágenes realmente incluidas en la carpeta de galería.
- [x] Retirada del catálogo de 400 modelos y de su selector BEV/PHEV.
- [x] Opción **Vehículo genérico**.
- [x] Opción **Añadir una foto personal** como última opción.
- [x] Instrucciones visibles para preparar la imagen: vista exterior frontal tres cuartos, morro a la derecha, coche completo, centrado, transparencia real, PNG 1200 × 675 px, escala homogénea y puerto de carga visible si es posible.
- [x] Subida autenticada al Home Assistant local, sin servicios externos.
- [x] Límite de 8 MB y normalización de la imagen personal a PNG transparente 1200 × 675.
- [x] Imágenes personales con nombre basado en SHA-256 y ruta persistente en la carpeta www local.
- [x] Selección de imagen guardada por vehículo y compartida por sus perfiles de carga.
- [x] Restauración de la imagen predeterminada o limpieza de la imagen personal.
- [x] Recursos estáticos locales para la tarjeta, galería y catálogo reducido.
- [x] Pruebas automáticas de inventario, existencia de imágenes, transparencia, endpoint y rutas.
- [ ] Verificar y, cuando proceda, normalizar los 18 renders incluidos a un lienzo común de 1200 × 675 y escala visual uniforme.
- [ ] Confirmar la procedencia y derechos de redistribución de cada render suministrado antes de publicar la release.
- [ ] Revisar el ZIP HACS generado y comprobar que incluye todos los módulos y recursos.

## Validación obligatoria en Home Assistant real
- [ ] Actualizar desde Beta 8 sin eliminar la integración ni las entradas de configuración.
- [ ] Confirmar que perfiles, entidades, tarifas, sensores e histórico permanecen intactos.
- [ ] Abrir el editor Lovelace y comprobar que solo aparecen los modelos con imagen.
- [ ] Comprobar que **Vehículo genérico** y **Añadir una foto personal** aparecen al final.
- [ ] Subir PNG y WebP transparentes y verificar vista previa y dashboard.
- [ ] Confirmar rechazo de JPEG, imágenes sin transparencia, archivos superiores a 8 MB e imágenes inválidas.
- [ ] Reiniciar Home Assistant y comprobar que la imagen personal sigue disponible.
- [ ] Verificar que la imagen se sirve desde la carpeta local www.
- [ ] Configurar dos vehículos distintos y confirmar que sus imágenes no se sobrescriben.
- [ ] Cerrar y reabrir el editor para comprobar que la selección persiste.
- [ ] Restaurar la imagen incluida del C10 y comprobar la limpieza para un vehículo genérico.
- [ ] Verificar que el recurso estático de imágenes funciona con la versión mínima soportada de Home Assistant.
- [ ] Revisar móvil/escritorio y temas claro/oscuro.
- [ ] Verificar orientación, escala, ubicación del puerto y animación del cable en carga, conectado y desconectado.

## Criterios visuales de aceptación
- Vista exterior frontal tres cuartos (frontal y un lateral visibles).
- Morro orientado hacia la derecha.
- Vehículo completo, sin recortes.
- Fondo transparente real, sin damero dibujado.
- Lienzo 1200 × 675 y escala/altura de ruedas homogéneas.
- Puerto de carga visible y anclaje del cable ajustable por vehículo.
- Sin fondos fotográficos, marcas de agua ni textos superpuestos.

## Criterio de publicación
La CI verde acredita las pruebas automatizadas, pero no sustituye las pruebas de instalación, persistencia y diseño en una instancia real de Home Assistant. No publicar la etiqueta/release hasta completar las validaciones obligatorias y revisar las licencias de los renders.
