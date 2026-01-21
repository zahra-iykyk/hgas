import network
import socket
import time
import machine
from machine import Pin
import json

# Konfigurasi WiFi
WIFI_SSID = "iot"
WIFI_PASSWORD = "Iot@12345678"

# Konfigurasi pin
RELAY_PINS = {
    "pompa1": 16,
    "pompa2": 17
}

# Inisialisasi relay
relays = {}
for name, pin in RELAY_PINS.items():
    relays[name] = Pin(pin, Pin.OUT)
    relays[name].value(1)  # Matikan relay saat start (aktif low)

# Status pompa
pump_status = {
    "pompa1": False,
    "pompa2": False
}

# Jadwal aktif pompa
pump_schedule = {
    "pompa1": [
        {"day": 0, "hour": 8, "minute": 0, "duration": 300, "last_executed": None},
        {"day": 2, "hour": 10, "minute": 0, "duration": 6, "last_executed": None},
        {"day": 5, "hour": 9, "minute": 0, "duration": 900, "last_executed": None},
    ],
    "pompa2": [
        {"day": 2, "hour": 10, "minute": 0, "duration": 300, "last_executed": None},
        {"day": 2, "hour": 10, "minute": 0, "duration": 6, "last_executed": None},
        {"day": 6, "hour": 11, "minute": 0, "duration": 900, "last_executed": None},
    ]
}

# Timer aktif pompa
active_timers = {
    "pompa1": {"active": False, "end_time": 0},
    "pompa2": {"active": False, "end_time": 0}
}

# Koneksi WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Menghubungkan ke WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
    
    if wlan.isconnected():
        print("\nTerhubung ke WiFi!")
        print("Alamat IP:", wlan.ifconfig()[0])
        return wlan.ifconfig()[0]
    else:
        print("\nGagal terhubung ke WiFi!")
        return None

# Setup Access Point
def setup_access_point():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="PompaController", password="12345678", authmode=3)
    print("Access Point aktif!")
    print("SSID: PompaController")
    print("Password: 12345678")
    print("Alamat IP:", ap.ifconfig()[0])
    return ap.ifconfig()[0]

# Fungsi kontrol pompa
def toggle_pump(pump_name):
    if pump_name in pump_status:
        pump_status[pump_name] = not pump_status[pump_name]
        relays[pump_name].value(0 if pump_status[pump_name] else 1)
        print(f"{pump_name}: {'HIDUP' if pump_status[pump_name] else 'MATI'}")
        
        if not pump_status[pump_name]:
            active_timers[pump_name] = {"active": False, "end_time": 0}
            
        return pump_status[pump_name]
    return None

def set_pump(pump_name, state):
    if pump_name in pump_status:
        pump_status[pump_name] = state
        relays[pump_name].value(0 if state else 1)
        print(f"{pump_name}: {'HIDUP' if state else 'MATI'}")
        
        if not state:
            active_timers[pump_name] = {"active": False, "end_time": 0}
            
        return state
    return None

# Aktifkan pompa dengan timer
def activate_pump_with_timer(pump_name, duration):
    set_pump(pump_name, True)
    active_timers[pump_name] = {
        "active": True,
        "end_time": time.time() + duration
    }
    print(f"Timer {pump_name} aktif: {duration} detik")

# Cek jadwal
def check_schedule():
    current_time = time.localtime()
    current_weekday = current_time[6]
    current_hour = current_time[3]
    current_minute = current_time[4]
    
    for pump_name, schedules in pump_schedule.items():
        for schedule in schedules:
            if (schedule["day"] == current_weekday and 
                schedule["hour"] == current_hour and 
                schedule["minute"] == current_minute):
                
                today = time.localtime()
                today_date = (today[0], today[1], today[2])
                
                if schedule["last_executed"] != today_date:
                    activate_pump_with_timer(pump_name, schedule["duration"])
                    schedule["last_executed"] = today_date
                    print(f"Jadwal {pump_name} dijalankan")

# Cek timer
def check_timers():
    current_time = time.time()
    
    for pump_name, timer_info in active_timers.items():
        if timer_info["active"] and current_time >= timer_info["end_time"]:
            set_pump(pump_name, False)
            print(f"Timer {pump_name} selesai")

# HTML Dashboard
def generate_html():
    status1 = "HIDUP" if pump_status["pompa1"] else "MATI"
    status2 = "HIDUP" if pump_status["pompa2"] else "MATI"
    status_color1 = "#28a745" if pump_status["pompa1"] else "#dc3545"
    status_color2 = "#28a745" if pump_status["pompa2"] else "#dc3545"
    
    # Waktu saat ini
    current_time = time.localtime()
    time_str = f"{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}"
    date_str = f"{current_time[2]}/{current_time[1]}/{current_time[0]}"
    
    # Timer info
    timer_info1 = ""
    timer_info2 = ""
    
    if active_timers["pompa1"]["active"]:
        time_left = int(active_timers["pompa1"]["end_time"] - time.time())
        if time_left > 0:
            timer_info1 = f'<div class="timer-info">Timer: {time_left} detik</div>'
    
    if active_timers["pompa2"]["active"]:
        time_left = int(active_timers["pompa2"]["end_time"] - time.time())
        if time_left > 0:
            timer_info2 = f'<div class="timer-info">Timer: {time_left} detik</div>'
    
    # Format jadwal
    schedule_html = ""
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    
    for pump_name, schedules in pump_schedule.items():
        schedule_html += f"<h3>Jadwal {pump_name}:</h3><ul>"
        for sched in schedules:
            minutes = sched['duration'] // 60
            schedule_html += f"<li>{days[sched['day']]} jam {sched['hour']:02d}:{sched['minute']:02d} - {minutes} menit</li>"
        schedule_html += "</ul>"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Kontrol Pompa</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f0f0f0; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; }}
        .time-display {{ text-align: center; font-size: 1.2em; color: #666; margin-bottom: 20px; }}
        .pump-container {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }}
        .pump-control {{ flex: 1; min-width: 300px; padding: 20px; background-color: #f8f9fa; border-radius: 10px; text-align: center; }}
        .status {{ font-size: 1.5em; font-weight: bold; margin: 15px 0; padding: 10px; border-radius: 5px; background-color: #e9ecef; }}
        .button {{ padding: 12px 24px; font-size: 1.1em; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }}
        .toggle {{ background-color: #007bff; color: white; }}
        .on {{ background-color: #28a745; color: white; }}
        .off {{ background-color: #dc3545; color: white; }}
        .schedule {{ margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 10px; }}
        .timer-info {{ margin-top: 10px; font-style: italic; color: #666; }}
        .auto-refresh {{ text-align: center; margin-top: 20px; color: #999; }}
    </style>
    <script>
        function togglePump(pumpName) {{
            fetch('/toggle/' + pumpName)
                .then(response => response.text())
                .then(data => {{
                    setTimeout(() => {{ location.reload(); }}, 100);
                }});
        }}
        
        function setPump(pumpName, state) {{
            fetch('/set/' + pumpName + '/' + (state ? '1' : '0'))
                .then(response => response.text())
                .then(data => {{
                    setTimeout(() => {{ location.reload(); }}, 100);
                }});
        }}
        
        // AUTO-REFRESH 1 DETIK - PERUBAHAN DI SINI
        setTimeout(() => {{
            location.reload();
        }}, 1000);
    </script>
</head>
<body>
    <div class="container">
        <h1>Dashboard Kontrol Pompa</h1>
        
        <div class="time-display">
            <strong>{date_str} {time_str}</strong>
        </div>
        
        <div class="pump-container">
            <div class="pump-control">
                <h2>POMPA 1</h2>
                <div class="status" style="color: {status_color1};">{status1}</div>
                <button class="button toggle" onclick="togglePump('pompa1')">TOGGLE</button><br>
                <button class="button on" onclick="setPump('pompa1', true)">HIDUPKAN</button>
                <button class="button off" onclick="setPump('pompa1', false)">MATIKAN</button>
                {timer_info1}
            </div>
            
            <div class="pump-control">
                <h2>POMPA 2</h2>
                <div class="status" style="color: {status_color2};">{status2}</div>
                <button class="button toggle" onclick="togglePump('pompa2')">TOGGLE</button><br>
                <button class="button on" onclick="setPump('pompa2', true)">HIDUPKAN</button>
                <button class="button off" onclick="setPump('pompa2', false)">MATIKAN</button>
                {timer_info2}
            </div>
        </div>
        
        <div class="schedule">
            <h2>JADWAL OTOMATIS</h2>
            {schedule_html}
            <p><em>Sistem akan otomatis menghidupkan pompa sesuai jadwal</em></p>
        </div>
        
        <div class="auto-refresh">
            Halaman akan refresh otomatis setiap 1 detik
        </div>
    </div>
</body>
</html>"""
    return html

# Web server
def run_web_server(ip_address):
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    
    print(f"Server berjalan di http://{ip_address}")
    
    # Timeout socket 1 detik
    s.settimeout(1.0)
    
    while True:
        try:
            check_schedule()
            check_timers()
            
            try:
                cl, addr = s.accept()
                print(f"Koneksi dari: {addr}")
                
                request = cl.recv(1024).decode()
                
                if "GET / " in request or "GET /index" in request or "GET / HTTP" in request:
                    response = generate_html()
                    cl.send('HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n')
                    cl.send(response)
                    
                elif "GET /toggle/" in request:
                    if "/toggle/pompa1" in request:
                        new_state = toggle_pump("pompa1")
                        response_json = json.dumps({"pump": "pompa1", "status": new_state})
                    elif "/toggle/pompa2" in request:
                        new_state = toggle_pump("pompa2")
                        response_json = json.dumps({"pump": "pompa2", "status": new_state})
                    else:
                        response_json = json.dumps({"error": "Pompa tidak ditemukan"})
                    
                    cl.send('HTTP/1.1 200 OK\r\nContent-type: application/json\r\n\r\n')
                    cl.send(response_json)
                    
                elif "GET /set/" in request:
                    parts = request.split()
                    if len(parts) > 0:
                        url = parts[1]
                        url_parts = url.split('/')
                        if len(url_parts) >= 4:
                            pump_name = url_parts[2]
                            state = int(url_parts[3])
                            new_state = set_pump(pump_name, bool(state))
                            response_json = json.dumps({"pump": pump_name, "status": new_state})
                            cl.send('HTTP/1.1 200 OK\r\nContent-type: application/json\r\n\r\n')
                            cl.send(response_json)
                            
                else:
                    cl.send('HTTP/1.1 404 Not Found\r\n\r\n')
                    
            except socket.timeout:
                continue
            except OSError as e:
                if e.errno == 110:
                    continue
            finally:
                try:
                    cl.close()
                except:
                    pass
                    
        except KeyboardInterrupt:
            print("\nServer dihentikan")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

# Setup time
def setup_time():
    try:
        import ntptime
        ntptime.host = "pool.ntp.org"
        ntptime.settime()
        print("Waktu disinkronisasi")
    except:
        print("Gagal sinkronisasi waktu")

# Main program
def main():
    print("=== SISTEM KONTROL POMPA ===")
    print("Pin 16: Pompa 1")
    print("Pin 17: Pompa 2")
    
    setup_time()
    
    ip_address = connect_wifi()
    
    if ip_address is None:
        print("\nMenggunakan mode Access Point...")
        ip_address = setup_access_point()
    
    try:
        run_web_server(ip_address)
    except KeyboardInterrupt:
        print("\nProgram dihentikan")
    finally:
        print("Mematikan semua pompa...")
        for pump_name in pump_status:
            set_pump(pump_name, False)

# Jalankan program
if __name__ == "__main__":
    main()
