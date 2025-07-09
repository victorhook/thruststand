import sys
import pandas as pd

'''
Takes desired PWM values in `allowed_pwms` and writes a summarized CSV file with
data from only those PWM values.
If multiple samples are from same PWM, these are averaged.
'''

allowed_pwms = [
    1000,1001,1012,1024,1038,1051,1065,1078,1092,1105,1118,1130,1145,1158,1172,
    1186,1198,1212,1225,1239,1252,1266,1279,1292,1306,1319,1332,1346,1360,1373,
    1386,1400,1414,1429,1443,1457,1470,1484,1498,1512,1526,1540,1555,1568,1583,
    1596,1609,1623,1636,1650,1664,1676,1690,1704,1717,1730,1746,1759,1773,1786,
    1800,1814,1827,1840,1854,1867,1881,1895,1909,1923,1937,1950,1963,1977,1989,2000
]

def main():
    if len(sys.argv) != 3:
        print("Usage: python average_thrust_by_pwm.py input.csv output")
        sys.exit(1)

    input_file = sys.argv[1]
    df = pd.read_csv(input_file, usecols=['pwm', 'thrust'])

    # Group by PWM and average thrust
    result = df.groupby('pwm', as_index=False).mean()

    # Round for cleaner output (optional)
    result['thrust'] = (result['thrust']).round(3)

    result_filtered = result[result['pwm'].isin(allowed_pwms)]

    # Save to CSV
    output_file = sys.argv[2]
    result.to_csv(output_file, index=False)
    print(f"Averaged results written to {output_file}")

    summarized = output_file.split('.csv')[0] + '_summarized.csv'
    result_filtered.to_csv(summarized, index=False)
    print(f"Summarized results written to {summarized}")


if __name__ == '__main__':
    main()
