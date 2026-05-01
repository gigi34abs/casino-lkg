import discord
from discord.ext import commands
import os
import threading
from flask import Flask
import sqlite3
import logging

# --- 1. CONFIGURATION DES LOGS ---
logging.basicConfig(level=logging.INFO)

# --- 2. LE SERVEUR POUR RAILWAY (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): 
    return "✅ Bot Casino Opérationnel sur Railway !"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 3. LE CŒUR DU BOT ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        
        # --- CONFIGURATION SQLITE POUR RAILWAY ---
        # On utilise le dossier /data lié au Volume Railway
        self.db_path = "data/database.db" 
        
        # Vérification si le dossier existe (évite les crashs au premier lancement)
        if not os.path.exists("data"):
            os.makedirs("data")
            
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                money INTEGER DEFAULT 1000,
                banque INTEGER DEFAULT 0,
                last_daily REAL DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                entreprise_secours INTEGER DEFAULT 0,
                last_secours_payout REAL DEFAULT 0,
                last_secours_claim REAL DEFAULT 0
            )
        ''')
        self.db.commit()
        print("🗄️ Base de données SQLite prête dans /data !")

    async def setup_hook(self):
        extensions = ['banque', 'jeux', 'autre', 'boutique', 'admin', 'autres2']
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Extension chargée : {ext}")
            except Exception as e:
                print(f"❌ Erreur sur {ext} : {e}")
        
        await self.tree.sync()
        print("✨ Slash Commands synchronisées !")

    async def on_ready(self):
        print(f"---")
        print(f"🤖 Connecté : {self.user.name}")
        print(f"🟢 Prêt à jouer !")
        print(f"---")
        await self.change_presence(activity=discord.Game(name="Plumer le casino 🎰"))

# --- 4. LANCEMENT ---
bot = MyBot()

@bot.event
async def on_close():
    bot.db.close()
    print("🔌 Connexion SQLite fermée.")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    token = os.environ.get('TOKEN')
    
    if token:
        try:
            bot.run(token)
        except Exception as e:
            print(f"💥 Erreur fatale : {e}")
    else:
        print("❌ ERREUR : Aucun TOKEN dans les variables Railway !")
