import discord
from discord import app_commands
from discord.ext import commands

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Tes 3 IDs Admins pour lancer la commande du panel
        self.admin_ids = [
            1495018019674390678,
            1433802915205742612,
            1342146881446350929
        ]
        self.ID_ROLE_VIP = 1499809955841310871

    @app_commands.command(name="setup_acces", description="Générer le panel d'accès au Casino (Admin uniquement)")
    async def setup_acces(self, interaction: discord.Interaction):
        # 1. Vérification Admin
        if interaction.user.id not in self.admin_ids:
            return await interaction.response.send_message("⛔ Seul un administrateur peut configurer le panel.", ephemeral=True)

        embed = discord.Embed(
            title="🎰 ACCÈS AU CASINO",
            description=(
                "Bienvenue sur notre plateforme de jeux !\n\n"
                "**En cliquant sur le bouton ci-dessous :**\n"
                "✅ Tu reconnais avoir lu le règlement.\n"
                "✅ Tu acceptes les prélèvements de taxes quotidiennes (1 500 €).\n"
                "✅ Ton compte bancaire sera officiellement ouvert (1 000 € offerts).\n"
                "✅ Tu recevras le rôle <@&1499809955841310871> pour accéder aux salons."
            ),
            color=0x5865F2
        )
        embed.set_footer(text="L'abus de jeu est dangereux pour la santé de ton portefeuille virtuel.")

        # --- CLASSE POUR LE BOUTON D'ACCEPTATION ---
        class AccesView(discord.ui.View):
            def __init__(self, bot, role_id):
                super().__init__(timeout=None) # Le bouton ne périme jamais
                self.bot = bot
                self.role_id = role_id

            @discord.ui.button(label="J'accepte et je joue !", style=discord.ButtonStyle.green, emoji="✅", custom_id="btn_acces_casino")
            async def accept(self, i: discord.Interaction, button: discord.ui.Button):
                # Vérifier si l'utilisateur a déjà le rôle
                role = i.guild.get_role(self.role_id)
                if role in i.user.roles:
                    return await i.response.send_message("✨ Tu es déjà membre du Casino !", ephemeral=True)

                # 1. Donner le rôle VIP
                try:
                    await i.user.add_roles(role)
                except:
                    return await i.response.send_message("❌ Erreur : Je n'ai pas la permission de donner le rôle.", ephemeral=True)

                # 2. Créer le compte bancaire en SQLite
                cursor = self.bot.db.cursor()
                # On utilise INSERT OR IGNORE pour ne pas écraser s'il existe déjà
                cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (i.user.id, 1000))
                self.bot.db.commit()

                await i.response.send_message("🎉 Félicitations ! Ton compte est ouvert et tu es désormais VIP.", ephemeral=True)

        await interaction.response.send_message("Panel envoyé !", ephemeral=True)
        await interaction.channel.send(embed=embed, view=AccesView(self.bot, self.ID_ROLE_VIP))

async def setup(bot):
    await bot.add_cog(Verification(bot))
