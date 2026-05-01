import discord
from discord.ext import commands
import os
import threading
from flask import Flask
import sqlite3 # <--- Ajouté pour SQLite

# --- 1. LE SERVEUR POUR RAILWAY (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): 
    return "✅ Bot Casino Opérationnel sur Railway !"

def run_web():
    # Railway utilise la variable d'environnement PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. LE CŒUR DU BOT ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        
        # --- INITIALISATION SQLITE ---
        # On crée la connexion à la base de données ici pour qu'elle soit accessible partout
        self.db = sqlite3.connect("database.db")
        self.create_tables()

    def create_tables(self):
        cursor = self.db.cursor()
        # Création de la table avec TOUTES les colonnes pour tous tes fichiers .py
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
        print("🗄️ Base de données SQLite initialisée avec succès !")

    async def setup_hook(self):
        # On charge tes fichiers banque.py, jeux.py, etc.
        extensions = ['banque', 'jeux', 'autre', 'boutique', 'admin', 'autres2']
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Extension chargée : {ext}")
            except Exception as e:
                print(f"❌ Impossible de charger {ext} : {e}")
        
        await self.tree.sync()
        print("✨ Commandes slash synchronisées !")

# --- 3. LANCEMENT ---
bot = MyBot()

if __name__ == "__main__":
    # Lancement du serveur web pour éviter que Railway ne coupe le bot
    threading.Thread(target=run_web, daemon=True).start()
    
    # Récupération du Token
    token = os.environ.get('TOKEN')
    
    if token:
        bot.run(token)
    else:
        print("❌ ERREUR : Aucun TOKEN trouvé dans les variables d'environnement !")
