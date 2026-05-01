import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class Jeux(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_user(self, user_id):
        """Récupère le solde du joueur dans SQLite"""
        cursor = self.bot.db.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, money, banque, last_daily, daily_streak) VALUES (?, ?, ?, ?, ?)", (user_id, 1000, 0, 0, 0))
        self.bot.db.commit()
        cursor.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]

    def update_money(self, user_id, amount):
        """Met à jour le solde (gain ou perte)"""
        cursor = self.bot.db.cursor()
        cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
        self.bot.db.commit()

    def check_mise(self, mise, mini, maxi, solde):
        """Vérifie si la mise est valide"""
        if mise < mini: return f"❌ Mise minimale : `{self.fmt(mini)} €`."
        if mise > maxi: return f"❌ Mise maximale : `{self.fmt(maxi)} €`."
        if solde < mise: return f"❌ Solde insuffisant (Portefeuille : `{self.fmt(solde)} €`)."
        return None

    def fmt(self, n):
        return f"{n:,}".replace(",", " ")

    group = app_commands.Group(name="jeux", description="🎰 Casino Haute Tension")

    # ==================== MYSTÈRE AMÉLIORÉ ====================
    @group.command(name="mystere", description=" Devine si ton nombre sera plus haut ou plus bas (1-14)")
    async def mystere(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 1, 2500, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        bc = random.randint(1, 14)
        uc = random.randint(1, 14)

        embed = discord.Embed(title="🔢 JEU DU MYSTÈRE", description=f"Le nombre de la banque est : **{bc}**\n\nTon nombre est caché. Sera-t-il plus **Haut** ou plus **Bas** ?", color=0x3498DB)
        embed.add_field(name="💰 Mise engagée", value=f"`{self.fmt(pari)} €`", inline=True)
        embed.add_field(name="📈 Gain potentiel", value=f"`{self.fmt(round(pari*1.5))} €`", inline=True)

        class MystereView(discord.ui.View):
            def __init__(self, cog, bc, uc, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.bc = bc
                self.uc = uc
                self.pari = pari

            async def process_choice(self, i: discord.Interaction, choice: str):
                if i.user.id != interaction.user.id: return await i.response.send_message("❌ Pas ton tour !", ephemeral=True)
                res_embed = discord.Embed(description=f"Banque : **{self.bc}**\nToi : **{self.uc}**", color=0x3498DB)
                
                if self.uc == self.bc:
                    res_embed.title = "🤝 ÉGALITÉ"; res_embed.color = 0x95A5A6
                elif (choice == "h" and self.uc > self.bc) or (choice == "b" and self.uc < self.bc):
                    gain = round(self.pari * 1.5)
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "✅ VICTOIRE !"; res_embed.color = 0x2ECC71
                    res_embed.description += f"\n\nBravo ! Tu remportes **{self.cog.fmt(gain)} €**."
                else:
                    perte = self.pari * 2
                    self.cog.update_money(i.user.id, -perte)
                    res_embed.title = "💀 CRASH"; res_embed.color = 0xE74C3C
                    res_embed.description += f"\n\nMauvais pronostic ! Tu perds **{self.cog.fmt(perte)} €**."
                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PLUS HAUT", emoji="⏫", style=discord.ButtonStyle.success)
            async def plus_haut(self, i, b): await self.process_choice(i, "h")
            @discord.ui.button(label="PLUS BAS", emoji="⏬", style=discord.ButtonStyle.danger)
            async def plus_bas(self, i, b): await self.process_choice(i, "b")

        await interaction.response.send_message(embed=embed, view=MystereView(self, bc, uc, pari))

# ==================== PORTES ====================
    @group.command(name="portes", description="🚪 Tente de trouver le trésor derrière l'une des 3 portes")
    async def portes(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        err = self.check_mise(pari, 1, 10000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        win_door = random.randint(1, 3)
        embed = discord.Embed(title="🚪 LE JEU DES PORTES", description="Choisis une porte !", color=0x9B59B6)
        embed.add_field(name="💰 Mise", value=f"`{self.fmt(pari)} €`")
        embed.add_field(name="🏆 Jackpot (x3)", value=f"`{self.fmt(pari*3)} €`")

        class PortesView(discord.ui.View):
            def __init__(self, cog, win_door, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.win_door = win_door
                self.pari = pari

            async def play(self, i: discord.Interaction, choice: int):
                if i.user.id != interaction.user.id: return await i.response.send_message("❌ Pas ton jeu !", ephemeral=True)
                result_text = "".join([f"Porte {n} : {'💰 **TRÉSOR**' if n == self.win_door else '💨 **VIDE**'}{' 👈' if choice == n else ''}\n" for n in range(1, 4)])
                res_embed = discord.Embed(title="🚪 RÉVÉLATION", description=result_text)

                if choice == self.win_door:
                    gain = self.pari * 3
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "✨ VICTOIRE !"; res_embed.color = 0xF1C40F
                    res_embed.add_field(name="Résultat", value=f"Gain : **+{self.cog.fmt(gain)} €**")
                else:
                    perte = round(self.pari * 0.75)
                    self.cog.update_money(i.user.id, -perte)
                    res_embed.title = "💨 VIDE..."; res_embed.color = 0xE74C3C
                    res_embed.add_field(name="Résultat", value=f"Perte : **-{self.cog.fmt(perte)} €**")
                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="1", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b1(self, i, b): await self.play(i, 1)
            @discord.ui.button(label="2", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b2(self, i, b): await self.play(i, 2)
            @discord.ui.button(label="3", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b3(self, i, b): await self.play(i, 3)

        await interaction.response.send_message(embed=embed, view=PortesView(self, win_door, pari))


