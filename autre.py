import discord
from discord.ext import commands, tasks
from discord import app_commands
import pytz
import random
import asyncio
import datetime

class Autre(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timezone = pytz.timezone("Europe/Paris")
        # ID du salon giveaway
        self.giveaway_channel_id = 1498394479319716040 
        self.auto_giveaway.start()

        # ID de sécurité (récupérés depuis tes instructions)
        self.ID_ROLE_VIP = 1499809955841310871
        self.ID_CATEGORIE_CASINO = 1498394439079559318

    def cog_unload(self):
        self.auto_giveaway.cancel()

    # --- UTILITAIRE SQLITE ---
    def ensure_user(self, user_id):
        """S'assure que l'utilisateur existe dans la base SQLite"""
        cursor = self.bot.db.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (user_id, 1000))
        self.bot.db.commit()

    # --- BOUCLE GIVEAWAY ---
    @tasks.loop(minutes=1)
    async def auto_giveaway(self):
        now = datetime.datetime.now(self.timezone)
        heure_minute = now.strftime("%H:%M")
        horaires = ["15:30", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00"]
        
        if heure_minute in horaires:
            channel = self.bot.get_channel(self.giveaway_channel_id)
            if channel:
                await self.lancer_giveaway_flash(channel, 10000, 5)

    async def lancer_giveaway_flash(self, channel, montant, minutes):
        embed = discord.Embed(
            title="🎁 GIVEAWAY FLASH !",
            description=f"Récompense : **{montant:,} €**\nFin dans : **{minutes} minutes**\n\n*Clique sur la réaction 🎉 pour participer !*".replace(',', ' '),
            color=0x00ff00
        )
        msg = await channel.send(content="@everyone 📢 Un nouveau giveaway vient de commencer !", embed=embed)
        await msg.add_reaction("🎉")
        
        await asyncio.sleep(minutes * 60)
        
        try:
            msg = await channel.fetch_message(msg.id)
            reaction = discord.utils.get(msg.reactions, emoji="🎉")
            users = [u async for u in reaction.users() if not u.bot]
            
            if users:
                gagnant = random.choice(users)
                # Sauvegarde SQLite
                self.ensure_user(gagnant.id)
                cursor = self.bot.db.cursor()
                cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (montant, gagnant.id))
                self.bot.db.commit()
                
                await channel.send(f"🎊 Bravo {gagnant.mention} ! Tu as gagné les **{montant:,} €** !".replace(',', ' '))
            else:
                await channel.send("😕 Aucun participant pour le giveaway flash.")
        except Exception as e:
            print(f"Erreur giveaway: {e}")

    # --- COMMANDE VOLER (SÉCURISÉE) ---
    @app_commands.command(name="voler", description="Tenter de braquer un joueur (50/50)")
    @app_commands.checks.has_role(1499809955841310871) # Vérifie le rôle VIP
    async def voler(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        # Vérification supplémentaire de la catégorie (sécurité double)
        current_cat = getattr(interaction.channel, 'category_id', None)
        if current_cat != self.ID_CATEGORIE_CASINO:
            return await interaction.response.send_message(f"🎰 Les vols sont uniquement autorisés dans la catégorie <#{self.ID_CATEGORIE_CASINO}> !", ephemeral=True)

        if montant <= 0:
            return await interaction.response.send_message("❌ Mise invalide.", ephemeral=True)
        if cible == interaction.user:
            return await interaction.response.send_message("❌ Tu ne peux pas te voler toi-même.", ephemeral=True)
        
        # Initialisation des comptes
        self.ensure_user(interaction.user.id)
        self.ensure_user(cible.id)
        
        cursor = self.bot.db.cursor()
        
        # Vérification du solde de la victime
        cursor.execute("SELECT money FROM users WHERE user_id = ?", (cible.id,))
        money_victime = cursor.fetchone()[0]
        
        if money_victime < montant:
            return await interaction.response.send_message(f"❌ {cible.display_name} n'a pas assez de cash sur lui.", ephemeral=True)

        if random.choice([True, False]):
            # Réussite
            cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (montant, interaction.user.id))
            cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (montant, cible.id))
            embed = discord.Embed(title="✅ BRAQUAGE RÉUSSI", color=0x2ecc71)
            embed.description = f"Tu as dérobé `{montant:,} €` à {cible.mention} !".replace(',', ' ')
        else:
            # Échec
            cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (montant, interaction.user.id))
            embed = discord.Embed(title="🚨 ALERTE POLICE", color=0xe74c3c)
            embed.description = f"Le braquage a échoué ! Tu perds `{montant:,} €` en frais d'avocat.".replace(',', ' ')
        
        self.bot.db.commit()
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Autre(bot))
