import discord
from discord import app_commands
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # On utilise ton ID au lieu du pseudo pour plus de sécurité
        self.admin_id = 1454933872142979215 

    # --- 🪄 AJOUTER DE L'ARGENT ---
    @app_commands.command(name="donner", description="Ajouter de l'argent à un joueur (Admin uniquement)")
    async def donner(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        if interaction.user.id != self.admin_id:
            return await interaction.response.send_message(f"⛔ Seul l'administrateur peut utiliser cette commande.", ephemeral=True)
        
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)

        # Utilisation de la DB SQLite du main.py
        cursor = self.bot.db.cursor()
        
        # On vérifie si l'utilisateur existe, sinon on le crée
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (cible.id, 1000))
        
        # On ajoute l'argent
        cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (montant, cible.id))
        self.bot.db.commit()
        
        await interaction.response.send_message(f"🪄 **ADMIN** : `{montant:,} €` ajoutés au portefeuille de **{cible.display_name}** !".replace(',', ' '))

    # --- 💸 RETIRER DE L'ARGENT ---
    @app_commands.command(name="retirer_admin", description="Retirer de l'argent à un joueur (Admin uniquement)")
    async def retirer_admin(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        if interaction.user.id != self.admin_id:
            return await interaction.response.send_message(f"⛔ Seul l'administrateur peut utiliser cette commande.", ephemeral=True)
        
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)

        cursor = self.bot.db.cursor()
        
        # On vérifie si l'utilisateur existe
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (cible.id, 1000))
        
        # On retire l'argent
        cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (montant, cible.id))
        self.bot.db.commit()
        
        await interaction.response.send_message(f"📉 **ADMIN** : `{montant:,} €` retirés du portefeuille de **{cible.display_name}** !".replace(',', ' '))

async def setup(bot):
    await bot.add_cog(Admin(bot))
