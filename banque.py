import discord
from discord import app_commands
from discord.ext import commands
import time

class Banque(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # IDs de configuration (Vérifie bien que ces IDs sont les bons)
        self.ID_ROLE_VIP = 1499809955841310871
        self.ID_CATEGORIE_CASINO = 1498394439079559318

    # --- LA BARRIÈRE DE SÉCURITÉ (S'applique à TOUT le fichier) ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 1. Vérification du rôle VIP
        user_role_ids = [role.id for role in interaction.user.roles]
        if self.ID_ROLE_VIP not in user_role_ids:
            await interaction.response.send_message("🚫 **Accès refusé** : Tu dois avoir le rôle VIP pour utiliser les commandes Casino.", ephemeral=True)
            return False # Bloque l'exécution

        # 2. Vérification de la catégorie
        current_cat = getattr(interaction.channel, 'category_id', None)
        if current_cat != self.ID_CATEGORIE_CASINO:
            await interaction.response.send_message(f"🎰 **Mauvais salon** : Les commandes ne sont autorisées que dans la catégorie <#{self.ID_CATEGORIE_CASINO}>.", ephemeral=True)
            return False # Bloque l'exécution

        return True # Autorise l'exécution si les deux conditions sont remplies

    # --- TES FONCTIONS DE DONNÉES ---
    def get_user_data(self, user_id):
        cursor = self.bot.db.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, money, banque, last_daily, daily_streak) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, 100, 0, 0, 0))
        self.bot.db.commit()
        
        cursor.execute("SELECT money, banque, last_daily, daily_streak FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return {
            "portefeuille": row[0],
            "banque": row[1],
            "last_daily": row[2],
            "daily_streak": row[3]
        }

    def update_user_data(self, user_id, portefeuille, banque, last_daily=None, daily_streak=None):
        cursor = self.bot.db.cursor()
        if last_daily is not None and daily_streak is not None:
            cursor.execute('''
                UPDATE users SET money = ?, banque = ?, last_daily = ?, daily_streak = ? 
                WHERE user_id = ?
            ''', (portefeuille, banque, last_daily, daily_streak, user_id))
        else:
            cursor.execute('''
                UPDATE users SET money = ?, banque = ? WHERE user_id = ?
            ''', (portefeuille, banque, user_id))
        self.bot.db.commit()

    def fmt(self, n):
        return f"{n:,}".replace(",", " ")

    group = app_commands.Group(name="banque", description="🏦 Gestion bancaire principale")

    @group.command(name="argent", description="💰 Gérer votre portefeuille et votre banque")
    async def argent(self, interaction: discord.Interaction):
        u = self.get_user_data(interaction.user.id)

        def create_embed(user_stats, member: discord.Member):
            total = user_stats["portefeuille"] + user_stats["banque"]
            pct_banque = int((user_stats["banque"] / total * 100)) if total > 0 else 0
            pct_wallet = 100 - pct_banque

            e = discord.Embed(title=f"🏦 Compte de {member.display_name}", color=0x5865F2)
            e.set_thumbnail(url=member.display_avatar.url)
            e.add_field(name="💵 Portefeuille", value=f"```\n{self.fmt(user_stats['portefeuille'])} €\n```", inline=True)
            e.add_field(name="🏛️ Banque", value=f"```\n{self.fmt(user_stats['banque'])} €\n```", inline=True)
            e.add_field(name="\u200b", value="\u200b", inline=True)
            
            bar_wallet = "█" * (pct_wallet // 10) + "░" * (10 - pct_wallet // 10)
            bar_banque = "█" * (pct_banque // 10) + "░" * (10 - pct_banque // 10)
            e.add_field(name="📊 Répartition", value=f"💵 `{bar_wallet}` {pct_wallet}%\n🏛️ `{bar_banque}` {pct_banque}%", inline=False)
            e.add_field(name="💳 Patrimoine total", value=f"**`{self.fmt(total)} €`**", inline=False)
            e.set_footer(text="Gérez votre argent via les boutons")
            return e

        # --- MODAL POUR LES SAISIES ---
        class MontantModal(discord.ui.Modal):
            def __init__(self, title, label, cog, owner_id, action):
                super().__init__(title=title)
                self.cog = cog
                self.owner_id = owner_id
                self.action = action
                self.montant_input = discord.ui.TextInput(label=label, placeholder="Ex: 500", min_length=1, max_length=12)
                self.add_item(self.montant_input)

            async def on_submit(self, i: discord.Interaction):
                try:
                    montant = int(self.montant_input.value.replace(" ", "").replace(",", ""))
                    if montant <= 0: raise ValueError
                except ValueError:
                    return await i.response.send_message("❌ Montant invalide.", ephemeral=True)

                u = self.cog.get_user_data(self.owner_id)
                if self.action == "deposer":
                    if montant > u["portefeuille"]:
                        return await i.response.send_message("❌ Pas assez d'argent en poche.", ephemeral=True)
                    u["portefeuille"] -= montant
                    u["banque"] += montant
                else:
                    if montant > u["banque"]:
                        return await i.response.send_message("❌ Pas assez d'argent en banque.", ephemeral=True)
                    u["banque"] -= montant
                    u["portefeuille"] += montant

                self.cog.update_user_data(self.owner_id, u["portefeuille"], u["banque"])
                await i.response.edit_message(embed=create_embed(u, i.user))

        # --- VIEW POUR LES BOUTONS ---
        class BankView(discord.ui.View):
            def __init__(self, cog, owner_id):
                super().__init__(timeout=120)
                self.cog = cog
                self.owner_id = owner_id

            @discord.ui.button(label="Tout déposer", emoji="⬆️", style=discord.ButtonStyle.success)
            async def dep_all(self, i: discord.Interaction, b):
                u = self.cog.get_user_data(self.owner_id)
                if u["portefeuille"] <= 0: return await i.response.send_message("Portefeuille vide !", ephemeral=True)
                m = u["portefeuille"]; u["banque"] += m; u["portefeuille"] = 0
                self.cog.update_user_data(self.owner_id, u["portefeuille"], u["banque"])
                await i.response.edit_message(embed=create_embed(u, i.user))

            @discord.ui.button(label="Tout retirer", emoji="⬇️", style=discord.ButtonStyle.danger)
            async def wit_all(self, i: discord.Interaction, b):
                u = self.cog.get_user_data(self.owner_id)
                if u["banque"] <= 0: return await i.response.send_message("Banque vide !", ephemeral=True)
                m = u["banque"]; u["portefeuille"] += m; u["banque"] = 0
                self.cog.update_user_data(self.owner_id, u["portefeuille"], u["banque"])
                await i.response.edit_message(embed=create_embed(u, i.user))

            @discord.ui.button(label="Dépôt", emoji="💰", style=discord.ButtonStyle.primary)
            async def dep_custom(self, i: discord.Interaction, b):
                await i.response.send_modal(MontantModal("Dépôt", "Montant (€)", self.cog, self.owner_id, "deposer"))

            @discord.ui.button(label="Retrait", emoji="💸", style=discord.ButtonStyle.secondary)
            async def wit_custom(self, i: discord.Interaction, b):
                await i.response.send_modal(MontantModal("Retrait", "Montant (€)", self.cog, self.owner_id, "retirer"))

        await interaction.response.send_message(embed=create_embed(u, interaction.user), view=BankView(self, interaction.user.id))

    @group.command(name="journalier", description="🎁 Récupère tes 500 € gratuits")
    async def journalier(self, interaction: discord.Interaction):
        u = self.get_user_data(interaction.user.id)
        now = time.time()
        
        if now - u["last_daily"] < 3600:
            rem = 3600 - (now - u["last_daily"])
            return await interaction.response.send_message(f"⏱️ Reviens dans {int(rem//60)}m {int(rem%60)}s !", ephemeral=True)

        streak = u["daily_streak"] + 1 if (now - u["last_daily"]) < 7200 else 1
        gain = 500 + min((streak - 1) * 25, 250)
        u["portefeuille"] += gain
        
        self.update_user_data(interaction.user.id, u["portefeuille"], u["banque"], now, streak)
        await interaction.response.send_message(f"🎁 **+{self.fmt(gain)} €** (Streak x{streak}) ! Portefeuille: {self.fmt(u['portefeuille'])} €")

    @group.command(name="classement", description="🏆 Top 10 des membres les plus riches")
    async def classement(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cursor = self.bot.db.cursor()
        cursor.execute("SELECT user_id, money + banque, money, banque FROM users ORDER BY (money + banque) DESC LIMIT 10")
        rows = cursor.fetchall()
        
        e = discord.Embed(title="🏆 Classement des Fortunes", color=0xF1C40F)
        lines = []
        emojis = ['🥇','🥈','🥉','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟']
        
        for i, row in enumerate(rows):
            member = interaction.guild.get_member(row[0])
            name = member.display_name if member else f"Joueur {row[0]}"
            lines.append(f"{emojis[i]} **{name}**\n　💰 `{self.fmt(row[1])} €` (💵 `{self.fmt(row[2])}` 🏛️ `{self.fmt(row[3])}`)")
        
        e.description = "\n\n".join(lines) if lines else "Aucune donnée disponible."
        await interaction.followup.send(embed=e)

    @group.command(name="voir", description="🔍 Consulter les finances d'un membre")
    async def voir(self, interaction: discord.Interaction, membre: discord.Member):
        u = self.get_user_data(membre.id)
        total = u["portefeuille"] + u["banque"]
        
        e = discord.Embed(title=f"🔍 Profil de {membre.display_name}", color=0x5865F2)
        e.add_field(name="💵 Portefeuille", value=f"```\n{self.fmt(u['portefeuille'])} €\n```", inline=True)
        e.add_field(name="🏛️ Banque", value=f"```\n{self.fmt(u['banque'])} €\n```", inline=True)
        e.add_field(name="💳 Total", value=f"```\n{self.fmt(total)} €\n```", inline=False)
        e.set_thumbnail(url=membre.display_avatar.url)
        await interaction.response.send_message(embed=e)

    @group.command(name="payer", description="💸 Donner de l'argent")
    async def payer(self, interaction: discord.Interaction, membre: discord.Member, montant: int):
        if membre.id == interaction.user.id or montant <= 0:
            return await interaction.response.send_message("Action invalide.", ephemeral=True)

        donneur = self.get_user_data(interaction.user.id)
        receveur = self.get_user_data(membre.id)

        if donneur["portefeuille"] < montant:
            return await interaction.response.send_message("Pas assez d'argent en poche !", ephemeral=True)

        donneur["portefeuille"] -= montant
        receveur["portefeuille"] += montant
        
        self.update_user_data(interaction.user.id, donneur["portefeuille"], donneur["banque"])
        self.update_user_data(membre.id, receveur["portefeuille"], receveur["banque"])
        await interaction.response.send_message(f"✅ Tu as envoyé **{self.fmt(montant)} €** à {membre.mention}")

async def setup(bot):
    await bot.add_cog(Banque(bot))
