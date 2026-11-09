# Плата A147 (ESP32-S3 + RS485), документация производителя

- `ESP32_S3_RS485_Schematic.pdf`, `Motherboard_Schematic.pdf` — схемы
- `Development_Board_Introduction.pdf` — описание платы
- `Network_Diagram.jpg` — схема сети: Wi-Fi через встроенный MAC, проводной Ethernet через W5500 по SPI (RST, CS, INT, MOSI, MISO, SCLK); внутренний TCP/IP стек W5500 не используется, работает lwIP на ESP32-S3

Ссылки (не копируем в репозиторий):
- ESP-IDF 5.2 для ESP32-S3: https://docs.espressif.com/projects/esp-idf/zh_CN/v5.2/esp32s3/get-started/index.html
- Примеры периферии (LCD, USB, GUI, датчики…): https://docs.espressif.com/projects/esp-iot-solution/zh_CN/latest/gettingstarted.html
- Даташит ESP32-S3: https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf

Примеры производителя (esp32s3_rs485: app_ethernet, app_uart, app_twai, app_gpio и др.) — в репозиторий не вносились.
