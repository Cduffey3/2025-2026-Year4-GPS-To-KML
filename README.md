# 2025-2026-Year4-GPS-To-KML
This partner project was done to demonstrate data mining and cleaning for practical use.
this project relied on given GPS files which had the professors real location
to replicate running the file create a file that follows this structure in a .txt file
## Structure of GPS file
$GPRMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,x.x,a,m*hh
$GPGGA,hhmmss.ss,ddmm.mmmm,N/S,dddmm.mmmm,E/W,1,NS,HDOP,AAlt,M,Speration,Checksum
## GPRMC Field Breakdown
* **$GPRMC**: Sentence ID / Header
* **hhmmss.ss**: UTC time of fix (hours, minutes, seconds, milliseconds)
* **A**: Data status (`A` = Valid fix, `V` = Navigation receiver warning)
* **llll.ll**: Latitude (degrees and decimal minutes)
* **a**: Hemisphere for latitude (`N` = North, `S` = South)
* **yyyyy.yy**: Longitude (degrees and decimal minutes)
* **a**: Hemisphere for longitude (`E` = East, `W` = West)
* **x.x**: Speed over ground in knots
* **x.x**: Track made good in degrees True
* **ddmmyy**: UTC date of fix (day, month, year)
* **x.x**: Magnetic variation degrees
* **a**: Direction of magnetic variation (`E` = East, `W` = West)
* **m**: Mode indicator (`A` = Autonomous, `D` = Differential, `E` = Estimated, `M` = Manual, `S` = Simulator, `N` = Data not valid)
* **\*hh**: Checksum (hexadecimal value to verify data integrity)
## GPGGA Field Breakdown
* **$GPGGA**: Sentence ID / Header
* **hhmmss.ss**: UTC time of fix (hours, minutes, seconds, milliseconds)
* **ddmm.mmmm**: Latitude (ddmm.mmmm)
* **N/S**: Latitude hemisphere indicator (`N` = North, `S` = South)	
* **dddmm.mmmm**: Longitude (dddmm.mmmm)
* **E/W**: Longitude hemisphere indicator (`E` = East, `W` = West)
* **1**: GPS Quality Indicator (1-6)
* **NS**: Number of satellites in use (00 to 24+)
* **HDOP**: Horizontal Dilution of Precision (i.e 0.9)
* **AAlt**: Antenna altitude above/below mean sea level (geoid) (i.e 545.4)
* **M**: Units of antenna altitude (`M` = meters)
* **Speration**: Geoidal separation (I.e 46.9)
* **Checksum**:Checksum (preceded by an asterisk *) (i.e *47)
## Logic
Demonstrate file cleaning and transformation for real world use
