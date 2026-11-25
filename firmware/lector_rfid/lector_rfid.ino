// ============================================================================
//  SISTEMA DE ASISTENCIA CON RFID - Firmware del lector (ESP32)
// ============================================================================
//  El ESP32 es un "lector tonto": lee el UID de la tarjeta, lo envia a Python
//  y espera la respuesta. Python (que tiene la base de datos) decide si la
//  lectura se acepta o se rechaza, y el ESP32 solo lo muestra.
//
//  LIBRERIAS (Administrador de librerias de Arduino IDE):
//    - MFRC522                (miguelbalboa)
//    - LiquidCrystal_PCF8574  (Matthias Hertel)
//
//  CONEXIONES
//    RC522   : SDA/SS=13  SCK=18  MOSI=23  MISO=19  RST=4  3.3V  GND
//              (el RC522 se alimenta SOLO con 3.3 V)
//    LCD I2C : SDA=21  SCL=22  VCC=5V  GND   (direccion 0x27)
//    Buzzer  : GPIO 15 -> (+) buzzer, (-) -> GND
//    LED verde: GPIO 26 -> resistencia 220 ohm -> anodo (pata larga), catodo -> GND
//    LED rojo : GPIO 27 -> resistencia 220 ohm -> anodo (pata larga), catodo -> GND
//
//  PROTOCOLO SERIAL (115200 baudios, cada mensaje termina en '\n')
//    ESP32 -> Python
//      READY              El lector arranco y esta listo.
//      UID:A1B2C3D4       Se leyo una tarjeta (hexadecimal, mayusculas).
//      PONG               Respuesta a PING.
//    Python -> ESP32
//      OK:linea1|linea2   Lectura ACEPTADA: LED verde + 1 pitido + texto en LCD.
//      ERR:linea1|linea2  Lectura RECHAZADA: LED rojo + 3 pitidos + texto en LCD.
//      MSG:linea1|linea2  Cambia el texto de reposo del LCD (sin LED ni pitido).
//      PING               Para comprobar que el lector esta conectado.
//    Cada linea del LCD admite hasta 16 caracteres. El texto llega en UTF-8 y
//    el LCD muestra en espanol: a, e, i, o, u con tilde, la ene minuscula y
//    mayuscula y la u con dieresis (son caracteres dibujados a mano, porque el
//    LCD no los trae). Las vocales MAYUSCULAS con tilde se muestran sin tilde.
//
//  Todo el programa funciona con millis(): no hay ningun delay() en loop().
// ============================================================================

#include <SPI.h>
#include <Wire.h>
#include <MFRC522.h>
#include <LiquidCrystal_PCF8574.h>

// ----------------------------- Pines ----------------------------------------
const uint8_t PIN_SS        = 13;
const uint8_t PIN_RST       = 4;
const uint8_t PIN_SCK       = 18;
const uint8_t PIN_MOSI      = 23;
const uint8_t PIN_MISO      = 19;
const uint8_t PIN_SDA       = 21;
const uint8_t PIN_SCL       = 22;
const uint8_t PIN_BUZZER    = 15;
const uint8_t PIN_LED_VERDE = 26;
const uint8_t PIN_LED_ROJO  = 27;

// ----------------------------- Ajustes --------------------------------------
// Buzzer ACTIVO (suena al darle 5V/3.3V, suele traer una etiqueta): false
// Buzzer PASIVO (necesita una frecuencia para sonar): true
const bool BUZZER_PASIVO = false;
const unsigned int FRECUENCIA_BUZZER = 2000;      // Hz, solo para buzzer pasivo

const unsigned long BAUDIOS             = 115200;
const uint8_t       DIRECCION_LCD       = 0x27;
const unsigned long T_RESULTADO_MS      = 2500;   // tiempo que se ve el resultado
const unsigned long T_ESPERA_PYTHON_MS  = 3000;   // maximo esperando respuesta
const unsigned long T_MISMA_TARJETA_MS  = 3000;   // ignora la misma tarjeta seguida
const unsigned long T_PITIDO_MS         = 120;    // duracion de cada pitido/pausa

const uint8_t COLUMNAS_LCD = 16;
const uint8_t TAM_BUFFER   = 96;                  // largo maximo de un comando
// Una letra con tilde ocupa 2 bytes en UTF-8, asi que 16 caracteres del LCD
// pueden ocupar hasta 32 bytes.
const uint8_t TAM_LINEA    = COLUMNAS_LCD * 2 + 1;

// ------------------- Caracteres en espanol para el LCD ----------------------
// El LCD permite dibujar 8 caracteres propios (posiciones 0 a 7), de 5x8 puntos.
const uint8_t CAR_A_TILDE  = 0;   // a con tilde
const uint8_t CAR_E_TILDE  = 1;   // e con tilde
const uint8_t CAR_I_TILDE  = 2;   // i con tilde
const uint8_t CAR_O_TILDE  = 3;   // o con tilde
const uint8_t CAR_U_TILDE  = 4;   // u con tilde
const uint8_t CAR_ENE_MIN  = 5;   // ene minuscula
const uint8_t CAR_ENE_MAY  = 6;   // ene mayuscula
const uint8_t CAR_U_DIERES = 7;   // u con dieresis

byte dibujos[8][8] = {
  {B00010, B00100, B01110, B00001, B01111, B10001, B01111, B00000},  // a tilde
  {B00010, B00100, B01110, B10001, B11111, B10000, B01110, B00000},  // e tilde
  {B00010, B00100, B00000, B01100, B00100, B00100, B01110, B00000},  // i tilde
  {B00010, B00100, B01110, B10001, B10001, B10001, B01110, B00000},  // o tilde
  {B00010, B00100, B10001, B10001, B10001, B10011, B01101, B00000},  // u tilde
  {B01110, B00000, B10110, B11001, B10001, B10001, B10001, B00000},  // ene min
  {B01110, B00000, B10001, B11001, B10101, B10011, B10001, B00000},  // ene may
  {B01010, B00000, B10001, B10001, B10001, B10011, B01101, B00000}   // u dieresis
};

// ----------------------------- Objetos --------------------------------------
MFRC522 rfid(PIN_SS, PIN_RST);
LiquidCrystal_PCF8574 lcd(DIRECCION_LCD);

// ----------------------------- Estado ---------------------------------------
enum Estado {
  ESPERANDO_TARJETA,     // reposo: se puede pasar una tarjeta
  ESPERANDO_RESPUESTA,   // se envio un UID y se espera OK/ERR de Python
  MOSTRANDO_RESULTADO    // LED y LCD mostrando el resultado
};
Estado estado = ESPERANDO_TARJETA;
unsigned long tEstado = 0;                 // momento en que se entro al estado

// Texto de reposo del LCD (Python lo puede cambiar con MSG:)
char reposo1[TAM_LINEA] = "Asistencia RFID";
char reposo2[TAM_LINEA] = "Pase su tarjeta";

// Comando que se va recibiendo por Serial
char bufferSerial[TAM_BUFFER];
uint8_t largoBuffer = 0;

// Ultima tarjeta leida (para no enviarla varias veces si se deja apoyada)
char ultimoUid[21] = "";
unsigned long tUltimaLectura = 0;

// Buzzer sin bloqueo: cada pitido son 2 "cambios" (encender y apagar)
uint8_t cambiosBuzzerPendientes = 0;
bool buzzerEncendido = false;
unsigned long tCambioBuzzer = 0;

// ============================================================================
//  LCD
// ============================================================================

// Traduce el segundo byte de una letra UTF-8 que empieza por 0xC3 (las letras
// con tilde y la ene) al caracter que debe escribirse en el LCD.
// Devuelve true si la letra se puede mostrar.
bool traducirLetraEspanol(uint8_t segundoByte, uint8_t *caracterLCD) {
  switch (segundoByte) {
    case 0xA1: *caracterLCD = CAR_A_TILDE;  return true;   // a con tilde
    case 0xA9: *caracterLCD = CAR_E_TILDE;  return true;   // e con tilde
    case 0xAD: *caracterLCD = CAR_I_TILDE;  return true;   // i con tilde
    case 0xB3: *caracterLCD = CAR_O_TILDE;  return true;   // o con tilde
    case 0xBA: *caracterLCD = CAR_U_TILDE;  return true;   // u con tilde
    case 0xB1: *caracterLCD = CAR_ENE_MIN;  return true;   // ene minuscula
    case 0x91: *caracterLCD = CAR_ENE_MAY;  return true;   // ene mayuscula
    case 0xBC: *caracterLCD = CAR_U_DIERES; return true;   // u con dieresis
    // Vocales mayusculas con tilde: se muestran sin tilde.
    case 0x81: *caracterLCD = 'A'; return true;
    case 0x89: *caracterLCD = 'E'; return true;
    case 0x8D: *caracterLCD = 'I'; return true;
    case 0x93: *caracterLCD = 'O'; return true;
    case 0x9A: *caracterLCD = 'U'; return true;
    case 0x9C: *caracterLCD = 'U'; return true;
  }
  return false;
}

// Escribe una fila completa: recorta a 16 caracteres y rellena con espacios,
// asi no hace falta lcd.clear() y la pantalla no parpadea.
void imprimirLinea(uint8_t fila, const char *texto) {
  lcd.setCursor(0, fila);
  uint8_t escritos = 0;
  for (uint8_t i = 0; texto[i] != '\0' && escritos < COLUMNAS_LCD; i++) {
    uint8_t c = (uint8_t)texto[i];

    if (c >= 32 && c <= 126) {                 // ASCII imprimible
      lcd.write(c);
      escritos++;
    } else if (c == 0xC3 && texto[i + 1] != '\0') {   // letra con tilde o ene
      uint8_t caracterLCD;
      i++;                                     // consume el segundo byte
      if (traducirLetraEspanol((uint8_t)texto[i], &caracterLCD)) {
        lcd.write(caracterLCD);
        escritos++;
      }
    }
    // Cualquier otro byte se ignora.
  }
  while (escritos < COLUMNAS_LCD) {
    lcd.print(' ');
    escritos++;
  }
}

void mostrarLCD(const char *linea1, const char *linea2) {
  imprimirLinea(0, linea1);
  imprimirLinea(1, linea2);
}

// ============================================================================
//  Buzzer y LEDs
// ============================================================================

void buzzerOn() {
  if (BUZZER_PASIVO) tone(PIN_BUZZER, FRECUENCIA_BUZZER);
  else               digitalWrite(PIN_BUZZER, HIGH);
  buzzerEncendido = true;
}

void buzzerOff() {
  if (BUZZER_PASIVO) noTone(PIN_BUZZER);
  digitalWrite(PIN_BUZZER, LOW);
  buzzerEncendido = false;
}

// Programa N pitidos; actualizarBuzzer() los va ejecutando sin bloquear.
void iniciarPitidos(uint8_t cantidad) {
  cambiosBuzzerPendientes = cantidad * 2 - 1;   // on, off, on, ... (ya va 1 on)
  buzzerOn();
  tCambioBuzzer = millis();
}

void actualizarBuzzer() {
  if (cambiosBuzzerPendientes == 0) return;
  if (millis() - tCambioBuzzer < T_PITIDO_MS) return;

  if (buzzerEncendido) buzzerOff();
  else                 buzzerOn();
  cambiosBuzzerPendientes--;
  tCambioBuzzer = millis();
}

void apagarLeds() {
  digitalWrite(PIN_LED_VERDE, LOW);
  digitalWrite(PIN_LED_ROJO, LOW);
}

// ============================================================================
//  Cambios de estado
// ============================================================================

void irAReposo() {
  apagarLeds();
  mostrarLCD(reposo1, reposo2);
  estado = ESPERANDO_TARJETA;
  tEstado = millis();
}

// Muestra el resultado de una lectura: aceptada (verde) o rechazada (rojo).
void mostrarResultado(bool aceptada, const char *linea1, const char *linea2) {
  apagarLeds();
  digitalWrite(aceptada ? PIN_LED_VERDE : PIN_LED_ROJO, HIGH);
  iniciarPitidos(aceptada ? 1 : 3);
  mostrarLCD(linea1, linea2);
  estado = MOSTRANDO_RESULTADO;
  tEstado = millis();
}

// ============================================================================
//  Comandos que llegan desde Python
// ============================================================================

// Separa "linea1|linea2" en dos punteros (modifica el texto original).
void separarLineas(char *texto, char **linea1, char **linea2) {
  *linea1 = texto;
  char *barra = strchr(texto, '|');
  if (barra != NULL) {
    *barra = '\0';
    *linea2 = barra + 1;
  } else {
    *linea2 = (char *)"";
  }
}

void procesarComando(char *comando) {
  char *linea1;
  char *linea2;

  if (strncmp(comando, "OK:", 3) == 0) {
    separarLineas(comando + 3, &linea1, &linea2);
    mostrarResultado(true, linea1, linea2);

  } else if (strncmp(comando, "ERR:", 4) == 0) {
    separarLineas(comando + 4, &linea1, &linea2);
    mostrarResultado(false, linea1, linea2);

  } else if (strncmp(comando, "MSG:", 4) == 0) {
    separarLineas(comando + 4, &linea1, &linea2);
    strncpy(reposo1, linea1, TAM_LINEA - 1);
    reposo1[TAM_LINEA - 1] = '\0';
    strncpy(reposo2, linea2, TAM_LINEA - 1);
    reposo2[TAM_LINEA - 1] = '\0';
    if (estado == ESPERANDO_TARJETA) mostrarLCD(reposo1, reposo2);

  } else if (strcmp(comando, "PING") == 0) {
    Serial.println("PONG");
  }
  // Cualquier otro texto se ignora.
}

// Lee los caracteres disponibles y arma el comando hasta encontrar '\n'.
void leerSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\r') continue;                 // ignora el retorno de carro

    if (c == '\n') {
      bufferSerial[largoBuffer] = '\0';
      if (largoBuffer > 0) procesarComando(bufferSerial);
      largoBuffer = 0;
    } else if (largoBuffer < TAM_BUFFER - 1) {
      bufferSerial[largoBuffer++] = c;
    }
    // Si el comando es mas largo que el buffer, se descarta el sobrante.
  }
}

// ============================================================================
//  Lectura de tarjetas
// ============================================================================

void leerTarjeta() {
  if (!rfid.PICC_IsNewCardPresent()) return;
  if (!rfid.PICC_ReadCardSerial()) return;

  // UID en hexadecimal, mayusculas y sin espacios: "A1B2C3D4"
  char uid[21];
  uint8_t pos = 0;
  for (uint8_t i = 0; i < rfid.uid.size && i < 10; i++) {
    pos += sprintf(uid + pos, "%02X", rfid.uid.uidByte[i]);
  }
  uid[pos] = '\0';

  rfid.PICC_HaltA();          // deja de comunicarse con esta tarjeta
  rfid.PCD_StopCrypto1();

  // Si es la misma tarjeta que se acaba de leer (se quedo apoyada), se ignora.
  bool mismaTarjeta = (strcmp(uid, ultimoUid) == 0);
  if (mismaTarjeta && millis() - tUltimaLectura < T_MISMA_TARJETA_MS) return;

  strcpy(ultimoUid, uid);
  tUltimaLectura = millis();

  Serial.print("UID:");
  Serial.println(uid);

  mostrarLCD("Leyendo...", uid);
  estado = ESPERANDO_RESPUESTA;
  tEstado = millis();
}

// ============================================================================
//  setup y loop
// ============================================================================

void setup() {
  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_ROJO, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  apagarLeds();
  buzzerOff();

  Serial.begin(BAUDIOS);

  Wire.begin(PIN_SDA, PIN_SCL);
  lcd.begin(COLUMNAS_LCD, 2);
  lcd.setBacklight(255);
  for (uint8_t i = 0; i < 8; i++) {
    lcd.createChar(i, dibujos[i]);       // carga las letras en espanol
  }

  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_SS);
  rfid.PCD_Init();

  irAReposo();
  Serial.println("READY");
}

void loop() {
  leerSerial();          // comandos de Python (siempre atentos)
  actualizarBuzzer();    // pitidos pendientes

  switch (estado) {
    case ESPERANDO_TARJETA:
      leerTarjeta();
      break;

    case ESPERANDO_RESPUESTA:
      // Si Python no contesta (app cerrada o cable suelto), se avisa.
      if (millis() - tEstado >= T_ESPERA_PYTHON_MS) {
        mostrarResultado(false, "Sin respuesta", "Revise la app");
      }
      break;

    case MOSTRANDO_RESULTADO:
      if (millis() - tEstado >= T_RESULTADO_MS) {
        irAReposo();
      }
      break;
  }
}
