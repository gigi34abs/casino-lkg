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

# ==================== PFC DUEL (Version SQLite) ====================
    @group.command(name="pfc", description="⚔️ Duel Pierre-Feuille-Ciseaux contre un autre joueur")
    async def pfc(self, interaction: discord.Interaction, adversaire: discord.Member, mise: int):
        if adversaire.id == interaction.user.id or adversaire.bot:
            return await interaction.response.send_message("❌ Action impossible.", ephemeral=True)

        u1_solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 1, 15000, u1_solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        u2_solde = self.get_user(adversaire.id)
        if u2_solde < mise:
            return await interaction.response.send_message(f"❌ **{adversaire.display_name}** n'a pas assez d'argent.", ephemeral=True)

        embed = discord.Embed(
            title="⚔️ INVITATION AU DUEL", 
            description=f"{interaction.user.mention} défie {adversaire.mention} !\n💰 Enjeu : **{self.fmt(mise)} €**", 
            color=0xF1C40F
        )

        class PFCInvite(discord.ui.View):
            def __init__(self, cog, p1, p2, mise):
                super().__init__(timeout=60)
                self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise

            @discord.ui.button(label="Accepter", emoji="⚔️", style=discord.ButtonStyle.success)
            async def accept(self, i: discord.Interaction, b):
                if i.user.id != self.p2.id: return await i.response.send_message("❌ Pas pour toi.", ephemeral=True)
                
                # Prélèvement des mises
                self.cog.update_money(self.p1.id, -self.mise)
                self.cog.update_money(self.p2.id, -self.mise)
                
                await i.response.edit_message(content="🎮 Le duel commence ! Choisissez votre arme...", embed=None, view=PFCGame(self.cog, self.p1, self.p2, self.mise))

            @discord.ui.button(label="Refuser", emoji="🚫", style=discord.ButtonStyle.danger)
            async def deny(self, i: discord.Interaction, b):
                if i.user.id != self.p2.id: return await i.response.send_message("❌ Pas pour toi.", ephemeral=True)
                await i.response.edit_message(content="❌ Duel refusé.", embed=None, view=None)

        class PFCGame(discord.ui.View):
            def __init__(self, cog, p1, p2, mise):
                super().__init__(timeout=60)
                self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise
                self.choices = {p1.id: None, p2.id: None}

            async def check_results(self, i):
                c1, c2 = self.choices[self.p1.id], self.choices[self.p2.id]
                if c1 and c2:
                    win_map = {"pierre": "ciseaux", "feuille": "pierre", "ciseaux": "feuille"}
                    res = discord.Embed(title="⚔️ RÉSULTAT DU DUEL", color=0x5865F2)
                    res.description = f"{self.p1.display_name} : **{c1}**\n{self.p2.display_name} : **{c2}**\n\n"
                    
                    if c1 == c2:
                        self.cog.update_money(self.p1.id, self.mise)
                        self.cog.update_money(self.p2.id, self.mise)
                        res.title = "🤝 ÉGALITÉ"; res.description += "Les mises sont rendues."
                    elif win_map[c1] == c2:
                        self.cog.update_money(self.p1.id, self.mise * 2)
                        res.title = f"🏆 {self.p1.display_name} GAGNE !"; res.description += f"Il remporte **{self.cog.fmt(self.mise*2)} €**"
                    else:
                        self.cog.update_money(self.p2.id, self.mise * 2)
                        res.title = f"🏆 {self.p2.display_name} GAGNE !"; res.description += f"Il remporte **{self.cog.fmt(self.mise*2)} €**"
                    
                    await i.edit_original_response(embed=res, view=None)

            async def make_choice(self, i, choice):
                if i.user.id not in self.choices: return await i.response.send_message("❌ Pas ton duel.", ephemeral=True)
                if self.choices[i.user.id]: return await i.response.send_message("✅ Déjà choisi !", ephemeral=True)
                self.choices[i.user.id] = choice
                await i.response.send_message(f"Tu as choisi {choice} !", ephemeral=True)
                await self.check_results(i)

            @discord.ui.button(label="Pierre", emoji="🪨")
            async def pierre(self, i, b): await self.make_choice(i, "pierre")
            @discord.ui.button(label="Feuille", emoji="🍃")
            async def feuille(self, i, b): await self.make_choice(i, "feuille")
            @discord.ui.button(label="Ciseaux", emoji="✂️")
            async def ciseaux(self, i, b): await self.make_choice(i, "ciseaux")

        await interaction.response.send_message(embed=embed, view=PFCInvite(self, interaction.user, adversaire, mise))

# ==================== PILE OU FACE (Version SQLite) ====================
    @group.command(name="pileouface", description="🪙 Tente le 50/50 (Max 7,500€)")
    async def pf(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        
        # Correction du crash : la fonction check_mise est maintenant reconnue
        err = self.check_mise(pari, 1, 7500, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        embed = discord.Embed(
            title="🪙 PILE OU FACE", 
            description="La pièce est lancée... Fais ton choix !", 
            color=0xF39C12
        )
        embed.add_field(name="💰 Mise engagée", value=f"`{self.fmt(pari)} €`", inline=True)
        embed.add_field(name="✨ Gain potentiel", value=f"`{self.fmt(round(pari*1.75))} €`", inline=True)

        class PFView(discord.ui.View):
            def __init__(self, cog, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.pari = pari

            async def play(self, i: discord.Interaction, choix: str):
                if i.user.id != interaction.user.id:
                    return await i.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)

                resultat = random.choice(["pile", "face"])
                emoji_resultat = "🟡" if resultat == "pile" else "⚪"
                
                res_embed = discord.Embed(
                    title="🪙 RÉSULTAT", 
                    description=f"La pièce s'arrête sur... {emoji_resultat} **{resultat.upper()}**", 
                    color=0xF39C12
                )

                if choix == resultat:
                    gain = round(self.pari * 1.75)
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "💰 GAGNÉ !"; res_embed.color = 0x2ECC71
                    res_embed.add_field(name="Résultat", value=f"Bien vu ! Tu remportes **{self.cog.fmt(gain)} €**")
                else:
                    self.cog.update_money(i.user.id, -self.pari)
                    res_embed.title = "❌ PERDU"; res_embed.color = 0xE74C3C
                    res_embed.add_field(name="Résultat", value=f"Pas de chance. Tu perds **{self.cog.fmt(self.pari)} €**")

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PILE", emoji="🟡", style=discord.ButtonStyle.primary)
            async def pile(self, i, b): await self.play(i, "pile")

            @discord.ui.button(label="FACE", emoji="⚪", style=discord.ButtonStyle.secondary)
            async def face(self, i, b): await self.play(i, "face")

        await interaction.response.send_message(embed=embed, view=PFView(self, pari))


