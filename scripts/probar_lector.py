"""Prueba del lector RFID real (necesita el ESP32 conectado por USB).

Muestra el UID de cada tarjeta que se pase y le responde al ESP32 para que
encienda el LED verde y lo muestre en el LCD. No usa la base de datos.
Sirve también para anotar los UID de las tarjetas.

Se ejecuta desde la carpeta del proyecto:
    python scripts/probar_lector.py          (elige el puerto automáticamente)
    python scripts/probar_lector.py COM5     (usa el puerto indicado)
Para salir: Ctrl + C.   Cierre antes el monitor serial de Arduino.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware import lector_serial
from hardware.lector_serial import LectorSerial

puertos = lector_serial.listar_puertos()
print("Puertos disponibles:")
for nombre, descripcion in puertos:
    print(f"  {nombre}  -  {descripcion}")

if len(sys.argv) > 1:
    puerto = sys.argv[1]
elif len(puertos) == 1:
    puerto = puertos[0][0]
else:
    print("\nIndique el puerto, por ejemplo:  python scripts/probar_lector.py COM5")
    sys.exit(1)

lector = LectorSerial()
try:
    lector.conectar(puerto)
except ConnectionError as error:
    print(f"\n{error}")
    sys.exit(1)

print(f"\nConectado a {puerto}. Esperando al lector...")

try:
    while True:
        for tipo, dato in lector.obtener_eventos():
            if tipo == lector_serial.EVENTO_LISTO:
                print("Lector listo. Pase una tarjeta (Ctrl + C para salir).")
                lector.enviar_mensaje_reposo("Prueba de lector", "Pase su tarjeta")
            elif tipo == lector_serial.EVENTO_UID:
                print(f"  Tarjeta leída: {dato}")
                lector.enviar(f"OK:Tarjeta leída|{dato}")
            elif tipo == lector_serial.EVENTO_DESCONECTADO:
                print(dato)
                sys.exit(1)
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nPrueba terminada.")
finally:
    lector.enviar_mensaje_reposo("Asistencia RFID", "Pase su tarjeta")
    time.sleep(0.2)
    lector.desconectar()
