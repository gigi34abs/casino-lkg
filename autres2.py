import discord
from discord.ext import commands
from discord import app_commands

class Autres2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Affiche toutes les commandes et infos du casino")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎰 GUIDE COMPLET DU CASINO",
            description="Voici toutes les informations sur les jeux, la banque et les maisons.",
            color=0x2f3136 
        )

        # --- SECTION JEUX ---
        embed.add_field(
            name="🎮 Jeux du Casino",
            value=(
                "**`/jeux pile ou face`**\n└ Gain : +175% | Perte : -100%\n"
                "**`/jeux mystère`**\n└ Gain : +150% | Perte : -200%\n"
                "**`/jeux pfc`**\n└ Duel Pierre-Feuille-Ciseaux (Duo)\n"
                "**`/jeux portes`**\n└ Gain : +300% | Perte : -75%"
            ),
            inline=False
        )

        # --- SECTION BANQUE ---
        embed.add_field(
            name="🏦 Gestion Banque",
            value=(
                "**`/banque voir`** : Espionner le solde d'un utilisateur\n"
                "**`/banque argent`** : Gérer tes économies\n"
                "**`/banque classement`** : Voir les plus riches\n"
                "**`/banque journalier`** : Bonus gratuit toutes les 1h\n"
                "**`/banque secours`** : Disponible si tu as moins de -400€"
            ),
            inline=False
        )

        # --- SECTION MAISONS (MODIFIÉE) ---
        embed.add_field(
            name="🏠 Système de Maisons",
            value=(
                "⚠️ *Bientôt disponible :*\n"
                "• `/maisons contribuer`\n"
                "• `/maisons liste`\n"
                "**💰 Taxe de maison :** 7 500€ / jour"
            ),
            inline=True
        )

        # --- SECTION GIVEAWAYS ---
        embed.add_field(
            name="🎁 Giveaways (Horaires)",
            value=(
                "Tous les jours à :\n"
                "16h • 16h30 • 17h • 17h30\n"
                "18h • 18h30 • 19h"
            ),
            inline=True
        )

        embed.set_footer(text="Utilise les commandes pour tenter de devenir le plus riche !")
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Autres2(bot))
