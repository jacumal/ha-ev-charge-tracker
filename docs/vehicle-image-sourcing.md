# ChargeTrack — requisitos de imágenes y procedencia

## Galería incluida
El selector de ChargeTrack no contiene un catálogo general de marcas y modelos. Solo muestra los vehículos para los que existe un render local dentro de la carpeta brand/vehicle-images. La galería actual contiene 18 modelos y una imagen genérica.

Para añadir otro modelo:
1. Incorporar un PNG del vehículo en esta carpeta.
2. Normalizarlo al estándar visual descrito abajo.
3. Añadir una entrada a vehicle_catalog.json con marca, modelo, carrocería y ruta local exacta.
4. Verificar que el archivo existe, tiene canal alfa y se carga correctamente en la tarjeta.
5. Documentar autor, fuente y licencia o autorización de redistribución.

No añadir al selector modelos que no tengan imagen incluida.

## Estándar visual
- Vista exterior frontal tres cuartos, frontal y un lateral visibles.
- Morro orientado hacia la derecha.
- Vehículo completo, sin recortes y centrado.
- Fondo transparente real (canal alfa).
- PNG con lienzo de 1200 × 675 px.
- Vehículo ocupando aproximadamente el 80–90 % del ancho, con altura de ruedas y escala comparables entre modelos.
- Puerto de carga visible si es posible.
- Sin fondos fotográficos, dameros dibujados, marcas de agua ni textos.

## Imágenes personales
El editor acepta PNG/WebP transparentes de hasta 8 MB. La tarjeta elimina el margen transparente sobrante, centra el vehículo y lo guarda como PNG de 1200 × 675 en el Home Assistant del usuario. No se utiliza ningún servicio externo. La detección automática no puede determinar con fiabilidad si el modelo, el ángulo o la orientación son correctos; el usuario debe seguir la guía visual.

## Procedencia y derechos
Para cada render incluido, conservar:
- modelo y ruta del archivo;
- autor/creador;
- URL de origen o evidencia de creación propia;
- licencia exacta y URL de licencia, o autorización de uso;
- atribución exigida;
- fecha de incorporación y revisión.

No asumir que una licencia de un archivo 3D concede automáticamente derechos sobre marcas, diseños o elementos protegidos del vehículo. Si la procedencia o los derechos no están claros, no declarar la imagen como validada para redistribución.
