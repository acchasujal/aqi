# Station Metadata Audit and Geographical Context Correction

**Date of Audit:** 8 November 2026  
**Reference Document:** `data/raw/challenge/Stations.csv`  
**Status:** Canonical Reference Document  

---

## 1. Ground-Truth Station Metadata from `Stations.csv`

The competition monitors four official continuous ambient air quality monitoring stations (CAAQMS) across the Mumbai Metropolitan Area:

| `location_id` | Official Station Name | Latitude | Longitude | Operator / Network | Sensor ID | True Geographical Setting |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **11606** | **Borivali East, Mumbai - IITM** | 19.232410 | 72.868950 | SAFAR / IITM | 12236418 | Northern suburbs; immediately borders the 103 $\text{km}^2$ protected forest of Sanjay Gandhi National Park (SGNP). |
| **11611** | **Malad West, Mumbai - IITM** | 19.197090 | 72.822040 | SAFAR / IITM | 12236426 | Western suburbs; high-density commercial/residential corridor near Link Road and Malad Creek. |
| **3409510** | **Byculla, Mumbai - BMC** | 18.976700 | 72.838000 | BMC / MPCB | 12238567 | South-Central Mumbai historic urban core; high vehicular traffic density, dense mid-rise urban fabric, near Byculla Zoo / railway corridor. |
| **3409511** | **Shivaji Nagar, Mumbai - BMC** | 19.060498 | 72.923356 | BMC / MPCB | 12238576 | Eastern suburbs (Govandi/Deonar); immediately adjacent to the 132-hectare Deonar Dumping Ground and Sion-Panvel Highway corridor. |

---

## 2. Corrections of Erroneous Labels in Prior Notes

In several early informal notes and working scripts, colloquial placeholders were inadvertently used instead of official station names:

1. **Station 11606 was mistakenly referred to as "Colaba / Coastal South":**
   - **Correction:** Station 11606 is **Borivali East** in the far northern suburbs ($19.23^\circ\text{N}$, $72.87^\circ\text{E}$), over 30 km north of Colaba.
   - **Atmospheric Implication:** Borivali East is not an open marine-cape station. Rather, its relatively lower baseline PM2.5 levels (2024 seasonal mean: 54.81 $\mu\text{g}/\text{m}^3$) are driven by its proximity to the vast canopy of Sanjay Gandhi National Park, which serves as a massive dry deposition particulate sink and buffer against regional urban plume transport.
2. **Station 3409511 was mistakenly referred to as "Khandeshwar, Panvel":**
   - **Correction:** Station 3409511 is **Shivaji Nagar, Govandi/Deonar** ($19.06^\circ\text{N}$, $72.92^\circ\text{E}$), located inside Mumbai proper near the eastern harbour front.
   - **Atmospheric Implication:** In air quality literature (e.g., NEERI, IIT Bombay, and SAFAR studies), Shivaji Nagar is documented as one of the most persistent PM2.5 pollution hotspots in South Asia. It borders the Deonar municipal solid waste landfill (frequent spontaneous subsurface combustion and open waste burning), suffers high density of unpaved roads, and experiences stagnant winter inversion layers trapped between the Trombay hills and eastern creeks. This explains why Shivaji Nagar exhibited extreme historical spikes (such as **688.07 $\mu\text{g}/\text{m}^3$** on 11 November 2025) and has a 2024 seasonal mean of **129.89 $\mu\text{g}/\text{m}^3$**.
3. **Station 3409510 was informally described as "Sion / Eastern Highway":**
   - **Correction:** Station 3409510 is **Byculla** ($18.98^\circ\text{N}$, $72.84^\circ\text{E}$) in South-Central Mumbai. Its 2024 seasonal mean is 75.81 $\mu\text{g}/\text{m}^3$, characteristic of dense inner-city vehicular emissions and commercial street activity.
4. **Station 11611 was informally described as "Bandra":**
   - **Correction:** Station 11611 is **Malad West** ($19.20^\circ\text{N}$, $72.82^\circ\text{E}$) in the western suburbs. Its 2024 seasonal mean is 78.43 $\mu\text{g}/\text{m}^3$, exhibiting strong morning and evening traffic-related diurnal peaks.

---

## 3. Distinguishing Empirical Patterns from Atmospheric Mechanisms

To ensure scientific integrity and compliance with competition rules, we explicitly distinguish between:
- **Observed Empirical Patterns in Validation Data:**
  - Station 11606 (Borivali East) consistently shows the lowest variance and lowest average PM2.5 concentrations among all 4 stations across all folds.
  - Station 3409511 (Shivaji Nagar) exhibits the highest absolute values, largest diurnal amplitudes, and highest frequency of extreme spikes ($>250 \mu\text{g}/\text{m}^3$).
  - Station 11611 (Malad West) and Station 3409510 (Byculla) track closely in intermediate pollution bands (40–80 $\mu\text{g}/\text{m}^3$).
- **Established Meteorological / Atmospheric Physics:**
  - The winter transition in Mumbai (early November) brings a shift from south-westerly maritime winds to north-easterly continental winds, transporting inland agricultural/industrial haze toward the coast.
  - Nocturnal and early-morning radiative cooling creates shallow thermal inversions (<300 m), trapping ground-level emissions until mid-day solar heating expands the planetary boundary layer (>1,200 m).
  - These physics explain why all stations exhibit pronounced morning (09:00–11:00 IST) and late-night (22:00–23:00 IST) peaks, and why Shivaji Nagar (with concentrated local emission sources) experiences severe particulate accumulation during low-wind inversion episodes.

All future reports, feature descriptions, and submission manifests will use official station metadata exclusively.
