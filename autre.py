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
        self.giveaway_channel_id = 1498394479319716040 
        self.ID_ROLE_VIP = 1499809955841310871
        self.ID_CATEGORIE_CASINO = 1498394439079559318
        
        if not self.auto_giveaway.is_running():
            self.auto_giveaway.start()

    def cog_unload(self):
        self.auto_giveaway.cancel()

    def ensure_user(self, user_id):
        cursor = self.bot.db.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)", (user_id, 100))
        self.bot.db.commit()

    # --- BOUCLE GIVEAWAY MIS À JOUR ---
    @tasks.loop(minutes=1)
    async def auto_giveaway(self):
        now = datetime.datetime.now(self.timezone)
        heure_minute = now.strftime("%H:%M")
        
        # Ajout des nouveaux horaires : 15:00, 15:30, 16:00
        horaires = [
            "15:00", "15:30", "16:00", "16:30", 
            "17:00", "17:30", "18:00", "18:30", "19:00"
        ]
        
        if heure_minute in horaires:
            channel = self.bot.get_channel(self.giveaway_channel_id)
            if channel:
                await self.lancer_giveaway_flash(channel, 3000, 5)

    async def lancer_giveaway_flash(self, channel, montant, minutes):
        embed = discord.Embed(
            title="🎁 GIVEAWAY FLASH !",
            description=f"Récompense : **{montant} €**\nFin dans : **{minutes} minutes**\n\n*Clique sur la réaction 🎉 pour participer !*",
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
                self.ensure_user(gagnant.id)
                cursor = self.bot.db.cursor()
                cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (montant, gagnant.id))
                self.bot.db.commit()
                await channel.send(f"🎊 Bravo {gagnant.mention} ! Tu as gagné les **{montant} €** !")
            else:
                await channel.send("😕 Aucun participant pour le giveaway flash.")
        except Exception as e:
            print(f"Erreur giveaway: {e}")

    # --- COMMANDE VOLER ---
    @app_commands.command(name="voler", description="Tente un braquage à haut risque (Quitte ou Double)")
    @app_commands.describe(cible="Le joueur à détrousser", montant="Le montant que vous risquez (doit être en poche)")
    async def voler(self, interaction: discord.Interaction, cible: discord.Member, montant: int):
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être supérieur à 0.", ephemeral=True)
        if cible.id == interaction.user.id:
            return await interaction.response.send_message("❌ Tu ne peux pas te braquer toi-même.", ephemeral=True)
        
        self.ensure_user(interaction.user.id)
        self.ensure_user(cible.id)
        
        cursor = self.bot.db.cursor()
        
        cursor.execute("SELECT money FROM users WHERE user_id = ?", (interaction.user.id,))
        argent_voleur = cursor.fetchone()[0]
        
        if argent_voleur < montant:
            return await interaction.response.send_message(f"⚠️ Tu n'as pas les **{montant} €** en poche pour tenter ce coup.", ephemeral=True)

        cursor.execute("SELECT money FROM users WHERE user_id = ?", (cible.id,))
        argent_cible = cursor.fetchone()[0]
        
        if argent_cible < montant:
            return await interaction.response.send_message(f"🔍 {cible.display_name} n'a pas autant de cash. Trouve une cible plus riche !", ephemeral=True)

        await interaction.response.defer()
        await asyncio.sleep(2)

        if random.choice([True, False]):
            cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (montant, cible.id))
            cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (montant, interaction.user.id))
            embed = discord.Embed(title="✅ BRAQUAGE RÉUSSI !", color=0x2ecc71)
            embed.description = f"🎯 **Cible :** {cible.mention}\n💰 **Butin :** `{montant} €` récupérés !"
            embed.set_image(url="https://media.tenor.com/On7yMAn_LpMAAAAC/casino-slot-machine.gif")
        else:
            cursor.execute("UPDATE users SET money = money - ? WHERE user_id = ?", (montant, interaction.user.id))
            embed = discord.Embed(title="🚨 ÉCHEC DU BRAQUAGE", color=0xe74c3c)
            embed.description = f"👮 La police t'a coincé ! Tu as perdu tes `{montant} €`.\n{cible.mention} n'a rien perdu."

        self.bot.db.commit()
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Autre(bot))
