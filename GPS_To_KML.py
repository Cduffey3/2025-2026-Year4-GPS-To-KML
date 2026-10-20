import math
import re
import os
from datetime import datetime, timedelta
import sys
from pathlib import Path

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the Earth (meters)."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def clean_gps_file(input_path):
    """
    Cleans GPS data according to requirements and writes to _CLEANED file.
    Returns path to cleaned file.
    """
    # Parameters
    MIN_SPEED = 2.0  # knots, below this is considered stopped
    MIN_DIST = 2.0   # meters, for parked filtering
    STRAIGHT_ANGLE_THRESH = 5.0  # degrees, for straight line filtering
    MAX_JUMP_DIST = 200.0  # meters, max allowed jump between points

    def parse_gprmc(parts):
        try:
            lat = toDecimal(parts[3], parts[4])
            lon = toDecimal(parts[5], parts[6])
            speed = float(parts[7]) if parts[7] else 0.0
            heading = float(parts[8]) if parts[8] else None
            status = parts[2]
            return lat, lon, speed, heading, status
        except Exception:
            return None, None, 0.0, None, ''

    def is_gps_line(line):
        return line.startswith('$GPRMC') or line.startswith('$GPGGA')

    cleaned_lines = []
    last_time = None
    last_lat, last_lon = None, None
    last_speed = 0.0
    last_heading = None
    last_valid = None
    started = False
    prev_lat, prev_lon = None, None

    with open(input_path, 'r+') as f:
        for line in f:
            # Ignore lines with multiple GPS sentences
            if line.count('$GPRMC') + line.count('$GPGGA') > 1:
                continue
            if line.startswith('$GPRMC'):
                #used for calculating speed for GPGGA
                parts = line.strip().split(',')
                utc_time = parts[1]
                hours = int(utc_time[0:2])
                minutes = int(utc_time[2:4])
                seconds = float(utc_time[4:])
                time_sec = hours * 3600 + minutes * 60 + seconds

                lat, lon, speed, heading, status = parse_gprmc(parts)
                if status != 'A' or lat is None or lon is None:
                    continue
                # Ignore junk jumps
                if last_lat is not None and last_lon is not None:
                    dist = haversine(last_lat, last_lon, lat, lon)
                    if dist > MAX_JUMP_DIST:
                        continue
                # Ignore parked points (not moving)
                if not started:
                    if speed < MIN_SPEED:
                        continue
                    started = True
                if speed < MIN_SPEED:
                    # If stopped, only keep first stopped point
                    if last_speed < MIN_SPEED:
                        continue
                cleaned_lines.append(line)
                prev2_lat, prev2_lon = prev_lat, prev_lon
                prev_lat, prev_lon = lat, lon
                last_lat, last_lon = lat, lon
                last_speed = speed
                last_heading = heading
                last_time = time_sec
                last_valid = line
            elif line.startswith('$GPGGA'):
                parts = line.strip().split(',')
                # Parse GPGGA lat/lon
                try:
                    # used for calculating speed for GPGGA
                    utc_time = parts[1]
                    hours = int(utc_time[0:2])
                    minutes = int(utc_time[2:4])
                    seconds = float(utc_time[4:])
                    time_sec = hours * 3600 + minutes * 60 + seconds

                    lat = toDecimal(parts[2], parts[3])
                    lon = toDecimal(parts[4], parts[5])
                except Exception:
                    lat, lon = None, None
                if lat is None or lon is None:
                    continue
                # Ignore junk jumps
                if last_lat is not None and last_lon is not None:
                    dist = haversine(last_lat, last_lon, lat, lon)
                    if dist > MAX_JUMP_DIST:
                        continue

                    dt = time_sec - last_time if last_time is not None else None
                    if dt and dt > 0:
                        speed_mps = dist / dt
                        speed_mph = speed_mps * 2.23694  # convert m/s → mph

                        # Append speed to line
                        line = line.strip() + f",{speed_mph:.2f}"
                # For GPGGA, estimate movement by distance
                if not started:
                    if last_lat is not None and last_lon is not None and last_time is not None:
                        dist = haversine(last_lat, last_lon, lat, lon)
                        if dist < MIN_DIST:
                            continue

                    started = True
                # Ignore parked points (not moving)
                if last_lat is not None and last_lon is not None:
                    dist = haversine(last_lat, last_lon, lat, lon)
                    if dist < MIN_DIST:
                        continue
                cleaned_lines.append(line)
                prev2_lat, prev2_lon = prev_lat, prev_lon
                prev_lat, prev_lon = lat, lon
                last_lat, last_lon = lat, lon
                last_valid = line
            else:
                # Non-GPS lines: keep if needed
                continue
    # Remove trailing parked points
    while cleaned_lines and cleaned_lines[-1].startswith('$GPRMC'):
        parts = cleaned_lines[-1].strip().split(',')
        try:
            speed = float(parts[7]) if parts[7] else 0.0
        except Exception:
            speed = 0.0
        if speed < MIN_SPEED:
            cleaned_lines.pop()
        else:
            break
    # Write cleaned file
    cleaned_path = input_path.replace('.txt', '_CLEANED.txt')
    with open(cleaned_path, 'w') as fout:
        for cl in cleaned_lines:
            fout.write(cl)
            if not cl.endswith('\n'):
                fout.write('\n')
    return cleaned_path

def toDecimal(degrees,direction):
    """
    Converts NMEA into KML standard
    :param degrees: Decimal
    :param direction: N,W,E,S single char
    :return: decimal/float/double
    """
    #split degrees and mintues
    if not degrees or degrees == "":
        return None
    degree, minnute = divmod(float(degrees), 100)
    decimal = degree + (minnute/60)
    if direction in ['S', 'W']:
        #make it negative
        decimal *= -1
    return decimal

def parseLine(line):
    """
    Reads in a Line in cleaned TXT to convert into KML accepted data
    :param line:
    :return: lat and lon in floar form
    """
    parts = line.strip().split(',')
    if line.startswith('$GPRMC'):
        lat = toDecimal(parts[3], parts[4])
        lon = toDecimal(parts[5], parts[6])
        knotSpd = parts[7]
        MPH = float(knotSpd) * 1.151
        return lat, lon, MPH
    elif line.startswith('$GPGGA'):
        lat = toDecimal(parts[2], parts[3])
        lon = toDecimal(parts[4], parts[5])
        if len(parts) == 16:
            knotSpd = parts[len(parts)-1]
        else:
            knotSpd = 1
        MPH = float(knotSpd) * 1.151
        return lat, lon, MPH
    return None

def toKML(txtFile, KML_file):
    """
    :param txtFile:
    :param KML_file:
    :return: None
    """
    coordinates = []
    with open(txtFile, 'r') as file:
        for line in file:
            result = parseLine(line)
            if result:
                lat, lon, MPH = result
                if lat and lon:
                    coordinates.append(f"{lon}, {lat}, {MPH}")

    #Build KML
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
    <Style id="yellowPoly">
        <LineStyle>
            <color>Af00ffff</color>
        <width>6</width>
    </LineStyle>
    <PolyStyle>
        <color>7f00ff00</color>
    </PolyStyle>
    </Style>
    <Placemark>
        <styleUrl>#yellowPoly</styleUrl>
        <LineString>
            <Description>Alltitutde is Speed in MPH</Description>
            <extrude>1</extrude>
            <tessellate>1</tessellate>
            <altitudeMode>absolute</altitudeMode>
            <coordinates>
                {' '.join(coordinates)}
            </coordinates>
        </LineString>
    </Placemark>
</Document>
</kml>
    """
    with open(KML_file, 'w')as file2:
        file2.write(content)

def format_timedelta(td):
    """Return a human-readable string for a timedelta."""
    total_seconds = int(td.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def parse_gprmc_datetime(parts):
    # parts[1] = time hhmmss(.sss), parts[9] = date ddmmyy
    time_str = parts[1] if len(parts) > 1 else ''
    date_str = parts[9] if len(parts) > 9 else ''
    if not time_str or not date_str:
        return None
    # strip fractional seconds if present
    time_main = time_str.split('.')[0]
    # pad time to at least HHMMSS
    if len(time_main) < 6:
        time_main = time_main.ljust(6, '0')
    dt_str = date_str + time_main
    try:
        # date ddmmyy and time HHMMSS
        dt = datetime.strptime(dt_str, '%d%m%y%H%M%S')
        return dt
    except Exception:
        return None

def compute_duration(txtFile):
    """
    Compute duration from first to last valid timestamp in the (cleaned) file.

    This function will try to detect if the file starts or ends while the car is
    already moving. If so it will search the original (raw) file for stationary
    timestamps; if none are found it will estimate start/end times by
    extrapolating using the first/last segment durations.

    Returns (duration_timedelta, info_string) where info_string documents any
    estimation that was performed.
    """
    MIN_SPEED = 2.0  # knots considered moving
    MIN_DIST = 1.0   # meters considered movement for GPGGA-only records

    # Helper to parse lines into records: (dt, lat, lon, speed)
    records = []
    last_known_date = None
    with open(txtFile, 'r') as f:
        for line in f:
            if line.startswith('$GPRMC'):
                parts = line.strip().split(',')
                status = parts[2] if len(parts) > 2 else ''
                if status == 'V':
                    continue
                dt = parse_gprmc_datetime(parts)
                try:
                    lat = toDecimal(parts[3], parts[4])
                    lon = toDecimal(parts[5], parts[6])
                except Exception:
                    lat, lon = None, None
                try:
                    speed = float(parts[7]) if parts[7] else 0.0
                except Exception:
                    speed = 0.0
                if dt:
                    last_known_date = dt.date()
                records.append({'dt': dt, 'lat': lat, 'lon': lon, 'speed': speed, 'src': 'GPRMC'})
            elif line.startswith('$GPGGA'):
                parts = line.strip().split(',')
                # parts[1] = time hhmmss(.sss)
                time_str = parts[1] if len(parts) > 1 else ''
                try:
                    lat = toDecimal(parts[2], parts[3])
                    lon = toDecimal(parts[4], parts[5])
                except Exception:
                    lat, lon = None, None
                dt = None
                if time_str and last_known_date is not None:
                    t_main = time_str.split('.')[0].ljust(6, '0')
                    try:
                        dt = datetime.strptime(f"{last_known_date.strftime('%d%m%y')}{t_main}", '%d%m%y%H%M%S')
                    except Exception:
                        dt = None
                records.append({'dt': dt, 'lat': lat, 'lon': lon, 'speed': None, 'src': 'GPGGA'})

    # Ensure records are ordered and fill in missing dates
    # Compute inferred speeds where missing
    records = [r for r in records if r['lat'] is not None and r['lon'] is not None]
    # propagate dates for GPGGA entries without dt
    for idx, rec in enumerate(records):
        if rec['dt'] is None:
            # look forward/backward for nearest dt
            # prefer previous
            for k in range(idx-1, -1, -1):
                if records[k]['dt'] is not None:
                    rec['dt'] = records[k]['dt']
                    break
            if rec['dt'] is None:
                for k in range(idx+1, len(records)):
                    if records[k]['dt'] is not None:
                        rec['dt'] = records[k]['dt']
                        break

    # Sort records with datetime where available
    records.sort(key=lambda x: (x['dt'] is None, x['dt']))

    # compute inferred speeds where missing using neighboring timestamped records
    for idx in range(1, len(records)):
        prev_rec = records[idx-1]
        next_rec = records[idx]
        if prev_rec['dt'] is None or next_rec['dt'] is None:
            continue
        dt_seconds = (next_rec['dt'] - prev_rec['dt']).total_seconds()
        if dt_seconds <= 0:
            continue
        dist = haversine(prev_rec['lat'], prev_rec['lon'], next_rec['lat'], next_rec['lon'])
        inferred_speed_m_s = dist / dt_seconds
        # convert m/s to knots (1 m/s = 1.943844 knots)
        inferred_knots = inferred_speed_m_s * 1.943844
        if prev_rec['speed'] is None:
            prev_rec['speed'] = inferred_knots
        if next_rec['speed'] is None:
            next_rec['speed'] = inferred_knots

    # Find first and last timestamped records
    timestamped = [r for r in records if r['dt'] is not None]
    if not timestamped:
        return None, 'no timestamped records available'
    first = timestamped[0]
    last = timestamped[-1]
    first_dt = first['dt']
    last_dt = last['dt']

    info_msgs = []

    # If file likely started while moving: first speed >= MIN_SPEED
    started_moving_at_start = (first['speed'] is not None and first['speed'] >= MIN_SPEED)
    # If file likely ended while moving (i.e., last speed >= MIN_SPEED), try to find later stationary
    was_moving_at_end = (last['speed'] is not None and last['speed'] >= MIN_SPEED)

    raw_candidate = txtFile.replace('_CLEANED', '')

    # Helper: search raw file for nearest stationary timestamp before/after
    def search_raw_for_stationary(raw_path, before_dt=None, after_dt=None):
        if not os.path.exists(raw_path):
            return None
        candidate = None
        with open(raw_path, 'r') as raw_file:
            for line in raw_file:
                if not line.startswith('$GPRMC'):
                    continue
                parts = line.strip().split(',')
                status = parts[2] if len(parts) > 2 else ''
                if status == 'V':
                    continue
                dt = parse_gprmc_datetime(parts)
                if dt is None:
                    continue
                try:
                    speed = float(parts[7]) if parts[7] else 0.0
                except Exception:
                    speed = 0.0
                if before_dt and dt < before_dt and speed < MIN_SPEED:
                    candidate = dt
                if after_dt and dt > after_dt and speed < MIN_SPEED:
                    return dt
        return candidate

    start_dt = first_dt
    end_dt = last_dt

    if started_moving_at_start:
        # try to find a stationary timestamp earlier in raw file
        found = search_raw_for_stationary(raw_candidate, before_dt=first_dt)
        if found:
            info_msgs.append(f'Found earlier stationary timestamp in raw file: {found.isoformat()}')
            start_dt = found
        else:
            # estimate by subtracting the first segment duration (if available)
            if len(timestamped) >= 2:
                seg_dt = (timestamped[1]['dt'] - timestamped[0]['dt']).total_seconds()
                if seg_dt > 0:
                    start_dt = first_dt - timedelta(seconds=seg_dt)
                    info_msgs.append(f'Estimated start time by back-extrapolating {int(seg_dt)} seconds')
                else:
                    start_dt = first_dt - timedelta(seconds=60)
                    info_msgs.append('Estimated start time by subtracting 60 seconds')
            else:
                start_dt = first_dt - timedelta(seconds=60)
                info_msgs.append('Estimated start time by subtracting 60 seconds')

    if was_moving_at_end:
        found_after = search_raw_for_stationary(raw_candidate, after_dt=last_dt)
        if found_after:
            info_msgs.append(f'Found later stationary timestamp in raw file: {found_after.isoformat()}')
            end_dt = found_after
        else:
            if len(timestamped) >= 2:
                seg_dt = (timestamped[-1]['dt'] - timestamped[-2]['dt']).total_seconds()
                if seg_dt > 0:
                    end_dt = last_dt + timedelta(seconds=seg_dt)
                    info_msgs.append(f'Estimated end time by forward-extrapolating {int(seg_dt)} seconds')
                else:
                    end_dt = last_dt + timedelta(seconds=60)
                    info_msgs.append('Estimated end time by adding 60 seconds')
            else:
                end_dt = last_dt + timedelta(seconds=60)
                info_msgs.append('Estimated end time by adding 60 seconds')

    duration = end_dt - start_dt
    info = '; '.join(info_msgs) if info_msgs else 'exact'
    return duration, info

def main(args):
    if len(args) == 0:
        print("Error: No input file provided.")
        return
    input_file = args[0]
    input_filename = Path(input_file).stem
    script_dir = Path(__file__).parent
    input_dir = script_dir / "InputData"
    kml_dir = script_dir / "KMLData"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(kml_dir, exist_ok=True)
    input_path = os.path.join(input_dir, input_file)
    outputKML = os.path.join(kml_dir, input_file[:len(input_file)-4] + ".kml") #len -4 strips the .txt from file to make it a KML

    # Clean GPS file
    cleaned_path = clean_gps_file(input_path)

    # Convert cleaned file to KML
    toKML(cleaned_path, outputKML)

    print(f"KML file created: {outputKML}")
    print("Open in Google Earth")

    # compute and print trip duration (may include estimates)
    result = compute_duration(cleaned_path)
    if result is None:
        print("Trip duration: unavailable (no timestamped records found)")
    else:
        duration, info = result
        if duration:
            print(f"Trip duration: {format_timedelta(duration)}")
            if info and info != 'exact':
                print(f"Note: {info}")
        else:
            print("Trip duration: 00:00:00")

if __name__ == "__main__":
    main(sys.argv[1:])