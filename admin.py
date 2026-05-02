import discord
from discord import app_commands
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Vos 3 IDs d'administrateurs
        self.admin_ids = [
            1495018019674390678,
            1433802915205742612,
            1342146881446350929
        ]

    # --- 🪄 AJOUTER DE L'ARGENT ---
    @app_commands.command(name="donner", description="Ajouter de l'argent à un joueur (Admin uniquement)")
    async def donner(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        # Vérification si l'utilisateur est dans la liste des admins
        if interaction.user.id not in self.admin_ids:
            return await interaction.response.send_message("⛔ Seul l'administrateur peut utiliser cette commande.", ephemeral=True)
        
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)

        cursor = self.bot.db.cursor()
        
        # On vérifie si l'utilisateur existe
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (cible.id, 1000))
        
        # On ajoute l'argent
        cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (montant, cible.id))
        self.bot.db.commit()
        
        await interaction.response.send_message(f"🪄 **ADMIN** : `{montant:,} €` ajoutés au portefeuille de **{cible.display_name}** !".replace(',', ' '))

    # --- 💸 RETIRER DE L'ARGENT ---
    @app_commands.command(name="retirer_admin", description="Retirer de l'argent à un joueur (Admin uniquement)")
    async def retirer_admin(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        if interaction.user.id not in self.admin_ids:
            return await interaction.response.send_message("⛔ Seul l'administrateur peut utiliser cette commande.", ephemeral=True)
        
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
