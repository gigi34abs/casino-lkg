import discord
from discord.ext import commands
from discord import app_commands
import os
import threading
from flask import Flask
import sqlite3
import logging

# --- 1. CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
ID_CATEGORIE_CASINO = 1498394439079559318
ID_ROLE_VIP = 1499809955841310871
ID_ROLE_ADMIN = 1454933872142979215

# --- 2. SERVEUR FLASK (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot Casino Opérationnel !"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 3. CLASSE DU BOT ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        
        # SQLite
        if not os.path.exists("data"): os.makedirs("data")
        self.db = sqlite3.connect("data/database.db", check_same_thread=False)
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

    async def setup_hook(self):
        # Chargement des extensions
        extensions = ['banque', 'jeux', 'autre', 'boutique', 'admin', 'autres2']
        for ext in extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                print(f"❌ Erreur sur {ext} : {e}")
        
        # Synchronisation
        await self.tree.sync()
        print("✨ Commandes synchronisées et verrouillées !")

bot = MyBot()

# --- 4. LE VERROU GLOBAL (SÉCURITÉ) ---
@bot.tree.interaction_check
async def global_check(interaction: discord.Interaction) -> bool:
    # 1. On laisse passer les Admins partout sans restriction
    if any(role.id == ID_ROLE_ADMIN for role in interaction.user.roles):
        return True

    # 2. Vérification du Rôle VIP (pour tous les autres)
    if not any(role.id == ID_ROLE_VIP for role in interaction.user.roles):
        await interaction.response.send_message("🚫 Tu n'as pas le rôle VIP pour utiliser le casino !", ephemeral=True)
        return False

    # 3. Vérification de la Catégorie (pour tous les autres)
    if interaction.channel.category_id != ID_CATEGORIE_CASINO:
        await interaction.response.send_message(f"🎰 Les commandes sont autorisées uniquement dans la catégorie <#{ID_CATEGORIE_CASINO}> !", ephemeral=True)
        return False

    return True

# --- 5. GESTION DES ERREURS DE PERMISSION ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message("❌ Tu n'as pas le rôle requis pour cette commande spécifique.", ephemeral=True)
    else:
        # Log l'erreur pour débugger si besoin
        print(f"Erreur commande: {error}")

# --- 6. LANCEMENT ---
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    token = os.environ.get('TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ Aucun TOKEN trouvé !")
