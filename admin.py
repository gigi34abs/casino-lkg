import discord
from discord import app_commands
from discord.ext import commands
import random

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
        if interaction.user.id not in self.admin_ids:
            return await interaction.response.send_message("⛔ Seul l'administrateur peut utiliser cette commande.", ephemeral=True)
        
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)

        cursor = self.bot.db.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (cible.id, 1000))
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
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (cible.id, 1000))
        cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (montant, cible.id))
        self.bot.db.commit()
        
        await interaction.response.send_message(f"📉 **ADMIN** : `{montant:,} €` retirés du portefeuille de **{cible.display_name}** !".replace(',', ' '))

    # --- 🎁 COMMANDE DROP ---
    @app_commands.command(name="drop", description="Créer un drop d'argent pour le premier qui clique ! (Admin uniquement)")
    async def drop(self, interaction: discord.Interaction, montant: int):
        # Vérification Admin
        if interaction.user.id not in self.admin_ids:
            return await interaction.response.send_message("⛔ Seul l'administrateur peut lancer un drop.", ephemeral=True)

        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être positif.", ephemeral=True)

        embed = discord.Embed(
            title="🎁 DROP D'ARGENT !",
            description=f"Un administrateur vient de lâcher un drop de **{montant:,} €** !\n\n**Le premier qui clique sur le bouton gagne la mise !**".replace(',', ' '),
            color=0x00ff00
        )
        embed.set_footer(text="Bonne chance à tous !")

        # Classe interne pour gérer le bouton du drop
        class DropView(discord.ui.View):
            def __init__(self, cog, amount):
                super().__init__(timeout=None) # Pas de timeout pour que le drop reste actif
                self.cog = cog
                self.amount = amount
                self.taken = False

            @discord.ui.button(label="RAMASSER !", style=discord.ButtonStyle.success, emoji="💸")
            async def pick_up(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                if self.taken:
                    return await btn_interaction.response.send_message("Trop tard ! Le drop a déjà été ramassé.", ephemeral=True)
                
                # Le global_check du main.py filtrera automatiquement les non-VIP, 
                # donc on sait que celui qui clique est autorisé à jouer.
                
                self.taken = True
                self.stop()
                
                # Mise à jour de la base de données
                cursor = self.cog.bot.db.cursor()
                cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (btn_interaction.user.id, 1000))
                cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (self.amount, btn_interaction.user.id))
                self.cog.bot.db.commit()

                # Modification de l'embed original pour montrer que c'est fini
                embed_finish = discord.Embed(
                    title="🎁 DROP TERMINÉ !",
                    description=f"Bravo à **{btn_interaction.user.mention}** qui a ramassé les **{self.amount:,} €** !".replace(',', ' '),
                    color=0xFFD700
                )
                await btn_interaction.response.edit_message(embed=embed_finish, view=None)

        await interaction.response.send_message("Drop envoyé !", ephemeral=True)
        await interaction.channel.send(embed=embed, view=DropView(self, montant))

async def setup(bot):
    await bot.add_cog(Admin(bot))
