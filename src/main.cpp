#include <Arduino.h>
#include <HX711_ADC.h>

#define PIN_HX711_dout PB9
#define PIN_HX711_sck PB8

#define LOOP_PERIOD_MS 10
#define PWM_MAX 2000
#define PWM_MIN 1000

HX711_ADC LoadCell(PIN_HX711_dout, PIN_HX711_sck);
int throttle_us = PWM_MIN;
float thrust = 0;
uint32_t next_update = 0;


void setup()
{
    Serial.begin(921600);
    LoadCell.begin();
    LoadCell.start(2000, true);
    next_update = millis();
}


void loop()
{
    if (millis() < next_update)
    {
        return;
    }

    if (Serial.available())
    {
        String input = Serial.readStringUntil('\n');  // Read until newline
        input.trim();
        if (input.startsWith("reboot"))
        {
            HAL_NVIC_SystemReset();
        }
        else
        {
            int new_throttle_us = input.toInt();
            throttle_us = constrain(new_throttle_us, PWM_MIN, PWM_MAX);
        }
    }


    if (LoadCell.update())
    {
        thrust = LoadCell.getData();
    }

    uint32_t now = millis();
    Serial.printf("%u, %u, %d\n", now, throttle_us, (int) thrust);

    next_update += LOOP_PERIOD_MS;
}
