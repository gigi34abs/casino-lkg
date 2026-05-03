import discord
from discord.ext import commands
from discord import app_commands
import os
import threading
from flask import Flask
import sqlite3

# --- 1. CONFIGURATION DES ACCÈS ---
ID_CATEGORIE_CASINO = 1498394439079559318
ID_ROLE_VIP = 1499809955841310871

# Tes IDs d'utilisateurs pour un accès total (Admins)
ADMIN_IDS = [
    1495018019674390678,
    1433802915205742612,
    1342146881446350929
]

# --- 2. SERVEUR DE MAINTIEN (RAILWAY) ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot Opérationnel"

def run_web():
    # Railway utilise la variable d'environnement PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 3. STRUCTURE DU BOT ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        
        # Connexion SQLite
        if not os.path.exists("data"):
            os.makedirs("data")
        self.db = sqlite3.connect("data/database.db", check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.db.cursor()
        # MODIFICATION : money DEFAULT passe de 1000 à 100
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                money INTEGER DEFAULT 100,
                banque INTEGER DEFAULT 0,
                last_daily REAL DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                entreprise_secours INTEGER DEFAULT 0,
                last_secours_payout REAL DEFAULT 0,
                last_secours_claim REAL DEFAULT 0
            )
        ''')
        self.db.commit()

    async def setup_hook(self):
        # On charge toutes tes extensions
        extensions = [
            'banque', 
            'jeux', 
            'admin', 
            'autre', 
            'boutique', 
            'autres2', 
            'verification'
        ]
        
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Extension chargée : {ext}")
            except Exception as e:
                print(f"❌ Erreur sur {ext} : {e}")
        
        # Synchronisation des commandes slash avec Discord
        await self.tree.sync()
        print("✨ Toutes les commandes sont synchronisées !")

bot = MyBot()

# --- 4. LE VERROU DE SÉCURITÉ GLOBAL ---
@bot.tree.interaction_check
async def global_check(interaction: discord.Interaction) -> bool:
    # A. Si l'utilisateur est un ADMIN (par ID), il passe tout
    if interaction.user.id in ADMIN_IDS:
        return True

    # B. Vérification du Rôle VIP (pour les autres)
    has_vip = any(role.id == ID_ROLE_VIP for role in interaction.user.roles)
    if not has_vip:
        await interaction.response.send_message("🚫 **Accès refusé** : Tu dois avoir le rôle VIP pour utiliser le bot.", ephemeral=True)
        return False

    # C. Vérification de la Catégorie (pour les autres)
    current_cat = getattr(interaction.channel, 'category_id', None)
    if current_cat != ID_CATEGORIE_CASINO:
        await interaction.response.send_message(f"🎰 **Mauvais salon** : Va dans la catégorie <#{ID_CATEGORIE_CASINO}> pour jouer !", ephemeral=True)
        return False

    return True

# --- 5. LANCEMENT ---
if __name__ == "__main__":
    # Démarrage du serveur web pour Railway
    threading.Thread(target=run_web, daemon=True).start()
    
    # Récupération du Token
    token = os.environ.get('TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ ERREUR : Aucun TOKEN trouvé dans les variables d'environnement Railway.")
