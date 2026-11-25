# ChargeTrack — galería local de vehículos

Esta carpeta contiene exclusivamente los renders que pueden seleccionarse en la tarjeta, además de la imagen genérica.

## Requisitos para incorporar un vehículo
- PNG RGBA, lienzo 1200 × 675 px.
- Vista exterior frontal tres cuartos, mostrando frontal y un lateral.
- Morro orientado hacia la derecha.
- Vehículo completo, centrado y sin recortes.
- Fondo transparente real, sin damero dibujado.
- Escala homogénea: coche ocupando aproximadamente el 80–90 % del ancho y ruedas a una altura comparable.
- Puerto de carga visible cuando sea posible.
- Sin fondos fotográficos, marcas de agua ni textos.

## Selector de la tarjeta
El selector se genera únicamente a partir de las entradas de vehicle_catalog.json que apuntan a un archivo local válido. No se mantiene una lista general de marcas/modelos. Los modelos sin imagen no aparecen.

Al final del selector se muestran dos opciones fijas:
1. Vehículo genérico.
2. Añadir una foto personal.

## Incorporar un nuevo render
1. Añadir el PNG a esta carpeta.
2. Añadir su marca, modelo, carrocería y ruta exacta en vehicle_catalog.json.
3. Comprobar que el archivo existe, tiene transparencia y se carga en la tarjeta.
4. Añadir la información de procedencia y licencia a la documentación del proyecto.
5. Ejecutar todas las pruebas y revisar la imagen en Home Assistant antes de publicar.

## Licencias y procedencia
No declarar validada la redistribución de un render sin autor, fuente y licencia o autorización verificables. Los derechos sobre el archivo 3D y los derechos sobre marcas/diseños del vehículo pueden ser distintos.
