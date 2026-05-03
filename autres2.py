import discord
from discord.ext import commands
from discord import app_commands

class Autres2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Affiche toutes les commandes et infos du casino")
    @app_commands.checks.has_role(1499809955841310871) # Protection VIP
    async def help_command(self, interaction: discord.Interaction):
        # Sécurité Catégorie
        if getattr(interaction.channel, 'category_id', None) != 1498394439079559318:
            return await interaction.response.send_message("❌ Utilise cette commande dans la catégorie Casino !", ephemeral=True)

        embed = discord.Embed(
            title="🎰 GUIDE COMPLET DU CASINO",
            description="Bienvenue ! Voici la liste de toutes les interactions disponibles sur le serveur.",
            color=0x2f3136 
        )

        # --- SECTION JEUX ---
        embed.add_field(
            name="🎮 Jeux d'Argent",
            value=(
                "**`/jeux pile ou face`** : 50/50 pour doubler la mise.\n"
                "**`/jeux mystère`** : Un nombre entre 1 et 10.\n"
                "**`/jeux pfc`** : Défie un autre joueur en duel.\n"
                "**`/jeux portes`** : Choisis la bonne porte pour le jackpot."
            ),
            inline=False
        )

        # --- SECTION BANQUE ---
        embed.add_field(
            name="🏦 Économie & Banque",
            value=(
                "**`/banque voir`** : Consulter son solde ou celui d'un ami.\n"
                "**`/banque argent`** : Déposer/Retirer de l'argent de la banque.\n"
                "**`/banque classement`** : Top 10 des plus riches.\n"
                "**`/banque journalier`** : Récupérer ton salaire (toutes les 1h).\n"
                "**`/banque secours`** : Aide de l'État si tu es en faillite."
            ),
            inline=False
        )

        # --- SECTION BOUTIQUE & CRIMES ---
        embed.add_field(
            name="🛒 Boutique & Intéractions",
            value=(
                "**`/boutique`** : Acheter des rôles ou des bonus.\n"
                "**`/voler`** : Tenter de braquer un joueur (Risqué !)\n"
                "**`/donner`** : (Admin) Envoyer de l'argent à quelqu'un.\n"
                "**`/drop`** : (Admin) Lancer un cadeau dans le chat."
            ),
            inline=False
        )

        # --- SECTION TAXES & GIVEAWAYS ---
        embed.add_field(
            name="📢 Infos Serveur",
            value=(
                "💰 **Taxe :** 1 500 € retirés chaque jour à minuit.\n"
                "🎁 **Giveaways :** Toutes les 30 min entre 15h30 et 19h00."
            ),
            inline=True
        )

        embed.set_footer(text="Bonne chance ! Ne misez pas ce que vous ne pouvez pas perdre.")
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Autres2(bot))
