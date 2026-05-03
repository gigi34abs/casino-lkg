import discord
from discord.ext import commands
from discord import app_commands

class Autres2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # IDs de configuration
        self.ADMINS = [1495018019674390678, 1433802915205742612, 1342146881446350929]
        self.CAT_ID = 1498394439079559318
        self.ROLE_VIP = 1499809955841310871

    @app_commands.command(name="help", description="Déploie le menu d'aide ultra-complet du Casino")
    async def help_command(self, interaction: discord.Interaction):
        # --- SYSTÈME DE SÉCURITÉ ---
        is_admin = interaction.user.id in self.ADMINS
        has_vip = any(r.id == self.ROLE_VIP for r in interaction.user.roles)
        
        if not is_admin and not has_vip:
            return await interaction.response.send_message("🚫 **ACCÈS REFUSÉ** : Seuls les membres VIP peuvent accéder aux archives du Casino.", ephemeral=True)

        # --- CRÉATION DE L'EMBED STYLE LUXE ---
        embed = discord.Embed(
            title="✨ CENTRE D'AIDE : CASINO EMPIRE ✨",
            description=(
                "Bienvenue dans l'antre du jeu ! Voici ton guide pour passer de simple visiteur à **Milliardaire du serveur**.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0xFFAA00 # Or
        )

        # --- SECTION JEUX ---
        embed.add_field(
            name="🎮 JEUX ET DIVERTISSEMENTS",
            value=(
                "💰 **`/jeux pile_ou_face`**\n"
                "└ *Le grand classique. 50% de chance de doubler ta mise !*\n"
                "🔮 **`/jeux mystère`**\n"
                "└ *Trouve le chiffre secret entre 1 et 10. Gain massif si tu as du flair.*\n"
                "⚔️ **`/jeux pfc`**\n"
                "└ *Défie un autre joueur en duel. Le gagnant rafle toute la mise !*\n"
                "🚪 **`/jeux portes`**\n"
                "└ *3 portes, 1 seul trésor. Le jeu le plus rentable du casino (+300%).*"
            ),
            inline=False
        )

        # --- SECTION BANQUE ---
        embed.add_field(
            name="🏦 ÉCONOMIE ET GESTION",
            value=(
                "💳 **`/banque voir`**\n"
                "└ *Espionne les comptes ou vérifie tes propres poches.*\n"
                "📦 **`/banque argent`**\n"
                "└ *Dépose ton cash sur ton compte pour le protéger des voleurs.*\n"
                "📈 **`/banque classement`**\n"
                "└ *Affiche le panthéon des 10 joueurs les plus riches du serveur.*\n"
                "🎁 **`/banque journalier`**\n"
                "└ *Récupère ton bonus gratuit toutes les 1h. Ne l'oublie pas !*\n"
                "🆘 **`/banque secours`**\n"
                "└ *L'État t'aide si tu es en faillite totale (en dessous de -400€).*"
            ),
            inline=False
        )

        # --- SECTION CRIMES ET BOUTIQUE ---
        embed.add_field(
            name="🛒 BOUTIQUE ET INFRACTIONS",
            value=(
                "🛍️ **`/boutique`**\n"
                "└ *Dépense tes millions pour acheter des rôles ou des avantages.*\n"
                "🥷 **`/voler`**\n"
                "└ *Tente de dérober le cash d'un autre joueur. Attention à la police !*\n"
                "🪄 **`/donner`**\n"
                "└ *Action Admin : Injecte de l'argent magique sur un compte.*\n"
                "📦 **`/drop`**\n"
                "└ *Action Admin : Crée un coffre au trésor dans le salon !*"
            ),
            inline=False
        )

        # --- SECTION INFOS TECHNIQUES ---
        embed.add_field(
            name="📢 RÈGLEMENT ET INFOS",
            value=(
                "💸 **Taxe Journalière :** 1 500 € (prélevés à minuit).\n"
                "🎉 **Giveaways :** Flash automatiques de 15h30 à 19h.\n"
                "💎 **Départ :** Tout nouveau joueur commence avec **100 €**."
            ),
            inline=False
        )

        # --- FOOTER ET THUMBNAIL ---
        embed.set_footer(text="🎰 Joue avec modération... ou pas ! | Casino Empire v3.0")
        
        # On utilise l'avatar du bot pour faire pro
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        # Remplacement de l'image par le GIF 1000004780_4ef1f9.gif
        embed.set_image(url="https://media.tenor.com/On7yMAn_LpMAAAAC/casino-slot-machine.gif")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Autres2(bot))
