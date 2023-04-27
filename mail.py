import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

def send_email(imagen1, imagen2, imagen3):
    sender_email = 'info.warrenbot@gmail.com'
    password = "gphcsawdrlquivbu"

    # Ruta y nombre del archivo de la imagen a adjuntar
    filename1 = imagen1
    filename2 = imagen2
    filename3 = imagen3

    # Crear el objeto mensaje
    message = MIMEMultipart()
    message['From'] = sender_email
    message['Subject'] = 'WarrenBot weekly report'

    # Adjuntar la imagen al mensaje
    with open(filename1, 'rb') as f:
        img_data1 = f.read()
    with open(filename2, 'rb') as f:
        img_data2 = f.read()
    with open(filename3, 'rb') as f:
        img_data3 = f.read()

    image = MIMEImage(img_data1, name=filename1)
    image.add_header('Content-Disposition', 'inline', filename=filename1)
    image.add_header('Content-ID', '<image1>')
    message.attach(image)

    image2 = MIMEImage(img_data2, name=filename2)
    image2.add_header('Content-Disposition', 'inline', filename=filename2)
    image2.add_header('Content-ID', '<image2>')
    message.attach(image2)

    image3 = MIMEImage(img_data3, name=filename3)
    image3.add_header('Content-Disposition', 'inline', filename=filename3)
    image3.add_header('Content-ID', '<image3>')
    message.attach(image3)

    # Crear el cuerpo del mensaje con la imagen incrustada
    body = """<html>
                  <body>
                      <p>WarrenBot weekly report for BTC/USDT pair. One week candle chart with buy/sell signals, profit and daily PNL report.    </p>
                      <p><img src="cid:image1"></p>
                      <p><img src="cid:image2"></p>
                      <p><img src="cid:image3"></p>
                  </body>
              </html>"""
    message.attach(MIMEText(body, 'html', 'utf-8'))

    # Leer las direcciones de correo electrónico del archivo directions.txt
    with open('directions.txt', 'r') as f:
        receiver_emails = f.readlines()

    # Eliminar los caracteres de nueva línea (\n) al final de cada dirección de correo electrónico
    receiver_emails = [email.strip() for email in receiver_emails]

    # Adjuntar las direcciones de correo electrónico al mensaje
    message['Bcc'] = ", ".join(receiver_emails)

    # Conectar y autenticar en el servidor SMTP de Gmail
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, password)

    # Enviar el mensaje
    server.send_message(message)
    print('Correo electrónico enviado con éxito')

    # Cerrar la conexión con el servidor SMTP de Gmail
    server.quit()

