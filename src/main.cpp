#include <Arduino.h>
#include <HX711_ADC.h>
#include <ArduinoJson.h>

#define PIN_HX711_dout PB9
#define PIN_HX711_sck PB8
#define PIN_ESC PA8

#define LOOP_PERIOD_MS 3
#define PWM_MAX 2000
#define PWM_MIN 1000

HX711_ADC LoadCell(PIN_HX711_dout, PIN_HX711_sck);
StaticJsonDocument<128> json;
int throttle_us = PWM_MIN;
float thrust = 0;
int dshot = 0;
uint32_t next_update = 0;

#define DSHOT_FRAME_SIZE 16
#define DSHOT_TIMER_PERIOD 240
#define DSHOT_ONE_PULSE 180
#define DSHOT_ZERO_PULSE 90
uint16_t pwm_buffer[DSHOT_FRAME_SIZE];

void send_dshot_frame(const uint16_t throttle_us, const bool telemetry);
void arm();


void setupPWM()
{
    // Enable clocks
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN | RCC_APB2ENR_TIM1EN;
    RCC->AHBENR  |= RCC_AHBENR_DMA1EN;

    GPIOA->CRH &= ~(0xF << 0);      // Clear PA8 bits
    GPIOA->CRH |=  (0xB << 0);      // MODE8 = 11 (50 MHz), CNF8 = 10 (AF PP)

    // TIM1 base config
    TIM1->PSC = 0;                          // No prescaler → 72MHz
    TIM1->ARR = DSHOT_TIMER_PERIOD - 1;    // 240 ticks
    TIM1->CCR1 = 0;

    // Channel 1 as PWM mode 1, preload enable
    TIM1->CCMR1 |= TIM_CCMR1_OC1PE | TIM_CCMR1_OC1M_1 | TIM_CCMR1_OC1M_2;
    TIM1->CCER  |= TIM_CCER_CC1E;          // Enable CH1 output

    // DMA request on update event
    TIM1->DIER |= TIM_DIER_UDE;

    // Advanced timer quirk: enable main output
    TIM1->BDTR |= TIM_BDTR_MOE;

    // Enable preload for ARR
    TIM1->CR1 |= TIM_CR1_ARPE;
}


void setup()
{
    Serial.begin(921600);
    LoadCell.begin();
    LoadCell.start(1000, true);
    setupPWM();
    TIM1->CR1 |= TIM_CR1_CEN;
    next_update = micros();
}


void loop()
{
    if (micros() < next_update)
    {
        return;
    }

    if (throttle_us == PWM_MIN)
    {
        arm();
    }
    else
    {
        send_dshot_frame(throttle_us, false);
    }

    if (Serial.available())
    {
        String input = Serial.readStringUntil('\n');  // Read until newline
        input.trim();
        int new_throttle_us = input.toInt();
        throttle_us = constrain(new_throttle_us, PWM_MIN, PWM_MAX);
    }

    if (LoadCell.update())
    {
        thrust = LoadCell.getData();
    }

    //Serial.write(0x0F);
    //Serial.write(throttle_us);
    //Serial.write(thrust);

    next_update += 1000;//LOOP_PERIOD_MS;
}

#define DSHOT_THROTTLE_MIN 48
#define DSHOT_THROTTLE_MAX 2047

uint16_t map_pwm_to_dshot(uint16_t pwm_us) {
  if (pwm_us < 1000) pwm_us = 1000;
  if (pwm_us > 2000) pwm_us = 2000;

  float scaled = ((float)(pwm_us - 1000) / 1000.0f) * 1999.0f + 48.0f;
  return (uint16_t)(scaled + 0.5f);  // proper rounding
}

void pack_dshot_frame(const uint16_t throttle_us, const bool telemetry, uint8_t* frame)
{
    uint16_t throttle_dshot = map_pwm_to_dshot(throttle_us);
    dshot = throttle_dshot;
    
    // CRC is calculated with throttle (11 bits) and telemetry (1 bit)
    uint16_t crc_data = (throttle_dshot << 1) | (telemetry ? 1 : 0);
    uint8_t crc = (crc_data >> 8) ^ ((crc_data >> 4) & 0x0F) ^ (crc_data & 0x0F);

    // Construct frame
    for (int i = 0; i <= 11; i++)
    {
        frame[i] = ((throttle_dshot >> (10 - i)) & 1) ? 180 : 90;
    }

    // Telemetry
    frame[11] = telemetry ? 180 : 90;

    for (int i = 0; i < 4; i++)
    {
        frame[12+i] = ((crc >> (3 - i)) & 1) ? 180 : 90;
    }
}

void send_dshot_raw_frame(const uint8_t* frame)
{
    // Send frame
    for (int i = 0; i < DSHOT_FRAME_SIZE; i++)
    {
        TIM1->CCR1 = frame[i];
        TIM1->EGR |= TIM_EGR_UG;
        delayMicroseconds(3);
    }

    // Set PWM to 0
    TIM1->CCR1 = 0;
    TIM1->EGR |= TIM_EGR_UG;

    //Serial.printf("PWM %d -> %d: ", throttle_us, dshot);
    //for (int i = 0; i < DSHOT_FRAME_SIZE; i++)
    //{
    //    Serial.printf("%d", frame[i] == 180);
    //}
    uint32_t now = millis();
    Serial.printf("%u, %u, %d\n", now, throttle_us, (int) thrust);
    //Serial.print("\n");
}

void send_dshot_frame(const uint16_t throttle_us, const bool telemetry)
{
    uint8_t frame[DSHOT_FRAME_SIZE];
    pack_dshot_frame(throttle_us, telemetry, frame);
    send_dshot_raw_frame(frame);
}

void arm()
{
    uint8_t arm_frame[DSHOT_FRAME_SIZE];
    memset(arm_frame, 90, DSHOT_FRAME_SIZE);
    send_dshot_raw_frame(arm_frame);
}
