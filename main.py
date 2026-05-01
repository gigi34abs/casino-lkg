import discord
from discord.ext import commands
import os
import threading
from flask import Flask
import sqlite3
import logging

# --- 1. CONFIGURATION DES LOGS (Pour voir les erreurs sur Railway) ---
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
        
        # Chemin de la base de données (Prêt pour les volumes Railway)
        # Si tu crées un volume /data sur Railway, utilise : "data/database.db"
        self.db_path = "database.db" 
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.db.cursor()
        # On regroupe tout ici : argent, banque, daily et secours
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
        print("🗄️ Base de données SQLite prête !")

    async def setup_hook(self):
        # Liste de tes fichiers .py
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
        print(f"🤖 Connecté en tant que : {self.user.name}")
        print(f"🆔 ID : {self.user.id}")
        print(f"🟢 Le bot est prêt à encaisser les mises !")
        print(f"---")
        # Petit statut stylé
        await self.change_presence(activity=discord.Game(name="Plumer le casino 🎰"))

# --- 4. LANCEMENT ---
bot = MyBot()

# Gestion propre de la fermeture
@bot.event
async def on_close():
    bot.db.close()
    print("🔌 Connexion SQLite fermée.")

if __name__ == "__main__":
    # Lancement du serveur Flask en thread séparé
    threading.Thread(target=run_web, daemon=True).start()
    
    # Récupération du Token (Variable d'environnement sur Railway)
    token = os.environ.get('TOKEN')
    
    if token:
        try:
            bot.run(token)
        except Exception as e:
            print(f"💥 Erreur fatale au lancement : {e}")
    else:
        print("❌ ERREUR : Le TOKEN est introuvable dans les variables Railway !")
