import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class Jeux(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = {}

        # 🔥 TRÈS IMPORTANT
        self.bot.tree.add_command(self.jeux)

    # ===== ARGENT =====
    def get_user(self, user_id):
        return self.data.get(user_id, 1000)

    def update_money(self, user_id, amount):
        self.data[user_id] = self.get_user(user_id) + amount

    def fmt(self, x):
        return f"{x:,}".replace(",", " ")

    def check_mise(self, mise, minv, maxv, solde):
        if mise < minv:
            return f"❌ Mise min : {minv}"
        if mise > maxv:
            return f"❌ Mise max : {maxv}"
        if solde < mise:
            return "❌ Pas assez d'argent"
        return None

    # =========================
    # 🎮 GROUPE /jeux
    # =========================

    jeux = app_commands.Group(name="jeux", description="🎮 Jeux casino")

# =========================
# 🪙 PILE OU FACE
# =========================

    @jeux.command(name="pileouface")
    async def pileouface(self, interaction: discord.Interaction, mise: int):

        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 10, 10000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)

        class View(discord.ui.View):
            def __init__(self, cog, user):
                super().__init__(timeout=30)
                self.cog, self.user = cog, user
                self.done = False

            async def play(self, i, choix):
                if self.done or i.user != self.user:
                    return

                self.done = True
                self.clear_items()

                res = random.choice(["pile", "face"])

                if res == choix:
                    gain = mise * 2
                    self.cog.update_money(self.user.id, gain)
                    txt = f"✅ {res.upper()} → +{gain}€"
                else:
                    txt = f"💀 {res.upper()} → perdu"

                await i.response.edit_message(content=txt, view=None)

            @discord.ui.button(label="PILE")
            async def pile(self, i, b): await self.play(i, "pile")

            @discord.ui.button(label="FACE")
            async def face(self, i, b): await self.play(i, "face")

        await interaction.response.send_message("🪙 Choisis :", view=View(self, interaction.user))


# =========================
# 🔢 MYSTERE
# =========================

    @jeux.command(name="mystere")
    async def mystere(self, interaction: discord.Interaction, mise: int):

        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 1, 2500, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)

        bc = random.randint(1, 14)
        uc = random.randint(1, 14)

        while uc == bc:
            uc = random.randint(1, 14)

        class View(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=30)
                self.cog = cog

            async def play(self, i, choix):
                if i.user.id != interaction.user.id:
                    return

                self.clear_items()

                win = (choix == "haut" and uc > bc) or (choix == "bas" and uc < bc)

                if win:
                    gain = mise * 2
                    self.cog.update_money(i.user.id, gain)
                    txt = f"✅ {uc}>{bc} → +{gain}€"
                else:
                    txt = f"💀 {uc} vs {bc} → perdu"

                await i.response.edit_message(content=txt, view=None)

            @discord.ui.button(label="HAUT")
            async def h(self, i, b): await self.play(i, "haut")

            @discord.ui.button(label="BAS")
            async def b(self, i, b): await self.play(i, "bas")

        await interaction.response.send_message(f"🔢 Banque : {bc}", view=View(self))


# =========================
# 🚪 PORTES
# =========================

    @jeux.command(name="portes")
    async def portes(self, interaction: discord.Interaction, mise: int):

        solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 1, 5000, solde)

        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        self.update_money(interaction.user.id, -mise)
        win = random.randint(1, 3)

        class View(discord.ui.View):
            def __init__(self, cog):
                super().__init__(timeout=30)
                self.cog = cog

            async def choose(self, i, choix):
                if i.user.id != interaction.user.id:
                    return

                self.clear_items()

                if choix == win:
                    gain = mise * 3
                    self.cog.update_money(i.user.id, gain)
                    txt = f"💰 Gagné {gain}€"
                else:
                    txt = "💀 Perdu"

                await i.response.edit_message(content=txt, view=None)

            @discord.ui.button(label="1")
            async def b1(self, i, b): await self.choose(i, 1)

            @discord.ui.button(label="2")
            async def b2(self, i, b): await self.choose(i, 2)

            @discord.ui.button(label="3")
            async def b3(self, i, b): await self.choose(i, 3)

        await interaction.response.send_message("🚪 Choisis une porte", view=View(self))


# =========================
# 🔧 SETUP
# =========================

async def setup(bot):
    await bot.add_cog(Jeux(bot))
