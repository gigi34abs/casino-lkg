import discord
from discord import app_commands
from discord.ext import commands

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Tes 3 IDs Admins
        self.admin_ids = [
            1495018019674390678,
            1433802915205742612,
            1342146881446350929
        ]
        self.ID_ROLE_VIP = 1499809955841310871

    @app_commands.command(name="setup_acces", description="Générer le panel d'accès (Admin uniquement)")
    async def setup_acces(self, interaction: discord.Interaction):
        # Vérification Admin
        if interaction.user.id not in self.admin_ids:
            return await interaction.response.send_message("⛔ Seul un administrateur peut configurer le panel.", ephemeral=True)

        embed = discord.Embed(
            title="🎰 ACCÈS AU CASINO",
            description=(
                "Bienvenue sur notre plateforme de jeux !\n\n"
                "**En cliquant sur le bouton ci-dessous :**\n"
                "✅ Tu reconnais avoir lu le règlement.\n"
                "✅ Tu acceptes les prélèvements de taxes quotidiennes (1 500 €).\n"
                "✅ Ton compte bancaire sera ouvert (**100 € offerts**).\n"
                "✅ Tu recevras le rôle <@&1499809955841310871>."
            ),
            color=0x5865F2
        )
        embed.set_footer(text="Clique sur le bouton vert pour commencer l'aventure.")

        # --- CLASSE DU BOUTON ---
        class AccesView(discord.ui.View):
            def __init__(self, bot, role_id):
                super().__init__(timeout=None)
                self.bot = bot
                self.role_id = role_id

            @discord.ui.button(label="J'accepte et je joue !", style=discord.ButtonStyle.green, emoji="✅", custom_id="btn_acces_casino")
            async def accept(self, i: discord.Interaction, button: discord.ui.Button):
                role = i.guild.get_role(self.role_id)
                
                if not role:
                    return await i.response.send_message("❌ Erreur : Le rôle VIP n'existe pas.", ephemeral=True)

                if role in i.user.roles:
                    return await i.response.send_message("✨ Tu as déjà accès au Casino !", ephemeral=True)

                try:
                    await i.user.add_roles(role)
                    cursor = self.bot.db.cursor()
                    cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (i.user.id, 100))
                    self.bot.db.commit()
                    await i.response.send_message("🎉 Compte créé avec **100 €** ! Tu peux maintenant accéder aux salons.", ephemeral=True)
                except Exception as e:
                    await i.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

        await interaction.response.send_message("Panel envoyé !", ephemeral=True)
        await interaction.channel.send(embed=embed, view=AccesView(self.bot, self.ID_ROLE_VIP))

    # --- NOUVELLE COMMANDE : SUPPRIMER UN COMPTE ---
    @app_commands.command(name="delete_compte", description="Supprime le compte Casino d'un joueur (Admin uniquement)")
    @app_commands.describe(joueur="Le joueur à supprimer")
    async def delete_compte(self, interaction: discord.Interaction, joueur: discord.Member):
        # Vérification Admin
        if interaction.user.id not in self.admin_ids:
            return await interaction.response.send_message("⛔ Tu n'as pas la permission de supprimer des comptes.", ephemeral=True)

        try:
            # 1. Retrait du rôle VIP
            role = interaction.guild.get_role(self.ID_ROLE_VIP)
            if role and role in joueur.roles:
                await joueur.remove_roles(role)

            # 2. Suppression dans la base de données
            cursor = self.bot.db.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (joueur.id,))
            self.bot.db.commit()

            await interaction.response.send_message(f"🗑️ Le compte de {joueur.mention} a été supprimé et son accès a été révoqué.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Une erreur est survenue : {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Verification(bot))
