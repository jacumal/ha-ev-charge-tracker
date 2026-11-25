# ChargeTrack — galería de vehículos

Esta carpeta contiene las imágenes locales de los vehículos que se muestran en la tarjeta.

## Estructura

```text
vehicle-images/
├── bev/       # Vehículos 100 % eléctricos
├── phev/      # Híbridos enchufables
└── generic/   # Imagen genérica para vehículos sin imagen propia
```

## Requisitos de imagen

- Un archivo por vehículo; nunca subir composiciones ni cuadrículas.
- PNG, lienzo de 1200 × 675 px.
- Transparencia real (canal alfa); no damero dibujado en el fondo ni en los cristales.
- Vehículo completo, sin recortes.
- Orientación coherente con la referencia Leapmotor C10: frontal tres cuartos, morro hacia la izquierda.
- Encuadre y escala lo más homogéneos posible.
- Nombre de archivo igual al identificador del catálogo, en minúsculas y con guiones. Ejemplos: `leapmotor-b10.png`, `byd-dolphin.png`, `tesla-model-3.png`.

## Dónde subir cada imagen

- BEV: `bev/<vehicle_id>.png`
- PHEV: `phev/<vehicle_id>.png`
- Imagen genérica: `generic/vehicle-generic.png`

El identificador del vehículo se consulta en `vehicle_catalog.json`. El catálogo completo permanece como fuente interna; el selector de la tarjeta solo debe mostrar los vehículos que tengan una imagen propia disponible, además de las opciones genérica y de imagen personal.

## Incorporación a la tarjeta

Subir un PNG a GitHub no lo incorpora automáticamente a Home Assistant. Después hay que registrar su ruta en el catálogo y asegurarse de que la integración sirve la carpeta de imágenes como recurso estático. No marcar una imagen como disponible hasta validar el archivo, su transparencia, la identificación del modelo y los derechos de uso y redistribución.

## Licencias y procedencia

Para cada imagen de terceros, conservar la página de origen, autor y licencia. No asumir que una licencia del archivo cubre automáticamente los derechos sobre el diseño o las marcas del vehículo.
