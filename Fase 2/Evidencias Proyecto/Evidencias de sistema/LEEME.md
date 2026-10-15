# 3Dedos — boletín con descuento del 20%

Esta copia está basada en el repositorio proporcionado. La carpeta original no se modificó. No incluye la base de datos original ni sus usuarios y pedidos.

## Uso

Ejecuta INICIAR_3DEDOS.bat con Python 3.10 o posterior. Para conservar tus datos, con el servidor original detenido, copia su carpeta datos dentro de esta carpeta antes de iniciar. Las tablas nuevas se crean automáticamente; no se borran las existentes.

## Gmail: iniciar y probar

Detén el servidor anterior con Ctrl+C. Abre INICIAR_CON_GMAIL.bat e ingresa tu Gmail y tu contraseña de aplicación de 16 caracteres en la ventana local. La clave no se guarda en archivos.

El iniciador comprueba la autenticación con Gmail. Después puedes ingresar una dirección destinataria para enviar una prueba; Enter omite el envío. Que Gmail acepte un mensaje no confirma su recepción: comprueba la bandeja de entrada, Spam y Promociones. Esta prueba no registra la suscripción: utiliza el formulario de la tienda para completar el flujo y activar ELGO20 para ese correo.

Los errores distinguen credenciales, destinatario, remitente y conexión, sin mostrar contraseñas ni respuestas privadas del proveedor. Un envío fallido permite reintentar de inmediato. La espera de cinco minutos comienza después de un envío aceptado. Si la versión antigua dejó una espera activa, esta expira a los cinco minutos de aquel intento.

## Configurar el envío real

Se necesita un proveedor SMTP con STARTTLS (normalmente puerto 587). En PowerShell, dentro de esta carpeta, configura las variables y ejecuta el servidor en esa misma ventana:

```powershell
$env:SMTP_HOST = 'smtp.tu-proveedor.com'
$env:SMTP_PORT = '587'
$env:SMTP_FROM = '3Dedos <tienda@tu-dominio.cl>'
$env:SMTP_USER = 'tu-usuario'
$env:SMTP_PASSWORD = 'tu-clave-smtp'
python servidor.py
```

Usa las credenciales SMTP y un remitente autorizado por tu proveedor. No guardes claves en el repositorio. Sin esta configuración, el formulario muestra que no puede enviar el correo; nunca afirma que lo envió.

## Comportamiento

- Suscripción sin crear una cuenta: solo correo y aceptación del boletín.
- Código compartido ELGO20, con validación individual por correo y vigencia de 30 días desde la solicitud inicial.
- El envío repetido conserva el código y está limitado a una solicitud cada cinco minutos por correo.
- El cliente inicia sesión para aplicar el cupón, usando el mismo correo.
- 20% sobre los productos, redondeado al peso, solo en la primera compra no cancelada.
- Un solo uso. Se consume al confirmar el pedido, que sigue pendiente de pago. Cancelarlo no reactiva el cupón.
- El servidor calcula y guarda el descuento; también aparece en el historial y la administración.
- El formulario registra la suscripción; no se ha agregado un sistema de campañas del boletín.

## Validación realizada

Pruebas con base temporal y envío simulado: correo inválido, consentimiento, solicitudes repetidas, asociación del código al correo, cálculo del 20%, confirmación repetida del mismo pedido y bloqueo del segundo uso. Sintaxis Python y JavaScript verificada.

No se envió ningún correo real. Falta configurar y probar el proveedor SMTP. Se conserva el servidor local de demostración del repositorio; este paquete no publica una tienda en internet.


## Imágenes de productos

En Administración > Productos > Editar producto, selecciona un JPG, PNG o WebP de hasta 30 MB y 40 megapíxeles. Revisa la vista previa y pulsa Guardar producto. También puedes reemplazar o quitar la imagen. Las imágenes se ajustan en el navegador a un máximo de 1600 píxeles por lado y 2 MB antes del envío. Se guardan en la base de datos con el producto.

La presentación conserva las proporciones sin recortes, dentro de un marco uniforme adaptable a celular, tablet y computador. Se verificó carga y guardado desde el panel y ausencia de desbordamiento horizontal del catálogo a 320, 768 y 1280 píxeles.

Después de actualizar estos archivos es necesario detener el servidor anterior con Ctrl+C y abrir INICIAR_CON_GMAIL.bat nuevamente. Recarga el navegador con Ctrl+F5. El servidor anterior conserva un límite de 64 KB y rechazará imágenes aunque la página muestre el formulario nuevo.
