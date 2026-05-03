import discord
from discord import app_commands
from discord.ext import commands
import time

class Banque2(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuration des IDs
        self.ID_ROLE_VIP = 1499809955841310871
        self.ID_CATEGORIE_CASINO = 1498394439079559318

    # --- LA BARRIÈRE DE SÉCURITÉ ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_role_ids = [role.id for role in interaction.user.roles]
        if self.ID_ROLE_VIP not in user_role_ids:
            await interaction.response.send_message("🚫 **Accès refusé** : Tu dois avoir le rôle VIP pour utiliser les commandes Casino.", ephemeral=True)
            return False

        current_cat = getattr(interaction.channel, 'category_id', None)
        if current_cat != self.ID_CATEGORIE_CASINO:
            await interaction.response.send_message(f"🎰 **Mauvais salon** : Les commandes ne sont autorisées que dans la catégorie <#{self.ID_CATEGORIE_CASINO}>.", ephemeral=True)
            return False

        return True

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

    group = app_commands.Group(name="banque", description="🏦 Services bancaires secondaires")

    # --- COMMANDE PAYER ---
    @group.command(name="payer", description="Envoyer de l'argent (Minimum 1€)")
    async def payer(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        if montant < 1: 
            return await interaction.response.send_message("❌ Tu ne peux pas envoyer moins de `1 €` !", ephemeral=True)
        
        if cible.id == interaction.user.id:
            return await interaction.response.send_message("❌ Tu ne peux pas t'envoyer de l'argent à toi-même.", ephemeral=True)

        u1 = self.get_user(interaction.user.id)
        u2 = self.get_user(cible.id)

        if u1["portefeuille"] < montant:
            return await interaction.response.send_message(f"❌ Pas assez de cash !", ephemeral=True)

        u1["portefeuille"] -= montant
        u2["portefeuille"] += montant
        
        self.save_user(interaction.user.id, u1)
        self.save_user(cible.id, u2)

        embed = discord.Embed(
            title="💸 TRANSFERT RÉUSSI",
            description=f"Tu as envoyé **`{montant:,} €`** à {cible.mention}.".replace(',', ' '),
            color=0x2ecc71
        )
        embed.add_field(name="💵 Portefeuille", value=f"`{u1['portefeuille']:,} €`".replace(',', ' '), inline=True)
        embed.add_field(name="🏛️ Banque", value=f"`{u1['banque']:,} €`".replace(',', ' '), inline=True)
        embed.add_field(name="💳 Nouveau Total", value=f"**`{u1['portefeuille'] + u1['banque']:,} €`**".replace(',', ' '), inline=False)
        await interaction.response.send_message(embed=embed)

    # --- COMMANDE SECOURS (CONDITION < 10 000€) ---
    @group.command(name="secours", description="Obtenir une entreprise (Si total < 10 000€ | 14 jours)")
    async def secours(self, interaction: discord.Interaction):
        u = self.get_user(interaction.user.id)
        
        total = u["portefeuille"] + u["banque"]
        if total >= 10000:
            return await interaction.response.send_message(f"❌ La banque de secours n'aide que les joueurs ayant moins de `10 000 €`. (Tu as `{total:,} €`)".replace(',', ' '), ephemeral=True)

        now = time.time()
        last_claim = u["last_secours_claim"]
        if now - last_claim < 1209600:
            jours = (1209600 - (now - last_claim)) // 86400
            return await interaction.response.send_message(f"⏳ Tu as déjà utilisé la roue de secours. Reviens dans `{int(jours)}` jours.", ephemeral=True)

        class SecoursView(discord.ui.View):
            def __init__(self, cog, uid):
                super().__init__(timeout=60)
                self.cog, self.uid = cog, uid

            @discord.ui.button(label="🎰 Tourner la roue", style=discord.ButtonStyle.primary)
            async def spin(self, i: discord.Interaction, button: discord.ui.Button):
                if i.user.id != self.uid:
                    return await i.response.send_message("❌ Ce n'est pas ta roue !", ephemeral=True)
                
                self.stop()
                await i.response.edit_message(content="🎡 **La roue tourne...**", view=None)
                
                msg = await i.original_response()
                for _ in range(5):
                    await msg.edit(content=f"🎡 **La roue tourne :** [ {random.randint(5, 50)}€ ]")
                    await asyncio.sleep(0.4)

                gain = random.randint(5, 50)
                usr = self.cog.get_user(self.uid)
                usr["entreprise_secours"] = gain
                usr["last_secours_claim"] = time.time()
                usr["last_secours_payout"] = time.time()
                self.cog.save_user(self.uid, usr)

                embed = discord.Embed(
                    title="🏢 ENTREPRISE DE SECOURS",
                    description=f"La roue s'est arrêtée ! Tu as gagné une entreprise qui rapporte :\n\n💰 **`{gain} €` toutes les 30 minutes.**",
                    color=0x9b59b6
                )
                embed.set_footer(text="Revenu passif activé.")
                await msg.edit(content=None, embed=embed)

        await interaction.response.send_message(
            content="🚑 **AIDE FINANCIÈRE**\nTon total est inférieur à 10 000 €, tu es éligible à une entreprise de secours.",
            view=SecoursView(self, interaction.user.id)
        )

async def setup(bot):
    await bot.add_cog(Banque2(bot))
