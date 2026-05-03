import discord
from discord.ext import commands
from discord import app_commands

class Autres2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ID_CATEGORIE_CASINO = 1498394439079559318
        self.ID_ROLE_VIP = 1499809955841310871
        self.ADMIN_IDS = [1495018019674390678, 1433802915205742612, 1342146881446350929]

    @app_commands.command(name="help", description="Affiche toutes les commandes et infos du casino")
    async def help_command(self, interaction: discord.Interaction):
        # 1. Calcul des permissions
        is_admin = interaction.user.id in self.ADMIN_IDS
        has_vip = any(role.id == self.ID_ROLE_VIP for role in interaction.user.roles)
        current_cat = getattr(interaction.channel, 'category_id', None)

        # 2. Vérifications de sécurité (les admins contournent tout)
        if not is_admin:
            if not has_vip:
                return await interaction.response.send_message("🚫 **Accès refusé** : Tu dois avoir le rôle VIP pour utiliser cette commande.", ephemeral=True)
            
            if current_cat != self.ID_CATEGORIE_CASINO:
                return await interaction.response.send_message(f"🎰 **Mauvais salon** : Utilise cette commande dans la catégorie <#{self.ID_CATEGORIE_CASINO}>.", ephemeral=True)

        # 3. Construction de l'Embed avec TOUTES les définitions
        embed = discord.Embed(
            title="🎰 GUIDE COMPLET DU CASINO",
            description="Bienvenue ! Voici la liste détaillée de toutes les interactions disponibles sur le serveur.",
            color=0x2f3136 
        )

        # --- SECTION JEUX ---
        embed.add_field(
            name="🎮 Jeux d'Argent",
            value=(
                "**`/jeux pile ou face`**\n└ Mise sur une face. Gain : +175% | Perte : -100%\n"
                "**`/jeux mystère`**\n└ Devine le nombre (1-10). Gain : +150% | Perte : -200%\n"
                "**`/jeux pfc`**\n└ Duel Pierre-Feuille-Ciseaux contre un autre joueur.\n"
                "**`/jeux portes`**\n└ Choisis la bonne porte. Gain : +300% | Perte : -75%"
            ),
            inline=False
        )

        # --- SECTION BANQUE ---
        embed.add_field(
            name="🏦 Économie & Banque",
            value=(
                "**`/banque voir`** : Consulte ton cash et ton solde bancaire.\n"
                "**`/banque argent`** : Dépose ton cash en banque pour le protéger des vols.\n"
                "**`/banque classement`** : Affiche les 10 plus gros riches du serveur.\n"
                "**`/banque journalier`** : Récupère ton bonus gratuit (disponible toutes les 1h).\n"
                "**`/banque secours`** : Aide financière si tu tombes en dessous de -400€."
            ),
            inline=False
        )

        # --- SECTION BOUTIQUE & ACTIONS ---
        embed.add_field(
            name="🛒 Boutique & Intéractions",
            value=(
                "**`/boutique`** : Achète des rôles exclusifs ou des multiplicateurs.\n"
                "**`/voler`** : Tente de braquer le cash d'un joueur (50% de chance).\n"
                "**`/donner`** : (Admin) Ajoute de l'argent au portefeuille d'un membre.\n"
                "**`/drop`** : (Admin) Crée un événement où le plus rapide gagne un prix."
            ),
            inline=False
        )

        # --- SECTION INFOS ---
        embed.add_field(
            name="📢 Informations Importantes",
            value=(
                "💰 **Taxe de vie :** 1 500 € sont retirés de ton cash chaque jour à minuit.\n"
                "🎁 **Giveaways Flash :** Des prix tombent à 15h30, 16h30, 17h, 17h30, 18h, 18h30 et 19h !"
            ),
            inline=False
        )

        embed.set_footer(text="Utilise les commandes pour tenter de devenir le plus riche !")
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Autres2(bot))
