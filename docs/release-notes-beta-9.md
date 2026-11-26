# ChargeTrack 0.1.0-beta.9 — Galería visual de vehículos

## Selector simplificado
- Se elimina del producto el listado de 400 modelos BEV/PHEV.
- El selector muestra únicamente los modelos que tienen una imagen local incluida en la integración.
- Las opciones adicionales son **Vehículo genérico** y **Añadir una foto personal**.
- El selector ya no necesita clasificar modelos por tecnología ni cargar una base de datos extensa.

## Imágenes incluidas
- Se mantiene la galería local de 18 modelos con render propio y la imagen genérica.
- Los renders se sirven desde Home Assistant; no dependen de enlaces a páginas externas.
- La procedencia y los derechos de redistribución de las imágenes suministradas deben quedar confirmados antes de publicar la release.

## Imagen personal
- La subida se realiza directamente a la instancia autenticada de Home Assistant.
- Los archivos se guardan en /config/www/ev-charge-tracker/custom/ con nombre SHA-256.
- Se aceptan PNG y WebP transparentes de hasta 8 MB; se normalizan a PNG 1200 × 675.
- La tarjeta actualiza su vista previa y envía el cambio a Lovelace; el usuario debe pulsar **Guardar** en el editor del panel.
- La imagen personal no se envía a servicios de terceros.
- La selección es por vehículo y se comparte entre los perfiles de carga asociados al mismo vehículo.

## Guía de composición de la imagen
- Vista exterior frontal tres cuartos, mostrando frontal y un lateral.
- Morro orientado hacia la derecha.
- Vehículo completo, centrado y sin recortes.
- Fondo transparente real (canal alfa), no un damero dibujado.
- Lienzo PNG 1200 × 675 px y coche ocupando aproximadamente el 80–90 % del ancho.
- Escala y altura de ruedas similares a los renders incluidos.
- Puerto de carga visible cuando sea posible para facilitar el ajuste del cable.
- Evitar fondos, sombras duras, textos, marcas de agua y perspectivas desde arriba.

## Tarjeta e integración
- Se mantiene la tarjeta responsive y los datos dinámicos de batería, autonomía, odómetro, estado de cable/carga, sesiones, costes e histórico.
- Se conserva el render local del Leapmotor C10 y la imagen genérica.
- Se conserva la selección de imagen independiente por vehículo.
- Se mantiene la integración con el dominio interno ev_charge_tracker para preservar instalaciones existentes.

## Validación antes de publicar
- CI verde en el commit final.
- Revisar el paquete HACS.
- Probar actualización desde Beta 8 conservando perfiles, entidades, tarifas e histórico.
- Probar subida, rechazo de archivos inválidos, persistencia tras reinicio y selección por vehículo en Home Assistant real.
- Verificar la ruta estática local.
- Revisar las imágenes en móvil/escritorio y temas claro/oscuro, así como orientación, escala, puerto y animación del cable.
- Confirmar procedencia y derechos de uso de los renders.

Esta beta no se considera release final hasta completar las comprobaciones manuales anteriores.
