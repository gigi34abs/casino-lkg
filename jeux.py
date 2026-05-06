import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class Jeux(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

        # IMPORTANT
        self.bot.tree.add_command(self.jeux)

    # =========================
    # 💰 SYSTÈME ARGENT
    # =========================

    def get_user(self, user_id):
        if user_id not in self.data:
            self.data[user_id] = 1000
        return self.data[user_id]

    def update_money(self, user_id, amount):
        self.data[user_id] = self.get_user(user_id) + amount

    def fmt(self, x):
        return f"{x:,}".replace(",", " ")

    def check_mise(self, mise, minv, maxv, solde):
        if mise < minv:
            return f"❌ Mise minimum : {minv} €"
        if mise > maxv:
            return f"❌ Mise maximum : {maxv} €"
        if solde < mise:
            return "❌ Tu n'as pas assez d'argent"
        return None

    # =========================
    # 🎮 GROUPE
    # =========================

    jeux = app_commands.Group(name="jeux", description="🎮 Jeux du casino")

# =========================
# 🪙 PILE OU FACE (ULTRA CLEAN)
# =========================

    @jeux.command(name="pileouface", description="🪙 Double ou rien")
    async def pileouface(self, interaction: discord.Interaction, mise: int):

        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 10, 20000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)

        embed = discord.Embed(
            title="🪙 PILE OU FACE",
            description="Choisis ton camp 👇",
            color=0x3498DB
        )

        embed.add_field(name="💰 Mise", value=f"{self.fmt(mise)} €")
        embed.add_field(name="🎯 Gain possible", value=f"{self.fmt(mise*2)} €")

        class PFView(discord.ui.View):
            def __init__(self, cog, user):
                super().__init__(timeout=30)
                self.cog = cog
                self.user = user
                self.played = False

            async def play(self, i, choix):
                if self.played:
                    return

                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Ce n'est pas ton jeu.", ephemeral=True)

                self.played = True
                self.clear_items()

                res = random.choice(["pile", "face"])
                embed = discord.Embed(title="🪙 RÉSULTAT")

                if res == choix:
                    gain = mise * 2
                    self.cog.update_money(self.user.id, gain)

                    embed.description = f"✅ **{res.upper()} !** Tu gagnes {self.cog.fmt(gain)} €"
                    embed.color = 0x2ECC71
                else:
                    embed.description = f"💀 **{res.upper()} !** Tu perds ta mise"
                    embed.color = 0xE74C3C

                await i.response.edit_message(embed=embed, view=None)

            @discord.ui.button(label="PILE", emoji="🪙", style=discord.ButtonStyle.primary)
            async def pile(self, i, b):
                await self.play(i, "pile")

            @discord.ui.button(label="FACE", emoji="🎯", style=discord.ButtonStyle.secondary)
            async def face(self, i, b):
                await self.play(i, "face")

        await interaction.response.send_message(embed=embed, view=PFView(self, interaction.user))


# =========================
# 🔢 MYSTÈRE (ULTRA CLEAN)
# =========================

    @jeux.command(name="mystere", description="🔢 Plus haut ou plus bas")
    async def mystere(self, interaction: discord.Interaction, mise: int):

        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 1, 5000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)

        bc = random.randint(1, 14)
        uc = random.randint(1, 14)

        while uc == bc:
            uc = random.randint(1, 14)

        embed = discord.Embed(
            title="🔢 JEU MYSTÈRE",
            description=f"La banque a tiré : **{bc}**\n\nTon nombre est caché...\nPlus haut ou plus bas ?",
            color=0x9B59B6
        )

        embed.add_field(name="💰 Mise", value=f"{self.fmt(mise)} €")
        embed.add_field(name="🎯 Gain", value=f"{self.fmt(mise*2)} €")

        class MystereView(discord.ui.View):
            def __init__(self, cog, user):
                super().__init__(timeout=30)
                self.cog = cog
                self.user = user
                self.played = False

            async def play(self, i, choix):
                if self.played:
                    return

                if i.user.id != self.user.id:
                    return await i.response.send_message("❌ Pas ton jeu.", ephemeral=True)

                self.played = True
                self.clear_items()

                win = (choix == "haut" and uc > bc) or (choix == "bas" and uc < bc)

                embed = discord.Embed(title="🔢 RÉSULTAT")

                if win:
                    gain = mise * 2
                    self.cog.update_money(self.user.id, gain)

                    embed.description = f"✅ {uc} vs {bc}\nTu gagnes {gain} €"
                    embed.color = 0x2ECC71
                else:
                    embed.description = f"💀 {uc} vs {bc}\nPerdu"
                    embed.color = 0xE74C3C

                await i.response.edit_message(embed=embed, view=None)

            @discord.ui.button(label="PLUS HAUT", emoji="⬆️", style=discord.ButtonStyle.success)
            async def haut(self, i, b):
                await self.play(i, "haut")

            @discord.ui.button(label="PLUS BAS", emoji="⬇️", style=discord.ButtonStyle.danger)
            async def bas(self, i, b):
                await self.play(i, "bas")

        await interaction.response.send_message(embed=embed, view=MystereView(self, interaction.user))
