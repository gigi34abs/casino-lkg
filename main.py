import discord
from discord.ext import commands
from discord import app_commands # Ajout nécessaire pour les erreurs de rôle
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
        
        self.db_path = "data/database.db" 
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

    # ==================== DOUBLE SÉCURITÉ GLOBALE ====================
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ALLOWED_CATEGORY_ID = 1498394439079559318
        ALLOWED_ROLE_ID = 1499809955841310871

        # 1. Vérification du Rôle
        role = interaction.user.get_role(ALLOWED_ROLE_ID)
        if not role:
            await interaction.response.send_message(
                "🚫 **Accès refusé** : Tu n'as pas le rôle VIP requis pour utiliser le casino.", 
                ephemeral=True
            )
            return False

        # 2. Vérification de la Catégorie
        if interaction.channel and hasattr(interaction.channel, 'category_id'):
            if interaction.channel.category_id != ALLOWED_CATEGORY_ID:
                await interaction.response.send_message(
                    f"🎰 **Mauvais endroit** : Les jeux sont réservés aux salons de la catégorie <#{ALLOWED_CATEGORY_ID}>.", 
                    ephemeral=True
                )
                return False
        
        return True # Si tout est OK
    # ================================================================

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
