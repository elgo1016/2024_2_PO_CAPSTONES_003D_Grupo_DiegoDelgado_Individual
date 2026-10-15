"""Inicio local con Gmail. Las credenciales solo permanecen en memoria."""
import getpass
import os
import re
import warnings
import servidor


def main():
    print('Conectar Gmail para enviar el descuento ELGO20')
    email = input('Tu correo Gmail: ').strip()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        print('Ingresa una direccion de correo valida.')
        return 1
    print('Usa la contraseña de aplicacion de 16 caracteres generada por Google, no la contraseña habitual.')
    print('Puedes pegarla con clic derecho o Ctrl+V. La entrada permanecera oculta.')
    while True:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                password = getpass.getpass('Contraseña de aplicacion (Enter para continuar; Ctrl+C para cancelar): ')
        except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
            print('\nEntrada cancelada. Abre INICIAR_CON_GMAIL.bat para volver a intentar.')
            return 1
        password = ''.join(password.split())
        if len(password) == 16:
            break
        print(f'Se recibieron {len(password)} caracteres sin espacios; se necesitan 16.')
        print('Copia la clave completa desde https://myaccount.google.com/apppasswords y vuelve a intentarlo.')
    os.environ.update(SMTP_HOST='smtp.gmail.com', SMTP_PORT='587', SMTP_FROM=email,
                      SMTP_USER=email, SMTP_PASSWORD=password)
    del password
    print('Comprobando la conexion y autenticacion con Gmail...')
    try:
        connection = servidor.smtp_connection()
        connection.close()
    except servidor.AppError as exc:
        os.environ.pop('SMTP_PASSWORD', None)
        print(exc.message)
        return 1
    print('Gmail acepto las credenciales. Esto aun no confirma la entrega de correos.')
    recipient = input('Destinatario de prueba (Enter para omitir): ').strip()
    if recipient:
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', recipient):
            print('Direccion de prueba invalida; no se envio ningun correo.')
        else:
            try:
                servidor.send_coupon(recipient, 'ELGO20')
                print('Gmail acepto el correo de prueba. Comprueba su recepcion, incluido Spam y Promociones.')
                print('La prueba solo envia el mensaje; suscribete en la tienda para activar el cupon para ese correo.')
            except servidor.AppError as exc:
                print(exc.message)
    print('Carpeta de esta tienda:', servidor.BASE)
    try:
        return servidor.main()
    finally:
        os.environ.pop('SMTP_PASSWORD', None)


if __name__ == '__main__':
    raise SystemExit(main())
