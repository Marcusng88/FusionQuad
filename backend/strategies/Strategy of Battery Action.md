# Battery Management System: Complete Strategy Guide

## Table of Contents

1. [Code Definitions](#code-definitions)
   - [Time Codes (T0 - T5)](#time-codes-t0---t5)
   - [Solar Intensity Codes (S0 - S3)](#solar-intensity-codes-s0---s3)
   - [Demand Codes (D0 - D4)](#demand-codes-d0---d4)
   - [Battery State of Charge Codes (B0 - B5)](#battery-state-of-charge-codes-b0---b5)
   - [Action Codes (A0 - A8)](#action-codes-a0---a8)
2. [Action Strategies by Condition](#action-strategies-by-condition)
   - [A0 - Forced Charge](#a0---forced-charge)
   - [A1 - Low Charge](#a1---low-charge)
   - [A2 - Medium Charge](#a2---medium-charge)
   - [A3 - High Charge](#a3---high-charge)
   - [A4 - No Action](#a4---no-action)
   - [A5 - Low Discharge](#a5---low-discharge)
   - [A6 - Medium Discharge](#a6---medium-discharge)
   - [A7 - High Discharge](#a7---high-discharge)
   - [A8 - Forced Discharge](#a8---forced-discharge)

---

## Code Definitions

### Time Codes (T0 - T5)

**T0** means weekday peak hour, which occurs Monday through Friday from 14:00 to 22:00, when electricity prices are highest and Maximum Demand risk is most critical.

**T1** means weekday semi-peak or morning period, which occurs Monday through Friday from 08:00 to 14:00, when electricity prices are medium and this period serves as a preparation window before peak hours begin.

**T2** means weekday off-peak or night period, which occurs Monday through Friday from 22:00 to 08:00 the next morning, when electricity prices are lowest and this is the most economical time for charging the battery.

**T3** means weekend, which includes all day Saturday and Sunday from 00:00 to 24:00, when electricity prices are low and Maximum Demand risk is minimal.

**T4** means public holiday, which includes all gazetted national and state holidays from 00:00 to 24:00, when electricity prices are low and Maximum Demand risk is minimal.

**T5** means pre-peak preparatory period, which occurs one to two hours before weekday peak hour begins (approximately 12:00 to 14:00), when the system should prepare the battery for upcoming high demand.

---

### Solar Intensity Codes (S0 - S3)

**S0** means no sunlight, which occurs during nighttime from approximately 20:00 to 07:00, when photovoltaic power output is zero percent of system capacity.

**S1** means weak sunlight, which occurs when solar irradiance is less than 200 watts per square meter, such as during early morning, late evening, cloudy days, or rainy conditions, resulting in photovoltaic power output between zero and twenty percent of system capacity.

**S2** means medium sunlight, which occurs when solar irradiance is between 200 and 600 watts per square meter, such as during partly cloudy days or periods with moderate cloud cover, resulting in photovoltaic power output between twenty and seventy percent of system capacity.

**S3** means strong sunlight, which occurs when solar irradiance is greater than 600 watts per square meter, such as during clear sky conditions around noon, resulting in photovoltaic power output between seventy and one hundred percent of system capacity.

---

### Demand Codes (D0 - D4)

**D0** means extremely low demand, which occurs when the current facility load is less than forty percent of the Maximum Demand threshold, indicating no risk of exceeding the MD limit.

**D1** means low demand, which occurs when the current facility load is between forty and sixty percent of the Maximum Demand threshold, indicating very low risk of exceeding the MD limit.

**D2** means medium demand, which occurs when the current facility load is between sixty and eighty percent of the Maximum Demand threshold, indicating moderate risk with sufficient buffer before reaching the MD limit.

**D3** means high demand, which occurs when the current facility load is between eighty and ninety-five percent of the Maximum Demand threshold, indicating high risk that requires active management to avoid exceeding the MD limit.

**D4** means extremely high demand, which occurs when the current facility load is at or above ninety-five percent of the Maximum Demand threshold, indicating critical risk where immediate action is required to prevent MD penalty.

---

### Battery State of Charge Codes (B0 - B5)

**B0** means emergency low battery level, which occurs when the battery State of Charge is less than ten percent, requiring immediate protection actions to prevent deep discharge damage.

**B1** means low warning battery level, which occurs when the battery State of Charge is between ten and twenty percent, indicating the battery is in a warning zone where discharge should be avoided and charging should be prioritized.

**B2** means normal low battery level, which occurs when the battery State of Charge is between twenty and fifty percent, indicating the battery has sufficient charge for normal operations but is on the lower side of the optimal range.

**B3** means normal high battery level, which occurs when the battery State of Charge is between fifty and eighty percent, indicating the battery is in the optimal operating range with good flexibility for both charging and discharging.

**B4** means high warning battery level, which occurs when the battery State of Charge is between eighty and ninety-five percent, indicating the battery is approaching full capacity where charging should be avoided and discharging should be prioritized.

**B5** means emergency high battery level, which occurs when the battery State of Charge exceeds ninety-five percent, requiring immediate forced discharge to prevent overcharge damage to the battery.

---

### Action Codes (A0 - A8)

**A0** means forced charge, which is an emergency action that charges the battery at one hundred percent of its maximum capacity regardless of other conditions, used only when battery level is critically low to prevent deep discharge damage.

**A1** means low charge, which charges the battery at less than thirty percent of its maximum charging capacity, used for gentle top-ups during low-risk periods or when only a small amount of charge is needed.

**A2** means medium charge, which charges the battery at between thirty and seventy percent of its maximum charging capacity, used for routine charging during preparatory periods or when moderate solar power is available.

**A3** means high charge, which charges the battery at greater than seventy percent of its maximum charging capacity, used for aggressive charging during emergency low battery situations or when cheap electricity is available during nighttime.

**A4** means no action, which keeps the battery idle at zero percent power with neither charging nor discharging, used when the battery is in optimal state and no immediate action is required.

**A5** means low discharge, which discharges the battery at less than thirty percent of its maximum discharging capacity, used for slight Maximum Demand reduction, electricity arbitrage, or minor peak shaving.

**A6** means medium discharge, which discharges the battery at between thirty and seventy percent of its maximum discharging capacity, used for significant Maximum Demand reduction when demand is high or moderately above the MD threshold.

**A7** means high discharge, which discharges the battery at greater than seventy percent of its maximum discharging capacity, used for aggressive Maximum Demand shaving when demand is extremely high or when the current peak may set the monthly MD record.

**A8** means forced discharge, which is an emergency action that discharges the battery at one hundred percent of its maximum capacity regardless of other conditions, used only when battery level is critically high to prevent overcharge damage, during grid emergencies, or when demand response events require maximum immediate reduction.

---

## Action Strategies by Condition

### A0 - Forced Charge (100% charging power)

A0 strategy can be used when:

1. T0, S0, D4, B0
2. T0, S0, D3, B0
3. T0, S0, D2, B0
4. T0, S0, D1, B0
5. T0, S0, D0, B0
6. T0, S1, D4, B0
7. T0, S1, D3, B0
8. T0, S1, D2, B0
9. T0, S1, D1, B0
10. T0, S1, D0, B0
11. T0, S2, D4, B0
12. T0, S2, D3, B0
13. T0, S2, D2, B0
14. T0, S2, D1, B0
15. T0, S2, D0, B0
16. T0, S3, D4, B0
17. T0, S3, D3, B0
18. T0, S3, D2, B0
19. T0, S3, D1, B0
20. T0, S3, D0, B0
21. T1, S0, D0-4, B0
22. T1, S1, D0-4, B0
23. T1, S2, D0-4, B0
24. T1, S3, D0-4, B0
25. T2, S0, D0-4, B0
26. T3, S0, D0-4, B0
27. T3, S1, D0-4, B0
28. T3, S2, D0-4, B0
29. T3, S3, D0-4, B0
30. T4, S0, D0-4, B0
31. T4, S1, D0-4, B0
32. T4, S2, D0-4, B0
33. T4, S3, D0-4, B0
34. T5, S0, D0-4, B0
35. T5, S1, D0-4, B0
36. T5, S2, D0-4, B0
37. T5, S3, D0-4, B0

---

### A1 - Low Charge (<30% charging power)

A1 strategy can be used when:

1. T0, S0, D4, B0
2. T0, S0, D3, B0
3. T0, S0, D2, B0
4. T0, S0, D1, B0
5. T0, S0, D0, B0
6. T0, S1, D4, B0
7. T0, S1, D3, B0
8. T0, S1, D2, B0
9. T0, S1, D1, B0
10. T0, S1, D0, B0
11. T0, S2, D4, B0
12. T0, S2, D3, B0
13. T0, S2, D2, B0
14. T0, S2, D1, B0
15. T0, S2, D0, B0
16. T0, S3, D4, B0
17. T0, S3, D3, B0
18. T0, S3, D2, B0
19. T0, S3, D1, B0
20. T0, S3, D0, B0
21. T1, S0, D4, B3
22. T1, S0, D3, B3
23. T1, S0, D2, B3
24. T1, S0, D1, B3
25. T1, S0, D0, B3
26. T1, S0, D4, B4
27. T1, S0, D3, B4
28. T1, S0, D2, B4
29. T1, S1, D4, B3
30. T1, S1, D3, B3
31. T1, S1, D4, B4
32. T2, S0, D0-4, B3
33. T3, S0, D0-4, B2
34. T3, S1, D0-4, B2
35. T3, S2, D0-4, B3
36. T3, S3, D0-4, B3
37. T4, S0, D0-4, B2
38. T4, S1, D0-4, B2
39. T4, S2, D0-4, B3
40. T4, S3, D0-4, B3
41. T5, S0, D0-4, B3
42. T5, S1, D0-4, B3
43. T5, S2, D0-4, B4

---

### A2 - Medium Charge (30-70% charging power)

A2 strategy can be used when:

1. T0, S3, D1, B0
2. T0, S3, D0, B0
3. T1, S0, D0-4, B1
4. T1, S0, D0-4, B2
5. T1, S1, D0-4, B1
6. T1, S1, D0-4, B2
7. T1, S2, D0-4, B1
8. T1, S2, D0-4, B2
9. T1, S3, D0-4, B1
10. T1, S3, D0-4, B2
11. T1, S3, D0-4, B0
12. T2, S0, D0-4, B1
13. T2, S0, D0-4, B2
14. T2, S0, D0-4, B0
15. T3, S0, D0-4, B1
16. T3, S1, D0-4, B1
17. T3, S2, D0-4, B1
18. T3, S2, D0-4, B2
19. T3, S3, D0-4, B1
20. T3, S3, D0-4, B2
21. T3, S3, D0-4, B0
22. T4, S0, D0-4, B1
23. T4, S1, D0-4, B1
24. T4, S2, D0-4, B1
25. T4, S2, D0-4, B2
26. T4, S3, D0-4, B1
27. T4, S3, D0-4, B2
28. T5, S0, D0-4, B1
29. T5, S0, D0-4, B2
30. T5, S1, D0-4, B1
31. T5, S1, D0-4, B2
32. T5, S2, D0-4, B1
33. T5, S2, D0-4, B2
34. T5, S3, D0-4, B1
35. T5, S3, D0-4, B2
36. T5, S3, D0-4, B0

---

### A3 - High Charge (>70% charging power)

A3 strategy can be used when:

1. T1, S0, D0-4, B0
2. T1, S0, D0-4, B1
3. T1, S1, D0-4, B0
4. T1, S1, D0-4, B1
5. T1, S2, D0-4, B0
6. T1, S2, D0-4, B1
7. T1, S3, D0-4, B0
8. T1, S3, D0-4, B1
9. T2, S0, D0-4, B0
10. T2, S0, D0-4, B1
11. T3, S3, D0-4, B0
12. T4, S3, D0-4, B0
13. T5, S0, D0-4, B0
14. T5, S0, D0-4, B1
15. T5, S1, D0-4, B0
16. T5, S2, D0-4, B0
17. T5, S3, D0-4, B0

---

### A4 - No Action (0% power)

A4 strategy can be used when:

1. T0, S0, D2, B2
2. T0, S0, D2, B3
3. T0, S0, D1, B2
4. T0, S0, D1, B3
5. T0, S0, D0, B2
6. T0, S0, D0, B3
7. T0, S1, D2, B2
8. T0, S1, D2, B3
9. T0, S1, D1, B2
10. T0, S1, D1, B3
11. T0, S2, D2, B2
12. T0, S2, D2, B3
13. T0, S2, D1, B2
14. T0, S2, D1, B3
15. T0, S3, D1, B2
16. T0, S3, D1, B3
17. T1, S0, D0-4, B3
18. T1, S0, D0-4, B4
19. T1, S1, D0-4, B3
20. T1, S2, D0-4, B3
21. T1, S3, D0-4, B3
22. T1, S3, D0-4, B4
23. T2, S0, D0-4, B3
24. T2, S0, D0-4, B4
25. T3, S0, D0-4, B2
26. T3, S0, D0-4, B3
27. T3, S1, D0-4, B2
28. T3, S1, D0-4, B3
29. T3, S2, D0-4, B3
30. T3, S3, D0-4, B3
31. T4, S0, D0-4, B2
32. T4, S0, D0-4, B3
33. T4, S1, D0-4, B3
34. T4, S2, D0-4, B3
35. T4, S3, D0-4, B3
36. T5, S0, D0-4, B3
37. T5, S1, D0-4, B3
38. T5, S2, D0-4, B3
39. T5, S3, D0-4, B3
40. T5, S3, D0-4, B4

---

### A5 - Low Discharge (<30% discharging power)

A5 strategy can be used when:

1. T0, S0, D3, B1
2. T0, S0, D3, B2
3. T0, S0, D3, B3
4. T0, S0, D2, B2
5. T0, S0, D2, B3
6. T0, S0, D2, B4
7. T0, S0, D1, B3
8. T0, S0, D1, B4
9. T0, S0, D0, B4
10. T0, S1, D3, B2
11. T0, S1, D3, B3
12. T0, S1, D2, B3
13. T0, S1, D1, B4
14. T0, S2, D3, B2
15. T0, S2, D2, B3
16. T0, S2, D1, B4
17. T0, S3, D2, B4
18. T0, S3, D1, B4
19. T0, S3, D1, B5
20. T1, S3, D0-4, B4
21. T1, S3, D0-4, B5
22. T3, S3, D0-4, B4
23. T3, S3, D0-4, B5
24. T4, S3, D0-4, B4
25. T4, S3, D0-4, B5
26. T5, S3, D0-4, B4

---

### A6 - Medium Discharge (30-70% discharging power)

A6 strategy can be used when:

1. T0, S0, D3, B2
2. T0, S0, D3, B3
3. T0, S0, D3, B4
4. T0, S0, D4, B1
5. T0, S0, D4, B2
6. T0, S0, D4, B3
7. T0, S0, D4, B4
8. T0, S1, D3, B2
9. T0, S1, D3, B3
10. T0, S1, D4, B2
11. T0, S1, D4, B3
12. T0, S2, D3, B2
13. T0, S2, D3, B3
14. T0, S2, D4, B2
15. T0, S2, D4, B3
16. T0, S3, D3, B2
17. T0, S3, D3, B3
18. T0, S3, D4, B2
19. T0, S3, D4, B3
20. T3, S3, D0-4, B5
21. T4, S3, D0-4, B5

---

### A7 - High Discharge (>70% discharging power)

A7 strategy can be used when:

1. T0, S0, D4, B2
2. T0, S0, D4, B3
3. T0, S0, D4, B4
4. T0, S0, D4, B5
5. T0, S0, D3, B4
6. T0, S0, D3, B5
7. T0, S1, D4, B2
8. T0, S1, D4, B3
9. T0, S1, D4, B4
10. T0, S2, D4, B2
11. T0, S2, D4, B3
12. T0, S2, D4, B4
13. T0, S3, D4, B2
14. T0, S3, D4, B3
15. T0, S3, D4, B4
16. T0 (last 30 min), S0-3, D3-4, B3-4
17. T1, S3, D0-4, B5

---

### A8 - Forced Discharge (100% discharging power)

A8 strategy can be used when:

1. T0, S0, D4, B3
2. T0, S0, D4, B4
3. T0, S0, D4, B5
4. T0, S1, D4, B3
5. T0, S1, D4, B4
6. T0, S2, D4, B3
7. T0, S2, D4, B4
8. T0, S3, D4, B3
9. T0, S3, D4, B4
10. Any T, Any S, Any D, B5
11. Any T, S3, D0-1, B4
12. Any T, S3, D0-1, B5
13. T2, S0, D0-4, B5
14. T3, S3, D0-4, B5
15. T4, S3, D0-4, B5
16. Any T (grid emergency), Any S, Any D, Any B
17. Any T (demand response), Any S, D4, B2-4
18. Any T (BMS thermal), Any S, Any D, Any B

---

## Summary Table

| Code | Full Meaning | Definition Sentence |
| :--- | :--- | :--- |
| T0 | Weekday Peak Hour | Monday to Friday, 14:00 to 22:00, highest prices and MD risk |
| T1 | Weekday Morning | Monday to Friday, 08:00 to 14:00, preparation window before peak |
| T2 | Weekday Night | Monday to Friday, 22:00 to 08:00, lowest prices for charging |
| T3 | Weekend | Saturday and Sunday all day, low prices and minimal MD risk |
| T4 | Public Holiday | Gazetted holidays all day, low prices and minimal MD risk |
| T5 | Pre-Peak Period | 1-2 hours before peak (12:00-14:00), final preparation window |
| S0 | No Sunlight | Nighttime, 0% PV output |
| S1 | Weak Sunlight | <200 W/m², 0-20% PV output |
| S2 | Medium Sunlight | 200-600 W/m², 20-70% PV output |
| S3 | Strong Sunlight | >600 W/m², 70-100% PV output |
| D0 | Extremely Low Demand | Load < 40% of MD threshold, no risk |
| D1 | Low Demand | Load 40-60% of MD threshold, very low risk |
| D2 | Medium Demand | Load 60-80% of MD threshold, moderate risk |
| D3 | High Demand | Load 80-95% of MD threshold, high risk |
| D4 | Extremely High Demand | Load ≥ 95% of MD threshold, critical risk |
| B0 | Emergency Low | SoC < 10%, prevent deep discharge |
| B1 | Low Warning | SoC 10-20%, avoid discharge, prioritize charge |
| B2 | Normal Low | SoC 20-50%, lower side of optimal range |
| B3 | Normal High | SoC 50-80%, optimal operating range |
| B4 | High Warning | SoC 80-95%, avoid charge, prioritize discharge |
| B5 | Emergency High | SoC > 95%, prevent overcharge |
| A0 | Forced Charge | 100% charge power, emergency only |
| A1 | Low Charge | <30% charge power, gentle top-ups |
| A2 | Medium Charge | 30-70% charge power, routine charging |
| A3 | High Charge | >70% charge power, aggressive charging |
| A4 | No Action | 0% power, idle state |
| A5 | Low Discharge | <30% discharge power, slight MD reduction |
| A6 | Medium Discharge | 30-70% discharge power, significant MD reduction |
| A7 | High Discharge | >70% discharge power, aggressive MD shaving |
| A8 | Forced Discharge | 100% discharge power, emergency only |

---

*End of Document*