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

ADMIN_IDS = [
    1495018019674390678,
    1433802915205742612,
    1342146881446350929
]

# --- 2. SERVEUR DE MAINTIEN ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot Opérationnel"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 3. STRUCTURE DU BOT ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)
        
        if not os.path.exists("data"):
            os.makedirs("data")
        self.db = sqlite3.connect("data/database.db", check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.db.cursor()
        # Création avec le nouveau défaut de 100€
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
        
        # --- RESET FORCE POUR LES ANCIENS COMPTES ---
        # Si un joueur a exactement 1000€ (le départ d'avant), on le passe à 100€
        cursor.execute("UPDATE users SET money = 100 WHERE money = 1000")
        
        self.db.commit()

    async def setup_hook(self):
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
        
        await self.tree.sync()
        print("✨ Toutes les commandes sont synchronisées !")

bot = MyBot()

# --- 4. LE VERROU DE SÉCURITÉ GLOBAL ---
@bot.tree.interaction_check
async def global_check(interaction: discord.Interaction) -> bool:
    # Les Admins passent tout
    if interaction.user.id in ADMIN_IDS:
        return True

    # Exception pour le panel de vérification (pour que les nouveaux puissent cliquer)
    # On laisse passer l'interaction si elle provient du bouton de vérification
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get('custom_id') == "btn_acces_casino":
            return True

    # Vérification du Rôle VIP
    has_vip = any(role.id == ID_ROLE_VIP for role in interaction.user.roles)
    if not has_vip:
        # On ne bloque pas la commande /setup_acces si c'est un admin (déjà géré plus haut)
        await interaction.response.send_message("🚫 **Accès refusé** : Tu dois avoir le rôle VIP pour utiliser le bot.", ephemeral=True)
        return False

    # Vérification de la Catégorie
    current_cat = getattr(interaction.channel, 'category_id', None)
    if current_cat != ID_CATEGORIE_CASINO:
        await interaction.response.send_message(f"🎰 **Mauvais salon** : Va dans la catégorie <#{ID_CATEGORIE_CASINO}> pour jouer !", ephemeral=True)
        return False

    return True

# --- 5. LANCEMENT ---
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    token = os.environ.get('TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ ERREUR : Aucun TOKEN trouvé.")
