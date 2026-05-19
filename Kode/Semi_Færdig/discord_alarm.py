import requests
import json

def send_discord_alarm(message):
    # Erstat med din faktiske Discord Webhook URL
    webhook_url = "https://discord.com/api/webhooks/1503731455061266492/ykKqiX3_BOSIeyfj1d9kF5yRuMeQ64adMxD3uLaC7wpqdaBTL0iRavszEU-ZPWBl4osf"
    
    # Data der sendes til Discord
    data = {
        "content": f"🚨 **ALARM:** {message}",
        "username": "Drone Alarm System"
    }

    try:
        response = requests.post(
            webhook_url, 
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'}
        )
        
        # Tjek om beskeden blev sendt korrekt
        if response.status_code == 204:
            print("Alarm sendt til Discord!")
        else:
            print(f"Fejl ved afsendelse: {response.status_code}")
            
    except Exception as e:
        print(f"En fejl opstod: {e}")

# Eksempel på brug i dit system:
if __name__ == "__main__":
    drone_detected = True

    if drone_detected:
        send_discord_alarm("Der er en drone!")