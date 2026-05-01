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
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        self.bot.db.commit()
        cursor.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]

    def update_money(self, user_id, amount):
        """Met à jour le solde (gain ou perte)"""
        cursor = self.bot.db.cursor()
        cursor.execute("UPDATE users SET money = money + ? WHERE user_id = ?", (amount, user_id))
        self.bot.db.commit()

    def fmt(self, n):
        return f"{n:,}".replace(",", " ")

    group = app_commands.Group(name="jeux", description="🎰 Casino Haute Tension")

    # ==================== MYSTÈRE AMÉLIORÉ (1-14) ====================
    @group.command(name="mystere", description="🔢 Devine si ton nombre sera plus haut ou plus bas (1-14)")
    async def mystere(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        
        # Vérification des limites
        if pari < 1: 
            return await interaction.response.send_message("❌ Mise minimale : `1 €`.", ephemeral=True)
        if pari > 2500: 
            return await interaction.response.send_message("❌ Mise maximale : `2 500 €`.", ephemeral=True)
        if solde < pari:
            return await interaction.response.send_message(f"❌ Solde insuffisant (`{self.fmt(solde)} €`).", ephemeral=True)

        # Génération des nombres (1 à 14)
        bc = random.randint(1, 14) # Nombre de la banque
        uc = random.randint(1, 14) # Nombre du joueur (caché au début)

        embed = discord.Embed(
            title="🔢 JEU DU MYSTÈRE", 
            description=f"Le nombre de la banque est : **{bc}**\n\nTon nombre est caché. Sera-t-il plus **Haut** ou plus **Bas** ?", 
            color=0x3498DB
        )
        embed.add_field(name="💰 Mise engagée", value=f"`{self.fmt(pari)} €`", inline=True)
        embed.add_field(name="📈 Gain potentiel", value=f"`{self.fmt(round(pari*1.5))} €`", inline=True)
        embed.set_footer(text="Tu as 30 secondes pour décider !")

        class MystereView(discord.ui.View):
            def __init__(self, cog, bc, uc, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.bc = bc
                self.uc = uc
                self.pari = pari
                self.message = None

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                if self.message:
                    await self.message.edit(view=self)

            async def process_choice(self, i: discord.Interaction, choice: str):
                if i.user.id != interaction.user.id:
                    return await i.response.send_message("❌ Ce n'est pas ton tour de jouer !", ephemeral=True)

                # Résultat final
                res_embed = discord.Embed(description=f"Banque : **{self.bc}**\nToi : **{self.uc}**", color=0x3498DB)
                
                # Cas d'égalité
                if self.uc == self.bc:
                    res_embed.title = "🤝 ÉGALITÉ"
                    res_embed.color = 0x95A5A6
                    res_embed.description += "\n\nLes nombres sont identiques. Ta mise est conservée."
                
                # Cas de Victoire (Haut ou Bas)
                elif (choice == "h" and self.uc > self.bc) or (choice == "b" and self.uc < self.bc):
                    gain = round(self.pari * 1.5)
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "✅ VICTOIRE !"
                    res_embed.color = 0x2ECC71
                    res_embed.description += f"\n\nBravo ! Tu remportes **{self.cog.fmt(gain)} €**."
                
                # Cas de Défaite (Crash)
                else:
                    perte = self.pari * 2
                    self.cog.update_money(i.user.id, -perte)
                    res_embed.title = "💀 CRASH"
                    res_embed.color = 0xE74C3C
                    res_embed.description += f"\n\nMauvais pronostic ! Tu perds **{self.cog.fmt(perte)} €** (Mise x2)."

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PLUS HAUT", emoji="⏫", style=discord.ButtonStyle.success)
            async def plus_haut(self, i, b):
                await self.process_choice(i, "h")

            @discord.ui.button(label="PLUS BAS", emoji="⏬", style=discord.ButtonStyle.danger)
            async def plus_bas(self, i, b):
                await self.process_choice(i, "b")

        view = MystereView(self, bc, uc, pari)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

# ==================== PORTES (Version VIP) ====================
    @group.command(name="portes", description="🚪 Tente de trouver le trésor derrière l'une des 3 portes")
    async def portes(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        
        # Vérification de la mise (Max 10 000€ selon ton code d'origine)
        err = self.check_mise(pari, 1, 10000, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        win_door = random.randint(1, 3)
        
        embed = discord.Embed(
            title="🚪 LE JEU DES PORTES",
            description="Trois portes sont devant toi. L'une d'elles cache un **trésor**, les autres sont **vides**.\n\nFais ton choix avec les boutons ci-dessous !",
            color=0x9B59B6
        )
        embed.add_field(name="💰 Mise", value=f"**`{self.fmt(pari)} €`**", inline=True)
        embed.add_field(name="🏆 Jackpot (x3)", value=f"**`{self.fmt(pari*3)} €`**", inline=True)
        embed.set_footer(text="Attention : en cas de défaite, tu perds 75% de ta mise.")

        class PortesView(discord.ui.View):
            def __init__(self, cog, win_door, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.win_door = win_door
                self.pari = pari
                self.message = None

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                if self.message:
                    try: await self.message.edit(view=self)
                    except: pass

            async def play(self, i: discord.Interaction, choice: int):
                if i.user.id != interaction.user.id:
                    return await i.response.send_message("❌ Ce n'est pas ton jeu !", ephemeral=True)

                # Construction du visuel de révélation
                result_text = ""
                for n in range(1, 4):
                    marker = " 👈" if choice == n else ""
                    icon = "💰 **TRÉSOR**" if n == self.win_door else "💨 **VIDE**"
                    result_text += f"Porte {n} : {icon}{marker}\n"

                res_embed = discord.Embed(title="🚪 RÉVÉLATION", description=result_text)

                if choice == self.win_door:
                    gain = self.pari * 3
                    self.cog.update_money(i.user.id, gain)
                    res_embed.title = "✨ INCROYABLE VICTOIRE !"
                    res_embed.color = 0xF1C40F
                    res_embed.add_field(name="Résultat", value=f"Tu as trouvé le trésor !\n**Gain : +{self.cog.fmt(gain)} €**")
                else:
                    perte = round(self.pari * 0.75)
                    self.cog.update_money(i.user.id, -perte)
                    res_embed.title = "💨 C'ÉTAIT VIDE..."
                    res_embed.color = 0xE74C3C
                    res_embed.add_field(name="Résultat", value=f"La chance n'était pas là.\n**Perte : -{self.cog.fmt(perte)} €**")

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="Porte 1", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b1(self, i, b): await self.play(i, 1)

            @discord.ui.button(label="Porte 2", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b2(self, i, b): await self.play(i, 2)

            @discord.ui.button(label="Porte 3", emoji="🚪", style=discord.ButtonStyle.primary)
            async def b3(self, i, b): await self.play(i, 3)

        v = PortesView(self, win_door, pari)
        await interaction.response.send_message(embed=embed, view=v)
        v.message = await interaction.original_response()

# ==================== PILE OU FACE (Version SQLite) ====================
    @group.command(name="pileouface", description="🪙 Tente le 50/50 (Max 7,500€)")
    async def pf(self, interaction: discord.Interaction, pari: int):
        solde = self.get_user(interaction.user.id)
        
        # Vérification de la mise
        err = self.check_mise(pari, 1, 7500, solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        embed = discord.Embed(
            title="🪙 PILE OU FACE", 
            description="La pièce est lancée dans les airs... Fais ton choix !", 
            color=0xF39C12
        )
        embed.add_field(name="💰 Mise engagée", value=f"`{self.fmt(pari)} €`", inline=True)
        embed.add_field(name="✨ Gain potentiel", value=f"`{self.fmt(round(pari*1.75))} €`", inline=True)

        class PFView(discord.ui.View):
            def __init__(self, cog, pari):
                super().__init__(timeout=30)
                self.cog = cog
                self.pari = pari
                self.message = None

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                if self.message:
                    try: await self.message.edit(view=self)
                    except: pass

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
                    res_embed.title = "💰 GAGNÉ !"
                    res_embed.color = 0x2ECC71
                    res_embed.add_field(name="Résultat", value=f"Bien vu ! Tu remportes **{self.cog.fmt(gain)} €**")
                else:
                    self.cog.update_money(i.user.id, -self.pari)
                    res_embed.title = "❌ PERDU"
                    res_embed.color = 0xE74C3C
                    res_embed.add_field(name="Résultat", value=f"Pas de chance cette fois. Tu perds **{self.cog.fmt(self.pari)} €**")

                await i.response.edit_message(embed=res_embed, view=None)

            @discord.ui.button(label="PILE", emoji="🟡", style=discord.ButtonStyle.primary)
            async def pile(self, i, b): await self.play(i, "pile")

            @discord.ui.button(label="FACE", emoji="⚪", style=discord.ButtonStyle.secondary)
            async def face(self, i, b): await self.play(i, "face")

        v = PFView(self, pari)
        await interaction.response.send_message(embed=embed, view=v)
        v.message = await interaction.original_response()

# ==================== CONNECTE 4 (2 JOUEURS) ====================
    @group.command(name="connecte4", description="🔴 Défie un ami au Puissance 4 ! (Mise partagée)")
    async def connecte4(self, interaction: discord.Interaction, mise: int):
        solde = self.get_user(interaction.user.id)
        if mise < 10: return await interaction.response.send_message("❌ Mise minimale : 10 €.", ephemeral=True)
        if solde < mise: return await interaction.response.send_message("❌ Tu n'as pas assez d'argent.", ephemeral=True)

        embed = discord.Embed(
            title="🔴 CONNECTE 4 : DÉFI LANCÉ !",
            description=f"**{interaction.user.display_name}** mise **{self.fmt(mise)} €** !\nQui accepte le duel ?",
            color=0xe74c3c
        )

        class C4View(discord.ui.View):
            def __init__(self, cog, p1, mise):
                super().__init__(timeout=60)
                self.cog = cog
                self.p1 = p1
                self.p2 = None
                self.mise = mise
                self.board = [[0]*7 for _ in range(6)] # 0: vide, 1: P1 (🔴), 2: P2 (🟡)
                self.turn = p1
                self.game_active = False

            def get_board_str(self):
                symbols = {0: "⚪", 1: "🔴", 2: "🟡"}
                txt = ""
                for row in self.board:
                    txt += "".join([symbols[cell] for cell in row]) + "\n"
                return txt + "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣"

            def check_win(self, p):
                # Horizontal
                for r in range(6):
                    for c in range(4):
                        if all(self.board[r][c+i] == p for i in range(4)): return True
                # Vertical
                for r in range(3):
                    for c in range(7):
                        if all(self.board[r+i][c] == p for i in range(4)): return True
                # Diagonal /
                for r in range(3, 6):
                    for c in range(4):
                        if all(self.board[r-i][c+i] == p for i in range(4)): return True
                # Diagonal \
                for r in range(3):
                    for c in range(4):
                        if all(self.board[r+i][c+i] == p for i in range(4)): return True
                return False

            @discord.ui.button(label="REJOINRE LE DUEL", style=discord.ButtonStyle.green)
            async def join(self, i: discord.Interaction, b: discord.ui.Button):
                if i.user.id == self.p1.id: return await i.response.send_message("❌ Tu ne peux pas jouer contre toi-même !", ephemeral=True)
                s2 = self.cog.get_user(i.user.id)
                if s2 < self.mise: return await i.response.send_message("❌ Tu n'as pas assez d'argent !", ephemeral=True)
                
                self.p2 = i.user
                self.game_active = True
                self.cog.update_money(self.p1.id, -self.mise)
                self.cog.update_money(self.p2.id, -self.mise)
                
                self.clear_items()
                for n in range(1, 8):
                    btn = discord.ui.Button(label=str(n), custom_id=str(n-1), style=discord.ButtonStyle.blurple)
                    btn.callback = self.play_move
                    self.add_item(btn)
                
                emb = discord.Embed(title="🎮 MATCH EN COURS", description=f"🔴 {self.p1.mention} vs 🟡 {self.p2.mention}\n\n{self.get_board_str()}", color=0x3498db)
                emb.set_footer(text=f"Tour de : {self.turn.display_name}")
                await i.response.edit_message(embed=emb, view=self)

            async def play_move(self, i: discord.Interaction):
                if i.user.id != self.turn.id: return await i.response.send_message("❌ Ce n'est pas ton tour !", ephemeral=True)
                col = int(i.data['custom_id'])
                
                # Placer le jeton
                row_placed = -1
                for r in range(5, -1, -1):
                    if self.board[r][col] == 0:
                        self.board[r][col] = 1 if i.user.id == self.p1.id else 2
                        row_placed = r
                        break
                
                if row_placed == -1: return await i.response.send_message("❌ Colonne pleine !", ephemeral=True)
                
                p_num = 1 if i.user.id == self.p1.id else 2
                if self.check_win(p_num):
                    pot = self.mise * 2
                    self.cog.update_money(i.user.id, pot)
                    emb = discord.Embed(title="🏆 VICTOIRE !", description=f"**{i.user.display_name}** a gagné le pot de **{self.cog.fmt(pot)} €** !\n\n{self.get_board_str()}", color=0x2ecc71)
                    return await i.response.edit_message(embed=emb, view=None)

                # Switch turn
                self.turn = self.p2 if self.turn == self.p1 else self.p1
                emb = discord.Embed(title="🎮 MATCH EN COURS", description=f"🔴 {self.p1.mention} vs 🟡 {self.p2.mention}\n\n{self.get_board_str()}", color=0x3498db)
                emb.set_footer(text=f"Tour de : {self.turn.display_name}")
                await i.response.edit_message(embed=emb, view=self)

        view = C4View(self, interaction.user, mise)
        await interaction.response.send_message(embed=embed, view=view)
